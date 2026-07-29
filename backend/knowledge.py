"""
DUKE Knowledge System (Phase 1) - chunking, embedding, and retrieval helpers.

Deliberately has zero dependency on coordinator_api.py (no model imports, no
DB engine) to avoid a circular import - coordinator_api.py imports from here,
never the other way around. DB I/O (inserting/querying KnowledgeChunk rows)
stays in coordinator_api.py; this module only does text -> chunks -> vectors,
plus the similarity-ranking query itself (which needs the model class passed
in, not imported).
"""

import os
import io
import logging
import re

import numpy as np

logger = logging.getLogger(__name__)

EMBED_MODEL_NAME = os.getenv("KNOWLEDGE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_TOP_K = int(os.getenv("KNOWLEDGE_TOP_K", "4"))
DEFAULT_SIM_THRESHOLD = float(os.getenv("KNOWLEDGE_SIM_THRESHOLD", "0.35"))

MAX_TEXT_CHARS = 300_000
MAX_PDF_BYTES = 15 * 1024 * 1024

_embedder = None
_embedder_load_attempted = False


def get_embedder():
    """
    Lazy singleton around a local sentence-transformers model. Loaded eagerly
    once at startup (see lifespan() in coordinator_api.py) but this lazy
    guard means any caller can safely ask for it without worrying about
    import order, and a failed load degrades to None rather than crashing
    the app - matching the existing duke_brain load pattern.
    """
    global _embedder, _embedder_load_attempted
    if _embedder is not None or _embedder_load_attempted:
        return _embedder

    _embedder_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
        logger.info(f"✅ Knowledge embedder loaded: {EMBED_MODEL_NAME}")
    except Exception as e:
        logger.error(f"❌ Failed to load knowledge embedder ({EMBED_MODEL_NAME}): {e}")
        _embedder = None
    return _embedder


def embed_chunks(texts: list[str]) -> list[np.ndarray]:
    """Batched embedding - always call this for multiple texts rather than looping embed_query."""
    embedder = get_embedder()
    if embedder is None:
        raise RuntimeError("Knowledge embedder is not available.")
    vectors = embedder.encode(texts, batch_size=16, show_progress_bar=False, normalize_embeddings=True)
    return [np.asarray(v, dtype=np.float32) for v in vectors]


def embed_query(text: str) -> np.ndarray:
    return embed_chunks([text])[0]


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = _SENTENCE_SPLIT.split(paragraph)
    pieces, current = [], ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current.strip())
    # A single sentence longer than max_chars still needs a hard cut so nothing is dropped.
    final = []
    for piece in pieces:
        while len(piece) > max_chars:
            final.append(piece[:max_chars])
            piece = piece[max_chars:]
        if piece:
            final.append(piece)
    return final


def chunk_text(text: str, target_chars: int = 1000, overlap_chars: int = 150, max_chars: int = 1600) -> list[str]:
    """
    Paragraph-first greedy packing: split on blank lines, pack paragraphs up
    to target_chars, carry the trailing overlap_chars of each chunk into the
    next chunk's start for cheap cross-boundary context continuity. A
    paragraph longer than max_chars gets further split on sentence
    boundaries. Character-length based - no tokenizer needed for a small
    local model.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    normalized: list[str] = []
    for p in paragraphs:
        if len(p) > max_chars:
            normalized.extend(_split_long_paragraph(p, max_chars))
        else:
            normalized.append(p)

    chunks: list[str] = []
    current = ""
    for paragraph in normalized:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > target_chars:
            chunks.append(current)
            carry = current[-overlap_chars:] if len(current) > overlap_chars else current
            current = f"{carry}\n\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)

    return [c for c in chunks if len(c.strip()) >= 20]


def extract_pdf_text(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages)


def retrieve_relevant_chunks(
    db,
    model_cls,
    persona_id: str | None,
    query_text: str,
    top_k: int = DEFAULT_TOP_K,
    min_similarity: float = DEFAULT_SIM_THRESHOLD,
    cross_agent: bool = False,
):
    """
    Embeds query_text and returns up to top_k KnowledgeChunk rows, ranked by
    cosine similarity, filtered to min_similarity. model_cls is passed in
    (the KnowledgeChunk class) rather than imported, so this module never
    needs to import coordinator_api.py.

    Normal mode: scoped to this persona plus DUKE-global knowledge
    (persona_id IS NULL). cross_agent=True (used for DUKE itself) drops the
    persona filter entirely and searches every agent's knowledge - semantic
    similarity alone decides which specialists' chunks are relevant to a
    given question, with no hand-written routing rules. Each returned row
    still carries its own persona_id so the caller can attribute which
    specialist each chunk came from.
    """
    embedder = get_embedder()
    if embedder is None:
        return []

    query_vec = embed_query(query_text)

    # pgvector's cosine_distance = 1 - cosine_similarity, so smaller is more similar.
    query = db.query(model_cls)
    if not cross_agent:
        query = query.filter((model_cls.persona_id == persona_id) | (model_cls.persona_id.is_(None)))
    rows = query.order_by(model_cls.embedding.cosine_distance(query_vec)).limit(top_k).all()

    # The DB query above only orders/limits by distance; do the actual threshold
    # check in Python against real cosine similarity - cheap since it's just top_k rows.
    filtered = []
    for row in rows:
        row_vec = np.asarray(row.embedding, dtype=np.float32)
        similarity = float(np.dot(query_vec, row_vec) / ((np.linalg.norm(query_vec) * np.linalg.norm(row_vec)) + 1e-8))
        if similarity >= min_similarity:
            filtered.append(row)
    return filtered
