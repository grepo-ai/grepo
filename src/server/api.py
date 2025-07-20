from contextlib import asynccontextmanager
from typing import Union, List, Optional
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pylate import indexes, models, retrieve
from src.server.schemas import CreateIndex, IndexCode
import uuid


# Cache in memory (temp for now)
model = {}
index = {}
retriever = {}


@asynccontextmanager
async def load_model(app: FastAPI):
    hf_model = "Alibaba-NLP/gte-modernbert-base"
    model = models.ColBERT(
        model_name_or_path=hf_model, document_length=8192, embedding_size=768
    )
    model["alibaba_modernbert"] = model
    print("=== Loaded model successfully ===")

    yield
    model.clear()


app = FastAPI(lifespan=load_model)


@app.post("/create-index")
def create_index(request_data: CreateIndex):
    index_details = {}
    index = indexes.PLAID(
        index_folder="grepo-indexes",
        index_name=request_data.index_name,
        override=request_data.override,
        embedding_size=request_data.embedding_size,
    )

    index_details["index"] = index

    return JSONResponse(
        status_code=status.HTTP_201_CREATED, content={"index_created": True}
    )


@app.get("/create-retriever")
def create_retriever():
    col_retriever = retrieve.ColBERT(index=index["index"])
    retriever["retriever"] = col_retriever

    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"retriever_initiated": True}
    )


# TODO
@app.post("/index-code")
def index_code(schema: IndexCode):
    # Step 1: Create embedding_size
    documents_embeddings = model.encode(
        documents,
        batch_size=32,
        is_query=False,  # Encoding documents
        show_progress_bar=False,
    )

    # Step 2: Add the embeddings to index

    resp = {"code_indexed": True}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=resp)


# TODO
@app.get("/query")
def query_docs(q: Optional[str] = None):
    resp = {}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=resp)
