import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from models.loan_file import PendingDoc, RejectedDoc


logger = logging.getLogger(__name__)


class InboxSeeder:
    """Seeds the loan file inbox with sample documents from the sample_docs directory"""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent / "sample_docs"

    def seed(self, loan_file):
        """
        Populate loan_file with sample documents from sample_docs/ directories.
        Only seeds if pending_docs is empty (to avoid re-seeding on navigation).

        Returns True if seeding was performed, False if skipped.
        """
        if loan_file.pending_docs:
            logger.info("Inbox already seeded, skipping")
            return False

        # Load pending docs
        pending_dir = self.base_dir / "pending"
        pending_docs = self._load_docs_from_dir(pending_dir, hours_ago=10)
        loan_file.pending_docs.extend(pending_docs)

        # Load reserved docs (for simulate button)
        reserved_dir = self.base_dir / "reserved"
        reserved_docs = self._load_docs_from_dir(reserved_dir, hours_ago=2)
        loan_file.reserved_docs.extend(reserved_docs)

        # Load rejected docs
        rejected_dir = self.base_dir / "rejected"
        rejected_docs = self._load_rejected_docs(rejected_dir)
        loan_file.rejected_docs.extend(rejected_docs)

        logger.info(
            f"Seeded inbox: {len(pending_docs)} pending, "
            f"{len(reserved_docs)} reserved, {len(rejected_docs)} rejected"
        )

        return True

    def _load_docs_from_dir(self, directory: Path, hours_ago: int = 10):
        """Load all documents from a directory as PendingDoc objects"""
        docs = []

        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return docs

        for file_path in directory.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    with open(file_path, 'rb') as f:
                        file_bytes = f.read()

                    # Determine media type from extension
                    media_type = self._get_media_type(file_path.suffix)

                    # Set received_at to simulate docs arriving earlier
                    received_at = datetime.now() - timedelta(hours=hours_ago)

                    doc = PendingDoc(
                        filename=file_path.name,
                        file_bytes=file_bytes,
                        media_type=media_type,
                        received_at=received_at,
                    )
                    docs.append(doc)
                    logger.info(f"Loaded document: {file_path.name}")

                except Exception as e:
                    logger.error(f"Failed to load {file_path.name}: {e}")

        if not docs and directory.exists():
            logger.warning(f"No documents found in {directory}")

        return docs

    def _load_rejected_docs(self, directory: Path):
        """Load rejected documents (placeholder until real files are added)"""
        rejected_docs = []

        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return rejected_docs

        for file_path in directory.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Hardcoded rejection reason as specified
                rejected_at = datetime.now() - timedelta(days=2)

                doc = RejectedDoc(
                    filename=file_path.name,
                    doc_label="Pay stub dated 2026-03-17",
                    reason="Pay stub is 47 days old (uploaded 2026-03-17), exceeds Fannie Mae 30-day freshness window. Borrower notified to upload most recent stub.",
                    rejected_at=rejected_at,
                    borrower_notified=True,
                )
                rejected_docs.append(doc)
                logger.info(f"Loaded rejected document: {file_path.name}")

        return rejected_docs

    def _get_media_type(self, extension: str) -> str:
        """Map file extension to media type"""
        extension = extension.lower()
        if extension == '.pdf':
            return 'application/pdf'
        elif extension in ['.png']:
            return 'image/png'
        elif extension in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        else:
            return 'application/octet-stream'
