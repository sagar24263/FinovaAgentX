import os
from typing import Any, Dict, List, Optional

from qdrant_client.http.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.config.mongo import get_collection
from app.config.qdrant import get_qdrant_client
from app.utils.logger import get_logger

logger = get_logger("knowledge_base_service")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
BATCH_SIZE = 64

PRODUCT_TYPE = "investment"
PRODUCT_ID = 115

KB_TYPE_CONFIG = {
    "generic": {
        "mongo_collection": "AgentX_knowledge_base_generic",
        "qdrant_collection": "AgentX_generic",
    },
    "NFO": {
        "mongo_collection": "AgentX_knowledge_base_NFO",
        "qdrant_collection": "AgentX_NFO",
    },
}

_DECK_META_KEYS = ["nfo_name", "insurer_name", "insurer_id", "nfo_date"]

_embedding_model: Optional[SentenceTransformer] = None


# ---------------------------------------------------------------------------
# Embedding model lifecycle
# ---------------------------------------------------------------------------

def load_embedding_model() -> None:
    global _embedding_model
    logger.info(f"Loading embedding model '{EMBEDDING_MODEL}'...")
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info(f"Embedding model loaded (dim={_embedding_model.get_sentence_embedding_dimension()})")


def get_embedding_model() -> SentenceTransformer:
    if _embedding_model is None:
        raise RuntimeError("Embedding model not loaded. Call load_embedding_model() at startup.")
    return _embedding_model


# ---------------------------------------------------------------------------
# KB service (MongoDB access)
# ---------------------------------------------------------------------------

class KnowledgeBaseService:
    def __init__(self, kb_type: str):
        config = KB_TYPE_CONFIG[kb_type]
        self.kb_type = kb_type
        self.collection = get_collection(collection_name=config["mongo_collection"])

    def get_all_entries(self, active_only: bool = False) -> List[dict]:
        if self.collection is None:
            logger.warning(f"MongoDB unavailable for kb_type='{self.kb_type}'")
            return []
        query = {}
        if active_only:
            query["is_active"] = True
        return list[dict](self.collection.find(query, {"_id": 0}))


def get_knowledge_base_service(kb_type: str) -> KnowledgeBaseService:
    return KnowledgeBaseService(kb_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deck_metadata_from_entry(entry: dict) -> Dict:
    return {k: entry.get(k) for k in _DECK_META_KEYS}


def _ensure_payload_indexes(client, collection_name: str) -> None:
    for field in ("nfo_name", "insurer_name", "nfo_date"):
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="insurer_id",
        field_schema=PayloadSchemaType.INTEGER,
    )
    logger.info(f"Payload indexes created for '{collection_name}'")


def _build_document_text(entry: dict) -> str:
    term = entry.get("term", "Unknown")
    keywords = entry.get("keywords", [])
    content = entry.get("content", "")

    lines = [f"# {term}"]

    if keywords:
        kw_list = keywords if isinstance(keywords, list) else [keywords]
        lines.append(f"Related to: {', '.join(kw_list)}")

    deck = _deck_metadata_from_entry(entry)
    meta_bits = []
    if deck.get("nfo_name"):
        meta_bits.append(f"NFO name: {deck['nfo_name']}")
    if deck.get("insurer_name"):
        meta_bits.append(f"InsurerName: {deck['insurer_name']}")
    if deck.get("insurer_id") is not None:
        meta_bits.append(f"InsurerID: {deck['insurer_id']}")
    if deck.get("nfo_date"):
        meta_bits.append(f"NFO date: {deck['nfo_date']}")
    if meta_bits:
        lines.append("\n".join(meta_bits))

    lines.append("\n## Information")
    lines.append(content)

    return "\n".join(lines)


def _build_metadata(entry: dict) -> dict:
    keywords = entry.get("keywords", [])
    metadata = {
        "term": entry.get("term", "Unknown"),
        "keywords": ", ".join(keywords) if isinstance(keywords, list) else str(keywords),
        "product_type": PRODUCT_TYPE,
        "product_id": PRODUCT_ID,
    }
    deck = _deck_metadata_from_entry(entry)
    for mk in _DECK_META_KEYS:
        val = deck.get(mk)
        if val is None:
            continue
        if isinstance(val, (bool, int, float)):
            metadata[mk] = val
        else:
            metadata[mk] = str(val)[:500]

    return metadata


# ---------------------------------------------------------------------------
# Core indexing
# ---------------------------------------------------------------------------

def _index_single(
    kb_type: str,
    model: SentenceTransformer,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
) -> str:
    from app.config.env import QDRANT_URL, QDRANT_API_KEY

    qdrant_col = KB_TYPE_CONFIG[kb_type]["qdrant_collection"]

    url = qdrant_url or QDRANT_URL
    api_key = QDRANT_API_KEY if qdrant_api_key is None else qdrant_api_key

    logger.info(f"Connecting to Qdrant at {url} for collection '{qdrant_col}'...")
    client = get_qdrant_client(url, api_key)

    logger.info(f"Loading knowledge base from MongoDB (product_type={PRODUCT_TYPE}, product_id={PRODUCT_ID}, type={kb_type})...")
    kb_service = get_knowledge_base_service(kb_type)
    if kb_service.collection is None:
        raise ConnectionError(f"Savings DB connection not available for '{kb_type}'")

    knowledge_base = kb_service.get_all_entries(active_only=True)
    if not knowledge_base:
        logger.error(f"No entries found in MongoDB for kb_type='{kb_type}'")
        raise ValueError(f"Knowledge base is empty for '{qdrant_col}'")

    logger.info(f"Loaded {len(knowledge_base)} entries from MongoDB")

    vector_size = model.get_sentence_embedding_dimension()

    existing = {c.name for c in client.get_collections().collections}
    if qdrant_col in existing:
        client.delete_collection(qdrant_col)
    client.create_collection(
        collection_name=qdrant_col,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info(f"Recreated collection '{qdrant_col}' (dim={vector_size}, cosine)")

    _ensure_payload_indexes(client, qdrant_col)

    documents = [_build_document_text(e) for e in knowledge_base]
    metadatas = [_build_metadata(e) for e in knowledge_base]

    logger.info(f"Indexing {len(documents)} documents into '{qdrant_col}'...")
    embeddings = model.encode(documents, show_progress_bar=False).tolist()

    for start in range(0, len(documents), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(documents))
        points = [
            PointStruct(
                id=i,
                vector=embeddings[i],
                payload={"document": documents[i], **metadatas[i]},
            )
            for i in range(start, end)
        ]
        client.upsert(collection_name=qdrant_col, points=points)

    count = client.count(collection_name=qdrant_col, exact=True).count
    logger.info(f"Collection '{qdrant_col}' has {count} points after indexing")

    test_vec = model.encode("what is").tolist()
    test_hits = client.query_points(
        collection_name=qdrant_col,
        query=test_vec,
        limit=1,
        with_payload=True,
    ).points
    if test_hits and test_hits[0].payload:
        sample = (test_hits[0].payload.get("document") or "")[:100]
        logger.info(f"Test query OK — sample: {sample}...")
    else:
        logger.warning("Test query returned no results")

    return qdrant_col


def index_knowledge_base(
    kb_type: Optional[str] = None,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
) -> dict:
    """
    Reindex knowledge base (product_type=investment, product_id=115).
    kb_type: 'generic' | 'NFO' | None  (None reindexes both)
    Returns {'indexed': [...], 'errors': [...]}
    """
    model = get_embedding_model()
    types_to_index = [kb_type] if kb_type else list(KB_TYPE_CONFIG.keys())

    indexed, errors = [], []
    for t in types_to_index:
        try:
            col = _index_single(t, model, qdrant_url=qdrant_url, qdrant_api_key=qdrant_api_key)
            indexed.append(col)
        except Exception as e:
            logger.error(f"Failed to index '{t}': {e}")
            errors.append(f"{t}: {str(e)}")

    return {"indexed": indexed, "errors": errors}
