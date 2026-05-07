"""Borrower welcome view - show simple upload status"""

import streamlit as st
from models.loan_file import LoanFile
from utils.borrower_language import borrower_friendly_name


class WelcomeView:
    """Welcome screen showing upload status"""

    def __init__(self, loan_file: LoanFile):
        self.lf = loan_file

    def render(self):
        """Render the welcome screen"""
        st.markdown(f"# 📋 Welcome, {self.lf.borrower.name}!")

        st.info(
            "✅ Great news — we just need a few documents from you to move forward. "
            "You can upload them all at once, or come back later to add more."
        )

        st.divider()

        self._render_upload_status()

        st.divider()

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📤 Start uploading documents", type="primary", use_container_width=True):
                st.session_state["borrower_stage"] = "upload"
                st.rerun()

    def _render_upload_status(self):
        """Show simple upload status"""
        st.markdown("### 📊 Upload Status")

        # Count documents uploaded
        num_pending = len(self.lf.pending_docs)
        num_accepted = len([d for d in self.lf.uploaded_docs if not d.removed])
        total_uploaded = num_pending + num_accepted

        if total_uploaded > 0:
            st.success(f"✅ You've uploaded **{total_uploaded} document(s)** — your loan officer is reviewing them")
        else:
            st.caption("You haven't uploaded any documents yet. Click the button below to get started!")

        st.divider()

        # Show the list of required documents
        st.markdown("### 📄 Documents we need from you")

        if not self.lf.stip_list:
            st.info("No specific documents required yet.")
            return

        st.caption("Here's what your loan officer needs to review your application:")

        for i, stip in enumerate(self.lf.stip_list, 1):
            friendly_name = borrower_friendly_name(stip.name)
            st.markdown(f"**{i}.** {friendly_name}")
