from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from models.borrower import Borrower
from models.stip import Stip


STAGES = ["intake", "documents", "review", "followup", "scrub", "done"]


@dataclass
class UploadedDoc:
    filename: str
    classification: dict
    extraction: Optional[dict]
    stip_index: Optional[int]
    superseded_by: Optional[int] = None
    upload_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    removed: bool = False


@dataclass
class LoanFile:
    borrower: Optional[Borrower] = None
    stip_list: List[Stip] = field(default_factory=list)
    stage: str = "intake"
    messages: List[dict] = field(default_factory=list)
    scrub_result: Optional[dict] = None
    uploaded_docs: List[UploadedDoc] = field(default_factory=list)

    def advance_to(self, stage: str):
        if stage not in STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        self.stage = stage

    def stip_progress(self):
        received = sum(1 for s in self.stip_list if s.status == "received")
        total = len(self.stip_list)
        pct = int(100 * received / total) if total else 0
        return received, total, pct

    def mark_stip(self, index: int, status: str, extraction: dict, doc_label: str):
        if 0 <= index < len(self.stip_list):
            self.stip_list[index].status = status
            self.stip_list[index].extraction = extraction
            self.stip_list[index].doc_label = doc_label

    def replace_document(self, old_doc_index: int, new_doc: UploadedDoc) -> int:
        """
        Replace a document with a new version. Marks old doc as superseded,
        updates stip statuses, and returns the new document's index.
        """
        if not (0 <= old_doc_index < len(self.uploaded_docs)):
            raise ValueError(f"Invalid document index: {old_doc_index}")

        old_doc = self.uploaded_docs[old_doc_index]

        # Reset the stip that the old doc was matched to (if any)
        if old_doc.stip_index is not None and 0 <= old_doc.stip_index < len(self.stip_list):
            self.stip_list[old_doc.stip_index].status = "missing"
            self.stip_list[old_doc.stip_index].extraction = None
            self.stip_list[old_doc.stip_index].doc_label = None

        # Add new document to the list
        new_doc_index = len(self.uploaded_docs)
        self.uploaded_docs.append(new_doc)

        # Mark old document as superseded
        old_doc.superseded_by = new_doc_index

        return new_doc_index

    def remove_document(self, doc_index: int):
        """
        Remove a document from the active file. Marks it as removed and
        resets any stip it was matched to.
        """
        if not (0 <= doc_index < len(self.uploaded_docs)):
            raise ValueError(f"Invalid document index: {doc_index}")

        doc = self.uploaded_docs[doc_index]

        # Can't remove a document that's already superseded
        if doc.superseded_by is not None:
            raise ValueError("Cannot remove a superseded document")

        # Can't remove a document that's already removed
        if doc.removed:
            raise ValueError("Document is already removed")

        # Reset the stip that the doc was matched to (if any)
        if doc.stip_index is not None and 0 <= doc.stip_index < len(self.stip_list):
            self.stip_list[doc.stip_index].status = "missing"
            self.stip_list[doc.stip_index].extraction = None
            self.stip_list[doc.stip_index].doc_label = None

        # Mark document as removed
        doc.removed = True

    def get_active_docs(self) -> List[UploadedDoc]:
        """Return only non-superseded, non-removed documents"""
        return [doc for doc in self.uploaded_docs
                if doc.superseded_by is None and not doc.removed]

    def get_superseded_docs(self) -> List[UploadedDoc]:
        """Return only superseded documents"""
        return [doc for doc in self.uploaded_docs if doc.superseded_by is not None]

    def get_removed_docs(self) -> List[UploadedDoc]:
        """Return only removed documents"""
        return [doc for doc in self.uploaded_docs if doc.removed]