"""Utility for generating borrower-friendly success and error messages."""


def success_message(classification: dict, extraction: dict) -> str:
    """
    Generate a friendly success message based on document classification and extraction.

    Returns a plain-language message suitable for borrower display.
    """
    doc_type = classification.get("doc_type", "")

    if doc_type == "pay_stub":
        employer = (extraction.get("employer") or {}).get("name", "your employer")
        pay_date = (extraction.get("pay_period") or {}).get("pay_date", "")
        if pay_date:
            return f"Got it — this looks like a pay stub from {employer}, dated {pay_date}. We've added it to your file."
        else:
            return f"Got it — this looks like a pay stub from {employer}. We've added it to your file."

    elif doc_type == "w2":
        year = extraction.get("year") or classification.get("doc_year")
        if year:
            return f"Got it — this looks like a W-2 for tax year {year}. We've added it to your file."
        else:
            return "Got it — this looks like a W-2. We've added it to your file."

    elif doc_type == "bank_statement":
        return "Got it — this looks like a bank statement. We've added it to your file."

    elif doc_type == "photo_id":
        return "Got it — we've added your ID to your file."

    else:
        # Generic fallback
        return "Got it — we've added this to your file."


def error_message(classification: dict, extraction: dict, reason: str, borrower_name: str = "") -> str:
    """
    Generate a friendly error message based on the failure reason.

    Returns a plain-language message suitable for borrower display.
    """
    if reason == "stale_paystub":
        pay_date = (extraction.get("pay_period") or {}).get("pay_date", "[date]")
        return (
            f"This pay stub is from {pay_date}, which is over 30 days old. "
            "Lenders need pay stubs within the last 30 days. Could you upload your most recent one?"
        )

    elif reason == "name_mismatch":
        name_on_doc = classification.get("borrower_name_on_doc", "someone else")
        if borrower_name:
            return (
                f"This document looks like it's for {name_on_doc}, but we have your application as {borrower_name}. "
                "Did you mean to upload this for someone else? If not, please upload your own document."
            )
        else:
            return (
                f"This document looks like it's for {name_on_doc}. "
                "Please make sure you're uploading documents with your name on them."
            )

    elif reason == "low_confidence":
        return (
            "We couldn't quite tell what this document is. Could you try uploading a clearer photo, "
            "or check that you've selected the right file?"
        )

    elif reason == "no_stip_match":
        return (
            "This doesn't look like one of the documents we've asked for. "
            "If you think this should be in your file, please reach out to your loan officer."
        )

    else:
        # Generic failure
        return (
            "We weren't able to accept this document. Please try again with a clearer copy, "
            "or contact your loan officer if you need help."
        )
