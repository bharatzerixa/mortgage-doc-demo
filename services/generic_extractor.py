from services.llm_service import LLMService


class GenericExtractor(LLMService):
    PROMPT_FILE = "generic_extraction.txt"

    def extract(self, file_bytes: bytes, media_type: str) -> dict:
        prompt = self.load_prompt(self.PROMPT_FILE)
        doc_block = self.build_doc_block(file_bytes, media_type)
        raw = self.call(
            [{
                "role": "user",
                "content": [doc_block, {"type": "text", "text": prompt}],
            }],
            max_tokens=1500,
        )
        return self.parse_json_response(raw)