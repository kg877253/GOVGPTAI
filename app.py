import os
import json
import logging
import time
from flask import Flask, Response, request, render_template, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("GovGPT")

# --- Gemini SDK Setup (use latest google-genai SDK) ---
api_key = os.getenv("GEMINI_API_KEY", "")

# BUG FIX #1 (app.py default model): was "gemini-1.0-pro" which is deprecated.
# Changed to "gemini-2.0-flash" — faster, cheaper, and works with new API keys.
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_gemini_ready = False
_genai_client = None

try:
    from google import genai
    from google.genai import types

    if api_key and not api_key.startswith("YOUR_"):
        _genai_client = genai.Client(api_key=api_key)
        _gemini_ready = True
        logger.info(f"Gemini API configured successfully. Model: {gemini_model}")
    else:
        logger.warning("GEMINI_API_KEY not set or is placeholder. Set it in .env to enable AI generation.")
except ImportError:
    logger.error("google-genai not installed. Run: pip install google-genai")

# --- Import local RAG module ---
try:
    from rag import get_scheme_context
    _rag_ready = True
    logger.info("RAG module loaded successfully.")
except Exception as e:
    logger.warning(f"RAG module could not be loaded: {e}. Proceeding without RAG.")
    _rag_ready = False

    def get_scheme_context(query: str, n_results: int = 2) -> str:
        return ""

# --- Auto-ingest if ChromaDB is missing ---
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
auto_ingest = os.getenv("AUTO_INGEST", "0") == "1"

if _gemini_ready and _rag_ready and auto_ingest:
    if not os.path.exists(db_path) or not os.listdir(db_path):
        logger.info("ChromaDB missing. Running auto-ingestion...")
        try:
            from ingest import ingest_data
            ingest_data()
            logger.info("Auto-ingestion complete.")
        except Exception as e:
            logger.error(f"Auto-ingestion failed: {e}")
elif _gemini_ready and _rag_ready:
    logger.info("Auto-ingest is disabled. Set AUTO_INGEST=1 to enable it.")

# --- Initialize Flask ---
app = Flask(__name__, template_folder="templates")
CORS(app, resources={r"/*": {"origins": "*"}})

# ═══════════════════════════════════════════════════════════════════
# MASTER DEPARTMENT ROUTING MAP — 35+ Authorities
# ═══════════════════════════════════════════════════════════════════
DEPARTMENT_ROUTING_MAP = """
ROUTING PRIORITY: Match the MOST SPECIFIC authority first. For state-level issues, route to
the State/District officer. For central scheme implementation failures, route to BOTH the
district-level implementing officer AND the central ministry CPIO.

CENTRAL SCHEME ROUTING:
━━━━━━━━━━━━━━━━━━━━━━
1. PM KISAN / PM-KISAN SAMMAN NIDHI / FARM INCOME SUPPORT
   → The CPIO, Department of Agriculture & Farmers Welfare, Krishi Bhawan, New Delhi – 110001
   → Local contact: District Agriculture Officer (DAO)

2. AYUSHMAN BHARAT / PM-JAY / HEALTH CARD / EMPANELLED HOSPITAL
   → The CPIO, National Health Authority (NHA), Sansad Marg, New Delhi – 110001
   → Local contact: District Health Officer (DHO) / State Health Agency (SHA)

3. MGNREGA / JOB CARD / RURAL EMPLOYMENT / WAGE DELAY
   → The SPIO, Block Development Officer (BDO), [Applicant's Block Name]
   → OR: The CPIO, Ministry of Rural Development, Krishi Bhawan, New Delhi – 110001

4. PM AWAS YOJANA GRAMIN (PMAY-G) / RURAL HOUSING
   → The SPIO, Block Development Officer (BDO), [Applicant's Block Name]
   → OR: The CPIO, Ministry of Rural Development, New Delhi – 110001

5. PM AWAS YOJANA URBAN (PMAY-U) / URBAN HOUSING
   → The CPIO, Ministry of Housing & Urban Affairs, Nirman Bhawan, New Delhi – 110011
   → Local contact: Urban Local Body (ULB) / Municipal Commissioner

6. RATION CARD / PDS / FAIR PRICE SHOP (FPS) / FOOD GRAINS
   → The SPIO, District Supply Officer (DSO), [Applicant's District]
   → OR: The CPIO, Department of Food & Public Distribution, Krishi Bhawan, New Delhi – 110001

7. PM UJJWALA YOJANA / LPG GAS CONNECTION
   → The CPIO, Ministry of Petroleum & Natural Gas, Shastri Bhawan, New Delhi – 110001
   → Local contact: LPG Distributor / District Manager (Oil PSU)

8. NATIONAL SOCIAL ASSISTANCE PROGRAMME (NSAP) / OLD AGE PENSION / WIDOW PENSION
   → The SPIO, Block Development Officer (BDO), [Applicant's Block]
   → OR: The CPIO, Ministry of Rural Development, New Delhi – 110001

9. SCHOLARSHIP / NATIONAL SCHOLARSHIP PORTAL (NSP) / STUDENT AID
   → The CPIO, Ministry of Education, Shastri Bhawan, New Delhi – 110001
   → OR: CPIO, Ministry of Social Justice & Empowerment (for SC/ST/OBC scholarships)

10. BETI BACHAO BETI PADHAO / SUKANYA SAMRIDDHI
    → The CPIO, Ministry of Women & Child Development, Shastri Bhawan, New Delhi – 110001

STATE / LOCAL ROUTING:
━━━━━━━━━━━━━━━━━━━━━━
11. ELECTRICITY / METER READING / BILLING DISPUTE / POWER OUTAGE
    → The SPIO, Superintending Engineer / Executive Engineer, State DISCOM
    → Example: BSES Rajdhani / UPPCL / MSEDCL (varies by state)

12. BIRTH CERTIFICATE / DEATH CERTIFICATE / CASTE CERTIFICATE
    → The SPIO, Municipal Corporation / Nagar Panchayat / Gram Panchayat Office

13. POLICE COMPLAINT / FIR NOT REGISTERED / INACTION BY POLICE
    → The SPIO, Superintendent of Police (SP), [Applicant's District]
    → Note: RTI cannot demand why an FIR was not filed — instead ask for copy of complaint, NCR number, officer name assigned

14. LAND RECORDS / PROPERTY DISPUTE / REGISTRY DELAY
    → The SPIO, Sub-Registrar / Tehsildar / Patwari Office, [Applicant's District]

15. ROAD CONSTRUCTION / PWD WORK DELAY
    → For National Highways: CPIO, NHAI / Ministry of Road Transport & Highways
    → For State/Village roads: SPIO, Executive Engineer, PWD, [Applicant's District]

16. DRINKING WATER / JAL JEEVAN MISSION PIPELINE
    → The SPIO, Executive Engineer, Public Health Engineering (PHE) Department
    → OR: CPIO, Ministry of Jal Shakti, New Delhi – 110001

CENTRAL AUTHORITY ROUTING:
━━━━━━━━━━━━━━━━━━━━━━━━━━
17. PASSPORT / VISA / OCI CARD
    → The CPIO, Passport Seva Kendra (PSK), [Applicant's City]
    → OR: CPIO, Ministry of External Affairs, South Block, New Delhi – 110011

18. RAILWAY / TRAIN DELAY / TICKET REFUND / RAILWAY COMPLAINT
    → The CPIO, Divisional Railway Manager (DRM), [Applicant's Railway Division]
    → OR: CPIO, Ministry of Railways, Rail Bhawan, New Delhi – 110001

19. INCOME TAX REFUND / TDS ISSUE
    → The CPIO, Commissioner of Income Tax, [Applicant's City]
    → OR: CPIO, Central Board of Direct Taxes (CBDT), Ministry of Finance, New Delhi

20. BANK / MUDRA LOAN / JAN DHAN ACCOUNT
    → The CPIO, Regional Manager, [Bank Name], [Applicant's Region]
    → OR: CPIO, Reserve Bank of India (RBI) / Ministry of Finance

21. AADHAR CARD / BIOMETRIC / UIDAI ISSUE
    → The CPIO, UIDAI Regional Office, [Applicant's State]
    → OR: CPIO, UIDAI Headquarters, Bangla Sahib Road, New Delhi – 110001

22. EPFO / PF WITHDRAWAL / PENSION
    → The CPIO, Regional PF Commissioner (RPFC), EPFO, [Applicant's Region]

23. COVID VACCINATION / COWIN CERTIFICATE
    → The CPIO, Ministry of Health & Family Welfare, Nirman Bhawan, New Delhi – 110011
"""

# ═══════════════════════════════════════════════════════════════════
# MASTER RTI GENERATION SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════
MASTER_RTI_PROMPT = """
You are GovGPT — India's most advanced AI-powered RTI (Right to Information) drafting assistant.
You have deep expertise in the RTI Act 2005, Indian administrative law, and government scheme implementation rules.
Your job is to draft the highest-quality, legally precise, maximally effective Section 6 RTI application.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPLICANT INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {name}
Address: {address}
Date of Application: {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CITIZEN'S PROBLEM (Treat this as ground truth — do not contradict it):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{problem}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OFFICIAL SCHEME DOCUMENTATION (from government PDFs — use as reference):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{scheme_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPARTMENT ROUTING REFERENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{department_map}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY DRAFTING RULES — FOLLOW ALL OF THEM WITHOUT EXCEPTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE 1 — IDENTIFY THE RIGHT AUTHORITY:
Select the single most specific public authority responsible for the issue from the Department Routing Reference.
For block/district-level scheme implementation issues (MGNREGA, PM Awas, Ration, Pensions), route to the Block/District officer — NOT directly to the Ministry.

RULE 2 — LANGUAGE DETECTION & OUTPUT LANGUAGE:
• Detect the language of the problem description.
• If the problem contains Hindi/Devanagari script OR Hinglish (Roman script Hindi words), write the ENTIRE RTI body in formal, correct Hindi (Devanagari script).
• If the problem is in English, write in formal English.
• Never mix languages in the output — choose one and be consistent.

RULE 3 — FORMAT THE LETTER EXACTLY LIKE THIS:

```
To,
The Central Public Information Officer (CPIO) / State Public Information Officer (SPIO),
[Exact Department Name],
[Full Department Address]

Subject: Application under Section 6(1) of the Right to Information Act, 2005 — [Specific issue in 10 words]

Sir/Madam,

I, [Name], a citizen of India residing at [Full Address], do hereby submit this application under Section 6(1) of the Right to Information Act, 2005, seeking the following information:

1. [First specific, record-seeking question]
2. [Second specific, record-seeking question]
3. [Third specific, record-seeking question]
4. [Fourth question — asking for name/designation of responsible officer]
5. [Fifth question — asking for copy of relevant rule/circular/guideline]

**Declaration under RTI Act 2005:**
I state that I am a citizen of India and the information requested above does not fall under the exemptions specified in Sections 8 and 9 of the Right to Information Act, 2005.

**Application Fee:**
A fee of Rs. 10/- (Rupees Ten Only) is enclosed/submitted via [Indian Postal Order / Bank Demand Draft / online RTI portal payment], as required under Section 6(1) of the RTI Act 2005.

I request you to provide the above information within the statutory period of 30 days as mandated under Section 7(1) of the RTI Act, 2005.

In case of failure to respond within 30 days, I reserve the right to file a First Appeal under Section 19(1) and approach the Central / State Information Commission under Section 18.

Yours faithfully,
[Name]
[Full Address]
[Date]
```

RULE 4 — WRITE POWERFUL, LEGALLY EFFECTIVE QUESTIONS:
NEVER write vague questions like "Why was my application rejected?" or "What is the status?"
CPIOs are NOT required to give opinions — they must only provide existing records.
ALWAYS frame questions to demand SPECIFIC RECORDS:
✅ CORRECT: "Provide a certified copy of the file noting and order sheet pertaining to the processing of [Scheme] benefit for applicant [Name]."
✅ CORRECT: "Provide the date-wise record of disbursement of [Scheme] instalments credited to beneficiary ID from [Year] to present."
✅ CORRECT: "State the name, designation, and office address of the officer currently responsible for processing this application."
❌ WRONG: "Why is my ration card not issued?"
❌ WRONG: "Please tell me the status of my application."

RULE 5 — CITE THE SCHEME CONTEXT IN QUESTIONS:
If the RAG scheme context mentions specific eligibility rules, payment timelines, or legal provisions — REFERENCE THEM in your questions.

RULE 6 — ALWAYS INCLUDE A FIRST APPEAL WARNING:
The last paragraph must always warn of the right to file a First Appeal and approach the Information Commission.

RULE 7 — START THE LETTER DIRECTLY:
Do NOT write any introduction, preamble, or explanation before the letter.
Begin DIRECTLY with: "To,"

OUTPUT FORMAT: Use clean Markdown. Use **bold** for section headers within the letter.
"""

# ═══════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Serve the main GovGPT web application."""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check endpoint for deployment monitoring."""
    return jsonify({
        "status": "ok",
        "gemini_ready": _gemini_ready,
        "rag_ready": _rag_ready,
        "chroma_db_exists": os.path.exists(db_path) and bool(os.listdir(db_path) if os.path.exists(db_path) else []),
        "timestamp": int(time.time())
    })


@app.route("/stream")
def stream_rti():
    """
    Server-Sent Events (SSE) endpoint.
    Accepts: ?problem=...&name=...&address=...
    Streams back RTI text tokens one by one.
    """
    problem = request.args.get("problem", "").strip()
    name = request.args.get("name", "").strip() or "Nagarik (Citizen of India)"
    address = request.args.get("address", "").strip() or "[Address not provided]"

    # --- Input validation ---
    if not problem:
        return _error_stream("कृपया अपनी समस्या लिखें। / Please describe your problem.")

    # BUG FIX #2 (app.py /stream): Add input length guard to prevent runaway API bills
    if len(problem) > 2000:
        return _error_stream("Input too long. Please limit your problem description to 2000 characters.")

    if not _gemini_ready:
        return _error_stream(
            "⚠️ Gemini API key not configured. Open the .env file, "
            "paste your key from https://aistudio.google.com/, and restart the server."
        )

    # --- Build prompt ---
    from datetime import date
    today = date.today().strftime("%d %B %Y")

    logger.info(f"[RTI Request] Name={name[:20]} | Problem={problem[:60]}...")

    # Fetch RAG context
    scheme_context = ""
    if _rag_ready:
        try:
            scheme_context = get_scheme_context(problem)
            logger.info(f"RAG returned {len(scheme_context)} chars of context.")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    if not scheme_context:
        scheme_context = "No matching scheme documents found. Proceed based on general Indian administrative law and RTI Act 2005 provisions."

    final_prompt = MASTER_RTI_PROMPT.format(
        name=name,
        address=address,
        date=today,
        problem=problem,
        scheme_context=scheme_context,
        department_map=DEPARTMENT_ROUTING_MAP
    )

    # --- Stream from Gemini ---
    def generate():
        try:
            if _genai_client is None:
                raise RuntimeError("Gemini client not initialized.")

            response = _genai_client.models.generate_content_stream(
                model=gemini_model,
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.9,
                    max_output_tokens=2048,
                ),
            )

            for chunk in response:
                # BUG FIX #3 (app.py SSE loop): Surface SAFETY/RECITATION finish reasons to frontend
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    finish_reason = getattr(candidate, 'finish_reason', None)
                    if finish_reason and str(finish_reason) in ("SAFETY", "RECITATION"):
                        yield f"data: {json.dumps(f'⚠️ Generation stopped by safety filter: {finish_reason}')}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                if hasattr(chunk, 'text') and chunk.text:
                    yield f"data: {json.dumps(chunk.text)}\n\n"

            logger.info("Gemini stream complete.")
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg:
                yield f"data: {json.dumps('❌ Invalid API Key. Please check your GEMINI_API_KEY in the .env file.')}\n\n"
            elif "quota" in error_msg.lower():
                yield f"data: {json.dumps('❌ API quota exceeded. Wait a moment and try again.')}\n\n"
            else:
                yield f"data: {json.dumps(f'❌ Generation error: {error_msg[:200]}')}\n\n"
            yield "data: [DONE]\n\n"

    response = Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )
    return response


def _error_stream(message: str):
    """Helper to return an error as an SSE stream."""
    def gen():
        yield f"data: {json.dumps('❌ ' + message)}\n\n"
        yield "data: [DONE]\n\n"
    return Response(gen(), mimetype='text/event-stream')


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"🚀 GovGPT starting on http://0.0.0.0:{port}")
    logger.info(f"   Gemini Ready: {_gemini_ready}")
    logger.info(f"   RAG Ready:    {_rag_ready}")
    logger.info(f"   Open http://localhost:{port} in Chrome")
    app.run(host="0.0.0.0", port=port, debug=False)