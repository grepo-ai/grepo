from pydantic import BaseModel
from typing import List


class CreateIndex(BaseModel):
    index_name: str
    override: bool
    embedding_size: int


class IndexCode(BaseModel):
    code_blocks: List[str]
    ids: List[int]
