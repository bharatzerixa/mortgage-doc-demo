import json
from datetime import date
from services.llm_service import LLMService
from models.borrower import Borrower
from models.stip import Stip


class PreSubmissionScrubber(LLMService):
    PROMPT_FILE = "scrub.txt"

    def scrub(self, borrower: Borrower, stip_list: list[Stip]) -> dict:
        """
        Perform pre-submission quality check on the loan file.
        Analyzes all extracted data to identify potential kickback issues.

        Returns a dict with:
        - overall_status: clear/caution/issues_found
        - risk_level: low/medium/high
        - summary: brief assessment
        - issues: list of identified problems
        - strengths: list of positive findings
        - readiness_score: 0-100
        - submission_recommendation: submit_now/address_minor_issues/address_critical_issues
        """
        template = self.load_prompt(self.PROMPT_FILE)

        # Format stips for the prompt
        stips_data = []
        for stip in stip_list:
            stip_info = {
                "name": stip.name,
                "category": stip.category,
                "status": stip.status,
                "doc_label": stip.doc_label,
                "notes": stip.notes,
            }
            if stip.accepted_years:
                stip_info["accepted_years"] = stip.accepted_years
            if stip.accepted_doc_age_days:
                stip_info["accepted_doc_age_days"] = stip.accepted_doc_age_days
            stips_data.append(stip_info)

        # Collect all extractions from received documents
        extractions_data = []
        for stip in stip_list:
            if stip.status in ("received", "needs_review") and stip.extraction:
                extractions_data.append({
                    "document": stip.doc_label or stip.name,
                    "stip_name": stip.name,
                    "category": stip.category,
                    "status": stip.status,
                    "extracted_data": stip.extraction,
                })

        prompt = template.format(
            today=date.today().isoformat(),
            borrower=json.dumps(borrower.to_dict(), indent=2),
            stips=json.dumps(stips_data, indent=2),
            extractions=json.dumps(extractions_data, indent=2),
        )

        raw = self.call(
            [{"role": "user", "content": prompt}],
            max_tokens=3000,
        )

        return self.parse_json_response(raw)
