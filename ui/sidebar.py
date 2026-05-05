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

        # Only show divider if there's borrower/stip content
        if self.lf.borrower or self.lf.stip_list:
            st.sidebar.divider()
            self._render_borrower()
            self._render_stip_list()

        # Demo controls (only in documents stage)
        self._render_demo_controls()

        st.sidebar.divider()
        if st.sidebar.button("🔄 Reset demo"):
            self.on_reset()
            st.rerun()

    def _render_stepper(self):
        current_idx = next(
            (i for i, (k, _) in enumerate(STAGES) if k == self.lf.stage), 0
        )
        st.sidebar.subheader("Workflow")
        for i, (stage_key, label) in enumerate(STAGES):
            # Add inbox count for documents stage
            if stage_key == "documents" and len(self.lf.pending_docs) > 0:
                inbox_count = f" ({len(self.lf.pending_docs)} pending)"
            else:
                inbox_count = ""

            if i < current_idx:
                st.sidebar.markdown(f"✅ {label}{inbox_count}")
            elif i == current_idx:
                st.sidebar.markdown(f"**▶ {label}{inbox_count}**")
            else:
                st.sidebar.markdown(f"◯ {label}{inbox_count}")

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

    def _render_demo_controls(self):
        """Demo controls section for simulate borrower upload"""
        # Only show in documents stage
        if self.lf.stage != "documents":
            return

        st.sidebar.divider()
        st.sidebar.markdown("**─── Demo Controls ───**")

        has_reserved = len(self.lf.reserved_docs) > 0

        if has_reserved:
            if st.sidebar.button("📥 Simulate borrower upload", use_container_width=True):
                # Pop one doc from reserved_docs to pending_docs
                doc = self.lf.reserved_docs.pop(0)
                self.lf.pending_docs.append(doc)
                st.rerun()
        else:
            st.sidebar.button(
                "📥 Simulate borrower upload",
                disabled=True,
                use_container_width=True,
                help="No more reserved documents"
            )

        if has_reserved:
            st.sidebar.caption(f"({len(self.lf.reserved_docs)} demo doc(s) available)")