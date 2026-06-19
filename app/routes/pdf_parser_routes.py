import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.models.pdf_parser import PdfParserResponse
from app.services.pdf_parser_service import PdfParserService
from app.utils.logger import get_logger

logger = get_logger("pdf_parser_routes")

router = APIRouter()
pdf_parser_service = PdfParserService()

_PDF_MAGIC = b"%PDF"
_CHUNK_SIZE = 1024 * 1024  # 1 MB


@router.post("/parse-pdf", response_model=PdfParserResponse)
async def parse_pdf(
    file: UploadFile = File(...),
    nfo_name: str = Form(..., description="Fund/NFO name (e.g. 'HDFC Life Top 500 Smart Value 50 Fund')"),
    insurer_name: str = Form(..., description="Insurer name (e.g. 'HDFC Life')"),
    insurer_id: Optional[int] = Form(None, description="Optional insurer ID"),
):
    if file.content_type != "application/pdf":
        return PdfParserResponse(
            isSuccess=False,
            errors=["Only PDF files are accepted"],
        )

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            first_chunk = True
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                if first_chunk:
                    if not chunk.startswith(_PDF_MAGIC):
                        return PdfParserResponse(
                            isSuccess=False,
                            errors=["File does not appear to be a valid PDF"],
                        )
                    first_chunk = False
                tmp.write(chunk)

        source_pdf = os.path.basename(file.filename or os.path.basename(tmp_path))
        logger.info(f"PDF parsing '{source_pdf}' — nfo_name='{nfo_name}', insurer='{insurer_name}'")

        pages = await run_in_threadpool(pdf_parser_service.parse, tmp_path)
        chunks = await run_in_threadpool(pdf_parser_service.chunk, pages)
        entries = await run_in_threadpool(
            pdf_parser_service.finalize,
            chunks,
            pages,
            source_pdf,
            nfo_name,
            insurer_name,
            insurer_id,
        )

        if not entries:
            logger.warning(f"No content extracted from '{source_pdf}'")
            return PdfParserResponse(
                isSuccess=False,
                errors=["No extractable text found — document may be a scanned image"],
            )

        return PdfParserResponse(isSuccess=True, data=entries)

    except Exception as e:
        logger.error(f"PDF parsing failed for '{file.filename}': {e}", exc_info=True)
        return PdfParserResponse(isSuccess=False, errors=[str(e)])

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
