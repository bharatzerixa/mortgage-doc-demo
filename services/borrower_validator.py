"""Service for validating borrower-uploaded documents.

This orchestrates the validation logic to determine if a document should be:
- Accepted (added to pending_docs for processor review)
- Rejected (added to rejected_docs, borrower notified)
"""

from datetime import datetime, timedelta
from typing import Optional


class BorrowerValidator:
    """Validates documents uploaded by borrowers through the portal"""

    def __init__(self, classifier, paystub_extractor, generic_extractor):
        self.classifier = classifier
        self.paystub_extractor = paystub_extractor
        self.generic_extractor = generic_extractor

    def validate(self, file_bytes: bytes, media_type: str, borrower, stip_list) -> dict:
        """
        Validate an uploaded document and determine if it should be accepted or rejected.

        Validation order:
        1. Classify the document
        2. Check for name mismatch (reject if mismatch)
        3. Check confidence and stip match (reject if low confidence or no match)
        4. Extract data
        5. Check freshness for pay stubs (reject if stale)

        Returns:
            dict with keys:
                - accepted: bool
                - classification: dict
                - extraction: dict (may be None if classification failed early)
                - reason_code: str | None (e.g., "name_mismatch", "stale_paystub", "low_confidence", "no_stip_match")
                - matched_stip_index: int | None
        """
        result = {
            "accepted": False,
            "classification": None,
            "extraction": None,
            "reason_code": None,
            "matched_stip_index": None,
        }

        # Step 1: Classify
        try:
            classification = self.classifier.classify(
                file_bytes, media_type, borrower, stip_list
            )
            result["classification"] = classification
        except Exception as e:
            result["reason_code"] = "classification_failed"
            return result

        # Step 2: Check name mismatch
        if classification.get("borrower_name_matches") is False:
            result["reason_code"] = "name_mismatch"
            return result

        # Step 3: Check confidence and stip match
        confidence = classification.get("match_confidence")
        stip_index = classification.get("matches_stip_index")

        if confidence == "low":
            result["reason_code"] = "low_confidence"
            return result

        if stip_index is None:
            result["reason_code"] = "no_stip_match"
            return result

        result["matched_stip_index"] = stip_index

        # Step 4: Extract data
        try:
            doc_type = classification.get("doc_type")
            if doc_type == "pay_stub":
                extraction = self.paystub_extractor.extract(file_bytes, media_type)
            else:
                extraction = self.generic_extractor.extract(file_bytes, media_type)
            result["extraction"] = extraction
        except Exception as e:
            result["reason_code"] = "extraction_failed"
            return result

        # Step 5: Check freshness for pay stubs
        if doc_type == "pay_stub":
            pay_date_str = (extraction.get("pay_period") or {}).get("pay_date")
            if pay_date_str:
                if self._is_stale_paystub(pay_date_str):
                    result["reason_code"] = "stale_paystub"
                    return result

        # All checks passed
        result["accepted"] = True
        return result

    def _is_stale_paystub(self, pay_date_str: str) -> bool:
        """
        Check if a pay stub is stale (more than 30 days old).

        Args:
            pay_date_str: Date string in YYYY-MM-DD format

        Returns:
            True if pay stub is stale, False otherwise
        """
        try:
            pay_date = datetime.strptime(pay_date_str, "%Y-%m-%d")
            days_ago = (datetime.now() - pay_date).days
            return days_ago > 30
        except Exception:
            # If we can't parse the date, don't reject on this basis
            return False
