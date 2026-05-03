import streamlit as st
from models.borrower import Borrower
from models.loan_file import LoanFile
from services.stip_generator import StipListGenerator


class IntakeView:
    def __init__(self, loan_file: LoanFile, stip_generator: StipListGenerator):
        self.lf = loan_file
        self.stip_generator = stip_generator

    def render(self):
        st.title("New Loan Application")
        st.caption("Step 1 — Capture borrower info and generate the stipulation list")

        borrower = self._render_form()

        st.divider()
        if st.button("Create Loan File & Generate Stip List", type="primary"):
            with st.spinner("Generating required document list based on borrower profile..."):
                try:
                    stips = self.stip_generator.generate(borrower)
                    self.lf.borrower = borrower
                    self.lf.stip_list = stips
                    self.lf.advance_to("documents")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't generate stip list: {e}")

    def _render_form(self) -> Borrower:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Borrower full name", value="John Smith")
            loan_purpose = st.selectbox(
                "Loan purpose",
                ["purchase", "refinance", "cash-out refinance"],
            )
            loan_amount = st.number_input(
                "Loan amount ($)",
                min_value=50000, max_value=3000000, value=400000, step=5000,
            )
            property_address = st.text_input(
                "Subject property address",
                value="123 Main St, Philadelphia, PA",
            )
        with col2:
            employment_type = st.selectbox(
                "Employment type",
                ["W-2 employee", "self-employed", "1099 contractor", "retired"],
            )
            employer = st.text_input("Employer (if applicable)", value="Acme Corp")
            annual_income = st.number_input(
                "Stated annual income ($)",
                min_value=0, max_value=2000000, value=85000, step=1000,
            )
            first_time_buyer = st.checkbox("First-time homebuyer", value=False)

        return Borrower(
            name=name,
            loan_purpose=loan_purpose,
            loan_amount=loan_amount,
            property_address=property_address,
            employment_type=employment_type,
            employer=employer,
            annual_income=annual_income,
            first_time_buyer=first_time_buyer,
        )