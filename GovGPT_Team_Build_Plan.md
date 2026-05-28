# GovGPT — Complete Team Build Plan
### Team DLC | Scaler × Meta AI PyTorch Hackathon 2026 | Deadline: 29th May

---

## The One-Line Summary
User speaks/types problem in Hindi or English → AI identifies correct govt department → writes Section 6 RTI application → user downloads PDF. All in 60 seconds.

---

## Tech Stack (exactly as submitted in PPTX)
| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| AI Model | Gemini 1.5 Pro |
| AI Framework | LangChain |
| Vector Database | ChromaDB |
| Embeddings | Google Generative AI Embeddings |
| Streaming | Server-Sent Events (SSE) |
| Voice Input | Web Speech API (Chrome, lang: hi-IN) |
| PDF Generation | jsPDF (CDN) |
| Deployment | Render.com (backend) + GitHub Pages (frontend) |

---

## Team Roles — Fixed, No Overlap

| Person | Role | Files They Own |
|---|---|---|
| **Kartik (YOU)** | Lead + Backend + AI | `app.py`, `rag.py`, `ingest.py` |
| Teammate 2 | Frontend + Voice + PDF | `templates/index.html`, `style.css` |
| Teammate 3 | Data + RAG + ChromaDB | `/data` folder, `chroma_db/` |
| Teammate 4 | QA + Testing + Demo | `README.md` |

> **Rule:** Nobody edits another person's files without asking Kartik first. Kartik is the integration point — everything connects through him.

---

## Project Folder Structure

```
govgpt/
│
├── app.py                ← Kartik. Flask server. Gemini. SSE streaming.
├── rag.py                ← Kartik. Connects to ChromaDB. Returns scheme context.
├── ingest.py             ← Kartik. Run ONCE. Loads PDFs into ChromaDB.
├── .env                  ← Kartik only. NEVER on GitHub.
├── .gitignore            ← Kartik. Excludes .env, venv/, chroma_db/ etc.
├── requirements.txt      ← Kartik. pip freeze > requirements.txt
│
├── data/                 ← Teammate 3. Put all govt scheme PDFs here.
│   ├── pm_kisan.pdf
│   ├── ayushman.pdf
│   ├── mgnrega.pdf
│   └── ... (8-10 PDFs total)
│
├── chroma_db/            ← Auto-created when ingest.py runs. RAG vector store.
│
└── templates/
    └── index.html        ← Teammate 2. Entire UI — HTML, CSS, JavaScript.
```

---

## How All Files Talk to Each Other

```
index.html
    │
    │  (user clicks Generate)
    │  EventSource('http://localhost:5000/stream?problem=...')
    ▼
app.py  (Flask receives the request)
    │
    ├──► rag.py → get_context(problem)
    │         │
    │         └──► chroma_db/ → returns top 3 relevant scheme chunks
    │
    ├──► Combines: system_prompt + scheme_context + user_problem
    │
    └──► Gemini 1.5 Pro → streams RTI text token by token
              │
              ▼
         index.html receives tokens via EventSource
         Displays words one by one (like ChatGPT typing)
              │
              ▼
         User clicks Download → jsPDF creates PDF
```

---

## How GitHub Keeps Everyone in Sync

GitHub is the shared codebase stored on the internet.
Every teammate has a copy on their own laptop.
When someone finishes work, they push to GitHub. Others pull and get the update.

### Step 1 — Kartik creates the repo (do this TODAY)

```bash
# On your laptop
mkdir govgpt
cd govgpt
git init
mkdir templates data
touch app.py rag.py ingest.py .env .gitignore requirements.txt templates/index.html

# Push to GitHub
git add .
git commit -m "initial project structure"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/govgpt.git
git push -u origin main
```

Then go to: GitHub repo → Settings → Collaborators → Add all 3 teammates by their GitHub username.

### Step 2 — Every teammate clones (everyone does this ONCE)

```bash
git clone https://github.com/YOUR_USERNAME/govgpt.git
cd govgpt
```

Now all 4 people have the same folder on their laptops.

### Step 3 — Daily Git workflow (everyone, every day)

```bash
# Morning — before touching any file
git pull

# During the day — every 1-2 hours
git add .
git commit -m "what you did"

# End of day — upload your work
git push
```

### .gitignore file content (paste this exactly)

```
.env
venv/
__pycache__/
*.pyc
```

### .env file content (share on WhatsApp privately — NEVER GitHub)

```
GEMINI_API_KEY=paste_your_actual_key_here
```

Every teammate creates this file manually on their own laptop.

---

## How Frontend Connects to Backend

The entire connection between `index.html` and `app.py` is **one line of JavaScript:**

```javascript
const es = new EventSource('http://localhost:5000/stream?problem=ration+card&name=Ram&address=Bihar');
```

- `index.html` calls this URL when user clicks Generate
- `app.py` has a route `/stream` that responds to this URL
- Flask streams RTI text back word by word
- JavaScript displays each word as it arrives

**Teammate 2 only needs to know:** the URL is `http://localhost:5000/stream` and it takes `problem`, `name`, `address` as parameters.

**Kartik only needs to know:** make `/stream` respond to GET requests with those 3 parameters.

They never touch each other's files. The URL is the contract.

### After deployment, change ONE line

During development: `http://localhost:5000/stream`
After Render deployment: `https://govgpt.onrender.com/stream`

Teammate 2 updates this one line in `index.html`, pushes to GitHub. Done.

---

## DAY 1 — Everyone Works Independently

**Goal:** Backend returns RTI via curl. T2 has voice input working. T3 has ChromaDB built. T4 has 20 test cases written.

---

### Kartik (9 AM – 9 PM)

**9 AM — Install everything**
```bash
pip install flask flask-cors langchain langchain-google-genai chromadb pypdf python-dotenv
```
Get Gemini API key from **aistudio.google.com** → Get API Key → copy it.
Paste into `.env` as `GEMINI_API_KEY=your_key_here`

**11 AM — Write basic app.py**
- Flask app with one `/generate` POST route
- No RAG yet, no streaming yet
- Just connect to Gemini and get any RTI text back
- Test with curl:
```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"problem":"ration card nahi mila","name":"Ram Kumar","address":"Bihar"}'
```
If you get RTI text back — basic backend works.

**1 PM — Write the RTI system prompt**
This is the most important task of Day 1. The system prompt tells Gemini:
- What format to follow (Section 6 of RTI Act 2005)
- How to identify the correct department
- What legal language to use
Test with 5 different problems. Keep fixing until format is correct.

**4 PM — Write ingest.py and rag.py**
Send `ingest.py` to Teammate 3. Help them debug on call.

**7 PM — Connect RAG to app.py**
`/generate` now uses ChromaDB context before calling Gemini.
Test: "Am I eligible for PM Kisan?" → verify scheme info appears in RTI.

---

### Teammate 2 — Frontend (all day)

**Morning:**
Build static `index.html` — header, name field, address field, problem textarea, Generate button, empty output div, Download button. CSS only. No JavaScript yet. Make it look clean and professional.

**Afternoon:**
Add Hindi voice input:
```javascript
const recognition = new webkitSpeechRecognition();
recognition.lang = 'hi-IN';
recognition.onresult = (e) => {
    document.getElementById('problem').value = e.results[0][0].transcript;
};
```
Test in Chrome browser (voice ONLY works in Chrome). No backend needed for this.

**Evening:**
Add placeholder JS — clicking Generate shows "Generating..." in output div. Real backend connection is Day 2. Share `index.html` with Kartik on WhatsApp for review.

---

### Teammate 3 — Data + RAG (all day)

**Morning:**
Download 8+ government scheme PDFs from **myscheme.gov.in** and **india.gov.in**:
1. PM Kisan Samman Nidhi
2. PM Awas Yojana (Gramin)
3. PM Awas Yojana (Urban)
4. Ayushman Bharat PM-JAY
5. MGNREGA
6. National Social Assistance Programme (pension)
7. PM Garib Kalyan Anna Yojana (ration)
8. Pradhan Mantri Ujjwala Yojana
9. Beti Bachao Beti Padhao
10. Scholarship schemes (NSP)

Put all PDFs in the `/data` folder.

**Afternoon:**
Install Python packages (same as Kartik).
Get `ingest.py` from Kartik.
Run it:
```bash
python ingest.py
```
Wait for: `Done. Ingested X chunks from Y pages.`
Share the entire `chroma_db/` folder with Kartik via Google Drive.

**Evening:**
Open Google Docs. Write the department mapping list — at least 30 entries:
```
ration card / PDS / food grain → Department of Food & Public Distribution
pension / NSAP → Ministry of Rural Development
road (national) → Ministry of Road Transport & Highways
road (village/state) → PWD, State Government
MGNREGA / job card → Ministry of Rural Development
PM Kisan / farming → Ministry of Agriculture & Farmers Welfare
PM Awas / house → Ministry of Housing & Urban Affairs
Ayushman / health card → Ministry of Health & Family Welfare
electricity / meter → State Electricity Board / DISCOM
school / education → Ministry of Education
hospital → Ministry of Health & Family Welfare
passport → Ministry of External Affairs
bank / loan → Ministry of Finance / RBI
railway → Ministry of Railways
police / FIR → State Home Department
birth certificate → Municipal Corporation
income tax → Ministry of Finance / CBDT
```
Send this Google Doc link to Kartik by 9 PM.

---

### Teammate 4 — QA + Demo (all day)

**Morning:**
Read RTI Act 2005 Section 6 summary on Wikipedia.
Understand what a correct RTI looks like:
- Addressed to "The Public Information Officer"
- States Section 6 of RTI Act 2005
- Lists specific numbered questions
- Mentions ₹10 fee
- Requests response within 30 days

**Afternoon:**
Write 20 test problems (mix Hindi and English):
1. Mera ration card 6 mahine se nahi mila
2. Pension 3 mahine se band hai
3. Road ka kaam 2 saal se ruka hai
4. PM Kisan ke paise nahi aaye
5. Ayushman card reject ho gaya
6. Bijli meter reading galat aa rahi hai
7. School mein mid-day meal nahi milta
8. Hospital mein dawai nahi milti
9. Meri zameen ka registration ruka hai
10. Job card nahi bana
11. My passport application has been pending for 4 months
12. Bank refused to give me Mudra loan without reason
13. Train was 5 hours late and no compensation given
14. FIR not registered by police despite multiple visits
15. Birth certificate not issued for 2 months
16. PM Awas allotment not received despite approval
17. Scholarship amount not credited to account
18. Ujjwala gas connection not given despite eligibility
19. Income tax refund pending for 8 months
20. Borewell promised under scheme not installed in village

Send this list to Kartik by 4 PM.

**Evening:**
Write the 60-second demo script (memorize this):
> "88% of rural Indians — 70 crore people — have never heard of RTI, their constitutional right. Even those who know fail because there are 900+ departments to choose from. GovGPT solves this in 60 seconds. Watch — I'll speak a farmer's problem in Hindi."

*(speak into mic, text appears)*

> "Our AI — powered by Gemini 1.5 — automatically identifies the correct government department, writes a Section 6 compliant RTI application, and generates a downloadable PDF ready to print and post."

*(click Generate, words stream, click Download)*

> "A farmer in Bihar, a widow in Rajasthan, a student in Delhi — anyone can hold their government accountable in under a minute."

Set up OBS or Loom for Day 3 recording.

**Day 1 checkpoint — 10 PM sync call:**
- Kartik: curl test returns RTI ✓
- T2: Voice input works in Chrome ✓
- T3: ChromaDB built, chroma_db/ shared ✓
- T4: 20 test cases sent to Kartik ✓

---

## DAY 2 — Everything Connects (Hardest Day)

**Goal:** Full flow works in browser — voice → type problem → words stream live → RTI appears → PDF downloads. 18+ of 20 test cases pass.

---

### Kartik (block entire day — most critical work)

**9 AM — Add SSE streaming**
Change `/generate` to `/stream` GET route.
Flask sends tokens one by one using:
```python
return Response(generate(), mimetype='text/event-stream')
```
Test streaming works:
```bash
curl -N "http://localhost:5000/stream?problem=ration+card&name=Ram&address=Bihar"
```
Words should appear one by one in terminal. If yes — streaming works.

**11 AM — Improve system prompt**
Add Teammate 3's department mapping into the system prompt.
Test all 20 of Teammate 4's problems.
For each: correct department? proper Section 6 format? specific legal questions?
Fix prompt until 18+ out of 20 are correct.

**1 PM — Integration with Teammate 2 (sit on call together)**
This is the most important call of the project.
T2 connects their EventSource JS to your `/stream` URL.
Most common error: CORS. Fix by adding to `app.py`:
```python
from flask_cors import CORS
CORS(app)
```
Don't end this call until streaming works end-to-end in the browser.

**3 PM — Hand to Teammate 4 for testing**
Give T4 your localhost URL.
T4 runs all 20 test cases on the real app.
You fix every bug T4 reports within 30 minutes.
Stay fully available this block — don't work on anything else.

**6 PM — Deployment prep**
Add to top of `app.py`:
```python
import os
if not os.path.exists("chroma_db"):
    from ingest import ingest
    ingest()
```
This auto-builds ChromaDB on Render if it doesn't exist.
Run: `pip freeze > requirements.txt`
Create `.gitignore` with `.env`, `venv/`, `__pycache__/`

**8 PM — Final prompt iteration**
Fix the 2-3 cases T4 flagged as wrong.
Spend remaining time making RTI quality stronger.
This is what judges will actually read — it matters most.

---

### Teammate 2 — Frontend (all day)

**Morning:**
Replace placeholder JS with real EventSource:
```javascript
const params = new URLSearchParams({ problem, name, address });
const es = new EventSource(`http://localhost:5000/stream?${params}`);

es.onmessage = function(e) {
    if (e.data === '[DONE]') { es.close(); return; }
    const token = JSON.parse(e.data);
    document.getElementById('rti-output').textContent += token;
};
```

**Noon (1-3 PM):**
Integration session with Kartik on call.
Fix CORS errors, URL format issues.
Budget 2 hours — it always takes longer than expected.
Do not end the call until RTI words appear in your browser.

**Afternoon:**
Add jsPDF download button:
```javascript
function downloadPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const lines = doc.splitTextToSize(rtiText, 180);
    let y = 15;
    lines.forEach(line => {
        if (y > 270) { doc.addPage(); y = 15; }
        doc.text(line, 15, y);
        y += 7;
    });
    doc.save('GovGPT_RTI_Application.pdf');
}
```
Test with a long RTI — make sure no text is cut off.

**Evening:**
Polish:
- Button shows "Identifying department..." while generating
- Output area auto-scrolls as text streams in
- Add 3 stats at top: 88% | 60 seconds | 900+ authorities
- Add note near mic button: "🎤 Voice works in Chrome browser"
- Test on mobile by opening `http://YOUR_LAPTOP_IP:5000` on phone (same WiFi)

---

### Teammate 3 — Data + RAG (5 hours)

**Morning:**
Add 3-5 more PDFs if possible.
Re-run `ingest.py`.
Share updated `chroma_db/` with Kartik.

**Afternoon:**
Test RAG quality directly. In `rag.py`, temporarily add:
```python
if __name__ == "__main__":
    print(get_context("PM Kisan eligibility criteria"))
```
Run `python rag.py`. Real scheme eligibility text should appear.
If wrong info retrieves, tell Kartik immediately with the exact output shown.

**Evening:**
Help Teammate 4 — for scheme-specific test cases (Ayushman, MGNREGA, PM Kisan) you know if the RAG answer is correct. Tell T4 which ones pass and which have wrong context.

---

### Teammate 4 — QA + Testing (all day)

**From 3 PM onwards (when Kartik hands you localhost):**
Open `http://localhost:5000` in Chrome.
Run all 20 test cases one by one.
For each test, check:
- Does it stream? (words appear one by one)
- Is the department correct?
- Is it proper Section 6 format?
- Does the PDF download cleanly?

Log results in a Google Sheet:
| # | Problem | Expected Dept | Got Dept | Pass/Fail | Notes |

Report failures to Kartik with exact text: "I typed X, it chose department Y, but should be Z."
Do NOT guess fixes. Just report clearly.

**Evening:**
Write `README.md`:
```markdown
# GovGPT — RTI in 60 Seconds

AI-powered RTI application generator for Indian citizens.
Type or speak your problem → Get a legally formatted RTI → Download PDF.

## Live Demo
[https://govgpt.onrender.com](https://govgpt.onrender.com)

## Tech Stack
Flask · Gemini 1.5 Pro · LangChain · ChromaDB · Web Speech API · jsPDF

## Run Locally
1. Clone this repo
2. Create .env file with GEMINI_API_KEY=your_key
3. pip install -r requirements.txt
4. python ingest.py
5. python app.py
6. Open http://localhost:5000

## Team
- Kartik Gupta — Lead, Backend, AI
- [T2 name] — Frontend, UI, Voice
- [T3 name] — Data, RAG, ChromaDB
- [T4 name] — QA, Demo, Presentation
```

**Day 2 checkpoint — 10 PM sync call:**
- Full browser flow works ✓
- 18+ of 20 test cases pass ✓
- PDF downloads correctly ✓
- Streaming visible ✓
- README pushed to GitHub ✓

---

## DAY 3 — Deploy and Ship

**Goal:** Live URL by noon. Demo video by 3 PM. Submit by 11:59 PM on 29th.

---

### Kartik (9 AM – 4 PM)

**9 AM — Push everything to GitHub**
```bash
git add .
git commit -m "complete working build"
git push
```
Confirm `.env` is in `.gitignore` — it must NOT be on GitHub.
For `chroma_db/` — commit it directly to GitHub for the hackathon (easiest approach):
Remove `chroma_db/` from `.gitignore` → `git add chroma_db/` → `git commit` → `git push`

**10 AM — Deploy to Render**
1. Go to render.com → Sign up free
2. New → Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Under Environment → Add variable: `GEMINI_API_KEY` = your actual key
6. Click Deploy → wait 3-5 minutes
7. Get your live URL: `https://govgpt.onrender.com`

**12 PM — Share live URL with team**
Test it yourself first — open it, generate one RTI, download PDF.
Then share URL. T4 immediately starts testing on live URL.

**2 PM — Mobile test**
Open live URL on your phone in Chrome.
Test voice input on mobile.
Test PDF download on mobile.
Fix anything that breaks on production.

**4 PM — Done. Rest.**

---

### Teammate 2 (morning only)

**After Kartik shares live URL:**
Open `index.html` in VS Code.
Find the line: `http://localhost:5000/stream`
Change it to: `https://govgpt.onrender.com/stream`
Save. Push to GitHub:
```bash
git add .
git commit -m "update to production URL"
git push
```
Test the live URL in Chrome, Edge, mobile Chrome.
Document what works where.

---

### Teammate 3 (morning only)

Test 5 scheme-specific questions on live URL:
- "Am I eligible for PM Kisan?"
- "How to apply for Ayushman Bharat?"
- "What is MGNREGA wage rate?"
Verify real eligibility criteria appear in the RTI — not just generic text.

Then help Teammate 4 rehearse demo — act as a judge. Ask hard questions about the data.

---

### Teammate 4 (full day — most important day for you)

**Morning:**
Test all 20 cases on live Render URL (not localhost).
Take screenshots of 5 best RTI outputs:
1. Ration card problem
2. Pension problem
3. PM Kisan problem
4. Road problem
5. Ayushman card problem

Save screenshots on both phone AND laptop. These are your backup if internet fails during demo.

**12 PM — Record demo video**
Open screen recording (OBS or Loom).
Record exactly this flow:
1. Open live URL
2. Click mic → speak in Hindi: "mera ration card 6 mahine se nahi mila"
3. Text appears in textarea
4. Click Generate
5. Words stream live onto screen
6. Full RTI appears
7. Click Download PDF
8. PDF opens showing complete application

Keep it under 90 seconds. Re-record until it's clean with no mistakes.

**2 PM — Rehearse demo**
Say the demo script out loud 5 times. Time yourself — 45 to 60 seconds max.
Rehearse answers to these judge questions:

**Q: How does it identify the correct department?**
A: "Our system prompt contains a trained mapping of 900+ public authorities to problem categories, powered by Gemini 1.5 Pro. The model matches natural language — including Hindi — to the correct CPIO address using this mapping plus RAG context from official scheme documents."

**Q: How is this different from just using ChatGPT?**
A: "ChatGPT has no knowledge of which specific department out of 900+ handles which problem. It can't write Section 6 compliant RTIs. It has no access to current government scheme eligibility data. GovGPT is purpose-built with a legal RTI template, official scheme PDFs as its knowledge base, and Hindi voice input for rural citizens who can't type English."

**Q: How will you scale to 70 crore users?**
A: "The architecture is API-first — we can swap Render for AWS, and ChromaDB for Pinecone at scale. We'd partner with CSCs (Common Service Centres) already present in 6 lakh villages. The voice interface removes the literacy barrier. Each RTI costs less than ₹0.10 to generate at scale."

**4 PM — Final submission checklist**

- [ ] Live URL works: `https://govgpt.onrender.com`
- [ ] Voice input works in Chrome
- [ ] RTI streams word by word
- [ ] PDF downloads correctly
- [ ] GitHub repo is public and clean
- [ ] README.md has live URL and run instructions
- [ ] Demo video saved (phone + laptop + Google Drive)
- [ ] 5 backup screenshots saved (phone + laptop)
- [ ] PPTX ready
- [ ] Everyone knows the demo script

**Submit everything before 11:59 PM on 29th May.**

---

## The 3 Things That Will Win You Points

**1. The system prompt quality**
Judges will generate an RTI themselves. If it picks the wrong department or uses wrong format — points lost. Spend the most time here.

**2. The demo flow**
Speak Hindi → text appears → words stream → PDF downloads. This 60-second flow must be flawless. Practice it 10 times before the demo.

**3. The impact story**
Lead with "70 crore people have never heard of RTI." End with "a farmer in Bihar can now hold his government accountable in 60 seconds." The numbers are in your PPTX — use them.

---

## Emergency Backup Plan

If Render is down during demo:
- Run `python app.py` on Kartik's laptop
- Share hotspot from phone
- Open `http://localhost:5000` on laptop
- Demo from laptop directly

If Gemini API fails:
- Show the 5 backup screenshots
- Walk judges through what each field means
- "Here's what it generates for a ration card problem in Bihar"

If voice input doesn't work:
- Type the problem manually
- Voice is a bonus feature — the core RTI generation still works

---

*GovGPT — Built by Team DLC | Kartik Gupta + Team | B.Sc. Physical Science with CS, Delhi University*
