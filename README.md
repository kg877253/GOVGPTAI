# ⚖️ GovGPT — RTI in 60 Seconds
**Scaler × Meta AI PyTorch Hackathon 2026** | **Team DLC**

![GovGPT Banner](https://img.shields.io/badge/Gemini-2.0_Flash-blueviolet?style=for-the-badge&logo=google)
![Python Flask](https://img.shields.io/badge/Flask-Backend-black?style=for-the-badge&logo=flask)
![ChromaDB RAG](https://img.shields.io/badge/ChromaDB-RAG-blue?style=for-the-badge)
![Version 2.0](https://img.shields.io/badge/Version-2.0.0-green?style=for-the-badge)

GovGPT is an AI-powered legal assistant designed to democratize the Right to Information (RTI) Act for 70 crore rural Indians. By combining Gemini 2.0 Flash, Voice-to-Text, and a localized RAG architecture, GovGPT drafts legally precise, Section 6 compliant RTI applications in under 60 seconds — in both Hindi and English.

---

## 🔥 Key Features

### Core Capabilities
- **🎙️ Multilingual Voice Input:** Speak your problem naturally in Hindi, Hinglish, or English.
- **🧠 900+ Department Routing:** GovGPT automatically maps the citizen's problem to the exact Ministry, State Department, or District Officer responsible.
- **📚 RAG-Grounded Legal Logic:** Uses ChromaDB to fetch rules from actual scheme documents (PM Kisan, MGNREGA, Ayushman Bharat, etc.) to ensure factual accuracy.
- **⚡ Live Streaming Output:** Token-by-token streaming using Server-Sent Events (SSE) for a ChatGPT-like experience.
- **📄 Professional A4 PDF:** One-click download of a properly formatted, legally binding application ready for print and post.
- **🎨 Premium UI/UX:** Glassmorphism dark mode with fully responsive mobile design.

### Version 2.0 Enhancements
- **🛡️ Rate Limiting:** 30 requests per minute per IP to prevent abuse
- **💾 Response Caching:** 1-hour TTL cache for repeated queries (reduces API costs)
- **🔄 Automatic Retry:** 3-attempt retry logic with exponential backoff for API failures
- **📊 Monitoring Endpoints:** `/health`, `/stats`, and `/api/docs` for system monitoring
- **🔍 Hybrid Search:** Semantic + keyword-based retrieval for better RAG accuracy
- **📕 PDF Support:** Ingest both PDF and text files for scheme documentation
- **⚡ Incremental Updates:** Only reprocess changed files (SHA256 hash tracking)
- **🧹 Input Sanitization:** XSS protection and input validation
- **📝 Enhanced System Prompt:** 10 drafting rules for legally precise RTI applications
- **📋 Comprehensive Logging:** File and console logging with structured format

---

## 🛠️ Architecture

1. **Frontend:** Vanilla HTML/CSS/JS with Markdown parsing (`marked.js`) and PDF generation (`jsPDF`).
2. **Backend:** Python Flask API serving Server-Sent Events (SSE).
3. **LLM:** Google Gemini 2.0 Flash via `google-genai` SDK (faster, cheaper than 1.5 Pro).
4. **Vector DB:** Local ChromaDB instance with overlapping text chunks and `text-embedding-004`.
5. **Caching:** In-memory cache with TTL for repeated queries.
6. **Logging:** Dual logging (file + console) with automatic log rotation.

---

## 🚀 How to Run Locally

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Set API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=5000
AUTO_INGEST=0  # Set to 1 to auto-ingest on startup
```
*(Get a free key from [Google AI Studio](https://aistudio.google.com/))*

### 3. Initialize the RAG Database
Run the ingestion script to process the government scheme PDFs/texts into ChromaDB:
```bash
python ingest.py
```

**New in v2.0:** Supports both `.txt` and `.pdf` files in the `data/` directory. Uses incremental updates - only reprocesses changed files.

Force reingest all files:
```python
from ingest import ingest_data
ingest_data(force_reingest=True)
```

### 4. Start the Server
```bash
python app.py
```

### 5. Use the App
Open Google Chrome (required for voice input) and navigate to:
**http://localhost:5000**

---

## 📊 API Endpoints

- `GET /` - Main web application
- `GET /health` - Health check with system status
- `GET /health/gemini` - Validate Gemini API key and quota
- `GET /stats` - System statistics (cache size, request counts)
- `GET /api/docs` - API documentation
- `GET /stream?problem=...&name=...&address=...` - SSE endpoint for RTI generation

---

## 🎯 The Hackathon Pitch

**The Problem:** 88% of rural Indians have never filed an RTI. They are denied rations, pensions, and housing benefits but lack the legal literacy to demand accountability.

**The Solution:** GovGPT bridges the gap between natural language complaints and rigid legal formats. 
- "Mera ration nahi mil raha" (My ration is denied) is transformed into a formal demand for the Fair Price Shop stock register addressed to the District Supply Officer.

**The Impact:** Zero cost to the citizen. Legally binding. 30-day statutory response time.

---

## 📁 Project Structure

```
govgpt/
├── app.py              # Main Flask application with rate limiting, caching, retry logic
├── rag.py              # Hybrid RAG with semantic + keyword search
├── ingest.py           # PDF/text ingestion with incremental updates
├── requirements.txt    # Python dependencies
├── .env                # API keys (not in git)
├── .gitignore          # Git ignore rules
├── data/               # Government scheme documents (.txt, .pdf)
├── chroma_db/          # Vector database (auto-created)
├── logs/               # Application logs (auto-created)
└── templates/
    └── index.html      # Frontend UI
```

---

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY` - Required: Your Google AI Studio API key
- `GEMINI_MODEL` - Optional: Model to use (default: gemini-2.0-flash)
- `PORT` - Optional: Server port (default: 5000)
- `AUTO_INGEST` - Optional: Auto-ingest on startup (default: 0)

### Rate Limiting
- Default: 30 requests per minute per IP
- Configurable via `RATE_LIMIT` constant in `app.py`

### Caching
- Default: 1 hour TTL
- Configurable via `CACHE_TTL` constant in `app.py`
- Max cache size: 100 entries

---

## 📈 Monitoring

Check system health:
```bash
curl http://localhost:5000/health
```

View statistics:
```bash
curl http://localhost:5000/stats
```

View API documentation:
```bash
curl http://localhost:5000/api/docs
```

---

## 🐛 Troubleshooting

**Issue:** ChromaDB connection error
**Solution:** Run `python ingest.py` first to initialize the database

**Issue:** Rate limit exceeded
**Solution:** Wait 1 minute or adjust `RATE_LIMIT` in `app.py`

**Issue:** API quota exhausted
**Solution:** System automatically falls back to template-based RTI generation

**Issue:** PDF not ingesting
**Solution:** Ensure `pypdf` is installed: `pip install pypdf>=4.0.0`

---

*Developed by Kartik Gupta & Team DLC for the Scaler Hackathon.*
