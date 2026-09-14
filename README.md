# Land Acquisition Intelligence Platform — AI / GenAI Module

An AI-powered intelligence layer for a Web-based National Land Acquisition & Management System.

This repository contains the AI/GenAI components developed for the land-acquisition platform, covering document intelligence, grounded retrieval, contextual copilot, natural-language analytics, project MIS generation, multilingual interaction, voice-based assistance, and unified intelligence APIs.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B)
![LangChain](https://img.shields.io/badge/LangChain-RAG-green)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-blueviolet)
![Status](https://img.shields.io/badge/Project-Learning-blue)

---

## 🎯 What This AI Layer Solves

Land acquisition workflows involve large volumes of heterogeneous records such as:

- Land records
- Acquisition notifications
- Awards and compensation documents
- Survey and parcel records
- Possession records
- Rehabilitation & Resettlement documents
- Inspection reports
- Scanned regional-language documents

The AI layer converts these fragmented records into an evidence-grounded intelligence system that can:

- Understand and structure land-acquisition documents
- Retrieve relevant evidence using semantic and deterministic search
- Answer parcel and project questions with citations
- Detect conflicts between authoritative database facts and documents
- Run natural-language analytics over PostgreSQL
- Generate project-level MIS reports
- Support English, Hindi, and Marathi
- Accept multilingual voice queries
- Generate spoken responses using Sarvam AI
- Expose unified intelligence APIs for Web/GIS integration

---

# 🏗️ AI Architecture

```text
                           LAND ACQUISITION AI
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
        Document Intelligence   PostgreSQL       Voice Layer
                │                 │                 │
                ▼                 │          Sarvam STT / TTS
        OCR + Extraction          │                 │
                │                 │                 │
                ▼                 │                 │
        Metadata + Chunking       │                 │
                │                 │                 │
        ┌───────┴───────┐         │                 │
        ▼               ▼         │                 │
    ChromaDB        PostgreSQL     │                 │
    Semantic       Structured     │                 │
    Retrieval        Facts        │                 │
        │               │         │                 │
        └───────┬───────┘         │                 │
                ▼                 ▼                 ▼
          Grounded RAG       NL Analytics       Voice Copilot
                │                 │                 │
                └──────────┬──────┴─────────────────┘
                           ▼
                    AI MIS / Reports
                           │
                           ▼
               Unified Intelligence APIs
                           │
                           ▼
                     Web / GIS Frontend
```

---

# 🚀 Major Capabilities

## 1. Document Intelligence & Structured Extraction

Supports ingestion of heterogeneous land-acquisition documents:

- PDF
- DOCX
- PPTX
- XLSX
- CSV
- TXT
- Images / scanned documents

### Processing Pipeline

```text
Document Upload
      ↓
SHA-256 Duplicate Detection
      ↓
Text / OCR Extraction
      ↓
Language Detection
      ↓
Metadata Classification
      ↓
Structured Entity Extraction
      ↓
Structure-Aware Chunking
      ↓
PostgreSQL + ChromaDB
```

### Land-Specific Structured Entities

The extraction pipeline handles concepts such as:

- Projects
- Villages
- Parcels
- Survey numbers
- Landowners
- Acquisition cases
- Compensation awards
- Acquisition stages
- Document categories

### Structured Data

PostgreSQL stores authoritative structured information such as:

```text
Parcel
Landowner
Acquisition Case
Compensation Award
Document ↔ Parcel mapping
Project metadata
```

PostgreSQL is treated as the authoritative source for structured numerical and project facts.

---

# 🔎 2. Grounded Retrieval-Augmented Generation (RAG)

The RAG system is designed around **evidence grounding rather than generic LLM generation**.

## Retrieval Architecture

```text
User Query
    ↓
Deterministic Query Parser
    ↓
Structured Filters
    │
    ├── Project
    ├── District
    ├── Village
    ├── Survey Number
    ├── Parcel ID
    ├── Document Category
    └── Acquisition Stage
          ↓
┌────────────────────────────┐
│ PostgreSQL authoritative    │
│ lookup                     │
└────────────────────────────┘
          +
┌────────────────────────────┐
│ Chroma semantic retrieval  │
└────────────────────────────┘
          ↓
Deterministic Ranking
          ↓
Evidence Fusion
          ↓
Conflict Detection
          ↓
Grounded LLM Response
```

### Retrieval Principles

- Exact survey/entity matches receive priority
- Project and parcel context are respected
- PostgreSQL facts are separated from document evidence
- ChromaDB is used for semantic retrieval, not as the authoritative database
- Retrieved evidence is explicitly tracked
- Citation metadata is validated against actual retrieved evidence
- Unsupported facts are not generated when evidence is insufficient

---

# 🧠 3. Grounded Land Acquisition Copilot

The contextual copilot allows users to ask questions about a selected project or parcel.

Example questions:

> What is the acquisition status of this parcel?

> What compensation was awarded?

> What does the award say about possession?

> Are there any conflicting records?

> Summarize all documents for this parcel.

### Evidence-Aware Responses

Responses contain:

- Answer
- Evidence coverage
- Source citations
- Detected conflicts
- Structured database facts
- Document evidence

Supported evidence states:

```text
COMPLETE
PARTIAL
INSUFFICIENT
```

The system explicitly reports insufficient evidence instead of hallucinating.

![Land Acquisition Copilot](images/Land%20Acquisition%20Copilot.png)
*Context-aware copilot with grounded evidence, citations, and conflict detection.*

---

# ⚠️ 4. Deterministic Conflict Detection

One of the key features of the platform is the ability to identify inconsistencies between authoritative database records and document evidence.

Example:

```text
Database Fact:
Area = 0.45 hectares

Document Evidence:
Area = 0.52 hectares
Surveyor Field Inspection Report, Page 4
```

The system reports:

```text
CONFLICT DETECTED
```

rather than silently selecting one value.

### Conflict Categories

- Numerical discrepancies
- Structured field inconsistencies
- Cross-document conflicts
- Database vs document mismatches

---

# 📊 5. Natural-Language Land Acquisition Analytics

A separate analytics layer operates directly over the structured PostgreSQL database.

Example questions:

```text
How many parcels have compensation pending?

What is the total awarded compensation?

How many parcels are in each village?

How many parcels are at Award Pending stage?

Show parcels in Vadadala where possession is pending.
```

### Secure Architecture

```text
Natural Language Query
        ↓
Structured AnalyticsRequest
        ↓
Pydantic Validation
        ↓
Allowlisted Operations
        ↓
Deterministic Parameterized SQL
        ↓
PostgreSQL
        ↓
Structured Result
        ↓
Optional LLM Explanation
```

The LLM is **never allowed to generate or execute arbitrary SQL**.

Supported analytical operations include:

- COUNT
- SUM
- AVG
- GROUP_BY
- Structured filtering

### Security Principles

- No arbitrary SQL generated by the LLM
- Pydantic schema validation
- Allowlisted operations and fields
- Parameterized SQL queries
- Secondary malicious-query rejection

---

# 📑 6. AI MIS & Project Report Generation

Project-level reports combine:

- PostgreSQL structured facts
- Existing RAG evidence
- Deterministic analytics
- Detected conflicts
- Document citations

### Report Sections

- Executive Summary
- Acquisition Progress
- Compensation Status
- Rehabilitation & Resettlement
- Possession Status
- Document Evidence
- Data Quality / Conflicts
- Overall Current Status

All numerical project metrics are calculated deterministically before being passed to the LLM.

The LLM is responsible for **grounded summarization and formatting**, not authoritative calculation.

Reports are downloadable as Markdown.

---

# 🌐 7. Multilingual Land Document Intelligence

The AI layer supports:

- English
- Hindi
- Marathi

### Multilingual Pipeline

```text
Hindi / Marathi / English Document
            ↓
Language-Aware OCR
            ↓
Language Detection
            ↓
Terminology Normalization
            ↓
Multilingual Embedding
            ↓
Cross-Language Retrieval
            ↓
Grounded Response
```

### Cross-Language Capabilities

Examples:

```text
Hindi document → English query
Marathi document → English query
English document → Hindi query
English document → Marathi query
```

Source document names, survey identifiers, and citation page numbers remain preserved in their original form.

### Land Terminology Normalization

Examples:

```text
मौजे / गाव        → village
तालुका / तहसील   → tehsil
जिल्हा / जिला    → district
गट क्र / खसरा नं → survey number
मुआवजा            → compensation
ताबा              → possession
पुनर्वसन          → rehabilitation / R&R
```

Original source text is preserved alongside normalized concepts.

---

# 🎙️ 8. Multilingual Voice Copilot — Sarvam AI

The voice layer enables natural-language interaction using:

- English
- Hindi
- Marathi

![Multilingual Voice Copilot](images/Multilingual%20voice%20Copilot.png)

### Voice Pipeline

```text
🎙️ User Speech
      ↓
Sarvam Speech-to-Text
      ↓
Text Query
      ↓
Existing Grounded RAG
      ↓
Answer + Citations + Evidence
      ↓
Sarvam Text-to-Speech
      ↓
🔊 Spoken Response
```

The voice layer is implemented as an adapter around the existing RAG system and does not duplicate retrieval logic.

### Voice Capabilities

- Microphone input
- Audio upload fallback
- Automatic / explicit language selection
- Speech-to-text
- Grounded RAG answer
- Text-to-speech
- Graceful fallback to text if TTS is unavailable

### Voice Interaction

```text
Voice Input
    ↓
Transcript
    ↓
Grounded Answer
    ↓
Source Citations
    ↓
Voice Response
```

---

# 🧩 9. Unified Intelligence APIs

The AI modules are exposed through FastAPI for integration with the Web/GIS frontend.

### Core APIs

```text
POST /ask
POST /analytics/query
POST /reports/project
```

### Unified Intelligence APIs

```text
GET /parcels/{parcel_id}/intelligence
GET /projects/{project_id}/intelligence
```

These APIs can aggregate relevant:

- Structured parcel/project facts
- Document evidence
- Conflicts
- Attention categories
- Anomaly results when available

### Current-State Attention Categories

```text
DATA_CONFLICT
ANOMALY_DETECTED
COMPENSATION_PENDING
POSSESSION_PENDING
R_AND_R_PENDING
DOCUMENT_MISSING
VERIFICATION_REQUIRED
```

The system intentionally does **not** implement future delay prediction in this module.

---

# 🛡️ Security & Reliability

## Grounded Generation

The LLM is explicitly instructed to:

- Use only supplied evidence
- Never invent facts
- Preserve exact numbers, dates, and identifiers
- Distinguish database facts from document evidence
- Report insufficient evidence
- Preserve citations
- Avoid unsupported legal conclusions

## Analytics Security

- No arbitrary SQL generated by LLM
- Pydantic schema validation
- Allowlisted operations and fields
- Parameterized SQL queries
- Secondary malicious-query rejection

## Voice & API Security

- API keys stored in environment variables
- API keys never hardcoded
- API keys never returned in responses
- Provider failures handled gracefully
- Invalid inputs rejected safely
- Voice service credentials are never exposed to the frontend

---

# 🧰 Technology Stack

## Backend

- Python
- FastAPI
- Pydantic
- PostgreSQL
- ChromaDB
- Uvicorn

## AI / NLP

- Ollama
- Llama 3.1 8B
- mxbai-embed-large
- Retrieval-Augmented Generation
- Structured LLM parsing

## Document Intelligence

- PyMuPDF
- python-docx
- python-pptx
- openpyxl
- Tesseract OCR
- Image/document parsing

## Voice

- Sarvam AI
- Speech-to-Text
- Text-to-Speech

## Frontend / Demo

- Streamlit

---

# 📈 Validation & Test Results

The implementation has been validated through dedicated automated test suites.

| Module | Tests | Result |
|---|---:|---|
| Phase 4 Contextual Copilot | 8 | ✅ 8/8 |
| Phase 5 Analytics | 10 | ✅ 10/10 |
| Phase 6 MIS Reports | 10 | ✅ 10/10 |
| Phase 7 Multilingual | 12 | ✅ 12/12 |
| Phase 8 Integration | 12 | ✅ 12/12 |
| Phase 9 Voice | 21 | ✅ 21/21 |

### Multilingual Retrieval Benchmark

Controlled cross-language retrieval testing achieved:

```text
English → English      100% Hit Rate
Hindi → Hindi          100% Hit Rate
Marathi → Marathi      100% Hit Rate
Hindi → English        100% Hit Rate
Marathi → English      100% Hit Rate
English → Hindi        100% Hit Rate
English → Marathi      100% Hit Rate
```

These results are from controlled prototype/test fixtures and should not be interpreted as production-scale benchmark performance.

---

# 🗂️ Project Structure

```text
Land_knowledge_intelligence/
│
├── backend/
│   ├── analytics/
│   ├── core/
│   ├── embedding/
│   ├── models/
│   ├── parsers/
│   ├── services/
│   ├── utils/
│   ├── vectorstore/
│   └── main.py
│
├── frontend/
│   ├── pages/
│   │   ├── 2_chat.py
│   │   ├── 3_analytics.py
│   │   └── 4_reports.py
│   ├── api.py
│   └── app.py
│
├── tests/
│   ├── test_phase4_copilot.py
│   ├── test_analytics.py
│   ├── test_reports.py
│   ├── test_multilingual.py
│   ├── test_integration_contracts.py
│   └── test_voice.py
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

# ⚙️ Local Setup

## 1. Create the Python environment

```powershell
py -3.13 -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 3. Configure environment variables

Create a `.env` file in the project root:

```env
SARVAM_API_KEY=your_sarvam_api_key
```

Never commit `.env`.

---

# ▶️ Running the Application

## Start FastAPI

From the project root:

```powershell
python -m uvicorn backend.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Start Streamlit

Open another terminal:

```powershell
cd frontend
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

---

# 🔬 Running Tests

Run individual suites:

```powershell
python -m unittest tests.test_phase4_copilot -v
python -m unittest tests.test_analytics -v
python -m unittest tests.test_reports -v
python -m unittest tests.test_multilingual -v
python -m unittest tests.test_integration_contracts -v
python -m unittest tests.test_voice -v
```

---

# 🔮 Integration Roadmap

The AI backend is designed to integrate with the final Web/GIS frontend.

```text
Web / GIS
    ↓
FastAPI
    ├── RAG / Copilot
    ├── Analytics
    ├── MIS Reports
    ├── Voice
    └── Intelligence APIs
            ↓
      PostgreSQL / ChromaDB
```

The anomaly-detection ML component is designed to connect through the existing `AnomalyService` / `AnomalyItem` contract without coupling the frontend directly to the model implementation.

---

# ⚠️ Current Limitations

- Multilingual OCR for scanned Devanagari documents depends on the corresponding Tesseract language packs being installed.
- Multilingual retrieval benchmarks are controlled prototype benchmarks, not production-scale evaluations.
- Voice functionality depends on valid Sarvam API access and network connectivity.
- The current in-memory analytics fallback is intended for offline/demo usage; PostgreSQL remains the authoritative production source.
- Final Web/GIS integration depends on the frontend implementation.
- The anomaly-detection model integration is designed through the Phase 8 contract and may remain deployment-dependent until the external model service is connected.

---

# 👨‍💻 AI / GenAI Contributions

### Core contributions in this module

- Designed and implemented the domain-adapted RAG architecture
- Built deterministic + semantic hybrid retrieval
- Implemented land-document metadata classification
- Implemented structured land and compensation extraction
- Added SHA-256 duplicate detection and stale vector cleanup
- Added survey/entity normalization
- Built grounded RAG with evidence coverage
- Implemented deterministic conflict detection
- Built contextual parcel/project copilot
- Built natural-language PostgreSQL analytics
- Built AI MIS/project report generation
- Implemented multilingual document and query handling
- Implemented cross-language retrieval
- Integrated Sarvam multilingual voice interaction
- Built unified intelligence APIs and frontend integration contracts
- Added automated regression, security, and integration testing across the AI stack

---

# 📌 Design Philosophy

This AI layer is designed around one principle:

> **Use AI to understand and interact with land-acquisition data, while keeping authoritative records and evidence outside the LLM.**

Structured facts come from PostgreSQL.

Document evidence comes from retrieved source documents.

Semantic retrieval comes from ChromaDB.

The LLM provides grounded interpretation and interaction.

This separation improves traceability, reduces hallucination risk, and allows the same intelligence services to power conversational, analytical, reporting, voice, and GIS workflows.
