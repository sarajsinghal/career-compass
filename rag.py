"""Small, transparent RAG pipeline with a local multilingual embedding model."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import streamlit as st

try:
    from docx import Document
    from openpyxl import load_workbook
    from pypdf import PdfReader
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError as exc:
    package = exc.name or "a required package"
    raise ModuleNotFoundError(
        f"Missing dependency '{package}'. From the career-assistant project folder, run: "
        "python -m pip install -r requirements.txt"
    ) from exc

ROOT = Path(__file__).parent
DATA = ROOT / "data"
UPLOADS = DATA / "documents"
INDEX_FILE = DATA / "index.npz"
META_FILE = DATA / "chunks.json"
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150


@st.cache_resource(show_spinner="Loading multilingual embedding model (first run downloads it)…")
def embedding_model():
    return SentenceTransformer(MODEL_NAME)


def _split(text):
    text = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _extract(path):
    suffix = path.suffix.lower()
    pages = []
    if suffix == ".pdf":
        for number, page in enumerate(PdfReader(str(path)).pages, start=1):
            pages.append((page.extract_text() or "", f"page {number}"))
    elif suffix == ".docx":
        doc = Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        pages = [(text, "paragraphs")]
        for table in doc.tables:
            rows = [" | ".join(cell.text for cell in row.cells) for row in table.rows]
            if rows:
                pages.append(("\n".join(rows), "table"))
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        pages = [(text, "text")]
    elif suffix == ".xlsx":
        workbook = load_workbook(path, read_only=True, data_only=True)
        for sheet in workbook.worksheets:
            for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                if values:
                    pages.append((" | ".join(values), f"sheet '{sheet.title}', row {row_number}"))
    elif suffix == ".xls":
        import pandas as pd
        workbook = pd.ExcelFile(path)
        for sheet_name in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet_name, header=None, dtype=str).fillna("")
            for row_number, row in enumerate(frame.itertuples(index=False, name=None), start=1):
                values = [str(value).strip() for value in row if str(value).strip()]
                if values:
                    pages.append((" | ".join(values), f"sheet '{sheet_name}', row {row_number}"))
    return pages


def _load_index():
    if not INDEX_FILE.exists() or not META_FILE.exists():
        return np.empty((0, 0), dtype=np.float32), []
    with np.load(INDEX_FILE) as data:
        vectors = data["vectors"].astype(np.float32)
    return vectors, json.loads(META_FILE.read_text(encoding="utf-8"))


def ingest_files(files):
    UPLOADS.mkdir(parents=True, exist_ok=True)
    vectors, chunks = _load_index()
    known = {item["id"] for item in chunks}
    pending = []
    added, skipped = 0, 0
    for upload in files:
        safe_name = Path(upload.name).name
        raw = upload.getvalue()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in known:
            skipped += 1
            continue
        destination = UPLOADS / f"{digest[:12]}_{safe_name}"
        destination.write_bytes(raw)
        try:
            page_texts = _extract(destination)
        except Exception as exc:
            destination.unlink(missing_ok=True)
            st.error(f"Could not read {safe_name}: {exc}")
            skipped += 1
            continue
        local = []
        for text, locator in page_texts:
            for part, piece in enumerate(_split(text), start=1):
                local.append({"id": digest, "file": safe_name, "locator": locator, "part": part, "text": piece})
        if not local:
            destination.unlink(missing_ok=True)
            st.warning(f"No extractable text found in {safe_name}. Scanned PDFs may need OCR first.")
            skipped += 1
            continue
        pending.extend(local)
        known.add(digest)
        added += 1
    if pending:
        new_vectors = embedding_model().encode([item["text"] for item in pending], normalize_embeddings=True, show_progress_bar=False)
        new_vectors = np.asarray(new_vectors, dtype=np.float32)
        vectors = np.vstack([vectors, new_vectors]) if vectors.size else new_vectors
        chunks.extend(pending)
        DATA.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(INDEX_FILE, vectors=vectors)
        META_FILE.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return added, skipped


def list_documents():
    _, chunks = _load_index()
    return list(dict.fromkeys(chunk["file"] for chunk in chunks))


def _retrieve(question, k=5):
    vectors, chunks = _load_index()
    if not chunks:
        return []
    query = embedding_model().encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
    scores = vectors @ np.asarray(query, dtype=np.float32)
    chosen = np.argsort(scores)[::-1][:k]
    return [(chunks[i], float(scores[i])) for i in chosen if scores[i] > 0.12]


def _ollama_answer(question, hits):
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    context = "\n\n".join(f"[{i}] {item['file']} ({item['locator']}): {item['text']}" for i, (item, _) in enumerate(hits, 1))
    prompt = ("You are a careful bilingual Hindi-English career knowledge assistant. Answer in the same language/script as the user's question (Hinglish may be answered naturally in Hinglish). "
              "Use only the supplied context. If it does not contain the answer, say so clearly. Do not invent qualifications, dates, or experience. "
              "Cite factual claims with bracket references like [1].\n\nCONTEXT:\n" + context + "\n\nQUESTION:\n" + question)
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}}).encode("utf-8")
    request = urllib.request.Request(f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def answer_question(question):
    hits = _retrieve(question)
    if not hits:
        return {"answer": "I couldn’t find relevant information in the indexed documents. Try adding a resume, job description, or career guide.\n\nमैं आपके दस्तावेज़ों में संबंधित जानकारी नहीं ढूँढ़ पाया।", "sources": []}
    answer = _ollama_answer(question, hits)
    if not answer:
        # Safe fallback: surface the strongest source passages without claiming a model-generated synthesis.
        answer = "I found these relevant passages in your documents. Review the cited sources below.\n\nमुझे आपके दस्तावेज़ों में ये संबंधित अंश मिले हैं। नीचे दिए गए स्रोत देखें।\n\n" + "\n\n".join(f"**[{i}]** {item['text']}" for i, (item, _) in enumerate(hits[:3], 1))
    sources = []
    for item, _score in hits:
        label = f"{item['file']} — {item['locator']}" + (f", section {item['part']}" if item["locator"] != "page 1" else "")
        sources.append({"label": label, "preview": item["text"][:280] + ("…" if len(item["text"]) > 280 else "")})
    return {"answer": answer, "sources": sources}
