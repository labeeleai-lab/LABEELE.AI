"""
core/document_qa.py - lets a user attach a file to a single question
("what does this contract say about termination?") and have DUKE answer
using that document's actual text, instead of guessing. This is a one-off,
per-question attachment - not a persistent Knowledge upload (see
routers/admin_knowledge.py for that).

Reuses knowledge.py's existing PDF extraction rather than duplicating it.
"""
import base64
import os
from typing import Optional

import knowledge as knowledge_lib

# Capped well under Vercel's ~4.5MB serverless request-body limit, not just
# a reasonable-file-size choice - the frontend proxy this travels through
# (base64-encoded, ~4/3 the raw size) would 413 before this code ever runs
# if the raw file were much bigger than this.
MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024
MAX_EXTRACTED_CHARS = 6000

_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}


def extract_attachment_text(attachment_base64: str, attachment_name: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (extracted_text, error_message) - exactly one is non-None."""
    try:
        file_bytes = base64.b64decode(attachment_base64, validate=True)
    except Exception:
        return None, "that attachment wasn't valid base64 data"

    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        return None, f"that attachment is too large (limit is {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB)"

    ext = os.path.splitext(attachment_name or "")[1].lower()

    if ext == ".pdf":
        try:
            text = knowledge_lib.extract_pdf_text(file_bytes)
        except Exception as e:
            return None, f"I couldn't read that PDF ({e})"
    elif ext in _TEXT_EXTENSIONS or not ext:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return None, "that file isn't plain text or a PDF I can read"
    else:
        return None, f"I can't read \"{ext}\" files yet - try a PDF or a plain text file"

    text = text.strip()
    if not text:
        return None, "that file didn't have any readable text in it"
    return text[:MAX_EXTRACTED_CHARS], None
