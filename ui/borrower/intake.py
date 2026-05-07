"""Borrower intake view - friendly form to capture basic information"""

import streamlit as st
from models.loan_file import LoanFile, Borrower


class BorrowerIntakeView:
    """Initial intake form for borrowers entering the portal"""

    def __init__(self, loan_file: LoanFile, stip_generator):
        self.lf = loan_file
        self.stip_generator = stip_generator

    def render(self):
        """Render the borrower intake form"""
        st.markdown("# 👋 Welcome to BHS Mortgage")
        st.markdown("### Let's get started with your mortgage application")
        st.info("📋 This will only take a minute — we just need a few details to get your document list ready.")

        st.divider()

        # Check if borrower already exists (came from processor intake)
        if self.lf.borrower:
            self._render_existing_borrower()
        else:
            self._render_intake_form()

    def _render_existing_borrower(self):
        """Show existing borrower info and move to welcome screen"""
        b = self.lf.borrower

        st.success(f"✅ Welcome back, **{b.name}**!")

        purpose_display = "buying a home" if b.loan_purpose == "purchase" else "refinancing your mortgage"
        st.markdown(f"""
        We have your application ready:
        - **What you're doing:** {purpose_display}
        - **Loan amount:** ${b.loan_amount:,}
        """)

        st.divider()

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📄 See what documents we need →", type="primary", use_container_width=True):
                # Move to welcome stage
                st.session_state["borrower_stage"] = "welcome"
                st.rerun()

    def _render_intake_form(self):
        """Render the intake form for new borrowers"""
        st.markdown("""
        Please tell us a bit about yourself and what you're looking for.
        This helps us create a personalized list of documents we'll need from you.
        """)

        st.divider()

        with st.form("borrower_intake_form"):
            # Name
            name = st.text_input(
                "Your full name",
                value="John Smith",
                help="Please enter your legal name as it appears on your ID"
            )

            # Loan purpose
            loan_purpose = st.radio(
                "What are you looking to do?",
                options=["purchase", "refinance"],
                format_func=lambda x: "Buy a home" if x == "purchase" else "Refinance my current mortgage",
                horizontal=True,
            )

            # Loan amount
            loan_amount = st.number_input(
                "How much are you looking to borrow?",
                min_value=50000,
                max_value=2000000,
                value=400000,
                step=10000,
                format="%d",
                help="Enter the total loan amount you need"
            )

            # Employment type
            employment_type = st.radio(
                "How do you earn income?",
                options=["W-2 employee", "Self-employed", "Other"],
                horizontal=False,
            )

            # Submit button
            st.divider()
            submitted = st.form_submit_button("✨ Get my document list", type="primary", use_container_width=True)

            if submitted:
                # Validation
                if not name or not name.strip():
                    st.error("Please enter your name")
                    return

                # Create borrower with defaults for fields not collected in borrower intake
                borrower = Borrower(
                    name=name.strip(),
                    loan_purpose=loan_purpose,
                    loan_amount=loan_amount,
                    property_address="",  # Not collected in borrower intake
                    employment_type=employment_type,
                    employer="",  # Not collected in borrower intake
                    annual_income=0,  # Not collected in borrower intake
                    first_time_buyer=False,  # Not collected in borrower intake
                )

                self.lf.borrower = borrower

                # Generate stip list
                with st.spinner("Creating your document list..."):
                    stip_list = self.stip_generator.generate(borrower)
                    self.lf.stip_list = stip_list

                # Move to welcome stage
                st.session_state["borrower_stage"] = "welcome"
                st.rerun()
