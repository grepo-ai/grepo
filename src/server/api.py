from contextlib import asynccontextmanager, AsyncExitStack
from typing import Union, List, Optional
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pylate import indexes, models, retrieve, rank
from .schemas import CreateIndex, IndexCode, RetrievedResults
import uuid
from collections import defaultdict


# Cache in memory (temp for now)
col_model = {}
col_index = {}
col_retriever = {}
code_docs_map = {
    "alibaba_modernbert": defaultdict(dict),
    "answerdotai_modernbert": defaultdict(dict),
}
query_embedds = {}


def app_lifespans(lifespans):
    @asynccontextmanager
    async def _lifespan_manager(app: FastAPI):
        exit_stack = AsyncExitStack()
        async with exit_stack:
            for lifespan in lifespans:
                await exit_stack.enter_async_context(lifespan(app))
            yield

    return _lifespan_manager


@asynccontextmanager
async def load_model_1(app: FastAPI):
    hf_model = "Alibaba-NLP/gte-modernbert-base"
    model = models.ColBERT(
        model_name_or_path=hf_model, document_length=8192, embedding_size=768
    )
    col_model["alibaba_modernbert"] = model
    print(f"=== Loaded model successfully {hf_model} ===")

    yield
    col_model.clear()
    print("=== Cleared model from cache successfully ===")


@asynccontextmanager
async def load_model_2(app: FastAPI):
    hf_model = "answerdotai/ModernBERT-base"
    model = models.ColBERT(
        model_name_or_path=hf_model, document_length=8192, embedding_size=768
    )
    col_model["answerdotai_modernbert"] = model
    print(f"=== Loaded model successfully {hf_model}")

    yield
    col_model.clear()
    print("=== Cleared model from cache successfully ===")


app = FastAPI(lifespan=app_lifespans([load_model_1, load_model_2]))


# ----------------------------------- #
# --------------- APIs -------------- #
# ----------------------------------- #


@app.post("/create-index")
def create_index(request_data: CreateIndex):
    index = indexes.PLAID(
        index_folder=request_data.model_name,
        index_name=request_data.index_name,
        override=request_data.override,
        embedding_size=request_data.embedding_size,
        centroid_score_threshold=0.70,
        ncells=16,
    )

    col_index[request_data.model_name] = index

    return JSONResponse(
        status_code=status.HTTP_201_CREATED, content={"index_created": True}
    )


@app.get("/create-retriever/{model_name}")
def create_retriever(model_name: str):
    retriever = retrieve.ColBERT(index=col_index[model_name])
    col_retriever[model_name] = retriever

    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"retriever_initiated": True}
    )


@app.post("/index-code")
def index_code(schema: IndexCode):
    # Step 1: Create embeddings for code blocks
    if not schema.ids:
        for block in range(len(schema.code_blocks)):
            code_docs_map[schema.model_name][uuid.uuid4().hex] = {
                "code": schema.code_blocks[block]
            }

    code_embeddings = col_model[schema.model_name].encode(
        schema.code_blocks,
        batch_size=32,
        is_query=False,  # Encoding documents
        show_progress_bar=False,
    )

    for code_id, embeddings in zip(
        list(code_docs_map[schema.model_name].keys()), code_embeddings
    ):
        code_docs_map[schema.model_name][code_id].update({"embeddings": embeddings})

    # Step 2: Add the embeddings to index
    col_index[schema.model_name].add_documents(
        documents_ids=list(code_docs_map[schema.model_name].keys()),
        documents_embeddings=code_embeddings,
    )

    resp = {"code_indexed": True}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=resp)


@app.get("/query/{model_name}")
def query_docs(model_name: str, q: Optional[str] = None):
    final_resp = {}

    query_embeddings = col_model[model_name].encode(
        q,
        batch_size=32,
        is_query=True,  # Encoding queries
        show_progress_bar=False,
    )

    query_embedds[q] = query_embeddings

    code_blocks_matched_scores = col_retriever[model_name].retrieve(
        queries_embeddings=query_embeddings,
        k=4,
    )

    for code_score in code_blocks_matched_scores[0]:
        final_resp[code_score["id"]] = {
            "score": code_score["score"],
            "code": code_docs_map[model_name][code_score["id"]]["code"],
        }

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=final_resp)


@app.post("/rerank")
def rerank_results(schema: RetrievedResults, q: str):
    "Reranks the results for the given query"

    final_resp = {}

    code_embeddings = []
    for code_id, map in code_docs_map[schema.model_name].items():
        code_embeddings.append(map["embeddings"])

    ranked_codes = rank.rerank(
        documents_ids=list(code_docs_map[schema.model_name].keys()),
        queries_embeddings=query_embedds[q],
        documents_embeddings=code_embeddings,
    )

    print(query_embedds)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(code_docs_map)
    print("=========================")

    final_resp = {
        "ranked_docs": ranked_codes,
        "code_map": code_docs_map[schema.model_name],
    }

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=final_resp)
