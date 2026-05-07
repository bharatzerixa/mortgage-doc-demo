"""Borrower-facing view router

Routes between borrower stages:
- intake: Borrower enters basic information
- welcome: Shows friendly document checklist
- upload: Upload documents with real-time feedback
- submitted: Confirmation and status summary
"""

import streamlit as st
from models.loan_file import LoanFile
from ui.borrower.intake import BorrowerIntakeView
from ui.borrower.welcome import WelcomeView
from ui.borrower.upload import UploadView
from ui.borrower.submitted import SubmittedView


class BorrowerView:
    """Main router for borrower-facing UI"""

    def __init__(self, loan_file: LoanFile, stip_generator, validator):
        self.lf = loan_file
        self.stip_generator = stip_generator
        self.validator = validator

    def render(self):
        """Route to the appropriate borrower screen based on borrower_stage"""
        # Add visual distinction for borrower portal - distinctive blue background
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] > .main {
            background: linear-gradient(to bottom, #bad1e3 0%, #d9e7f0 300px, #ffffff 600px);
        }
        [data-testid="stSidebar"] {
            background-color: #bad1e3 !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            background-color: #bad1e3 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Get or initialize borrower_stage
        if "borrower_stage" not in st.session_state:
            # Default stage depends on whether borrower exists
            if self.lf.borrower:
                st.session_state["borrower_stage"] = "welcome"
            else:
                st.session_state["borrower_stage"] = "intake"

        stage = st.session_state["borrower_stage"]

        # Route to appropriate view
        if stage == "intake":
            BorrowerIntakeView(self.lf, self.stip_generator).render()
        elif stage == "welcome":
            WelcomeView(self.lf).render()
        elif stage == "upload":
            UploadView(self.lf, self.validator).render()
        elif stage == "submitted":
            SubmittedView(self.lf).render()
        else:
            st.error(f"Unknown borrower stage: {stage}")
