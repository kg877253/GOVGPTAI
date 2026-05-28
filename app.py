import os
import json
import logging
import time
import uuid
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, Response, request, render_template, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables FIRST
load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# File logging
file_handler = logging.FileHandler(os.path.join(log_dir, "govgpt.log"), encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
file_handler.setFormatter(file_formatter)

# Console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger("GovGPT")

# Request tracking and rate limiting
request_stats = defaultdict(lambda: {'count': 0, 'last_reset': datetime.now()})
request_cache = {}
CACHE_TTL = 3600  # 1 hour cache
RATE_LIMIT = 30  # requests per minute per IP

# Error tracking for monitoring
error_stats = defaultdict(int)

# --- Multi-Provider AI Setup ---
api_key = os.getenv("GEMINI_API_KEY", "")
groq_api_key = os.getenv("GROQ_API_KEY", "")

# Gemini Setup
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_gemini_ready = False
_genai_client = None
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

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

# Groq Setup (Free alternative)
_groq_ready = False
_groq_client = None
groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")

try:
    from groq import Groq
    
    if groq_api_key and not groq_api_key.startswith("YOUR_"):
        _groq_client = Groq(api_key=groq_api_key)
        _groq_ready = True
        logger.info(f"Groq API configured successfully. Model: {groq_model}")
    else:
        logger.warning("GROQ_API_KEY not set. Set it in .env to enable Groq as fallback.")
except ImportError:
    logger.warning("groq not installed. Run: pip install groq to enable Groq fallback")

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

# --- Fallback RTI (non-AI) helpers ---
_FALLBACK_DEPARTMENTS = [
    ("pm kisan", "The CPIO, Department of Agriculture & Farmers Welfare, Krishi Bhawan, New Delhi – 110001"),
    ("kisan", "The CPIO, Department of Agriculture & Farmers Welfare, Krishi Bhawan, New Delhi – 110001"),
    ("mgnrega", "The SPIO, Block Development Officer (BDO), [Applicant's Block Name]"),
    ("ayushman", "The CPIO, National Health Authority (NHA), Sansad Marg, New Delhi – 110001"),
    ("ration", "The SPIO, District Supply Officer (DSO), [Applicant's District]"),
    ("pds", "The SPIO, District Supply Officer (DSO), [Applicant's District]"),
    ("pm awas", "The SPIO, Block Development Officer (BDO), [Applicant's Block Name]"),
    ("ujjwala", "The CPIO, Ministry of Petroleum & Natural Gas, Shastri Bhawan, New Delhi – 110001"),
    ("pension", "The SPIO, Block Development Officer (BDO), [Applicant's Block Name]"),
]


def _is_hindi_text(text: str) -> bool:
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return True
    lowered = text.lower()
    hindi_keywords = [
        "nahi", "seva", "yojana", "pension", "ration", "labh", "kisan",
        "bheja", "bheji", "nidhi", "aadhar", "aadhaar", "bank", "khata",
    ]
    return any(word in lowered for word in hindi_keywords)


def _fallback_department(problem: str, address: str = "") -> str:
    lowered = problem.lower()
    
    # Try to extract district from address
    district = ""
    block = ""
    state = ""
    
    if address:
        # Common district indicators in Indian addresses
        district_patterns = ["district", "dist", "zila", "zilla", "जिला"]
        block_patterns = ["block", "tehsil", "taluka", "तहसील"]
        state_patterns = ["state", "rajasthan", "up", "uttar pradesh", "maharashtra", "madhya pradesh"]
        
        addr_lower = address.lower()
        for pattern in district_patterns:
            if pattern in addr_lower:
                idx = addr_lower.find(pattern)
                # Extract district name after the pattern
                district = address[idx+len(pattern):].strip().split(',')[0].strip()
                break
        
        for pattern in block_patterns:
            if pattern in addr_lower:
                idx = addr_lower.find(pattern)
                # Extract block name after the pattern
                block = address[idx+len(pattern):].strip().split(',')[0].strip()
                break
        
        for pattern in state_patterns:
            if pattern in addr_lower:
                # Extract state
                parts = address.split(',')
                for part in parts:
                    if pattern in part.lower():
                        state = part.strip()
                        break
    
    # Check specific schemes
    for key, dept in _FALLBACK_DEPARTMENTS:
        if key in lowered:
            # Replace placeholders with actual values
            if "[Applicant's District]" in dept and district:
                dept = dept.replace("[Applicant's District]", district)
            elif "[Applicant's District]" in dept:
                dept = dept.replace("[Applicant's District]", address.split(',')[-1].strip())
            
            if "[Applicant's Block Name]" in dept and block:
                dept = dept.replace("[Applicant's Block Name]", block)
            elif "[Applicant's Block Name]" in dept:
                dept = dept.replace("[Applicant's Block Name]", address.split(',')[0].strip())
            
            return dept
    
    # Generic fallback with extracted location - NO PLACEHOLDERS
    if district and state:
        return f"The CPIO/SPIO, District Collector Office, {district}, {state}"
    elif district:
        return f"The CPIO/SPIO, District Collector Office, {district}"
    elif block:
        return f"The CPIO/SPIO, Block Development Office, {block}"
    elif address:
        # Use the address itself if no district/block found
        return f"The CPIO/SPIO, District Collector Office, {address.split(',')[-1].strip()}"
    else:
        return "The CPIO/SPIO, District Collector Office"


def _build_fallback_rti(name: str, address: str, problem: str, date_str: str) -> str:
    dept_line = _fallback_department(problem, address)
    subject = "Request for information regarding public scheme/benefit"
    if "pm kisan" in problem.lower():
        subject = "PM-KISAN installment disbursement details"
    elif "ration" in problem.lower() or "pds" in problem.lower():
        subject = "Ration card distribution and supply details"
    elif "pension" in problem.lower():
        subject = "Pension disbursement status details"
    elif "ayushman" in problem.lower():
        subject = "Ayushman Bharat card and treatment details"
    elif "awas" in problem.lower():
        subject = "PM Awas Yojana allotment details"

    if _is_hindi_text(problem):
        # Keep Hindi concise and fully in Devanagari
        return (
            "To,\n"
            "The Central Public Information Officer (CPIO) / State Public Information Officer (SPIO),\n"
            f"{dept_line}\n\n"
            "Subject: आरटीआई अधिनियम 2005 की धारा 6(1) के तहत आवेदन — योजना लाभ/भुगतान संबंधी जानकारी\n\n"
            "Sir/Madam,\n\n"
            f"मैं {name}, पता {address}, भारत का नागरिक, आरटीआई अधिनियम 2005 की धारा 6(1) के तहत निम्न जानकारी चाहता/चाहती हूं:\n\n"
            "1. संबंधित योजना/लाभ से जुड़ी मेरी फाइल/आवेदन का डायरी नंबर, प्राप्ति तिथि और वर्तमान स्थिति की प्रमाणित प्रति दें।\n"
            "2. पिछले 12 महीनों में भुगतान/लाभ जारी करने की तिथि‑वार विवरणी और संबंधित आदेश/नोटशीट की प्रति दें।\n"
            "3. यदि भुगतान रोका गया है, तो रोकने के आदेश/कारण दर्शाने वाले रिकॉर्ड/नोटशीट की प्रति दें।\n"
            "4. इस आवेदन/लाभ के लिए वर्तमान में जिम्मेदार अधिकारी का नाम, पदनाम और कार्यालय पता दें।\n"
            "5. योजना से संबंधित लागू नियम/परिपत्र/दिशानिर्देश की प्रति दें।\n\n"
            "**RTI Act 2005 के तहत घोषणा:**\n"
            "मैं भारत का नागरिक हूं और मांगी गई जानकारी RTI अधिनियम 2005 की धारा 8/9 में वर्जित नहीं है।\n\n"
            "**आवेदन शुल्क:**\n"
            "रु. 10/- का शुल्क संलग्न/ऑनलाइन जमा किया गया है।\n\n"
            "कृपया 30 दिनों के भीतर सूचना उपलब्ध कराएं। विलंब होने पर प्रथम अपील करने का अधिकार सुरक्षित रखता/रखती हूं।\n\n"
            "Yours faithfully,\n"
            f"{name}\n{address}\n{date_str}\n"
        )

    # Generate more specific questions based on problem
    questions = []
    if "pm kisan" in problem.lower():
        questions = [
            "Provide the diary number, date of registration, and current status of my PM-KISAN beneficiary registration.",
            "Provide the date-wise record of all PM-KISAN installments credited to my account in the last 24 months with transaction IDs.",
            "If any installment was withheld or rejected, provide the specific reason, authority order, and the officer responsible.",
            "Provide the name, designation, and contact details of the officer currently handling my PM-KISAN case.",
            "Provide a copy of the PM-KISAN scheme guidelines and eligibility criteria."
        ]
    elif "ration" in problem.lower() or "pds" in problem.lower():
        questions = [
            "Provide the ration card number, date of issue, and current status of my ration card.",
            "Provide the record of all ration grains distributed to my family in the last 12 months with dates and quantities.",
            "If ration distribution was stopped or reduced, provide the reason and the authority order.",
            "Provide the name, designation, and address of the Fair Price Shop dealer and the Food Supply Officer.",
            "Provide a copy of the PDS scheme rules and entitlement calculation method."
        ]
    else:
        questions = [
            f"Provide the diary/receipt number, date of receipt, and current status of my application/file related to: {problem[:100]}",
            "Provide the date-wise record of all actions taken on my application in the last 12 months.",
            "If my application was rejected or delayed, provide the specific reason, authority order, and the officer responsible.",
            "Provide the name, designation, and office address of the officer currently responsible for this matter.",
            "Provide a copy of the relevant rule, circular, or guideline governing this matter."
        ]

    return (
        "To,\n"
        "The Central Public Information Officer (CPIO) / State Public Information Officer (SPIO),\n"
        f"{dept_line}\n\n"
        f"Subject: Application under Section 6(1) of the RTI Act, 2005 — {subject}\n\n"
        "Sir/Madam,\n\n"
        f"I, {name}, son/daughter/wife of [Father's/Husband's Name], resident of {address}, being a citizen of India, hereby submit this application under Section 6(1) of the Right to Information Act, 2005, to seek the following information:\n\n"
        f"1. {questions[0]}\n\n"
        f"2. {questions[1]}\n\n"
        f"3. {questions[2]}\n\n"
        f"4. {questions[3]}\n\n"
        f"5. {questions[4]}\n\n"
        "**Declaration under RTI Act 2005:**\n\n"
        "I hereby declare that I am a citizen of India and the information sought by me in this application does not fall within the restrictions contained in Section 8 and Section 9 of the Right to Information Act, 2005 and to the best of my knowledge, it pertains to your public authority.\n\n"
        "**Application Fee:**\n\n"
        "A fee of Rs. 10/- (Rupees Ten Only) is enclosed herewith as Indian Postal Order/Bank Demand Draft No. [Number] drawn in favour of [Payee Name] payable at [City], as prescribed under the RTI Rules, 2012.\n\n"
        "I request you to provide the above information within the statutory period of 30 days from the date of receipt of this application as mandated under Section 7(1) of the Right to Information Act, 2005.\n\n"
        "In case of failure to provide the information within the stipulated period, I shall be constrained to file First Appeal before the First Appellate Authority under Section 19(1) of the RTI Act, 2005 and thereafter approach the State/Central Information Commission under Section 18 of the Act.\n\n"
        "Thanking you,\n\n"
        "Yours faithfully,\n\n"
        "(Signature)\n"
        f"{name}\n"
        f"{address}\n"
        f"Mobile: [Your Mobile Number]\n"
        f"Email: [Your Email ID]\n"
        f"Date: {date_str}\n"
    )

# ═══════════════════════════════════════════════════════════════════
# MASTER RTI GENERATION SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════
MASTER_RTI_PROMPT = """
You are GovGPT — India's most advanced AI-powered RTI (Right to Information) drafting assistant.
You have deep expertise in the RTI Act 2005, Indian administrative law, government scheme implementation rules, and general public authority information requests.
Your job is to draft the highest-quality, legally precise, maximally effective Section 6 RTI application for ANY type of information request from public authorities.

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
ALWAYS include the full official designation: "The Public Information Officer" or "The Central Public Information Officer (CPIO)" or "The State Public Information Officer (SPIO)".

CRITICAL: NEVER use placeholders like "[Relevant Department]" or "[Full Department Address]". 
You MUST use the actual department name and address based on the problem and the applicant's address.
Extract the district/state from the applicant's address and use it to determine the correct department address.
Example: If applicant is from "District Pali, Rajasthan", use "The CPIO, District Collector Office, Pali, Rajasthan"

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
[Full Department Address with Pin Code]

Subject: Application under Section 6(1) of the Right to Information Act, 2005 — [Specific issue in 10-15 words]

Sir/Madam,

I, [Full Name], son/daughter/wife of [Father's/Husband's Name], resident of [Full Address with District and State], being a citizen of India, hereby submit this application under Section 6(1) of the Right to Information Act, 2005, to seek the following information:

1. [First specific, record-seeking question with exact details]

2. [Second specific, record-seeking question with exact details]

3. [Third specific, record-seeking question with exact details]

4. [Fourth question — asking for name/designation of responsible officer with contact details]

5. [Fifth question — asking for copy of relevant rule/circular/guideline/office order]

**Declaration under RTI Act 2005:**

I hereby declare that I am a citizen of India and the information sought by me in this application does not fall within the restrictions contained in Section 8 and Section 9 of the Right to Information Act, 2005 and to the best of my knowledge, it pertains to your public authority.

**Application Fee:**

A fee of Rs. 10/- (Rupees Ten Only) is enclosed herewith as Indian Postal Order/Bank Demand Draft No. [Number] drawn in favour of [Payee Name] payable at [City], as prescribed under the RTI Rules, 2012.

I request you to provide the above information within the statutory period of 30 days from the date of receipt of this application as mandated under Section 7(1) of the Right to Information Act, 2005.

In case of failure to provide the information within the stipulated period, I shall be constrained to file First Appeal before the First Appellate Authority under Section 19(1) of the RTI Act, 2005 and thereafter approach the State/Central Information Commission under Section 18 of the Act.

Thanking you,

Yours faithfully,

(Signature)
[Full Name]
[Full Address]
[Mobile Number]
[Email ID]
Date: [Date]
```

RULE 4 — WRITE POWERFUL, LEGALLY EFFECTIVE QUESTIONS:
NEVER write vague questions like "Why was my application rejected?" or "What is the status?"
CPIOs are NOT required to give opinions — they must only provide existing records.
ALWAYS frame questions to demand SPECIFIC RECORDS with precise legal language:

✅ CORRECT EXAMPLES:
- "Provide certified copy of the complete file noting, order sheet, and all correspondence related to my application for [Scheme Name] submitted on [Date] bearing application/reference number [Number]."
- "Provide date-wise record of all payments released/disbursed to beneficiary account [Account Number] under [Scheme Name] from [Start Date] to [End Date] along with supporting payment vouchers and bank transaction details."
- "Provide the name, designation, office address, contact number, and email ID of the officer currently responsible for processing applications under [Scheme Name] in [District/Block]."
- "Provide certified copy of the eligibility criteria, guidelines, and office memorandum governing the implementation of [Scheme Name] along with any amendments issued from [Year] to present."
- "Provide the details of action taken on my representation/complaint dated [Date] including the name of the officer who processed it and the final decision with reasons recorded."

❌ WRONG EXAMPLES:
- "Why is my ration card not issued?"
- "Please tell me the status of my application."
- "When will I get my pension?"
- "What is happening with my complaint?"

RULE 5 — CITE THE SCHEME CONTEXT IN QUESTIONS:
If the RAG scheme context mentions specific eligibility rules, payment timelines, or legal provisions — REFERENCE THEM in your questions with exact section numbers, dates, and circular references if available.

RULE 6 — ALWAYS INCLUDE A FIRST APPEAL WARNING:
The last paragraph must always warn of the right to file a First Appeal and approach the Information Commission with specific section references.

RULE 7 — START THE LETTER DIRECTLY:
Do NOT write any introduction, preamble, or explanation before the letter.
Begin DIRECTLY with: "To,"

RULE 8 — INCLUDE APPLICANT RELATIONSHIP:
Always include "son/daughter/wife of [Father's/Husband's Name]" after the applicant's name for proper identification as per Indian government format.

RULE 12 — USE ACTUAL ADDRESS ONLY:
NEVER use placeholders like "[Your Address]" or "[Full Address]" in the RTI letter.
You MUST use the exact address provided by the applicant: {address}
This address should appear in the body of the letter after the applicant's name.
Example: "I, {name}, son/daughter/wife of [Father's/Husband's Name], resident of {address}, being a citizen of India..."

RULE 9 — SPECIFIC FEE DETAILS:
Always specify the mode of fee payment (IPO/DD/Online) with placeholder for number and payee details for authenticity.

RULE 10 — CONTACT INFORMATION:
Include mobile number and email ID in the signature block for faster communication.

RULE 11 — PROPER SPACING:
- Add a blank line after each numbered question for better readability
- Add a blank line after major section headers (Declaration, Application Fee)
- Ensure consistent spacing between paragraphs
- Do not crowd text - use proper line breaks for professional appearance

OUTPUT FORMAT: Use clean Markdown. Use **bold** for section headers within the letter. Ensure proper spacing and paragraph breaks for readability.
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
        "cache_size": len(request_cache),
        "active_requests": len(request_stats),
        "timestamp": int(time.time())
    })


@app.route("/stats")
def stats():
    """Statistics endpoint for monitoring."""
    return jsonify({
        "cache_entries": len(request_cache),
        "rate_limited_ips": len([ip for ip, stats in request_stats.items() if stats['count'] >= RATE_LIMIT]),
        "total_requests_tracked": sum(stats['count'] for stats in request_stats.values()),
        "error_stats": dict(error_stats),
        "total_errors": sum(error_stats.values()),
        "model": gemini_model,
        "timestamp": int(time.time())
    })


@app.route("/api/docs")
def api_docs():
    """API documentation endpoint."""
    return jsonify({
        "name": "GovGPT API",
        "version": "2.0.0",
        "description": "AI-powered RTI application generator for Indian citizens",
        "endpoints": {
            "GET /": "Serve the main web application",
            "GET /health": "Health check endpoint",
            "GET /health/gemini": "Validate Gemini API key and quota",
            "GET /stats": "System statistics (cache size, request counts)",
            "GET /api/docs": "This API documentation",
            "GET /stream": {
                "description": "Server-Sent Events endpoint for RTI generation",
                "parameters": {
                    "problem": "string (required) - Citizen's problem description",
                    "name": "string (optional) - Applicant's name",
                    "address": "string (optional) - Applicant's address"
                },
                "response": "SSE stream with JSON-formatted text tokens",
                "rate_limit": "30 requests per minute per IP"
            }
        },
        "features": [
            "Rate limiting (30 req/min per IP)",
            "Response caching (1 hour TTL)",
            "Automatic retry on API failures (3 attempts)",
            "Hybrid RAG search (semantic + keyword)",
            "PDF and text file ingestion",
            "Incremental data updates",
            "Hindi and English support",
            "Input sanitization"
        ],
        "model": gemini_model,
        "documentation": "https://github.com/YOUR_USERNAME/govgpt"
    })


@app.route("/health/gemini")
def health_gemini():
    """Validate Gemini API key/quota with a lightweight test call."""
    if not _gemini_ready or _genai_client is None:
        return jsonify({
            "status": "error",
            "gemini_ready": _gemini_ready,
            "message": "Gemini client not initialized. Check GEMINI_API_KEY and restart server."
        }), 500

    try:
        # Minimal request to verify auth/quota without streaming
        _genai_client.models.generate_content(
            model=gemini_model,
            contents="ping",
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=5,
            ),
        )
        return jsonify({
            "status": "ok",
            "model": gemini_model
        })
    except Exception as e:
        err_text = str(e)
        return jsonify({
            "status": "error",
            "model": gemini_model,
            "message": err_text[:300]
        }), 500


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

    # --- Rate limiting ---
    client_ip = get_client_ip()
    allowed, rate_error = check_rate_limit(client_ip)
    if not allowed:
        return _error_stream(rate_error)
    
    # --- Request ID for tracking ---
    request_id = str(uuid.uuid4())[:8]
    
    # --- Input validation ---
    if not problem:
        return _error_stream("कृपया अपनी समस्या लिखें। / Please describe your problem.")

    # BUG FIX #2 (app.py /stream): Add input length guard to prevent runaway API bills
    if len(problem) > 2000:
        return _error_stream("Input too long. Please limit your problem description to 2000 characters.")
    
    # Input sanitization to prevent injection
    problem = problem.replace('<', '&lt;').replace('>', '&gt;')
    name = name.replace('<', '&lt;').replace('>', '&gt;')
    address = address.replace('<', '&lt;').replace('>', '&gt;')

    if not _gemini_ready:
        return _error_stream(
            "⚠️ Gemini API key not configured. Open the .env file, "
            "paste your key from https://aistudio.google.com/, and restart the server."
        )
    
    # --- Check cache ---
    cache_key = get_cache_key(problem, name, address)
    cached = get_cached_response(cache_key)
    if cached:
        logger.info(f"[Request {request_id}] Cache hit - returning cached response")
        def stream_cached():
            for line in cached.splitlines(keepends=True):
                yield f"data: {json.dumps(line)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_cached(), mimetype='text/event-stream')

    # --- Build prompt ---
    from datetime import date
    today = date.today().strftime("%d %B %Y")

    logger.info(f"[Request {request_id}] IP={client_ip} | Name={name[:20]} | Problem={problem[:60]}...")

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

    # --- Stream from Gemini with retry logic ---
    def generate():
        full_response = ""
        
        for attempt in range(MAX_RETRIES):
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
                        full_response += chunk.text
                        yield f"data: {json.dumps(chunk.text)}\n\n"

                logger.info(f"[Request {request_id}] Gemini stream complete.")
                # Cache successful response
                set_cached_response(cache_key, full_response)
                yield "data: [DONE]\n\n"
                return

            except Exception as e:
                logger.error(f"[Request {request_id}] Gemini generation error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                
                # Use centralized error handler
                error_message = handle_api_error(e, request_id)
                
                if "Invalid API Key" in error_message:
                    yield f"data: {json.dumps(error_message)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"[Request {request_id}] Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    continue
                
                # Final attempt failed, try Groq fallback if available
                if "quota" in error_message.lower() or "server error" in error_message.lower():
                    if _groq_ready:
                        logger.warning(f"[Request {request_id}] Gemini quota exhausted, switching to Groq")
                        try:
                            # Use Groq as fallback
                            response = _groq_client.chat.completions.create(
                                model=groq_model,
                                messages=[
                                    {"role": "system", "content": "You are an expert RTI application generator for Indian citizens. Generate professional RTI applications following the RTI Act 2005 format."},
                                    {"role": "user", "content": final_prompt}
                                ],
                                stream=True,
                                temperature=0.7
                            )
                            
                            for chunk in response:
                                if chunk.choices[0].delta.content:
                                    yield f"data: {json.dumps(chunk.choices[0].delta.content)}\n\n"
                            
                            yield "data: [DONE]\n\n"
                            logger.info(f"[Request {request_id}] Groq fallback successful")
                            return
                        except Exception as groq_error:
                            logger.error(f"[Request {request_id}] Groq fallback failed: {groq_error}")
                    
                    # If Groq also fails, use static fallback
                    logger.warning(f"[Request {request_id}] Using static fallback RTI generation")
                    fallback_text = _build_fallback_rti(name, address, problem, today)
                    # Send entire fallback as a single chunk to ensure proper PDF capture
                    yield f"data: {json.dumps(fallback_text)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                else:
                    yield f"data: {json.dumps(error_message)}\n\n"
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


def get_client_ip():
    """Get client IP address, accounting for proxies."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr or 'unknown'


def check_rate_limit(ip: str) -> tuple[bool, str]:
    """Check if IP has exceeded rate limit."""
    now = datetime.now()
    stats = request_stats[ip]
    
    # Reset counter if minute has passed
    if (now - stats['last_reset']).total_seconds() >= 60:
        stats['count'] = 0
        stats['last_reset'] = now
    
    if stats['count'] >= RATE_LIMIT:
        return False, f"Rate limit exceeded ({RATE_LIMIT} requests/minute). Please wait."
    
    stats['count'] += 1
    return True, ""


def get_cache_key(problem: str, name: str, address: str) -> str:
    """Generate cache key for request."""
    content = f"{problem}|{name}|{address}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_response(cache_key: str) -> str | None:
    """Get cached response if available and not expired."""
    if cache_key in request_cache:
        cached_data = request_cache[cache_key]
        if (datetime.now() - cached_data['timestamp']).total_seconds() < CACHE_TTL:
            logger.info(f"Cache hit for key: {cache_key[:8]}...")
            return cached_data['response']
        else:
            del request_cache[cache_key]
    return None


def set_cached_response(cache_key: str, response: str):
    """Cache a response."""
    request_cache[cache_key] = {
        'response': response,
        'timestamp': datetime.now()
    }
    # Limit cache size
    if len(request_cache) > 100:
        oldest_key = min(request_cache.keys(), key=lambda k: request_cache[k]['timestamp'])
        del request_cache[oldest_key]


def track_error(error_type: str):
    """Track error statistics for monitoring."""
    error_stats[error_type] += 1
    logger.warning(f"Error tracked: {error_type} (total: {error_stats[error_type]})")


def handle_api_error(error: Exception, request_id: str) -> str:
    """Centralized API error handler with fallback logic."""
    error_msg = str(error)
    error_type = type(error).__name__
    track_error(error_type)
    
    logger.error(f"[Request {request_id}] API Error ({error_type}): {error_msg}")
    
    # Handle specific error types
    if "API_KEY_INVALID" in error_msg or "401" in error_msg:
        return "❌ Invalid API Key. Please check your GEMINI_API_KEY in the .env file."
    elif "quota" in error_msg.lower() or "resource_exhausted" in error_msg.lower() or "429" in error_msg:
        return "⚠️ API quota exhausted. Using fallback RTI generation."
    elif "timeout" in error_msg.lower() or "504" in error_msg:
        return "⚠️ Request timeout. Please try again."
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        return "⚠️ Server error. Retrying with fallback generation."
    else:
        return f"⚠️ Generation error: {error_msg[:200]}"


if __name__ == "__main__":
    import socket
    
    def find_available_port(start_port=5000, max_attempts=10):
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        return None
    
    base_port = int(os.getenv("PORT", 5000))
    available_port = find_available_port(base_port)
    
    if available_port is None:
        logger.error(f"Could not find an available port between {base_port} and {base_port + 10}")
        logger.error("Please close other applications or specify a different PORT in .env")
        exit(1)
    
    if available_port != base_port:
        logger.warning(f"Port {base_port} is in use, using port {available_port} instead")
    
    logger.info(f"🚀 GovGPT starting on http://0.0.0.0:{available_port}")
    logger.info(f"   Gemini Ready: {_gemini_ready}")
    logger.info(f"   RAG Ready:    {_rag_ready}")
    logger.info(f"   Open http://localhost:{available_port} in Chrome")
    
    try:
        app.run(host="0.0.0.0", port=available_port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.error("Please check if the port is available and try again.")
        exit(1)