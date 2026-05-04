import streamlit as st
from models.loan_file import LoanFile
from services.scrubber import PreSubmissionScrubber


class ScrubView:
    def __init__(self, loan_file: LoanFile, scrubber: PreSubmissionScrubber):
        self.lf = loan_file
        self.scrubber = scrubber

    def render(self):
        st.title("Pre-Submission Quality Check")
        st.caption(
            "Step 5 — AI-powered review of the assembled file to identify "
            "potential issues that could cause lender kickbacks."
        )

        # Check if we have any received documents
        received = [s for s in self.lf.stip_list if s.status in ("received", "needs_review")]
        if not received:
            st.warning("⚠️ **No documents have been received yet.** Upload and classify documents before running the scrub.")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("← Back to Review", use_container_width=True):
                    self.lf.advance_to("review")
                    st.rerun()
            with col2:
                if st.button("Go to Documents", use_container_width=True):
                    self.lf.advance_to("documents")
                    st.rerun()
            return

        # Run scrub or show cached result
        if self.lf.scrub_result is None or st.session_state.get("scrub_rerun", False):
            with st.spinner("Running quality check... Analyzing extracted data for potential issues..."):
                try:
                    result = self.scrubber.scrub(self.lf.borrower, self.lf.stip_list)
                    self.lf.scrub_result = result
                    st.session_state["scrub_rerun"] = False
                except Exception as e:
                    st.error(f"❌ Error running quality check: {str(e)}")
                    st.stop()

        result = self.lf.scrub_result

        # Show the scrub results
        self._render_summary(result)
        st.divider()

        issues = result.get("issues", [])
        if issues:
            self._render_issues(issues)
            st.divider()

        strengths = result.get("strengths", [])
        if strengths:
            self._render_strengths(strengths)
            st.divider()

        self._render_actions(result)

    def _render_summary(self, result: dict):
        """Render overall summary and readiness score"""
        st.subheader("Quality Check Summary")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            status = result.get("overall_status", "unknown")
            status_icon = "🟢" if status == "clear" else "🟡" if status == "caution" else "🔴"
            st.metric("Overall Status", f"{status_icon} {status.replace('_', ' ').title()}")

        with col2:
            risk = result.get("risk_level", "unknown")
            risk_icon = "🟢" if risk == "low" else "🟡" if risk == "medium" else "🔴"
            st.metric("Risk Level", f"{risk_icon} {risk.title()}")

        with col3:
            score = result.get("readiness_score", 0)
            score_color = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
            st.metric("Readiness Score", f"{score_color} {score}/100")

        with col4:
            issues_count = len(result.get("issues", []))
            st.metric("Issues Found", issues_count,
                     delta="None" if issues_count == 0 else None,
                     delta_color="normal" if issues_count == 0 else "inverse")

        # Summary text
        summary = result.get("summary", "Quality check complete.")
        if result.get("overall_status") == "clear":
            st.success(f"✅ **{summary}**")
        elif result.get("overall_status") == "caution":
            st.warning(f"⚠️ **{summary}**")
        else:
            st.error(f"🔴 **{summary}**")

        # Recommendation
        recommendation = result.get("submission_recommendation", "review_needed")
        if recommendation == "submit_now":
            st.info("💡 **Recommendation:** File is ready for submission.")
        elif recommendation == "address_minor_issues":
            st.info("💡 **Recommendation:** Address minor issues below, then proceed to submission.")
        else:
            st.info("💡 **Recommendation:** Critical issues must be resolved before submission.")

    def _render_issues(self, issues: list):
        """Render identified issues"""
        st.subheader(f"Issues Identified ({len(issues)})")

        # Group by severity
        critical = [i for i in issues if i.get("severity") == "critical"]
        moderate = [i for i in issues if i.get("severity") == "moderate"]
        minor = [i for i in issues if i.get("severity") == "minor"]

        if critical:
            st.markdown("### 🔴 Critical Issues")
            st.caption("These issues will likely cause the file to be kicked back. Must be resolved.")
            for issue in critical:
                self._render_issue_card(issue, "critical")

        if moderate:
            st.markdown("### 🟡 Moderate Issues")
            st.caption("These issues may cause questions or delays. Should be addressed.")
            for issue in moderate:
                self._render_issue_card(issue, "moderate")

        if minor:
            st.markdown("### 🟢 Minor Issues")
            st.caption("Best practices or documentation suggestions. Nice to fix but not dealbreakers.")
            for issue in minor:
                self._render_issue_card(issue, "minor")

    def _render_issue_card(self, issue: dict, severity: str):
        """Render a single issue card"""
        # Severity icon
        icon = "🔴" if severity == "critical" else "🟡" if severity == "moderate" else "🟢"

        with st.expander(f"{icon} {issue.get('title', 'Issue')}", expanded=(severity == "critical")):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Category:** {issue.get('category', 'other').title()}")
                st.markdown(f"**Description:** {issue.get('description', 'N/A')}")

                affected = issue.get("affected_documents", [])
                if affected:
                    st.markdown(f"**Affected documents:** {', '.join(affected)}")

            with col2:
                st.markdown(f"**Severity:** {severity.title()}")

            st.divider()
            st.markdown(f"**💡 Recommendation:** {issue.get('recommendation', 'Review and address.')}")

    def _render_strengths(self, strengths: list):
        """Render positive findings"""
        with st.expander(f"✅ File Strengths ({len(strengths)})", expanded=False):
            st.caption("Positive aspects of this file:")
            for strength in strengths:
                st.markdown(f"- {strength}")

    def _render_actions(self, result: dict):
        """Render action buttons"""
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.button("← Back to Review", use_container_width=True):
                self.lf.advance_to("review")
                st.rerun()

        with col2:
            if st.button("Back to Documents", use_container_width=True):
                self.lf.advance_to("documents")
                st.rerun()

        with col3:
            if st.button("🔄 Re-run Scrub", use_container_width=True):
                st.session_state["scrub_rerun"] = True
                st.rerun()

        with col4:
            # Only allow proceeding if no critical issues or user discretion
            critical_issues = [i for i in result.get("issues", []) if i.get("severity") == "critical"]

            if not critical_issues:
                if st.button("Continue to Final Review →", type="primary", use_container_width=True):
                    self.lf.advance_to("done")
                    st.rerun()
            else:
                st.button("Continue to Final Review",
                         disabled=True,
                         help=f"{len(critical_issues)} critical issue(s) should be resolved first",
                         use_container_width=True)
