"""Utility for translating processor vocabulary to borrower-friendly language."""


# Mapping from processor stip names to borrower-friendly names
STIP_NAME_MAPPING = {
    "Government-issued photo ID": "A photo of your driver's license or passport",
    "Signed Uniform Residential Loan Application (Form 1003)": "Your signed loan application",
    "Credit authorization form": "Permission for us to check your credit",
    "Most recent pay stub": "Your most recent pay stub",
    "Prior pay stub": "Second most recent pay stub",
    "Most recent W-2": "Your most recent W-2 from your employer",
    "Prior year W-2": "Your prior year W-2",
    "Bank statement (most recent month)": "Your most recent bank statement",
    "Bank statement (prior month)": "Your prior month's bank statement",
    "Purchase contract": "The signed purchase contract for the home",
    "Current mortgage statement": "Your current mortgage statement",
    "Homeowners insurance declarations": "Your current homeowners insurance declaration",
}


def borrower_friendly_name(stip_name: str) -> str:
    """
    Translate a processor-vocabulary stip name to borrower-friendly language.

    If no mapping exists, returns the original name unchanged.
    """
    return STIP_NAME_MAPPING.get(stip_name, stip_name)
