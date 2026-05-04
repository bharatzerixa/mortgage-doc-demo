import json
from datetime import date
from services.llm_service import LLMService
from models.borrower import Borrower
from models.stip import Stip


class FollowupGenerator(LLMService):
    PROMPT_FILE = "followup_generation.txt"

    def generate(self, borrower: Borrower, missing_stips: list[Stip]) -> dict:
        """
        Generate a follow-up message for the borrower requesting missing documents.

        Returns a dict with:
        - subject: email subject line
        - message: message body
        - channel_suggestion: email/sms/both
        - urgency: low/medium/high
        - reasoning: explanation of tone/urgency choice
        """
        template = self.load_prompt(self.PROMPT_FILE)

        # Format missing docs list for the prompt
        missing_docs_list = []
        for stip in missing_stips:
            doc_info = f"- {stip.name}"
            if stip.notes:
                doc_info += f" ({stip.notes})"
            if stip.accepted_years:
                doc_info += f" [years: {', '.join(map(str, stip.accepted_years))}]"
            if stip.accepted_doc_age_days:
                doc_info += f" [must be within {stip.accepted_doc_age_days} days]"
            missing_docs_list.append(doc_info)

        missing_docs_str = "\n".join(missing_docs_list)

        # Get first name from full name
        first_name = borrower.name.split()[0] if borrower.name else "there"

        prompt = template.format(
            today=date.today().isoformat(),
            borrower_name=first_name,
            missing_docs=missing_docs_str,
        )

        raw = self.call(
            [{"role": "user", "content": prompt}],
            max_tokens=1000,
        )

        return self.parse_json_response(raw)
