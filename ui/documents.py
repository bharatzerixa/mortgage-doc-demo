import streamlit as st
from models.loan_file import LoanFile, UploadedDoc
from services.classifier import DocumentClassifier
from services.paystub_extractor import PayStubExtractor
from services.generic_extractor import GenericExtractor
from utils.dates import freshness_status
from utils.income import estimate_monthly_income


# Custom CSS to make the drop zone visually obvious
DROP_ZONE_CSS = """
<style>
[data-testid="stFileUploader"] section {
    border: 2px dashed #4a90e2;
    border-radius: 12px;
    padding: 2rem 1rem;
    background-color: rgba(74, 144, 226, 0.04);
    transition: all 0.2s ease-in-out;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #2563eb;
    background-color: rgba(74, 144, 226, 0.08);
}
[data-testid="stFileUploader"] section > div:first-child {
    font-weight: 500;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: #4a90e2;
}
</style>
"""


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
        st.markdown(DROP_ZONE_CSS, unsafe_allow_html=True)

        st.title("Document Collection")
        st.caption(
            "Step 2 — Drag and drop borrower documents below. "
            "The system classifies each doc, extracts data, and updates the file."
        )

        self._render_uploader()
        self._render_batch_summary()
        self._render_uploaded_list()
        self._render_continue()

    def _render_uploader(self):
        # Reset uploader widget after each batch by changing its key
        uploader_key = f"uploader_{len(self.lf.uploaded_docs)}"
        uploaded_files = st.file_uploader(
            "Drag and drop files here, or click to browse",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key=uploader_key,
            label_visibility="visible",
        )
        if not uploaded_files:
            return

        st.caption(f"📎 {len(uploaded_files)} file(s) ready to process")

        if st.button(f"Process {len(uploaded_files)} Document(s)", type="primary"):
            self._process_batch(uploaded_files)

    def _process_batch(self, uploaded_files):
        progress_bar = st.progress(0.0, text="Starting...")
        results = []  # collect results to display after rerun would clobber them

        for i, uploaded in enumerate(uploaded_files):
            progress_bar.progress(
                i / len(uploaded_files),
                text=f"Processing {uploaded.name} ({i + 1} of {len(uploaded_files)})..."
            )
            file_bytes = uploaded.read()
            result = self._process_document(file_bytes, uploaded.type, uploaded.name)
            results.append((uploaded.name, result))

        progress_bar.progress(1.0, text="All documents processed.")

        # Stash the batch results so we can show a summary after rerun
        st.session_state["last_batch_results"] = results
        st.rerun()

    def _render_batch_summary(self):
        results = st.session_state.pop("last_batch_results", None)
        if not results:
            return
        st.divider()
        st.subheader("Last batch summary")
        for filename, r in results:
            if not r.get("ok"):
                st.error(f"❌ **{filename}** — error: {r.get('error')}")
                continue

            outcome = r["outcome"]
            if outcome == "received":
                st.success(
                    f"✅ **{filename}** → matched stip "
                    f"*{r['matched_stip_name']}* (confidence: {r['confidence']})"
                )
            elif outcome == "needs_review":
                st.warning(
                    f"⚠️ **{filename}** → matched stip *{r['matched_stip_name']}* "
                    f"but confidence was *{r['confidence']}*. Marked needs review."
                )
            else:
                st.warning(
                    f"❓ **{filename}** (detected as `{r['doc_type']}`) → "
                    f"no stip match. Reason: {r['reasoning']}"
                )
                
    def _process_document(self, file_bytes, media_type, filename):
        """Process a single document. Returns a result dict for diagnostics."""
        try:
            classification = self.classifier.classify(
                file_bytes, media_type, self.lf.borrower, self.lf.stip_list
            )

            doc_type = classification.get("doc_type")
            if doc_type == "pay_stub":
                extraction = self.paystub.extract(file_bytes, media_type)
            else:
                extraction = self.generic.extract(file_bytes, media_type)

            idx = classification.get("matches_stip_index")
            confidence = classification.get("match_confidence")
            outcome = "no_match"
            new_status = None

            if idx is not None and 0 <= idx < len(self.lf.stip_list):
                if confidence in ("high", "medium"):
                    new_status = "received"
                    outcome = "received"
                else:
                    new_status = "needs_review"
                    outcome = "needs_review"
                self.lf.mark_stip(
                    index=idx,
                    status=new_status,
                    extraction=extraction,
                    doc_label=classification.get("doc_type_label", ""),
                )

            self.lf.uploaded_docs.append(UploadedDoc(
                filename=filename,
                classification=classification,
                extraction=extraction,
                stip_index=idx,
            ))

            return {
                "ok": True,
                "outcome": outcome,
                "doc_type": doc_type,
                "matched_stip_index": idx,
                "matched_stip_name": (
                    self.lf.stip_list[idx].name
                    if idx is not None and 0 <= idx < len(self.lf.stip_list)
                    else None
                ),
                "confidence": confidence,
                "reasoning": classification.get("match_reasoning", ""),
            }

        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _render_uploaded_list(self):
        if not self.lf.uploaded_docs:
            return
        st.divider()

        # Show active documents
        active_docs = self.lf.get_active_docs()
        if active_docs:
            st.subheader("Documents in this file")
            for i, doc in enumerate(self.lf.uploaded_docs):
                if doc.superseded_by is None and not doc.removed:
                    self._render_doc_card(doc, i)

        # Show document history if there are superseded or removed docs
        superseded_docs = self.lf.get_superseded_docs()
        removed_docs = self.lf.get_removed_docs()
        history_count = len(superseded_docs) + len(removed_docs)

        if history_count > 0:
            with st.expander(f"📋 Document History ({history_count} items)", expanded=False):
                if superseded_docs:
                    st.markdown("**Replaced documents:**")
                    for i, doc in enumerate(self.lf.uploaded_docs):
                        if doc.superseded_by is not None:
                            self._render_doc_card(doc, i, is_superseded=True)

                if removed_docs:
                    if superseded_docs:
                        st.divider()
                    st.markdown("**Removed documents:**")
                    for i, doc in enumerate(self.lf.uploaded_docs):
                        if doc.removed:
                            self._render_doc_card(doc, i, is_removed=True)

    def _render_doc_card(self, doc: UploadedDoc, doc_index: int, is_superseded: bool = False, is_removed: bool = False):
        cls = doc.classification
        label = cls.get("doc_type_label", doc.filename)
        confidence = cls.get("match_confidence", "unknown")

        # Add visual indicator for superseded/removed docs
        if is_removed:
            label = f"🗑️ {label} (removed)"
        elif is_superseded:
            label = f"🗄️ {label} (replaced)"
        else:
            label = f"📄 {label}"

        with st.expander(label, expanded=False):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(f"**File:** `{doc.filename}`")
                st.markdown(f"**Type:** `{cls.get('doc_type')}`")
                st.markdown(f"**Match confidence:** `{confidence}`")
                if cls.get("match_reasoning"):
                    st.caption(cls.get("match_reasoning"))
                st.caption(f"Uploaded: {doc.upload_timestamp[:19].replace('T', ' ')}")

            with cols[1]:
                if doc.stip_index is not None:
                    stip = self.lf.stip_list[doc.stip_index]
                    st.success(f"Matched: {stip.name}")
                else:
                    st.warning("No stip match")

            if cls.get("borrower_name_matches") is False:
                st.error(
                    f"⚠ Borrower name mismatch: doc shows "
                    f"'{cls.get('borrower_name_on_doc')}', file is for "
                    f"'{self.lf.borrower.name}'"
                )

            if doc.extraction:
                st.divider()
                if cls.get("doc_type") == "pay_stub":
                    PayStubPanel(doc.extraction).render()
                else:
                    GenericPanel(doc.extraction).render()

            # Add replace and remove buttons for active documents only
            if not is_superseded and not is_removed:
                st.divider()
                self._render_document_actions(doc_index)

    def _render_document_actions(self, doc_index: int):
        """Render action buttons (replace and remove) for a document"""
        replace_key = f"replace_{doc_index}"
        remove_key = f"remove_{doc_index}"

        # Action buttons row
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 Replace", key=f"btn_{replace_key}", help="Upload a replacement for this document"):
                st.session_state[f"show_uploader_{replace_key}"] = True
                st.rerun()

        with col2:
            if st.button("🗑️ Remove", key=f"btn_{remove_key}", help="Remove this document from the file", type="secondary"):
                st.session_state[f"confirm_remove_{remove_key}"] = True
                st.rerun()

        # Show confirmation dialog for removal
        if st.session_state.get(f"confirm_remove_{remove_key}", False):
            st.warning("⚠️ **Are you sure you want to remove this document?**")
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("Yes, Remove", key=f"confirm_yes_{remove_key}", type="primary"):
                    self._process_removal(doc_index)
                    st.session_state[f"confirm_remove_{remove_key}"] = False
                    st.rerun()
            with col_b:
                if st.button("Cancel", key=f"confirm_no_{remove_key}"):
                    st.session_state[f"confirm_remove_{remove_key}"] = False
                    st.rerun()

        # Show file uploader if replace button was clicked
        if st.session_state.get(f"show_uploader_{replace_key}", False):
            st.markdown("**Upload replacement document:**")
            uploaded_file = st.file_uploader(
                "Choose replacement file",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"uploader_{replace_key}",
                label_visibility="collapsed",
            )

            col_a, col_b = st.columns([1, 1])
            with col_a:
                if uploaded_file and st.button("Process Replacement", key=f"process_{replace_key}", type="primary"):
                    with st.spinner(f"Processing replacement for {uploaded_file.name}..."):
                        self._process_replacement(doc_index, uploaded_file)
                        # Clear the uploader state
                        st.session_state[f"show_uploader_{replace_key}"] = False
                        st.rerun()

            with col_b:
                if st.button("Cancel", key=f"cancel_{replace_key}"):
                    st.session_state[f"show_uploader_{replace_key}"] = False
                    st.rerun()

    def _process_removal(self, doc_index: int):
        """Process document removal"""
        try:
            doc = self.lf.uploaded_docs[doc_index]
            doc_name = doc.filename

            # Remove the document
            self.lf.remove_document(doc_index)

            st.success(f"✅ Document '{doc_name}' removed successfully")

        except Exception as e:
            st.error(f"❌ Error removing document: {str(e)}")

    def _process_replacement(self, old_doc_index: int, uploaded_file):
        """Process a replacement document"""
        try:
            file_bytes = uploaded_file.read()

            # Process the new document
            classification = self.classifier.classify(
                file_bytes, uploaded_file.type, self.lf.borrower, self.lf.stip_list
            )

            doc_type = classification.get("doc_type")
            if doc_type == "pay_stub":
                extraction = self.paystub.extract(file_bytes, uploaded_file.type)
            else:
                extraction = self.generic.extract(file_bytes, uploaded_file.type)

            # Create new UploadedDoc
            new_doc = UploadedDoc(
                filename=uploaded_file.name,
                classification=classification,
                extraction=extraction,
                stip_index=classification.get("matches_stip_index"),
            )

            # Replace the document
            new_doc_index = self.lf.replace_document(old_doc_index, new_doc)

            # Update stip status for the new document
            idx = classification.get("matches_stip_index")
            confidence = classification.get("match_confidence")

            if idx is not None and 0 <= idx < len(self.lf.stip_list):
                if confidence in ("high", "medium"):
                    new_status = "received"
                else:
                    new_status = "needs_review"

                self.lf.mark_stip(
                    index=idx,
                    status=new_status,
                    extraction=extraction,
                    doc_label=classification.get("doc_type_label", ""),
                )

            st.success(f"✅ Document replaced successfully with {uploaded_file.name}")

        except Exception as e:
            st.error(f"❌ Error processing replacement: {str(e)}")

    def _render_continue(self):
        received, total, _ = self.lf.stip_progress()
        st.divider()
        col_l, col_r = st.columns([3, 1])
        with col_l:
            st.markdown(
                f"**File status:** {received} of {total} required documents received."
            )
        with col_r:
            if st.button("Continue to Review →"):
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