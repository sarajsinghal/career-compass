# Career Knowledge Assistant (Hindi + English)

A local-first retrieval-augmented generation (RAG) application for querying resumes, job descriptions, certificates, career guides, and spreadsheet data. It accepts PDF, DOCX, TXT, XLSX, and legacy XLS files, retrieves relevant passages across Hindi and English, and identifies each source by file and page, section, or worksheet row.

**Live app:** https://career-compass-bpyji.streamlit.app/

## 1. What happens when you ask a question?

```text
PDF / DOCX / TXT / XLSX / XLS
      │ extract text and keep page/section labels
      ▼
Text chunks ── multilingual embeddings (runs locally) ──► local NumPy vector index
                                                               ▲
Hindi / English / Hinglish question ── same embedding ──► top matching chunks
                                                               │
                                              Ollama local LLM (optional)
                                                               ▼
                                      grounded answer + source citations
```

This project uses a compact multilingual Sentence Transformers model for semantic search and a small local Ollama model for answer writing. It does not require Gemini, an OpenAI key, or any paid API. If Ollama is unavailable, it still searches locally and displays the best source passages instead of inventing a response. Embeddings are calculated on your machine; no uploaded documents are sent to an API by this project.

### Project files

- `app.py` — polished Streamlit dashboard with chat, clickable starter questions, library view, upload controls, and citations.
- `rag.py` — extraction, chunking, local indexing, multilingual retrieval, answer generation, and source metadata.
- `requirements.txt` — Python packages, including readers for modern and legacy Excel files.
- `.streamlit/config.toml` — consistent light theme and accessible contrast colors.
- `data/documents/` — uploaded files (created when you add a document).
- `data/index.npz` and `data/chunks.json` — generated local search index and citations.

## 2. Windows setup

Install Python 3.11 (64-bit) from [python.org](https://www.python.org/downloads/windows/) and select **Add python.exe to PATH** in the installer. Then open PowerShell in this project folder. These commands assume the folder is named `career-assistant`.

```powershell
cd path\to\career-assistant
py -3.11 -m venv .venv
```

`cd` enters the project folder. `py -3.11 -m venv .venv` creates an isolated Python environment so this app's packages do not affect other Python projects.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The first command activates the environment in this PowerShell window. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same window, then activate again; this change lasts only until the window closes. The next command updates the package installer. The last command installs Streamlit, the multilingual embedding model runtime, and PDF/DOCX/Excel readers.

### Optional: install a local answer model

Install [Ollama for Windows](https://ollama.com/download/windows), open a new PowerShell window after installation, then run:

```powershell
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

`ollama pull` downloads the model; `ollama run` checks that it starts. You can exit the interactive model prompt with `/bye`. Keep Ollama installed and available while using the app. It normally serves at `http://localhost:11434`.

To choose another Ollama model or a different Ollama host, set these environment variables before starting Streamlit:

```powershell
$env:OLLAMA_MODEL = "qwen2.5:3b"
$env:OLLAMA_HOST = "http://localhost:11434"
```

The embedding model can also be changed with `EMBEDDING_MODEL`. Use a Sentence Transformers model that supports Hindi and English, such as `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (the default). Changing embedding models means rebuilding the index: delete `data\index.npz` and `data\chunks.json`, then re-upload your documents. Keep Ollama bound to a trusted local network; the app has no authentication layer.

## 3. Start the app

From the activated environment, run:

```powershell
streamlit run app.py
```

This starts the local web app and opens it in your browser using the project's light color theme. After changing the UI or theme settings, stop any existing Streamlit run with `Ctrl+C` and launch it again. On its first start, the embedding model downloads once from Hugging Face; later starts reuse the cached model. Add documents in the left panel, explore the library and tips tab, or click a starter question. You can ask questions in Hindi, English, or Hinglish. Search is semantic, so a question and source passage need not use identical words.

### First question checklist

1. Add a text-based resume, job description, career guide, or workbook using **Add documents**.
2. Wait for indexing to finish. PDF files retain page numbers. DOCX files cite paragraph/table sections because Word documents do not have stable page numbers until rendered. Excel citations name the worksheet and row number.
3. Ask something grounded in those files, such as “Which skills does this job description require?” or “इस नौकरी के लिए कौन-से कौशल चाहिए?”
4. Open **Sources / स्रोत** under the answer to review the exact supporting passages.

Scanned/image-only PDFs do not contain selectable text and need OCR before upload. Do not rely on the assistant for consequential hiring, legal, or financial decisions; verify claims against the cited original documents.

## 4. Deployment options

### Keep it private and local (recommended for resumes)

Use the local setup above. Documents and the search index stay in the project folder. The model downloads are separate from your documents. Back up `data/` if you want to keep the uploaded files and index.

### Streamlit Community Cloud (public demo)

1. Create a GitHub repository and add `app.py`, `rag.py`, `requirements.txt`, and `.gitignore`.
2. Do **not** commit resumes, `data/`, or secrets. `.gitignore` excludes uploaded files and the local index.
3. In Streamlit Community Cloud, create an app from that repository and set the main file to `app.py`.
4. After deployment, upload non-sensitive sample files. The first model download and embedding may take a few minutes.

Community Cloud's filesystem is not a durable private document store: uploaded files and the local index may disappear on restart/redeploy. The app also has no login/authentication, so a public deployment should be treated as a demo with non-sensitive documents only. Ollama is not automatically available in a hosted deployment; without a reachable Ollama service, the app falls back to retrieved passages with citations. For a production deployment, add authentication and durable, access-controlled storage, and configure a private reachable Ollama service or an LLM provider you have independently chosen.

## 5. Troubleshooting

- **`py` is not recognized:** reinstall Python and enable the PATH option, or use `python` instead of `py -3.11` if Python 3.11 is already on PATH.
- **Activation is blocked:** run the process-scoped execution policy command above, then activate again.
- **Ollama connection error / no generated answer:** confirm Ollama is running and `ollama run qwen2.5:3b` succeeds. Search still works with the cited passage fallback.
- **Model download fails:** check internet access once; Hugging Face downloads the embedding model on first use. The core app does not need an API key.
- **PDF returns no text:** it may be scanned. Run OCR on it first or use a text-based PDF.
- **Want to start fresh:** stop Streamlit with `Ctrl+C`. Remove `data\index.npz`, `data\chunks.json`, and the files inside `data\documents` to clear the index and uploads.

## 6. How to extend it

The app intentionally keeps the pipeline small and inspectable. Good next additions are OCR for scanned files, user login for private hosted use, a delete/rebuild index control, and richer DOCX location metadata. Preserve the document `file` and `locator` fields when changing retrieval so source citations remain traceable.
