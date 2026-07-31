"""
routers/admin_knowledge.py - POST /admin/knowledge/upload, GET /admin/knowledge,
GET /admin/knowledge/sources/{source_id}/chunks, DELETE /admin/knowledge/sources/{source_id},
DELETE /admin/knowledge/chunks/{chunk_id}.

Owns the knowledge.py import. Persistent, per-agent (or DUKE-global when
persona_id is null) knowledge base with real retrieval-augmented generation.
Documents are chunked, embedded (backend/knowledge.py), and stored as
KnowledgeChunk rows; a "document" in the admin UI is just every row sharing
one source_id. retrieve_relevant_chunks() is used by routers/tasks.py's
/tasks/submit (that router does its own `import knowledge as knowledge_lib`
too - importing the same already-loaded module from multiple files is
normal and cheap in Python).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger
from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.orm import KnowledgeChunk, PersonaConfig
from coordinator_API.models.schemas import (
    KnowledgeUploadRequest, KnowledgeUploadResponse, KnowledgeSourceSummary, KnowledgeChunkDetail,
)

import knowledge as knowledge_lib

KNOWLEDGE_MAX_TEXT_CHARS = knowledge_lib.MAX_TEXT_CHARS
KNOWLEDGE_MAX_PDF_BYTES = knowledge_lib.MAX_PDF_BYTES

router = APIRouter()


def _require_known_persona(persona_id: Optional[str], db: Session):
    if persona_id is None:
        return
    exists = db.query(PersonaConfig).filter(PersonaConfig.persona_id == persona_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")


@router.post(
    "/admin/knowledge/upload",
    response_model=KnowledgeUploadResponse,
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def upload_knowledge(payload: KnowledgeUploadRequest, db: Session = Depends(get_db)):
    _require_known_persona(payload.persona_id, db)

    if payload.content_type == "pdf":
        import base64
        try:
            file_bytes = base64.b64decode(payload.file_base64)
        except Exception:
            raise HTTPException(status_code=422, detail="file_base64 is not valid base64")
        if len(file_bytes) > KNOWLEDGE_MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail=f"PDF exceeds {KNOWLEDGE_MAX_PDF_BYTES // (1024*1024)}MB limit")
        try:
            text = knowledge_lib.extract_pdf_text(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not extract text from PDF: {e}")
    else:
        if not payload.text:
            raise HTTPException(status_code=422, detail="text is required for content_type 'text'/'markdown'")
        text = payload.text

    if len(text) > KNOWLEDGE_MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"Content exceeds {KNOWLEDGE_MAX_TEXT_CHARS} character limit")

    chunks = knowledge_lib.chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="No usable content found after chunking")

    try:
        vectors = knowledge_lib.embed_chunks(chunks)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    source_id = str(uuid.uuid4())
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.add(
            KnowledgeChunk(
                id=str(uuid.uuid4()),
                source_id=source_id,
                source_name=payload.source_name,
                source_type=payload.content_type,
                persona_id=payload.persona_id,
                chunk_index=i,
                content=chunk,
                content_length=len(chunk),
                embedding=vector,
            )
        )
    db.commit()

    logger.info(f"✅ Knowledge uploaded: '{payload.source_name}' -> {len(chunks)} chunks (persona={payload.persona_id or 'GLOBAL'})")
    return KnowledgeUploadResponse(source_id=source_id, chunks_created=len(chunks), total_characters=len(text))


@router.get(
    "/admin/knowledge",
    response_model=List[KnowledgeSourceSummary],
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_knowledge(scope: str, persona_id: Optional[str] = None, db: Session = Depends(get_db)):
    if scope not in ("global", "agent"):
        raise HTTPException(status_code=422, detail="scope must be 'global' or 'agent'")
    if scope == "agent" and not persona_id:
        raise HTTPException(status_code=422, detail="persona_id is required when scope='agent'")

    filter_persona = None if scope == "global" else persona_id
    rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.persona_id == filter_persona)
        .order_by(KnowledgeChunk.source_id, KnowledgeChunk.chunk_index)
        .all()
    )

    sources: dict[str, KnowledgeSourceSummary] = {}
    for row in rows:
        if row.source_id not in sources:
            sources[row.source_id] = KnowledgeSourceSummary(
                source_id=row.source_id,
                source_name=row.source_name,
                source_type=row.source_type,
                persona_id=row.persona_id,
                chunk_count=0,
                created_at=row.created_at,
                preview=row.content[:200],
            )
        sources[row.source_id].chunk_count += 1

    return sorted(sources.values(), key=lambda s: s.created_at, reverse=True)


@router.get(
    "/admin/knowledge/sources/{source_id}/chunks",
    response_model=List[KnowledgeChunkDetail],
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_knowledge_source_chunks(source_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.source_id == source_id)
        .order_by(KnowledgeChunk.chunk_index)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return [
        KnowledgeChunkDetail(id=r.id, chunk_index=r.chunk_index, content=r.content, content_length=r.content_length)
        for r in rows
    ]


@router.delete(
    "/admin/knowledge/sources/{source_id}",
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def delete_knowledge_source(source_id: str, db: Session = Depends(get_db)):
    deleted = db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id == source_id).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return {"status": "success", "deleted_chunks": deleted}


@router.delete(
    "/admin/knowledge/chunks/{chunk_id}",
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def delete_knowledge_chunk(chunk_id: str, db: Session = Depends(get_db)):
    row = db.query(KnowledgeChunk).filter(KnowledgeChunk.id == chunk_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Chunk '{chunk_id}' not found")
    db.delete(row)
    db.commit()
    return {"status": "success"}
