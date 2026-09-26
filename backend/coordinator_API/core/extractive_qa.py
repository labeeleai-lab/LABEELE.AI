"""
core/extractive_qa.py - finds the actual most-relevant excerpt of a fetched
web page or attached document for a specific question, using the same
embedding model the Knowledge system already uses (see knowledge.py).

Why extractive instead of generative: live testing showed the local Duke
Brain (a small 1.1B model) does not reliably use injected context when
generating a free-form answer - given a one-line test document saying
"The secret code is 4471" and asked what the code was, it invented an
unrelated answer about backend architecture instead, and did the same
with a real fetched web page and a real multi-sentence document. Returning
the actual most-relevant text directly, instead of asking this model to
paraphrase it, is the reliable way to answer "what does this say about X"
- consistent with how core/math_solver.py and core/grounding.py already
avoid asking the model to guess at anything checkable.
"""
import numpy as np

import knowledge as knowledge_lib


def find_best_excerpt(question: str, content: str, top_k: int = 2) -> str:
    chunks = knowledge_lib.chunk_text(content, target_chars=400, overlap_chars=0, max_chars=600)
    if not chunks:
        return content[:500].strip()
    if len(chunks) == 1:
        return chunks[0]

    try:
        vectors = knowledge_lib.embed_chunks(chunks)
        q_vec = knowledge_lib.embed_query(question)
    except Exception:
        # Embedder unavailable - the first chunk is still better than nothing.
        return chunks[0]

    scored = sorted(zip(chunks, vectors), key=lambda cv: -float(np.dot(cv[1], q_vec)))
    return "\n\n".join(c for c, _ in scored[:top_k])
