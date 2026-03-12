# 🔒 ISO 27001 / NIS2 Compliance Assistant

A specialised AI chatbot that helps organisations prepare for **ISO 27001:2022** certification and **NIS2 Directive** compliance. Built with LangChain, OpenAI GPT-4o, ChromaDB, and Streamlit.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **Advanced RAG** | Upload ISO PDFs, NIS2 docs, company policies — MultiQueryRetriever for query translation |
| **Source Citations** | Every answer referencing a document shows the filename and page |
| **Token Usage** | Live per-message and cumulative token counter with cost estimate |
| **Risk Calculator** | ISO 27001 likelihood × impact matrix with Annex A control suggestions |
| **Gap Analyser** | Checks all 93 ISO 27001:2022 Annex A controls, themed breakdown + NIS2 impact |
| **Policy Generator** | 5 ready-to-use policy templates (Access Control, Incident Response, Risk Mgmt, etc.) |
| **Control Mapper** | Maps any ISO 27001 control ↔ NIS2 Article 21/23 bidirectionally |
| **Quick Actions** | One-click buttons for common tasks |

---

## 🚀 Quick Start

### 1. Clone / download this project

```bash
git clone <your-repo>
cd iso-compliance-assistant
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 📁 Project Structure

```
iso-compliance-assistant/
├── app.py                  # Streamlit UI — main entry point
├── agent.py                # LangChain tool-calling agent + token tracking
├── rag_engine.py           # Document loading, ChromaDB, MultiQueryRetriever
├── compliance_tools.py     # All 5 LangChain tools + ISO 27001 & NIS2 data
├── config.py               # Central configuration
├── requirements.txt
├── .env.example
├── knowledge_base/         # Drop your PDFs here (optional — you can upload via UI)
└── chroma_db/              # Created automatically on first document index
```

---

## 🏗️ Architecture

```
User Input
    │
    ▼
Streamlit UI (app.py)
    │
    ▼
LangChain Agent (create_tool_calling_agent)
    │
    ├── search_documents ──► MultiQueryRetriever ──► ChromaDB (RAG)
    │                              │
    │                        Query Translation
    │                    (3 query variants via GPT-4o-mini)
    │
    ├── calculate_risk_score    (likelihood × impact matrix)
    ├── analyze_compliance_gaps (93 Annex A controls + NIS2 mapping)
    ├── generate_policy_template (5 policy types)
    └── map_iso_nis2_controls   (bidirectional ISO ↔ NIS2)
```

### RAG Pipeline Detail

1. **Ingestion:** PDFs/DOCX/TXT → `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)
2. **Embedding:** `text-embedding-3-small` via OpenAI
3. **Storage:** ChromaDB with persistence (`./chroma_db/`)
4. **Retrieval:** `MultiQueryRetriever` generates 3 alternative phrasings of your question, retrieves top-6 for each, deduplicates — dramatically improves recall for complex compliance questions

---

## 🛠️ Tools Reference

### 1. `search_documents`
Searches the uploaded knowledge base. Used automatically when you ask about document content.

### 2. `calculate_risk_score`
```
Asset: Customer Database
Asset value: 5/5
Threat likelihood: 3/5
Vulnerability level: 4/5
→ Risk Score: 17/25 (HIGH)
```

### 3. `analyze_compliance_gaps`
Input comma-separated control IDs you've implemented:
```
5.1, 5.2, 6.3, 8.5, 8.7, 8.13
→ 6/93 controls (6.5%) | 87 gaps identified
→ Critical gaps: 5.4, 5.9, 5.12...
→ NIS2 impact: Art.21(a), Art.21(g)...
```

### 4. `generate_policy_template`
Available templates:
- `access_control` — ISO 5.15–5.18, 8.2, 8.5
- `incident_response` — ISO 5.24–5.28, NIS2 Art.21(b), Art.23
- `risk_management` — ISO Clause 6.1, NIS2 Art.21(a)
- `data_classification` — ISO 5.12–5.13
- `supplier_security` — ISO 5.19–5.22, NIS2 Art.21(d)

### 5. `map_iso_nis2_controls`
```
Input: "8.5"  →  Art.21(i) (access control), Art.21(j) (MFA)
Input: "Art.21(b)"  →  5.24, 5.25, 5.26, 5.27, 5.28, 6.8
```

---

## 📄 Recommended Documents to Upload

| Document | Where to Get |
|----------|-------------|
| ISO/IEC 27001:2022 | Purchase from ISO store |
| NIS2 Directive (EU) 2022/2555 | eur-lex.europa.eu (free) |
| ISO/IEC 27002:2022 (implementation guide) | Purchase from ISO store |
| Your company's existing policies | Internal |
| Previous audit reports | Internal |
| Risk register | Internal |

---

## ⚠️ Known Limitations

- **ISO 27001 full text:** The standard itself is copyrighted and must be purchased. The assistant has built-in knowledge of all 93 Annex A controls but for detailed clause text you need to upload the official PDF.
- **Rate limits:** Heavy use may hit OpenAI rate limits. The app handles these gracefully.
- **ChromaDB persistence:** The `chroma_db/` folder is local. For production, consider a hosted vector database.

---

## 🔒 Security Notes

- API keys are never stored or logged
- Uploaded documents are processed in memory (temp files deleted immediately)
- ChromaDB data is stored locally — keep it out of version control

---

## 📜 Compliance Coverage

| Standard | Coverage |
|----------|---------|
| ISO 27001:2022 | All 93 Annex A controls, Clauses 4–10 |
| NIS2 Directive | Articles 21, 23, 24, 26 |
| ISO 27001 ↔ NIS2 | Full bidirectional mapping |
| GDPR | Basic overlap via data classification & access control |
