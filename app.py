"""Bilingual (Hindi/English) career knowledge assistant."""
import streamlit as st

from rag import answer_question, ingest_files, list_documents

st.set_page_config(page_title="Career Compass", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { --ink:#18312f; --muted:#637674; --teal:#087f72; --mint:#e8f5ef; --line:#e3ebe7; }
.stApp, [data-testid="stAppViewContainer"] { background:linear-gradient(180deg,#f5faf7 0,#fbfcfa 330px,#fbfcfa 100%); color:var(--ink); }
html, body, [class*="css"] { font-family:'Aptos','Segoe UI',sans-serif; }
h1,h2,h3 { font-family:'Segoe UI','Aptos',sans-serif !important; color:var(--ink); }
p, label, [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] { color:#425b57; }
.block-container { max-width:1160px; padding-top:2rem; padding-bottom:3rem; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background:#f0f7f3 !important; color:#18312f !important; border-right:1px solid var(--line); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color:#18312f !important; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:14px 18px; border-radius:15px; box-shadow:0 5px 18px #173b2b08; }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { color:var(--ink); font-family:'Segoe UI','Aptos',sans-serif; }
.hero { background:linear-gradient(115deg,#123b36 0%,#146d61 58%,#49a58b 100%); border-radius:24px; padding:30px 34px; color:white; margin:4px 0 22px; box-shadow:0 14px 36px #105c4b20; }
.hero h1 { color:white !important; font-size:2.15rem; margin:0 0 8px; }
.hero p { color:#e1f4ed; font-size:1.03rem; margin:0; max-width:740px; }
.eyebrow { text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; color:#b5e6d4; font-weight:700; margin-bottom:10px; }
.stButton button { border-radius:12px; border:1px solid #d8e8df; transition:all .18s ease; }
.stButton button:hover { border-color:#83bba6; color:#086e60; transform:translateY(-1px); }
[data-testid="stFileUploader"] section { background:#fff !important; border:1px dashed #9bbcaf !important; border-radius:14px !important; }
[data-testid="stFileUploader"] section, [data-testid="stFileUploader"] section * { color:#24413b !important; }
[data-testid="stFileUploader"] button { background:#f3faf6 !important; color:#155b4e !important; border:1px solid #c9ddd2 !important; }
[data-testid="stAlert"] { background:#eef7f1 !important; border:1px solid #cfe4d7 !important; border-radius:14px !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] div { color:#21463b !important; }
[data-testid="stTabs"] button { color:#48645e !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#087f72 !important; }
[data-testid="stChatMessage"] { border:1px solid #e6eee9; border-radius:18px; padding:16px 18px; background:white; box-shadow:0 4px 14px #123b3608; }
[data-testid="stChatInput"] { background:#fff !important; border:1px solid #bfd8ce !important; border-radius:16px !important; }
[data-testid="stChatInput"] textarea { background:#fff !important; color:#18312f !important; }
[data-testid="stChatInput"] textarea::placeholder { color:#637674 !important; opacity:1; }
[data-testid="stChatInput"] button { background:#e8f5ef !important; color:#087f72 !important; }
.subtle { color:#637674; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("## 🧭 Career Compass")
    st.caption("Your personal career knowledge space")
    st.divider()
    st.subheader("📚 Build your library")
    uploads = st.file_uploader(
        "Upload career documents", type=["pdf", "docx", "txt", "xlsx", "xls"],
        accept_multiple_files=True, help="PDF, Word, text, and Excel files are supported.",
    )
    if st.button("✨ Add to my library", type="primary", disabled=not uploads, use_container_width=True):
        with st.spinner("Reading files and preparing multilingual search…"):
            added, skipped = ingest_files(uploads)
        if added:
            st.success(f"Added {added} file(s) to your library.")
        if skipped:
            st.info(f"Skipped {skipped} duplicate, empty, or unreadable file(s).")
    st.divider()
    st.caption("🔒 Your documents and search index stay on this computer. Embeddings run locally.")
    with st.expander("How answers are generated"):
        st.write("The assistant searches your documents in Hindi and English, then uses Ollama if available. If Ollama is not running, it shows matching passages with citations.")
    if st.session_state.get("messages") and st.button("🧹 Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

docs = list_documents()
st.markdown("""
<div class="hero">
  <div class="eyebrow">YOUR CAREER, BETTER PREPARED</div>
  <h1>Career knowledge, at your fingertips.</h1>
  <p>Ask questions about your resume, job descriptions, and career documents. बातचीत करें हिंदी, English, या Hinglish में.</p>
</div>
""", unsafe_allow_html=True)

metric_cols = st.columns(3)
metric_cols[0].metric("📄 Documents", len(docs), help="Files currently indexed in your local library")
metric_cols[1].metric("💬 Questions", sum(m["role"] == "user" for m in st.session_state.messages), help="Questions in this conversation")
metric_cols[2].metric("🌐 Languages", "Hindi + English", help="Hinglish questions work too")

ask_tab, library_tab = st.tabs(["💬  Ask your assistant", "🗂️  Your library & tips"])
with ask_tab:
    if not docs:
        st.info("**Start by adding a document** in the left panel. Your resume, a job description, or a career guide are great first files.")
    if not st.session_state.messages and docs:
        st.markdown("#### A few things you can ask")
        prompts = [
            "Which skills are mentioned in my documents?",
            "इस नौकरी के लिए कौन-से कौशल चाहिए?",
            "Mere resume mein kaunsa experience relevant hai?",
        ]
        prompt_cols = st.columns(3)
        for index, prompt in enumerate(prompts):
            if prompt_cols[index].button(prompt, key=f"prompt_{index}", use_container_width=True):
                st.session_state["pending_question"] = prompt
                st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander(f"📎 Sources / स्रोत ({len(message['sources'])})"):
                    for source in message["sources"]:
                        st.markdown(f"**{source['label']}**")
                        st.caption(source["preview"])

with library_tab:
    st.markdown("#### Your indexed documents")
    if docs:
        for doc in docs:
            with st.container(border=True):
                col_icon, col_name, col_state = st.columns([0.6, 5, 1.3])
                col_icon.markdown("📄")
                col_name.markdown(f"**{doc}**")
                col_state.caption("Ready to search")
    else:
        st.markdown("Your library is empty so far. Add a file from the left panel to get started.")
    st.markdown("#### Get better answers")
    tip1, tip2, tip3 = st.columns(3)
    with tip1:
        st.markdown("**🎯 Ask specifically**")
        st.caption("Name a role, skill, or experience you want to find.")
    with tip2:
        st.markdown("**🌍 Use your language**")
        st.caption("Ask in Hindi, English, or mix the two naturally.")
    with tip3:
        st.markdown("**🔎 Check the sources**")
        st.caption("Open citations to verify each answer in the original file.")
    st.info("Text-based PDFs work best. Scanned PDFs need OCR first. Excel citations include worksheet and row; Word files cite paragraph or table sections.")

typed_question = st.chat_input("Ask about your documents… / अपने दस्तावेज़ों के बारे में पूछें…", disabled=not docs)
question = st.session_state.pop("pending_question", None) or typed_question
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("🔍 Finding the most relevant passages…"):
            result = answer_question(question)
        st.markdown(result["answer"])
        if result["sources"]:
            with st.expander(f"📎 Sources / स्रोत ({len(result['sources'])})", expanded=True):
                for source in result["sources"]:
                    st.markdown(f"**{source['label']}**")
                    st.caption(source["preview"])
        st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result["sources"]})
