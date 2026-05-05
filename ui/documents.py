import streamlit as st
from datetime import datetime
from models.loan_file import LoanFile, UploadedDoc, PendingDoc
from services.classifier import DocumentClassifier
from services.paystub_extractor import PayStubExtractor
from services.generic_extractor import GenericExtractor
from utils.dates import freshness_status
from utils.income import estimate_monthly_income


class DocumentsView:
    def __init__(self, loan_file: LoanFile,
                 classifier: DocumentClassifier,
                 paystub_extractor: PayStubExtractor,
                 generic_extractor: GenericExtractor):
        self.lf = loan_file
        self.classifier = classifier
        self.paystub = paystub_extractor
        self.generic = generic_extractor

    def render(self):
        st.title("Document Review")
        st.caption(
            "Step 2 — Review documents from the borrower portal. "
            "AI has pre-classified and extracted data for your review."
        )

        # Check if we're reviewing a specific document
        reviewing_doc_index = st.session_state.get("reviewing_doc_index")

        if reviewing_doc_index is not None and 0 <= reviewing_doc_index < len(self.lf.pending_docs):
            self._render_review_screen(reviewing_doc_index)
        else:
            # Main inbox view
            self._render_inbox()

            # Only show dividers if there's content in the sections
            if self.lf.rejected_docs:
                st.divider()
                self._render_rejected_section()

            if self.lf.get_active_docs():
                st.divider()
                self._render_processed_docs()

            st.divider()
            self._render_continue()

    def _render_inbox(self):
        """Section A: Pending review (the inbox)"""
        st.subheader(f"📥 Pending Review ({len(self.lf.pending_docs)})")

        if not self.lf.pending_docs:
            st.info("No documents pending review. All caught up!")
            self._render_manual_upload()
            return

        st.caption("Documents uploaded by borrower through the portal")

        for i, doc in enumerate(self.lf.pending_docs):
            self._render_inbox_item(i, doc)

        # Manual upload section at bottom
        self._render_manual_upload()

    def _render_inbox_item(self, index: int, doc: PendingDoc):
        """Render a single inbox item"""
        cols = st.columns([3, 2, 1])

        with cols[0]:
            st.markdown(f"**📄 {doc.filename}**")

        with cols[1]:
            # Format received time
            now = datetime.now()
            time_diff = now - doc.received_at
            if time_diff.days == 0:
                time_str = doc.received_at.strftime("Received %I:%M %p today")
            elif time_diff.days == 1:
                time_str = "Received yesterday"
            else:
                time_str = f"Received {time_diff.days} days ago"

            st.caption(time_str)

        with cols[2]:
            if st.button("Review", key=f"review_btn_{index}", type="primary"):
                st.session_state["reviewing_doc_index"] = index
                st.rerun()

        # Only add divider between items, not after the last one
        if index < len(self.lf.pending_docs) - 1:
            st.divider()

    def _render_rejected_section(self):
        """Section B: Rejected at upload"""
        if not self.lf.rejected_docs:
            return

        st.subheader(f"⚠️ Rejected at Upload ({len(self.lf.rejected_docs)})")
        st.caption("These documents failed automatic validation. Borrower has been notified to resubmit.")

        for doc in self.lf.rejected_docs:
            with st.container():
                st.markdown(
                    f'<div style="background-color: rgba(255, 193, 7, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107;">',
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**{doc.filename}** — {doc.doc_label}")
                    st.caption(f"**Reason:** {doc.reason}")

                with col2:
                    st.caption("🔔 Borrower notified")
                    st.caption("Awaiting resubmission")

                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()

    def _render_manual_upload(self):
        """Small manual upload affordance for exception cases"""
        with st.expander("➕ Add document manually", expanded=False):
            st.caption(
                "For documents received outside the portal (email, text, fax). "
                "These will flow through the same review process."
            )

            uploaded_file = st.file_uploader(
                "Upload document",
                type=["pdf", "png", "jpg", "jpeg"],
                key="manual_upload",
                label_visibility="collapsed",
            )

            if uploaded_file and st.button("Add to Inbox", key="add_manual"):
                # Add to pending_docs
                file_bytes = uploaded_file.read()
                doc = PendingDoc(
                    filename=uploaded_file.name,
                    file_bytes=file_bytes,
                    media_type=uploaded_file.type,
                    received_at=datetime.now(),
                )
                self.lf.pending_docs.append(doc)
                st.success(f"✅ {uploaded_file.name} added to inbox for review")
                st.rerun()

    def _render_review_screen(self, doc_index: int):
        """The review screen for a specific pending document"""
        doc = self.lf.pending_docs[doc_index]

        # Back button
        if st.button("← Back to Inbox"):
            st.session_state["reviewing_doc_index"] = None
            st.rerun()

        st.subheader(f"Reviewing: {doc.filename}")
        st.caption(f"Received: {doc.received_at.strftime('%Y-%m-%d %I:%M %p')}")

        st.divider()

        # Run classification and extraction if not already done
        if doc.classification is None:
            with st.spinner("Classifying and extracting data..."):
                try:
                    doc.classification = self.classifier.classify(
                        doc.file_bytes, doc.media_type, self.lf.borrower, self.lf.stip_list
                    )

                    doc_type = doc.classification.get("doc_type")
                    if doc_type == "pay_stub":
                        doc.extraction = self.paystub.extract(doc.file_bytes, doc.media_type)
                    else:
                        doc.extraction = self.generic.extract(doc.file_bytes, doc.media_type)

                except Exception as e:
                    st.error(f"❌ Error processing document: {str(e)}")
                    return

        # Display classification results
        self._render_classification_results(doc)

        st.divider()

        # Display extraction results
        if doc.extraction:
            st.subheader("Extracted Data")
            if doc.classification.get("doc_type") == "pay_stub":
                PayStubPanel(doc.extraction).render()
            else:
                GenericPanel(doc.extraction).render()

        st.divider()

        # Action buttons
        self._render_review_actions(doc_index, doc)

    def _render_classification_results(self, doc: PendingDoc):
        """Show AI's classification and reasoning"""
        cls = doc.classification

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Document Type:** {cls.get('doc_type_label', 'Unknown')}")
            st.markdown(f"**Confidence:** {cls.get('match_confidence', 'unknown').upper()}")

            if cls.get("match_reasoning"):
                with st.expander("💡 AI's Reasoning", expanded=False):
                    st.caption(cls.get("match_reasoning"))

        with col2:
            # Proposed stip match
            idx = cls.get("matches_stip_index")
            if idx is not None and 0 <= idx < len(self.lf.stip_list):
                stip = self.lf.stip_list[idx]
                confidence = cls.get("match_confidence", "unknown")

                if confidence in ("high", "medium"):
                    st.success(f"✅ Match: {stip.name}")
                else:
                    st.warning(f"⚠️ Low confidence: {stip.name}")
            else:
                st.warning("❓ No stip match found")

        # Borrower name mismatch warning
        if cls.get("borrower_name_matches") is False:
            st.error(
                f"⚠️ **Name Mismatch:** Document shows '{cls.get('borrower_name_on_doc')}', "
                f"but file is for '{self.lf.borrower.name}'"
            )

    def _render_review_actions(self, doc_index: int, doc: PendingDoc):
        """Action buttons for review screen"""
        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("✅ Accept & File Document", type="primary", use_container_width=True):
                self._accept_document(doc_index, doc)

        with col2:
            st.caption("Override and Reject buttons coming soon")

    def _accept_document(self, doc_index: int, doc: PendingDoc):
        """Accept the document and file it"""
        cls = doc.classification
        idx = cls.get("matches_stip_index")
        confidence = cls.get("match_confidence")

        # Create UploadedDoc
        uploaded_doc = UploadedDoc(
            filename=doc.filename,
            classification=cls,
            extraction=doc.extraction,
            stip_index=idx,
        )

        # Add to uploaded_docs
        self.lf.uploaded_docs.append(uploaded_doc)

        # Update stip status
        if idx is not None and 0 <= idx < len(self.lf.stip_list):
            if confidence in ("high", "medium"):
                new_status = "received"
            else:
                new_status = "needs_review"

            self.lf.mark_stip(
                index=idx,
                status=new_status,
                extraction=doc.extraction,
                doc_label=cls.get("doc_type_label", ""),
            )

        # Remove from pending
        self.lf.pending_docs.pop(doc_index)

        # Clear review state
        st.session_state["reviewing_doc_index"] = None

        st.success("✅ Document accepted and filed")
        st.rerun()

    def _render_processed_docs(self):
        """Section C: Documents in this file (already processed)"""
        active_docs = self.lf.get_active_docs()

        if not active_docs:
            return

        st.subheader(f"📁 Documents in File ({len(active_docs)})")
        st.caption("Documents that have been reviewed and filed")

        for i, doc in enumerate(self.lf.uploaded_docs):
            if doc.superseded_by is None and not doc.removed:
                self._render_processed_doc_card(doc, i)

    def _render_processed_doc_card(self, doc: UploadedDoc, doc_index: int):
        """Render a card for a processed document"""
        cls = doc.classification
        label = cls.get("doc_type_label", doc.filename)

        with st.expander(f"📄 {label}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**File:** `{doc.filename}`")
                st.markdown(f"**Type:** `{cls.get('doc_type')}`")
                st.markdown(f"**Confidence:** `{cls.get('match_confidence', 'unknown')}`")

            with col2:
                if doc.stip_index is not None:
                    stip = self.lf.stip_list[doc.stip_index]
                    st.success(f"Matched: {stip.name}")
                else:
                    st.warning("No stip match")

            if doc.extraction:
                st.divider()
                if cls.get("doc_type") == "pay_stub":
                    PayStubPanel(doc.extraction).render()
                else:
                    GenericPanel(doc.extraction).render()

    def _render_continue(self):
        """Navigation to next stage"""
        received, total, _ = self.lf.stip_progress()
        st.subheader("File Status")

        col_l, col_r = st.columns([3, 1])
        with col_l:
            st.markdown(
                f"**Progress:** {received} of {total} required documents received."
            )
            if self.lf.pending_docs:
                st.caption(f"⏳ {len(self.lf.pending_docs)} document(s) still pending review")

        with col_r:
            if st.button("Continue to Review →", type="primary"):
                self.lf.advance_to("review")
                st.rerun()


class PayStubPanel:
    def __init__(self, extraction: dict):
        self.extraction = extraction

    def render(self):
        employer = (self.extraction.get("employer") or {}).get("name") or "—"
        employee = (self.extraction.get("employee") or {}).get("name") or "—"
        pp = self.extraction.get("pay_period") or {}
        earnings = self.extraction.get("earnings") or {}

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Employer:** {employer}")
            st.markdown(f"**Employee:** {employee}")
        with c2:
            st.markdown(f"**Pay Date:** {pp.get('pay_date') or '—'}")
            st.markdown(f"**Frequency:** {pp.get('frequency') or '—'}")

        self._render_freshness(pp.get("pay_date"))
        self._render_income(earnings)
        self._render_quality_flags()

    def _render_freshness(self, pay_date):
        status, msg = freshness_status(pay_date)
        full_msg = f"Fannie Mae Freshness Check: {msg}"
        if status == "current":
            st.success(f"✓ {full_msg}")
        elif status == "borderline":
            st.warning(f"⚠ {full_msg}")
        elif status == "stale":
            st.error(f"⚠ {full_msg}")
        else:
            st.info(full_msg)

    def _render_income(self, earnings):
        m1, m2, m3 = st.columns(3)
        current = earnings.get("gross_pay_current_period")
        ytd = earnings.get("gross_pay_ytd")
        m1.metric("Gross (current)", f"${current:,.2f}" if current else "—")
        m2.metric("YTD Gross", f"${ytd:,.2f}" if ytd else "—")
        monthly, method = estimate_monthly_income(self.extraction)
        if monthly:
            m3.metric("Est. Monthly Gross",
                      f"${monthly:,.2f}", help=f"Method: {method}")
        else:
            m3.metric("Est. Monthly Gross", "—", help=method)

    def _render_quality_flags(self):
        issues = (self.extraction.get("data_quality") or {}).get("issues") or []
        if issues:
            st.warning("Data quality flags: " + "; ".join(issues))


class GenericPanel:
    def __init__(self, extraction: dict):
        self.extraction = extraction

    def render(self):
        st.markdown(f"**Summary:** {self.extraction.get('summary', '—')}")

        key_fields = self.extraction.get("key_fields") or {}
        if key_fields:
            st.markdown("**Key fields:**")
            for k, v in key_fields.items():
                st.markdown(f"- {k}: {v}")

        dates = self.extraction.get("dates") or {}
        amounts = self.extraction.get("amounts") or {}
        if dates or amounts:
            c1, c2 = st.columns(2)
            with c1:
                if dates:
                    st.markdown("**Dates:**")
                    for k, v in dates.items():
                        st.markdown(f"- {k}: {v}")
            with c2:
                if amounts:
                    st.markdown("**Amounts:**")
                    for k, v in amounts.items():
                        try:
                            st.markdown(f"- {k}: ${float(v):,.2f}")
                        except Exception:
                            st.markdown(f"- {k}: {v}")

        issues = (self.extraction.get("data_quality") or {}).get("issues") or []
        if issues:
            st.warning("Data quality flags: " + "; ".join(issues))
