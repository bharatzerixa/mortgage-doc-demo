"""Borrower submitted view - confirmation and status summary"""

import streamlit as st
from models.loan_file import LoanFile


class SubmittedView:
    """Confirmation screen after borrower submits documents"""

    def __init__(self, loan_file: LoanFile):
        self.lf = loan_file

    def render(self):
        """Render the submitted confirmation screen"""
        st.markdown("# ✅ Thanks for uploading your documents!")

        # Generate dynamic message based on documents uploaded
        self._render_status_message()

        st.divider()

        # Show what we received
        self._render_received_summary()

        st.divider()

        # Action buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📤 Upload more documents", use_container_width=True, type="secondary"):
                st.session_state["borrower_stage"] = "upload"
                st.rerun()

        st.divider()

        st.info("💬 **What happens next?** Your loan officer will review your documents and reach out if we need anything else. You'll hear from us soon!")

    def _render_status_message(self):
        """Generate dynamic status message based on documents uploaded"""
        # Count documents uploaded
        num_pending = len(self.lf.pending_docs)
        num_accepted = len([d for d in self.lf.uploaded_docs if not d.removed])
        total_uploaded = num_pending + num_accepted

        if total_uploaded > 0:
            st.success(
                f"🎉 **You've uploaded {total_uploaded} document(s)!** "
                "Your loan officer will review them and reach out if we need anything else."
            )
        else:
            st.warning(
                "**We haven't received any documents yet.** "
                "Please upload your documents so we can move forward with your application."
            )

    def _render_received_summary(self):
        """Show summary of uploaded documents"""
        st.markdown("### 📊 Your document summary")

        # Count documents uploaded
        num_pending = len(self.lf.pending_docs)
        num_accepted = len([d for d in self.lf.uploaded_docs if not d.removed])
        total_uploaded = num_pending + num_accepted

        if total_uploaded > 0:
            st.info(
                f"✅ **{total_uploaded} document(s) uploaded** — "
                "your loan officer is reviewing them and will reach out if anything else is needed."
            )
        else:
            st.caption("No documents uploaded yet.")
