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
    clarifying_question: str


def _topic(
    id: str,
    title: str,
    keywords: tuple[str, ...],
    summary: str,
    details: str,
    practical_steps: str,
    clarifying_question: str = (
        "Could you share a bit more—what happened, where, and what outcome "
        "you need (complaint, compensation, or insurance)?"
    ),
) -> LegalTopic:
    return {
        "id": id,
        "title": title,
        "keywords": keywords,
        "summary": summary,
        "details": details,
        "practical_steps": practical_steps,
        "clarifying_question": clarifying_question,
    }


LEGAL_TOPICS: tuple[LegalTopic, ...] = (
    _topic(
        id="bns_ipc_transition",
        title="BNS, BNSS, BSA and the older IPC / CrPC framework",
        keywords=(
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
            "old ipc",
            "new criminal code",
        ),
        summary=(
            "India's central criminal-law statutes were substantially reorganised. "
            "The Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita "
            "(BNSS), and Bharatiya Sakshya Adhiniyam (BSA) are central to the new "
            "framework that largely replaced the Indian Penal Code (IPC), Code of "
            "Criminal Procedure (CrPC), and Indian Evidence Act for many matters, "
            "with effect from 1 July 2024, subject to transitional provisions and "
            "the facts of each case."
        ),
        details=(
            "Whether older labels (for example “IPC section”) or new BNS provisions "
            "apply depends on the date of the alleged conduct, filing, and any "
            "transitional rules. Courts and investigators may still refer to older "
            "statutes in pending matters. This assistant does not map old sections "
            "to new ones automatically—official consolidated texts should be checked."
        ),
        practical_steps=(
            "Note the approximate date of the incident and any police or court papers "
            "you have. Compare the statute names cited on those papers with current "
            "acts on India Code (indiacode.nic.in). Ask a qualified advocate how "
            "transitional rules apply to your situation."
        ),
        clarifying_question=(
            "Are you asking about which statute name applies generally, or about a "
            "specific police/court paper that still cites IPC or CrPC?"
        ),
    ),
    _topic(
        id="fir_and_complaint",
        title="FIRs and criminal complaints (general process)",
        keywords=(
            "fir",
            "first information report",
            "police complaint",
            "register fir",
            "cognizable",
            "non cognizable",
            "ncr",
            "station diary",
            "complaint police",
            "police station complaint",
        ),
        summary=(
            "In cognizable cases, police may register an FIR and begin investigation "
            "without prior magistrate permission in many situations. For non-cognizable "
            "offences, the usual route is often a complaint to a Magistrate rather than "
            "a direct FIR. Exact powers and remedies depend on the offence and facts."
        ),
        details=(
            "You can generally request a copy of the FIR or acknowledgement of your "
            "complaint. If police refuse to register where the law requires it, "
            "remedies may include supervisory complaint or approaching the Magistrate—"
            "specific steps vary by state practice and the offence category."
        ),
        practical_steps=(
            "Keep written notes of dates, witnesses, and documents. Visit the police "
            "station with any evidence you safely have. If turned away, ask for a "
            "written reason and consult an advocate about Magistrate complaint routes."
        ),
        clarifying_question=(
            "Is your question about how to file a police complaint generally, or about "
            "a specific incident (for example a road accident or theft)?"
        ),
    ),
    _topic(
        id="bail_basics",
        title="Bail and personal liberty (high-level)",
        keywords=(
            "bail",
            "anticipatory bail",
            "regular bail",
            "interim bail",
            "custody",
            "arrest",
            "remand",
        ),
        summary=(
            "Bail is a way to secure release from custody during investigation or "
            "trial, subject to conditions. Anticipatory bail is sought before arrest "
            "in some situations; regular bail after arrest or during trial. Courts weigh "
            "factors such as seriousness, flight risk, tampering concerns, and prior "
            "record—outcomes are fact-specific."
        ),
        details=(
            "Bail law operates under the criminal procedure code applicable to the case "
            "(including BNSS provisions where in force). This tool cannot predict whether "
            "bail will be granted in a particular matter."
        ),
        practical_steps=(
            "If someone is arrested or at risk of arrest, contact a criminal advocate "
            "immediately. Preserve medical records, employment proof, and family ties "
            "documents that may support a bail application."
        ),
        clarifying_question=(
            "Has an arrest already happened, or are you asking about anticipatory bail "
            "before a possible arrest?"
        ),
    ),
    _topic(
        id="return_of_property",
        title="Refusal to return belongings or money",
        keywords=(
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
        summary=(
            "When someone withholds your movable property or money, available routes "
            "often depend on how you parted with it (loan, deposit, sale, tenancy, "
            "employment, fraud allegation). Civil recovery, police complaint, or "
            "special tribunals may each be relevant for different fact patterns."
        ),
        details=(
            "A polite written demand with proof (messages, receipts, photos) is a "
            "common first step. Wrongful retention may support a civil suit for recovery "
            "or, if dishonesty is alleged with supporting facts, criminal avenues—"
            "which offence (if any) applies must be assessed by a lawyer from your documents."
        ),
        practical_steps=(
            "Gather proof of ownership and communications. Send a dated written demand. "
            "If the amount or value is significant, consult an advocate about civil "
            "recovery and whether a police complaint is appropriate."
        ),
    ),
    _topic(
        id="consumer_grievance",
        title="Consumer disputes and defective services",
        keywords=(
            "consumer",
            "defective product",
            "refund",
            "warranty",
            "consumer court",
            "e commerce",
            "online purchase",
        ),
        summary=(
            "The Consumer Protection Act framework provides remedies for defective "
            "goods, deficient services, and unfair trade practices through consumer "
            "commissions at district, state, and national levels, depending on claim value."
        ),
        details=(
            "You typically need proof of purchase, defect or deficiency, and correspondence "
            "with the seller. Limitation periods apply to filing complaints."
        ),
        practical_steps=(
            "Raise a written grievance with the seller and keep responses. File a complaint "
            "on the National Consumer Helpline or approach the appropriate consumer commission "
            "with an advocate if the value is high."
        ),
    ),
    _topic(
        id="fundamental_rights_overview",
        title="Constitutional rights (overview)",
        keywords=(
            "fundamental rights",
            "constitution",
            "article 21",
            "equality",
            "freedom of speech",
            "illegal detention",
            "habeas",
        ),
        summary=(
            "Part III of the Constitution of India guarantees fundamental rights such as "
            "equality before law, freedom of speech and expression (with reasonable restrictions), "
            "protection of life and personal liberty, and remedies through courts including "
            "constitutional writs in appropriate cases."
        ),
        details=(
            "Enforcement usually requires approaching High Courts or the Supreme Court, or "
            "raising rights within criminal or civil proceedings. Specific articles and remedies "
            "depend on the violation alleged."
        ),
        practical_steps=(
            "Document the government or private action you challenge. Consult a constitutional "
            "or civil rights advocate for writ remedies or defences in ongoing cases."
        ),
    ),
    _topic(
        id="domestic_violence_safety",
        title="Domestic violence and immediate safety",
        keywords=(
            "domestic violence",
            "dowry",
            "protection officer",
            "maintenance",
            "cruelty",
            "498a",
            "dv act",
        ),
        summary=(
            "The Protection of Women from Domestic Violence Act provides civil protection "
            "orders, residence orders, monetary relief, and custody directions in defined "
            "domestic relationships. Parallel criminal laws may apply where facts support them."
        ),
        details=(
            "If you are in immediate danger, contact local emergency services or a trusted "
            "helpline before relying on legal process alone."
        ),
        practical_steps=(
            "Reach a safe place if possible. Contact police or women's helplines, preserve "
            "medical or message evidence, and meet an advocate about protection orders under "
            "the DV Act and other remedies."
        ),
    ),
    _topic(
        id="legal_advice_disclaimer",
        title="How to use legal information safely",
        keywords=(
            "legal advice",
            "lawyer",
            "advocate",
            "consult",
            "indiacode",
            "not a lawyer",
        ),
        summary=(
            "LawyerAI provides general legal information for learning, not personalised "
            "legal advice. Outcomes depend on evidence, jurisdiction, and procedure. "
            "Official statutes are published on India Code; courts interpret law on specific facts."
        ),
        details=(
            "No automated tool can replace an advocate who reviews your documents. "
            "Deadlines (limitation, filing, appeal) are strict and fact-specific."
        ),
        practical_steps=(
            "List your goal (complaint, defence, recovery, compliance). Collect documents. "
            "Book a consultation with a qualified advocate licensed in your state."
        ),
    ),
    # —— Road / vehicle incidents (Phase 1 expansion) ——
    _topic(
        id="road_accident_basics",
        title="Road accidents and what to do first",
        keywords=(
            "road accident",
            "car accident",
            "bike accident",
            "scooter accident",
            "motor accident",
            "vehicle accident",
            "traffic accident",
            "road crash",
            "met accident",
            "accident aagiduchi",
            "accident aayiduchu",
            "car crash",
            "two wheeler accident",
            "auto accident",
            "road mishap",
        ),
        summary=(
            "After a road accident in India, immediate priorities are safety and medical "
            "help, then documenting the scene where it is safe to do so. Police reporting, "
            "insurance notification, and later civil or criminal steps depend on injuries, "
            "property damage, and whether a vehicle fled the scene."
        ),
        details=(
            "Useful early records often include photos of vehicle positions and damage, "
            "location details, registration numbers, dashcam or CCTV leads, and names of "
            "witnesses. Do not invent offence labels or section numbers yourself—police "
            "and counsel apply the statutes that fit the facts. Official motor-vehicle "
            "and criminal frameworks are published on India Code; state traffic rules may "
            "also apply."
        ),
        practical_steps=(
            "Call emergency/medical help if anyone is hurt. Move to safety if possible. "
            "Note the other vehicle’s registration and driver details. Inform the local "
            "police station when required for your situation. Notify your insurer promptly "
            "as your policy usually requires. Consult an advocate if there are injuries, "
            "disputed fault, or significant loss."
        ),
        clarifying_question=(
            "Was anyone injured, was there only vehicle damage, or did the other vehicle "
            "leave without stopping? That helps point to the most relevant next steps."
        ),
    ),
    _topic(
        id="hit_and_run",
        title="Hit-and-run and a vehicle that flees",
        keywords=(
            "hit and run",
            "hit-and-run",
            "vehicle fled",
            "driver ran away",
            "escaped without stopping",
            "number plate escaped",
            "odittu poyiduchu",
            "odittu poitaanga",
            "flee after accident",
            "absconding driver",
            "did not stop accident",
        ),
        summary=(
            "When a vehicle involved in a collision leaves without exchanging particulars "
            "or rendering aid where expected, people commonly report the incident to police "
            "with whatever identification they have (registration fragment, colour, CCTV "
            "area, time). Investigation and any criminal or civil follow-up depend on "
            "evidence and injuries—outcomes are not automatic."
        ),
        details=(
            "Preserve photos, videos, witness contacts, and medical records. Ask nearby "
            "shops or cameras about footage quickly. This assistant will not invent the "
            "exact offence label or section; an advocate or police can map facts to the "
            "applicable law under the current criminal and motor-vehicle framework."
        ),
        practical_steps=(
            "Seek medical care if injured. File a police report with time, place, and any "
            "vehicle description. Inform your insurer. Keep treatment bills. Speak with an "
            "advocate about compensation options if there are injuries or major loss."
        ),
        clarifying_question=(
            "Do you have any part of the registration number, dashcam/CCTV lead, or only "
            "a general vehicle description?"
        ),
    ),
    _topic(
        id="vehicle_damage_claim",
        title="Vehicle damage after a collision",
        keywords=(
            "vehicle damage",
            "car damage",
            "bike damage",
            "scooter damage",
            "bumper damage",
            "dent accident",
            "repair claim",
            "own damage",
            "third party damage",
            "garage estimate",
            "car scratch accident",
            "vehicle repair",
        ),
        summary=(
            "Property damage from a collision is often handled through motor insurance "
            "(own-damage cover and/or the other party’s third-party liability), supported "
            "by photographs, a repair estimate, and the insurer’s survey process. A police "
            "report may be needed depending on insurer instructions and the seriousness of "
            "the incident."
        ),
        details=(
            "Policies differ on deductibles, cashless garages, depreciation, and "
            "documentation deadlines. Dispute with an insurer may later involve the "
            "insurer’s grievance process, the Insurance Ombudsman in suitable cases, or "
            "civil recovery—fact-specific advice needs a professional."
        ),
        practical_steps=(
            "Photograph damage before repairs. Do not dispose of damaged parts if the "
            "insurer asks to inspect them. Call your insurer’s claim helpline promptly. "
            "Ask whether a police report or FIR acknowledgement is required for your claim. "
            "Keep all invoices."
        ),
        clarifying_question=(
            "Do you have comprehensive (own-damage) cover on your policy, or are you "
            "hoping to claim only against the other vehicle’s insurer?"
        ),
    ),
    _topic(
        id="accident_injury_compensation",
        title="Injuries in a road accident and compensation pathways",
        keywords=(
            "accident injury",
            "road injury",
            "fracture accident",
            "hospital accident",
            "injured in accident",
            "compensation accident",
            "motor accident claim",
            "maat claim",
            "personal injury accident",
            "medical bills accident",
            "kaayam",
            "injury claim",
        ),
        summary=(
            "If a road accident causes injury, priorities are medical treatment and "
            "preserving records (hospital notes, bills, disability certificates where "
            "issued). Compensation may involve motor insurance, and in many cases "
            "specialised motor accident claim processes or civil claims—routes depend on "
            "fault, cover, and evidence."
        ),
        details=(
            "Do not treat online summaries as a guarantee of compensation amount. Serious "
            "injuries, death claims, and disputed liability need an advocate familiar with "
            "motor accident practice in your state. Keep police and medical documents "
            "aligned on dates and vehicle details."
        ),
        practical_steps=(
            "Get treatment first. Preserve all medical bills and reports. Ensure the "
            "incident is recorded with police where appropriate. Notify insurers. Consult "
            "an advocate early about claim forums and limitation periods."
        ),
        clarifying_question=(
            "Are injuries minor outpatient injuries, or was there hospital admission / "
            "longer-term disability?"
        ),
    ),
    _topic(
        id="motor_insurance_claim",
        title="Motor insurance claims after an accident",
        keywords=(
            "insurance claim",
            "motor insurance",
            "car insurance claim",
            "bike insurance",
            "third party insurance",
            "comprehensive insurance",
            "claim rejected",
            "insurance surveyor",
            "cashless claim",
            "policy claim accident",
            "insurance claim process",
            "own damage claim",
        ),
        summary=(
            "Motor insurance in India commonly includes third-party liability cover "
            "(compulsory for use on public roads) and may include own-damage cover under "
            "a comprehensive or similar package. After an accident, insurers typically "
            "expect prompt intimation, documents, and sometimes a survey before repair "
            "approval."
        ),
        details=(
            "Claim outcomes turn on policy terms, non-disclosure, delay, intoxication "
            "clauses, driving licence validity, and whether the driver was authorised— "
            "this tool cannot decide your claim. Grievance escalation may include the "
            "insurer’s IRDAI-mandated process and, in eligible matters, the Insurance "
            "Ombudsman. Verify current IRDAI consumer guidance on official sites."
        ),
        practical_steps=(
            "Intimate the insurer as soon as practicable. Share photos, FIR/GD copy if "
            "asked, driving licence, RC, and policy details. Follow surveyor instructions "
            "before major repairs when required. If a claim is delayed or denied, use the "
            "insurer grievance channel in writing and keep copies."
        ),
        clarifying_question=(
            "Has the insurer already registered a claim number, or are you still at the "
            "first notification stage?"
        ),
    ),
    _topic(
        id="accident_police_complaint",
        title="Police complaints after a traffic or road incident",
        keywords=(
            "accident police",
            "police after accident",
            "traffic police complaint",
            "accident fir",
            "gd entry accident",
            "complaint after crash",
            "report accident police",
            "traffic complaint",
            "accident station",
        ),
        summary=(
            "For many road incidents—especially those with injury, death, or a fleeing "
            "vehicle—people report to the local police station or traffic police with "
            "date, time, place, vehicle numbers, and injury details. The form of record "
            "(for example a report that leads to investigation) depends on the facts and "
            "local practice."
        ),
        details=(
            "Ask for an acknowledgement or copy of what was recorded. If you believe a "
            "cognizable case should be registered and police refuse without reason, note "
            "the refusal and consult an advocate about supervisory or Magistrate routes. "
            "This app will not invent specific section numbers for your case."
        ),
        practical_steps=(
            "Write a clear timeline before you go to the station. Carry ID, vehicle "
            "papers if available, photos, and medical notes. Request written "
            "acknowledgement. Inform your insurer that a police report was made."
        ),
        clarifying_question=(
            "Are you the injured party / vehicle owner seeking to file a complaint, or "
            "has the other side already filed one against you?"
        ),
    ),
)
