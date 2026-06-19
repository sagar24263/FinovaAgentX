"""
PDF Parser Service — sends PDF directly to Gemini for semantic chunking.
No local text extraction needed. Gemini sees the full visual layout natively.
"""

import base64
import json
import os
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from app.services.llm_service import get_llm_service
from app.utils.logger import get_logger

logger = get_logger("pdf_parser_service")

_MAX_OUTPUT_CHUNKS = 10

_LLM_CHUNK_PROMPT = """\
You are a semantic document chunking agent for a Retrieval-Augmented Generation (RAG) pipeline.

Analyze the attached PDF document and split it into semantically meaningful chunks.

Guidelines:
- Each chunk should represent one complete topic or concept.
- Split only when a genuinely new topic begins.
- Keep related paragraphs, tables, bullet lists, and examples together.
- Never split inside tables, lists, or examples.
- Aim for 5–10 chunks for a typical document.
- Preserve the original content exactly — do NOT summarize or rewrite.

For each chunk, provide:
1. "heading" — the section title if one exists, otherwise empty string
2. "content" — the full text content of that chunk (preserve original wording)
3. "keywords" — 5–10 high-quality searchable keywords for RAG retrieval

Output ONLY a JSON array. No explanation, no markdown fences.

Example format:
[
  {
    "heading": "Overview",
    "content": "Full text of the section...",
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }
]
"""


class PdfParserService:
    """Sends PDF to Gemini for chunking, then formats into KB entries."""

    def process(
        self,
        pdf_path: str,
        source_pdf: str,
        nfo_name: str,
        insurer_name: str,
        insurer_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline: PDF → Gemini → chunks → KB entries.

        Args:
            pdf_path: path to the temp PDF file
            source_pdf: original filename
            nfo_name: fund/product name (from user)
            insurer_name: insurer name (from user)
            insurer_id: optional insurer ID (from user)

        Returns:
            List of KB entry dicts ready for storage/indexing
        """
        logger.info(f"Processing PDF: {source_pdf} | nfo={nfo_name} | insurer={insurer_name}")

        # Send PDF to Gemini
        chunks = self._chunk_with_gemini(pdf_path)

        if not chunks:
            logger.warning(f"No chunks produced for {source_pdf}")
            return []

        # Cap at max chunks
        if len(chunks) > _MAX_OUTPUT_CHUNKS:
            chunks = chunks[:_MAX_OUTPUT_CHUNKS]

        # Format into KB entries
        total = len(chunks)
        entries = []
        for idx, chunk in enumerate(chunks, start=1):
            content = (chunk.get("content") or "").strip()
            if not content:
                continue

            entries.append({
                "term": f"{nfo_name} (deck section {idx}/{total})",
                "content": content,
                "keywords": self._normalize_keywords(chunk.get("keywords")),
                "product_type": "nfo",
                "metadata": {
                    "source_pdf": source_pdf,
                    "chunk_index": idx,
                    "chunk_total": total,
                    "nfo_name": nfo_name,
                    "section_heading": (chunk.get("heading") or "").strip(),
                    "extraction_strategy": "gemini_pdf",
                    "insurer_name": insurer_name,
                    "insurer_id": insurer_id,
                    "nfo_date": None,
                },
            })

        logger.info(f"Produced {len(entries)} KB entries for {source_pdf}")
        return entries

    def _chunk_with_gemini(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Send PDF directly to Gemini and get structured chunks back."""
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

            llm = get_llm_service().get_llm(
                temperature=0.0,
                max_tokens=8000,
            )

            message = HumanMessage(
                content=[
                    {"type": "text", "text": _LLM_CHUNK_PROMPT},
                    {
                        "type": "media",
                        "mime_type": "application/pdf",
                        "data": pdf_b64,
                    },
                ]
            )

            response = llm.invoke([message])

            # Extract text from response
            raw_content = response.content
            if isinstance(raw_content, list):
                raw_text = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in raw_content
                ).strip()
            else:
                raw_text = str(raw_content).strip()

            # Parse JSON array
            return self._parse_json_array(raw_text)

        except Exception as e:
            logger.error(f"Gemini PDF chunking failed: {e}", exc_info=True)
            return []

    def _parse_json_array(self, raw: str) -> List[Dict[str, Any]]:
        """Extract JSON array from LLM response."""
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting array substring
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start:end + 1])
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON array from Gemini response")
        return []

    def _normalize_keywords(self, raw_keywords: Any) -> List[str]:
        """Deduplicate and normalize keywords."""
        if not isinstance(raw_keywords, list):
            return []

        seen: set = set()
        keywords: List[str] = []
        for item in raw_keywords:
            if not isinstance(item, str):
                continue
            normalized = item.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                keywords.append(normalized)
        return keywords
