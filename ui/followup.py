import streamlit as st
from models.loan_file import LoanFile
from services.followup_generator import FollowupGenerator


class FollowupView:
    def __init__(self, loan_file: LoanFile, followup_generator: FollowupGenerator):
        self.lf = loan_file
        self.generator = followup_generator

    def render(self):
        st.title("Borrower Follow-up")
        st.caption(
            "Step 4 — Generate a professional follow-up message requesting missing documents from the borrower."
        )

        # Get missing stips
        missing_stips = [s for s in self.lf.stip_list if s.status == "missing"]

        if not missing_stips:
            st.success("🎉 **All documents received!** No follow-up needed.")
            st.info("You can skip to the Pre-Submission Scrub stage.")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("← Back to Review", use_container_width=True):
                    self.lf.advance_to("review")
                    st.rerun()
            with col2:
                if st.button("Skip to Pre-Submission Scrub →", type="primary", use_container_width=True):
                    self.lf.advance_to("scrub")
                    st.rerun()
            return

        # Show what's missing
        st.subheader(f"Missing Documents ({len(missing_stips)})")
        with st.expander("View missing items", expanded=False):
            for stip in missing_stips:
                st.markdown(f"- **{stip.name}**")
                if stip.notes:
                    st.caption(f"  {stip.notes}")

        st.divider()

        # Generate or show cached message
        if "followup_message" not in st.session_state or st.session_state.get("followup_regenerate", False):
            with st.spinner("Generating follow-up message..."):
                try:
                    result = self.generator.generate(self.lf.borrower, missing_stips)
                    st.session_state["followup_message"] = result
                    st.session_state["followup_regenerate"] = False
                except Exception as e:
                    st.error(f"❌ Error generating message: {str(e)}")
                    st.stop()

        message_data = st.session_state["followup_message"]

        # Show the generated message
        self._render_message(message_data, missing_stips)

        st.divider()
        self._render_actions()

    def _render_message(self, message_data: dict, missing_stips: list):
        """Render the generated follow-up message"""
        st.subheader("Generated Follow-up Message")

        # Show metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            channel = message_data.get("channel_suggestion", "email")
            icon = "📧" if channel == "email" else "📱" if channel == "sms" else "📧📱"
            st.metric("Suggested Channel", f"{icon} {channel.title()}")

        with col2:
            urgency = message_data.get("urgency", "medium")
            color = "🔴" if urgency == "high" else "🟡" if urgency == "medium" else "🟢"
            st.metric("Urgency", f"{color} {urgency.title()}")

        with col3:
            st.metric("Missing Items", len(missing_stips))

        # Show reasoning
        if message_data.get("reasoning"):
            with st.expander("💡 Why this tone/urgency?", expanded=False):
                st.caption(message_data["reasoning"])

        st.divider()

        # Email preview
        st.markdown("### Email Preview")

        # Subject line
        st.text_input(
            "Subject",
            value=message_data.get("subject", "Documents Needed"),
            key="followup_subject",
            disabled=False,
        )

        # Message body
        message_text = message_data.get("message", "")
        st.text_area(
            "Message",
            value=message_text,
            height=300,
            key="followup_body",
            help="You can edit the message before sending",
        )

        # Action buttons for the message
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("📋 Copy to Clipboard", use_container_width=True):
                # Note: Actual clipboard copy requires JavaScript, this is a demo placeholder
                st.success("Message copied! (Demo mode)")

        with col2:
            if st.button("🔄 Regenerate", use_container_width=True):
                st.session_state["followup_regenerate"] = True
                st.rerun()

        with col3:
            if st.button("📧 Approve & Send", type="primary", use_container_width=True):
                # Mock sending - in production would integrate with email/SMS service
                st.session_state["followup_sent"] = True
                st.success("✅ Follow-up sent! (Demo mode - no actual email sent)")

    def _render_actions(self):
        """Show navigation actions"""
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("← Back to Review", use_container_width=True):
                self.lf.advance_to("review")
                st.rerun()

        with col2:
            if st.button("Back to Documents", use_container_width=True):
                self.lf.advance_to("documents")
                st.rerun()

        with col3:
            # Allow proceeding even if follow-up not sent (processor discretion)
            if st.button("Continue to Scrub →", use_container_width=True):
                self.lf.advance_to("scrub")
                st.rerun()
