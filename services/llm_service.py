import os
import json
import base64
from pathlib import Path
import anthropic


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class LLMService:
    """Base service. Holds the client + model + utilities. Subclass per concern."""

    DEFAULT_MODEL = "claude-opus-4-5"  # double-check current model in Anthropic docs

    def __init__(self, model: str = None):
        self.client = anthropic.Anthropic()
        self.model = model or self.DEFAULT_MODEL

    def load_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        return path.read_text()

    def parse_json_response(self, raw: str):
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rstrip("`").strip()
        return json.loads(cleaned)

    def build_doc_block(self, file_bytes: bytes, media_type: str):
        b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
        if media_type == "application/pdf":
            return {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            }
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }

    def call(self, messages, max_tokens: int = 2000):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.content[0].text