"""Borrower upload view - drag-drop zone with real-time feedback"""

import streamlit as st
from datetime import datetime
from models.loan_file import LoanFile, PendingDoc, RejectedDoc
from utils.borrower_language import borrower_friendly_name
from utils.borrower_messages import success_message, error_message


class UploadView:
    """Document upload screen with real-time validation feedback"""

    def __init__(self, loan_file: LoanFile, validator):
        self.lf = loan_file
        self.validator = validator

    def render(self):
        """Render the upload screen"""
        st.markdown("# 📤 Upload your documents")

        st.info(
            "💡 **Tip:** You can upload multiple files at once. We'll check each one as you go "
            "and let you know right away if there are any issues."
        )

        st.divider()

        # Show document count
        self._render_progress()

        st.divider()

        # Upload zone
        self._render_upload_zone()

        st.divider()

        # Navigation buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Back"):
                st.session_state["borrower_stage"] = "welcome"
                st.rerun()
        with col3:
            if st.button("I'm done for now", type="primary"):
                st.session_state["borrower_stage"] = "submitted"
                st.rerun()

    def _render_progress(self):
        """Show how many documents have been uploaded"""
        st.markdown("### 📊 Your uploads")

        # Count documents uploaded
        num_pending = len(self.lf.pending_docs)
        num_accepted = len([d for d in self.lf.uploaded_docs if not d.removed])
        total_uploaded = num_pending + num_accepted

        if total_uploaded > 0:
            st.success(f"✅ **{total_uploaded} document(s) uploaded** — your loan officer will review them shortly")
        else:
            st.caption("No documents uploaded yet. Use the upload area below to get started.")

        st.divider()

        # Show document checklist with checkboxes
        st.markdown("### 📋 Document checklist")

        if not self.lf.stip_list:
            st.caption("No specific documents required yet.")
        else:
            # Count how many documents are matched to each stip index
            stip_match_count = {}

            # Check pending docs - these haven't been processor-reviewed yet
            for doc in self.lf.pending_docs:
                if doc.classification and doc.classification.get("matches_stip_index") is not None:
                    idx = doc.classification["matches_stip_index"]
                    stip_match_count[idx] = stip_match_count.get(idx, 0) + 1

            # Check uploaded docs - these have been processor-reviewed
            for doc in self.lf.uploaded_docs:
                if not doc.removed and doc.stip_index is not None:
                    idx = doc.stip_index
                    stip_match_count[idx] = stip_match_count.get(idx, 0) + 1

            # Track remaining documents to distribute (for spillover logic)
            remaining_counts = stip_match_count.copy()

            # Show required documents list with checkboxes
            for i, stip in enumerate(self.lf.stip_list, 1):
                friendly_name = borrower_friendly_name(stip.name)
                stip_idx = i - 1

                # Check if we have a document matching this requirement
                has_document = False

                # First, check if this specific stip has documents matched to it
                if remaining_counts.get(stip_idx, 0) > 0:
                    has_document = True
                    remaining_counts[stip_idx] -= 1

                # If not, check stip status (processor might have manually set it)
                elif stip.status in ["received", "needs_review"]:
                    has_document = True

                # Spillover logic: if we have extra documents for a similar stip, use them
                else:
                    # Check if there are similar stips with extra documents
                    stip_name_lower = stip.name.lower()

                    # Look for related stips with extra documents
                    for other_idx, count in remaining_counts.items():
                        if count > 0 and other_idx < len(self.lf.stip_list):
                            other_stip_name = self.lf.stip_list[other_idx].name.lower()

                            # Check if stips are related (same document type)
                            # e.g., "Most recent pay stub" and "Prior pay stub"
                            if ("pay stub" in stip_name_lower and "pay stub" in other_stip_name) or \
                               ("w-2" in stip_name_lower and "w-2" in other_stip_name) or \
                               ("bank statement" in stip_name_lower and "bank statement" in other_stip_name):
                                has_document = True
                                remaining_counts[other_idx] -= 1
                                break

                if has_document:
                    st.markdown(f"**{i}.** ✅ {friendly_name}")
                else:
                    st.markdown(f"**{i}.** ⬜ {friendly_name}")

    def _render_upload_zone(self):
        """Render the upload zone with real-time validation"""
        st.markdown("### 📁 Drop your files here")

        uploaded_files = st.file_uploader(
            "Drag and drop your files here, or click to browse",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="borrower_upload",
            label_visibility="visible",
            help="Accepted formats: PDF, PNG, JPG. You can upload multiple files at once.",
        )

        if uploaded_files:
            # Track which files have been processed to avoid infinite loop
            if "processed_files" not in st.session_state:
                st.session_state["processed_files"] = set()

            # Get current file identifiers (name + size as unique identifier)
            current_files = {(f.name, f.size) for f in uploaded_files}

            # Check if we need to process any new files
            new_files = [f for f in uploaded_files if (f.name, f.size) not in st.session_state["processed_files"]]

            if new_files:
                st.divider()
                st.markdown("### ⚙️ Checking your documents...")
                st.caption("Please wait while we verify each file...")

                for uploaded_file in new_files:
                    self._process_uploaded_file(uploaded_file)
                    # Mark this file as processed
                    st.session_state["processed_files"].add((uploaded_file.name, uploaded_file.size))

                # Rerun to show updated state
                st.rerun()
            else:
                # All files already processed, show completion message
                # Count accepted documents
                num_pending = len(self.lf.pending_docs)
                num_accepted = len([d for d in self.lf.uploaded_docs if not d.removed])
                total_accepted = num_pending + num_accepted
                num_rejected = len(self.lf.rejected_docs)

                if num_rejected > 0:
                    st.info(f"✅ All files have been processed. {total_accepted} accepted, {num_rejected} rejected. You can upload more files or click 'I'm done for now' below.")
                else:
                    st.success(f"✅ All {total_accepted} file(s) have been processed and accepted. You can upload more files or click 'I'm done for now' below.")

    def _process_uploaded_file(self, uploaded_file):
        """Process a single uploaded file with real-time feedback"""
        filename = uploaded_file.name

        with st.container():
            st.markdown(f"#### 📄 {filename}")

            with st.spinner("🔍 Checking your document..."):
                # Read file bytes
                file_bytes = uploaded_file.read()
                media_type = uploaded_file.type

                # Validate
                result = self.validator.validate(
                    file_bytes, media_type, self.lf.borrower, self.lf.stip_list
                )

                if result["accepted"]:
                    self._handle_accepted(filename, file_bytes, media_type, result)
                else:
                    self._handle_rejected(filename, result)

            st.markdown("---")

    def _handle_accepted(self, filename: str, file_bytes: bytes, media_type: str, result: dict):
        """Handle an accepted document"""
        classification = result["classification"]
        extraction = result["extraction"]

        # Create success message
        msg = success_message(classification, extraction)
        st.success(f"✅ **Success!** {msg}")

        # Add to pending_docs - processor will handle stip assignment
        doc = PendingDoc(
            filename=filename,
            file_bytes=file_bytes,
            media_type=media_type,
            received_at=datetime.now(),
        )
        # Pre-populate classification and extraction to avoid re-processing
        doc.classification = classification
        doc.extraction = extraction

        self.lf.pending_docs.append(doc)

    def _handle_rejected(self, filename: str, result: dict):
        """Handle a rejected document"""
        classification = result["classification"]
        extraction = result["extraction"]
        reason_code = result["reason_code"]

        # Generate error message
        msg = error_message(
            classification or {},
            extraction or {},
            reason_code,
            self.lf.borrower.name
        )
        st.error(f"❌ **We couldn't accept this file.** {msg}")

        # Add to rejected_docs
        doc_label = (classification or {}).get("doc_type_label", filename)
        rejected_doc = RejectedDoc(
            filename=filename,
            doc_label=doc_label,
            reason=msg,
            rejected_at=datetime.now(),
            borrower_notified=True,
        )
        self.lf.rejected_docs.append(rejected_doc)
