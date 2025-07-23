from pydantic import BaseModel
from typing import List, Optional, Any


class CreateIndex(BaseModel):
    index_name: str
    override: bool
    embedding_size: int
    model_name: str  # alibaba_modernbert or answerdotai_modernbert


class IndexCode(BaseModel):
    code_blocks: List[str]
    ids: Optional[List[int]] = None
    model_name: str  # alibaba_modernbert or answerdotai_modernbert


class RetrievedResults(BaseModel):
    query: Any
    code_blocks: Any
    model_name: str  # alibaba_modernbert or answerdotai_modernbert
