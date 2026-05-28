# ⚖️ GovGPT — RTI in 60 Seconds
**Scaler × Meta AI PyTorch Hackathon 2026** | **Team DLC**

![GovGPT Banner](https://img.shields.io/badge/Gemini-1.5_Pro-blueviolet?style=for-the-badge&logo=google)
![Python Flask](https://img.shields.io/badge/Flask-Backend-black?style=for-the-badge&logo=flask)
![ChromaDB RAG](https://img.shields.io/badge/ChromaDB-RAG-blue?style=for-the-badge)

GovGPT is an AI-powered legal assistant designed to democratize the Right to Information (RTI) Act for 70 crore rural Indians. By combining Gemini 1.5 Pro, Voice-to-Text, and a localized RAG architecture, GovGPT drafts legally precise, Section 6 compliant RTI applications in under 60 seconds — in both Hindi and English.

---

## 🔥 Key Features

- **🎙️ Multilingual Voice Input:** Speak your problem naturally in Hindi, Hinglish, or English.
- **🧠 900+ Department Routing:** GovGPT automatically maps the citizen's problem to the exact Ministry, State Department, or District Officer responsible.
- **📚 RAG-Grounded Legal Logic:** Uses ChromaDB to fetch rules from actual scheme documents (PM Kisan, MGNREGA, Ayushman Bharat, etc.) to ensure factual accuracy.
- **⚡ Live Streaming Output:** Token-by-token streaming using Server-Sent Events (SSE) for a ChatGPT-like experience.
- **📄 Professional A4 PDF:** One-click download of a properly formatted, legally binding application ready for print and post.
- **🎨 Premium UI/UX:** Glassmorphism dark mode with fully responsive mobile design.

---

## 🛠️ Architecture

1. **Frontend:** Vanilla HTML/CSS/JS with Markdown parsing (`marked.js`) and PDF generation (`jsPDF`).
2. **Backend:** Python Flask API serving Server-Sent Events (SSE).
3. **LLM:** Google Gemini 1.5 Pro via `google-genai` SDK.
4. **Vector DB:** Local ChromaDB instance with overlapping text chunks and `text-embedding-004`.

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
```
*(Get a free key from [Google AI Studio](https://aistudio.google.com/))*

### 3. Initialize the RAG Database
Run the ingestion script to process the government scheme PDFs/texts into ChromaDB:
```bash
python ingest.py
```

### 4. Start the Server
```bash
python app.py
```

### 5. Use the App
Open Google Chrome (required for voice input) and navigate to:
**http://localhost:5000**

---

## 🎯 The Hackathon Pitch

**The Problem:** 88% of rural Indians have never filed an RTI. They are denied rations, pensions, and housing benefits but lack the legal literacy to demand accountability.

**The Solution:** GovGPT bridges the gap between natural language complaints and rigid legal formats. 
- "Mera ration nahi mil raha" (My ration is denied) is transformed into a formal demand for the Fair Price Shop stock register addressed to the District Supply Officer.

**The Impact:** Zero cost to the citizen. Legally binding. 30-day statutory response time.

---

*Developed by Kartik Gupta & Team DLC for the Scaler Hackathon.*
