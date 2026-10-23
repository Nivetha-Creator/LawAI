"""
Curated Indian legal information for local (no-API) responses.

Only include facts the maintainers have verified. Do not add statute numbers
or case citations here unless they are part of the curated entry text.
"""

from __future__ import annotations

from typing import TypedDict


class LegalTopic(TypedDict):
    id: str
    title: str
    keywords: tuple[str, ...]
    summary: str
    details: str
    practical_steps: str


LEGAL_TOPICS: tuple[LegalTopic, ...] = (
    {
        "id": "bns_ipc_transition",
        "title": "BNS, BNSS, BSA and the older IPC / CrPC framework",
        "keywords": (
            "bns",
            "bnss",
            "bsa",
            "ipc",
            "crpc",
            "evidence act",
            "bharatiya",
            "criminal law",
            "new criminal laws",
            "july 2024",
        ),
        "summary": (
            "India's central criminal-law statutes were substantially reorganised. "
            "The Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita "
            "(BNSS), and Bharatiya Sakshya Adhiniyam (BSA) are central to the new "
            "framework that largely replaced the Indian Penal Code (IPC), Code of "
            "Criminal Procedure (CrPC), and Indian Evidence Act for many matters, "
            "with effect from 1 July 2024, subject to transitional provisions and "
            "the facts of each case."
        ),
        "details": (
            "Whether older labels (for example “IPC section”) or new BNS provisions "
            "apply depends on the date of the alleged conduct, filing, and any "
            "transitional rules. Courts and investigators may still refer to older "
            "statutes in pending matters. This assistant does not map old sections "
            "to new ones automatically—official consolidated texts should be checked."
        ),
        "practical_steps": (
            "Note the approximate date of the incident and any police or court papers "
            "you have. Compare the statute names cited on those papers with current "
            "acts on India Code (indiacode.nic.in). Ask a qualified advocate how "
            "transitional rules apply to your situation."
        ),
    },
    {
        "id": "fir_and_complaint",
        "title": "FIRs and criminal complaints (general process)",
        "keywords": (
            "fir",
            "first information report",
            "police complaint",
            "register fir",
            "cognizable",
            "non cognizable",
            "ncr",
            "station diary",
        ),
        "summary": (
            "In cognizable cases, police may register an FIR and begin investigation "
            "without prior magistrate permission in many situations. For non-cognizable "
            "offences, the usual route is often a complaint to a Magistrate rather than "
            "a direct FIR. Exact powers and remedies depend on the offence and facts."
        ),
        "details": (
            "You can generally request a copy of the FIR or acknowledgement of your "
            "complaint. If police refuse to register where the law requires it, "
            "remedies may include supervisory complaint or approaching the Magistrate—"
            "specific steps vary by state practice and the offence category."
        ),
        "practical_steps": (
            "Keep written notes of dates, witnesses, and documents. Visit the police "
            "station with any evidence you safely have. If turned away, ask for a "
            "written reason and consult an advocate about Magistrate complaint routes."
        ),
    },
    {
        "id": "bail_basics",
        "title": "Bail and personal liberty (high-level)",
        "keywords": (
            "bail",
            "anticipatory bail",
            "regular bail",
            "interim bail",
            "custody",
            "arrest",
            "remand",
        ),
        "summary": (
            "Bail is a way to secure release from custody during investigation or "
            "trial, subject to conditions. Anticipatory bail is sought before arrest "
            "in some situations; regular bail after arrest or during trial. Courts weigh "
            "factors such as seriousness, flight risk, tampering concerns, and prior "
            "record—outcomes are fact-specific."
        ),
        "details": (
            "Bail law operates under the criminal procedure code applicable to the case "
            "(including BNSS provisions where in force). This tool cannot predict whether "
            "bail will be granted in a particular matter."
        ),
        "practical_steps": (
            "If someone is arrested or at risk of arrest, contact a criminal advocate "
            "immediately. Preserve medical records, employment proof, and family ties "
            "documents that may support a bail application."
        ),
    },
    {
        "id": "return_of_property",
        "title": "Refusal to return belongings or money",
        "keywords": (
            "belongings",
            "return my property",
            "refuse to return",
            "deposit",
            "landlord",
            "tenant",
            "borrowed",
            "cheque bounce",
            "money back",
        ),
        "summary": (
            "When someone withholds your movable property or money, available routes "
            "often depend on how you parted with it (loan, deposit, sale, tenancy, "
            "employment, fraud allegation). Civil recovery, police complaint, or "
            "special tribunals may each be relevant for different fact patterns."
        ),
        "details": (
            "A polite written demand with proof (messages, receipts, photos) is a "
            "common first step. Wrongful retention may support a civil suit for recovery "
            "or, if dishonesty is alleged with supporting facts, criminal avenues—"
            "which offence (if any) applies must be assessed by a lawyer from your documents."
        ),
        "practical_steps": (
            "Gather proof of ownership and communications. Send a dated written demand. "
            "If the amount or value is significant, consult an advocate about civil "
            "recovery and whether a police complaint is appropriate."
        ),
    },
    {
        "id": "consumer_grievance",
        "title": "Consumer disputes and defective services",
        "keywords": (
            "consumer",
            "defective product",
            "refund",
            "warranty",
            "consumer court",
            "e commerce",
            "online purchase",
        ),
        "summary": (
            "The Consumer Protection Act framework provides remedies for defective "
            "goods, deficient services, and unfair trade practices through consumer "
            "commissions at district, state, and national levels, depending on claim value."
        ),
        "details": (
            "You typically need proof of purchase, defect or deficiency, and correspondence "
            "with the seller. Limitation periods apply to filing complaints."
        ),
        "practical_steps": (
            "Raise a written grievance with the seller and keep responses. File a complaint "
            "on the National Consumer Helpline or approach the appropriate consumer commission "
            "with an advocate if the value is high."
        ),
    },
    {
        "id": "fundamental_rights_overview",
        "title": "Constitutional rights (overview)",
        "keywords": (
            "fundamental rights",
            "constitution",
            "article 21",
            "equality",
            "freedom of speech",
            "illegal detention",
            "habeas",
        ),
        "summary": (
            "Part III of the Constitution of India guarantees fundamental rights such as "
            "equality before law, freedom of speech and expression (with reasonable restrictions), "
            "protection of life and personal liberty, and remedies through courts including "
            "constitutional writs in appropriate cases."
        ),
        "details": (
            "Enforcement usually requires approaching High Courts or the Supreme Court, or "
            "raising rights within criminal or civil proceedings. Specific articles and remedies "
            "depend on the violation alleged."
        ),
        "practical_steps": (
            "Document the government or private action you challenge. Consult a constitutional "
            "or civil rights advocate for writ remedies or defences in ongoing cases."
        ),
    },
    {
        "id": "domestic_violence_safety",
        "title": "Domestic violence and immediate safety",
        "keywords": (
            "domestic violence",
            "dowry",
            "protection officer",
            "maintenance",
            "cruelty",
            "498a",
            "dv act",
        ),
        "summary": (
            "The Protection of Women from Domestic Violence Act provides civil protection "
            "orders, residence orders, monetary relief, and custody directions in defined "
            "domestic relationships. Parallel criminal laws may apply where facts support them."
        ),
        "details": (
            "If you are in immediate danger, contact local emergency services or a trusted "
            "helpline before relying on legal process alone."
        ),
        "practical_steps": (
            "Reach a safe place if possible. Contact police or women's helplines, preserve "
            "medical or message evidence, and meet an advocate about protection orders under "
            "the DV Act and other remedies."
        ),
    },
    {
        "id": "legal_advice_disclaimer",
        "title": "How to use legal information safely",
        "keywords": (
            "legal advice",
            "lawyer",
            "advocate",
            "consult",
            "indiacode",
            "not a lawyer",
        ),
        "summary": (
            "LawyerAI provides general legal information for learning, not personalised "
            "legal advice. Outcomes depend on evidence, jurisdiction, and procedure. "
            "Official statutes are published on India Code; courts interpret law on specific facts."
        ),
        "details": (
            "No automated tool can replace an advocate who reviews your documents. "
            "Deadlines (limitation, filing, appeal) are strict and fact-specific."
        ),
        "practical_steps": (
            "List your goal (complaint, defence, recovery, compliance). Collect documents. "
            "Book a consultation with a qualified advocate licensed in your state."
        ),
    },
)
