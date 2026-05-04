import streamlit as st
from models.loan_file import LoanFile


class DoneView:
    def __init__(self, loan_file: LoanFile):
        self.lf = loan_file

    def render(self):
        st.title("🎉 File Ready for Submission")
        st.caption(
            "Step 6 — Your loan file has been assembled, reviewed, and is ready for submission to the lender."
        )

        st.divider()

        # Celebration message
        st.success(
            "**Congratulations!** This loan file has completed the pre-submission workflow "
            "and is ready to be sent to the wholesale lender."
        )

        st.divider()

        # File summary
        self._render_file_summary()
        st.divider()

        # Quality check summary (if available)
        if self.lf.scrub_result:
            self._render_scrub_summary()
            st.divider()

        # Document inventory
        self._render_document_inventory()
        st.divider()

        # Actions
        self._render_actions()

    def _render_file_summary(self):
        """Show high-level file summary"""
        st.subheader("File Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Borrower:** {self.lf.borrower.name}")
            st.markdown(f"**Loan Purpose:** {self.lf.borrower.loan_purpose.title()}")
            st.markdown(f"**Loan Amount:** ${self.lf.borrower.loan_amount:,}")
            st.markdown(f"**Property:** {self.lf.borrower.property_address}")

        with col2:
            st.markdown(f"**Employment Type:** {self.lf.borrower.employment_type}")
            st.markdown(f"**Employer:** {self.lf.borrower.employer}")
            st.markdown(f"**Annual Income:** ${self.lf.borrower.annual_income:,}")
            st.markdown(f"**First-time Buyer:** {'Yes' if self.lf.borrower.first_time_buyer else 'No'}")

        # Document completeness
        received, total, pct = self.lf.stip_progress()

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Documents Required", total)
        with col2:
            st.metric("Documents Received", received)
        with col3:
            st.metric("Completeness", f"{pct}%")

    def _render_scrub_summary(self):
        """Show quality check summary if available"""
        st.subheader("Quality Check Results")

        result = self.lf.scrub_result

        col1, col2, col3 = st.columns(3)

        with col1:
            status = result.get("overall_status", "unknown")
            status_icon = "🟢" if status == "clear" else "🟡" if status == "caution" else "🔴"
            st.metric("Overall Status", f"{status_icon} {status.replace('_', ' ').title()}")

        with col2:
            score = result.get("readiness_score", 0)
            score_icon = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
            st.metric("Readiness Score", f"{score_icon} {score}/100")

        with col3:
            issues_count = len(result.get("issues", []))
            st.metric("Issues Identified", issues_count)

        # Show summary
        summary = result.get("summary", "Quality check complete.")
        if result.get("overall_status") == "clear":
            st.success(f"✅ {summary}")
        elif result.get("overall_status") == "caution":
            st.warning(f"⚠️ {summary}")
        else:
            st.info(f"ℹ️ {summary}")

        # Show critical issues if any
        critical_issues = [i for i in result.get("issues", []) if i.get("severity") == "critical"]
        if critical_issues:
            with st.expander(f"⚠️ {len(critical_issues)} Critical Issue(s) Noted", expanded=True):
                for issue in critical_issues:
                    st.markdown(f"- **{issue.get('title')}**: {issue.get('description')}")
                st.caption("Note: File can still be submitted at processor's discretion.")

    def _render_document_inventory(self):
        """Show all received documents"""
        st.subheader("Document Inventory")

        received_stips = [s for s in self.lf.stip_list if s.status == "received"]
        needs_review_stips = [s for s in self.lf.stip_list if s.status == "needs_review"]

        # Group by category
        from collections import defaultdict
        by_category = defaultdict(list)

        for stip in received_stips + needs_review_stips:
            by_category[stip.category].append(stip)

        # Display as expandable sections
        for category in sorted(by_category.keys()):
            stips = by_category[category]
            with st.expander(f"📁 {category.title()} ({len(stips)} documents)", expanded=False):
                for stip in stips:
                    icon = "✅" if stip.status == "received" else "⚠️"
                    st.markdown(f"{icon} **{stip.name}**")
                    if stip.doc_label:
                        st.caption(f"   Matched from: {stip.doc_label}")

    def _render_actions(self):
        """Show submission and navigation actions"""
        st.subheader("Next Steps")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("← Back to Scrub Review", use_container_width=True):
                self.lf.advance_to("scrub")
                st.rerun()

        with col2:
            if st.button("📋 View File Summary", use_container_width=True):
                self.lf.advance_to("review")
                st.rerun()

        with col3:
            if st.button("📤 Submit to Lender", type="primary", use_container_width=True):
                st.session_state["submission_confirmed"] = True
                st.rerun()

        # Show submission confirmation
        if st.session_state.get("submission_confirmed", False):
            st.divider()
            st.success("✅ **File Submitted!** (Demo Mode)")
            st.info(
                "**In production, this would:**\n"
                "- Package all documents into a submission bundle\n"
                "- Send to your chosen wholesale lender via their portal/API\n"
                "- Generate confirmation email to borrower\n"
                "- Update loan status in your LOS (Loan Origination System)\n"
                "- Create audit trail entry with submission timestamp"
            )

            st.markdown("---")
            st.markdown("### 🎊 Thank You for Using BHS Mortgage Workflow Demo")
            st.markdown(
                "This demonstration showed how AI can streamline the mortgage loan file assembly process:\n\n"
                "1. ✅ **Intelligent document classification** (Stage 2)\n"
                "2. ✅ **Automated data extraction** (Stage 2)\n"
                "3. ✅ **File completeness tracking** (Stage 3)\n"
                "4. ✅ **Smart borrower follow-ups** (Stage 4)\n"
                "5. ✅ **Pre-submission quality checks** (Stage 5)\n"
                "6. ✅ **Ready for submission** (Stage 6)\n\n"
                "**Time saved per file:** 2-3 hours of manual work reduced to minutes."
            )

            if st.button("🔄 Start New File", use_container_width=True, type="primary"):
                # Reset session state for new file
                st.session_state.clear()
                st.rerun()
