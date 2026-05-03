import streamlit as st
from collections import defaultdict
from models.loan_file import LoanFile


class ReviewView:
    def __init__(self, loan_file: LoanFile):
        self.lf = loan_file

    def render(self):
        st.title("File Completeness Review")
        st.caption(
            "Step 3 — Review what's been collected, identify missing items, "
            "and address any documents flagged for review."
        )

        self._render_summary_metrics()
        st.divider()

        # Show items needing review first (highest priority)
        needs_review = [s for s in self.lf.stip_list if s.status == "needs_review"]
        if needs_review:
            self._render_needs_review(needs_review)
            st.divider()

        # Show categorized breakdown
        self._render_by_category()
        st.divider()

        # Show missing items
        missing = [s for s in self.lf.stip_list if s.status == "missing"]
        if missing:
            self._render_missing_items(missing)
            st.divider()

        # Show received items
        received = [s for s in self.lf.stip_list if s.status == "received"]
        if received:
            self._render_received_items(received)
            st.divider()

        self._render_actions()

    def _render_summary_metrics(self):
        """Show high-level file completeness metrics"""
        received_count = sum(1 for s in self.lf.stip_list if s.status == "received")
        needs_review_count = sum(1 for s in self.lf.stip_list if s.status == "needs_review")
        missing_count = sum(1 for s in self.lf.stip_list if s.status == "missing")
        total = len(self.lf.stip_list)
        pct = int(100 * received_count / total) if total else 0

        st.subheader("File Status Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Overall Progress", f"{pct}%", help="Based on received documents only")

        with col2:
            st.metric("Received", f"{received_count}/{total}",
                     delta="Ready for submission" if received_count == total else None,
                     delta_color="normal")

        with col3:
            color = "🟡" if needs_review_count > 0 else "🟢"
            st.metric("Needs Review", f"{color} {needs_review_count}",
                     help="Low confidence matches requiring processor attention")

        with col4:
            color = "🔴" if missing_count > 0 else "🟢"
            st.metric("Still Missing", f"{color} {missing_count}",
                     help="Documents not yet uploaded")

        # Overall status message
        if received_count == total:
            st.success("🎉 **All required documents received!** File is ready for next stage.")
        elif missing_count == 0 and needs_review_count > 0:
            st.warning(f"⚠️ **All documents uploaded**, but {needs_review_count} item(s) need processor review before proceeding.")
        else:
            st.info(f"📋 **File is {pct}% complete.** {missing_count} document(s) still needed from borrower.")

    def _render_needs_review(self, needs_review):
        """Highlight items flagged for review"""
        st.subheader(f"⚠️ Items Requiring Review ({len(needs_review)})")
        st.caption(
            "These documents were uploaded but matched with low confidence. "
            "Please verify they satisfy the requirement or request a replacement."
        )

        for stip in needs_review:
            with st.expander(f"⚠️ {stip.name}", expanded=True):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Category:** {stip.category}")
                    if stip.notes:
                        st.markdown(f"**Requirements:** {stip.notes}")
                    if stip.doc_label:
                        st.markdown(f"**Uploaded as:** {stip.doc_label}")

                with col2:
                    st.warning("Low Confidence Match")
                    if st.button("View in Documents", key=f"view_review_{stip.name}"):
                        self.lf.advance_to("documents")
                        st.rerun()

                # Show extraction data if available
                if stip.extraction:
                    st.divider()
                    st.markdown("**Extracted data:**")
                    self._render_extraction_summary(stip.extraction)

    def _render_by_category(self):
        """Show breakdown by document category"""
        st.subheader("Documents by Category")

        # Group stips by category
        by_category = defaultdict(list)
        for stip in self.lf.stip_list:
            by_category[stip.category].append(stip)

        # Calculate category stats
        category_stats = {}
        for category, stips in by_category.items():
            received = sum(1 for s in stips if s.status == "received")
            needs_review = sum(1 for s in stips if s.status == "needs_review")
            missing = sum(1 for s in stips if s.status == "missing")
            total = len(stips)
            category_stats[category] = {
                "received": received,
                "needs_review": needs_review,
                "missing": missing,
                "total": total,
                "pct": int(100 * received / total) if total else 0
            }

        # Display as columns
        categories = sorted(by_category.keys())
        cols = st.columns(min(len(categories), 3))

        for i, category in enumerate(categories):
            stats = category_stats[category]
            with cols[i % 3]:
                # Determine status color
                if stats["received"] == stats["total"]:
                    status = "🟢 Complete"
                elif stats["missing"] == stats["total"]:
                    status = "🔴 Not Started"
                else:
                    status = f"🟡 {stats['pct']}%"

                st.markdown(f"**{category.title()}**")
                st.markdown(f"Status: {status}")
                st.markdown(f"✅ {stats['received']} | ⚠️ {stats['needs_review']} | ◯ {stats['missing']}")

                # Show list of items in this category
                with st.expander(f"View {stats['total']} items"):
                    for stip in by_category[category]:
                        icon = "✅" if stip.status == "received" else "⚠️" if stip.status == "needs_review" else "◯"
                        st.markdown(f"{icon} {stip.name}")

    def _render_missing_items(self, missing):
        """Show all missing documents"""
        st.subheader(f"📋 Missing Documents ({len(missing)})")
        st.caption("These documents still need to be uploaded by the borrower.")

        # Group by category for better organization
        by_category = defaultdict(list)
        for stip in missing:
            by_category[stip.category].append(stip)

        for category in sorted(by_category.keys()):
            with st.expander(f"{category.title()} ({len(by_category[category])} items)", expanded=False):
                for stip in by_category[category]:
                    st.markdown(f"**◯ {stip.name}**")
                    if stip.notes:
                        st.caption(f"Requirements: {stip.notes}")
                    if stip.accepted_years:
                        st.caption(f"Accepted years: {', '.join(map(str, stip.accepted_years))}")
                    st.divider()

    def _render_received_items(self, received):
        """Show all successfully received documents"""
        with st.expander(f"✅ Received Documents ({len(received)})", expanded=False):
            st.caption("These documents have been successfully collected and matched.")

            # Group by category
            by_category = defaultdict(list)
            for stip in received:
                by_category[stip.category].append(stip)

            for category in sorted(by_category.keys()):
                st.markdown(f"**{category.title()}**")
                for stip in by_category[category]:
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(f"✅ {stip.name}")
                        if stip.doc_label:
                            st.caption(f"Matched from: {stip.doc_label}")
                    with cols[1]:
                        if stip.extraction:
                            if st.button("View Data", key=f"view_received_{stip.name}"):
                                st.session_state[f"show_extraction_{stip.name}"] = True
                                st.rerun()

                    # Show extraction data if requested
                    if st.session_state.get(f"show_extraction_{stip.name}", False):
                        self._render_extraction_summary(stip.extraction)
                        if st.button("Hide Data", key=f"hide_received_{stip.name}"):
                            st.session_state[f"show_extraction_{stip.name}"] = False
                            st.rerun()

                    st.divider()

    def _render_extraction_summary(self, extraction: dict):
        """Render a compact summary of extraction data"""
        if not extraction:
            st.caption("No extraction data available")
            return

        # Handle different extraction types
        if "pay_date" in extraction or "pay_period" in extraction:
            # Pay stub
            pay_period = extraction.get("pay_period", {})
            earnings = extraction.get("earnings", {})
            st.markdown(f"- Pay Date: {pay_period.get('pay_date', 'N/A')}")
            st.markdown(f"- Gross Pay: ${earnings.get('gross_pay_current_period', 0):,.2f}")
        elif "summary" in extraction:
            # Generic extraction
            st.markdown(f"- {extraction.get('summary', 'N/A')}")
        else:
            # Show key fields
            for key, value in list(extraction.items())[:3]:
                if isinstance(value, dict):
                    continue
                st.markdown(f"- {key}: {value}")

    def _render_actions(self):
        """Show action buttons for next steps"""
        received_count = sum(1 for s in self.lf.stip_list if s.status == "received")
        needs_review_count = sum(1 for s in self.lf.stip_list if s.status == "needs_review")
        missing_count = sum(1 for s in self.lf.stip_list if s.status == "missing")
        total = len(self.lf.stip_list)

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("← Back to Documents", use_container_width=True):
                self.lf.advance_to("documents")
                st.rerun()

        with col2:
            # Only allow follow-up if there are missing items
            if missing_count > 0:
                if st.button("Generate Follow-up Message →", type="primary", use_container_width=True):
                    self.lf.advance_to("followup")
                    st.rerun()
            else:
                st.button("Generate Follow-up Message", disabled=True,
                         help="No missing documents to follow up on", use_container_width=True)

        with col3:
            # Allow skipping to scrub if all docs received (even if some need review)
            if received_count == total:
                if st.button("Skip to Pre-Submission Scrub →", use_container_width=True):
                    self.lf.advance_to("scrub")
                    st.rerun()
            elif needs_review_count == 0 and missing_count == 0:
                if st.button("Skip to Pre-Submission Scrub →", use_container_width=True):
                    self.lf.advance_to("scrub")
                    st.rerun()
