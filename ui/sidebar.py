import streamlit as st
from models.loan_file import LoanFile


STAGES = [
    ("intake", "1. Borrower Intake"),
    ("documents", "2. Document Collection"),
    ("review", "3. Completeness Review"),
    ("followup", "4. Borrower Follow-up"),
    ("scrub", "5. Pre-Submission Scrub"),
    ("done", "6. Submission Ready"),
]


class Sidebar:
    def __init__(self, loan_file: LoanFile, on_reset):
        self.lf = loan_file
        self.on_reset = on_reset

    def render(self):
        st.sidebar.title("BHS Mortgage")
        st.sidebar.caption("Borrower Intake & Pre-Submission System — Prototype")
        st.sidebar.divider()

        self._render_stepper()
        st.sidebar.divider()
        self._render_borrower()
        self._render_stip_list()

        st.sidebar.divider()
        if st.sidebar.button("🔄 Reset demo"):
            self.on_reset()
            st.rerun()

    def _render_stepper(self):
        current_idx = next(
            (i for i, (k, _) in enumerate(STAGES) if k == self.lf.stage), 0
        )
        st.sidebar.subheader("Workflow")
        for i, (_, label) in enumerate(STAGES):
            if i < current_idx:
                st.sidebar.markdown(f"✅ {label}")
            elif i == current_idx:
                st.sidebar.markdown(f"**▶ {label}**")
            else:
                st.sidebar.markdown(f"◯ {label}")

    def _render_borrower(self):
        if not self.lf.borrower:
            return
        b = self.lf.borrower
        st.sidebar.subheader("Borrower")
        st.sidebar.markdown(f"**{b.name}**")
        st.sidebar.caption(
            f"{b.loan_purpose.title()} · ${b.loan_amount:,} · {b.employment_type}"
        )
        st.sidebar.divider()

    def _render_stip_list(self):
        if not self.lf.stip_list:
            return
        st.sidebar.subheader("Required Documents")
        for stip in self.lf.stip_list:
            if stip.status == "received":
                st.sidebar.markdown(f"✅ {stip.name}")
            elif stip.status == "needs_review":
                st.sidebar.markdown(f"⚠️ {stip.name}")
            else:
                st.sidebar.markdown(f"◯ {stip.name}")

        received, total, pct = self.lf.stip_progress()
        st.sidebar.progress(
            pct / 100, text=f"File {pct}% complete ({received}/{total})"
        )