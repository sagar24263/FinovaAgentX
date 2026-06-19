from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class PdfParserResponse(BaseModel):
    isSuccess: bool
    data: Optional[Union[List[Any], Dict[str, Any]]] = None
    errors: Optional[list[str]] = None
