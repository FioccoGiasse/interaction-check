from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3
import unicodedata
import re
import tempfile
import urllib.request
from pypdf import PdfReader
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "enia.db"

app = FastAPI(
    title="ENIA Interaction Check API",
    version="0.1.0",
    description="Backend API for ENIA Interaction Check"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_rome():
    return datetime.now(ZoneInfo("Europe/Rome")).isoformat()

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


FOOD_AND_SUPPLEMENT_TERMS = [
    "alcol",
    "alcool",
    "bevande alcoliche",
    "etilismo",
    "alcolismo",
    "alcoolismo",
    "etanolo",
    "abuso di alcol",
    "consumo di alcol",
    "cibo",
    "alimenti",
    "alimentazione",
    "pasto",
    "pasti",
    "succo di pompelmo",
    "pompelmo",
    "latte",
    "calcio",
    "integratori",
    "integratore",
    "iperico",
    "erba di san giovanni",
    "st john",
    "liquirizia",
    "caffeina",
    "caffè",
    "te",
    "tè",
    "soia",
    "vitamina k",
    "vitamina d",
    "vitamina a",
    "potassio",
    "magnesio",
    "ferro",
    "zinco",
    "cranberry",
    "mirtillo rosso",
    "ginkgo",
    "ginseng",
    "echinacea",
    "curcuma",
    "aglio",
    "omega 3",
    "olio di pesce"
]


def clean_document_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def download_pdf_to_temp(url: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ENIA Interaction Check research prototype"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()

    Path(tmp.name).write_bytes(content)
    return Path(tmp.name)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []

    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"\n\n--- PAGE {index} ---\n\n{page_text}")

    return clean_document_text("\n".join(pages))


def extract_rcp_section_45(text: str) -> str:
    compact = clean_document_text(text)

    patterns = [
        r"4\s*[\.\)]\s*5\s+Interazioni.*?(?=4\s*[\.\)]\s*6\s+|5\s*[\.\)]\s*1\s+|$)",
        r"4\.5\s+Interazioni.*?(?=4\.6\s+|5\.1\s+|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, compact, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_document_text(match.group(0))

    return ""


def split_document_sentences(text: str) -> list[str]:
    text = clean_document_text(text)
    parts = re.split(r"(?<=[\.\;\:])\s+(?=[A-ZÀ-Ü0-9])", text)
    return [part.strip() for part in parts if part.strip()]


def find_food_candidates_in_section(section_text: str, source_url: str) -> list[dict]:
    candidates = []
    sentences = split_document_sentences(section_text)

    for sentence in sentences:
        sentence_lower = sentence.lower()
        matched_terms = []

        for term in FOOD_AND_SUPPLEMENT_TERMS:
            pattern = r"\b" + re.escape(term.lower()) + r"\b"
            if re.search(pattern, sentence_lower):
                matched_terms.append(term)

        if matched_terms:
            candidates.append({
                "matched_terms": sorted(set(matched_terms)),
                "source_name": "AIFA RCP",
                "source_url": source_url,
                "source_section": "4.5 Interazioni con altri medicinali ed altre forme di interazione",
                "validation_status": "candidate_from_document",
                "candidate_text": sentence
            })

    return candidates


def find_unclassified_interaction_sentences(section_text: str, candidates: list[dict]) -> list[dict]:
    candidate_texts = {
        clean_document_text(candidate.get("candidate_text", ""))
        for candidate in candidates
    }

    trigger_terms = [
        "assunzione",
        "concomitante",
        "concomitanza",
        "interazione",
        "interazioni",
        "esposizione",
        "sostanze",
        "metabolismo",
        "induzione",
        "induttori",
        "inibitori",
        "aumento",
        "riduzione",
        "rischio",
        "tossicità",
        "tossicita",
        "monitoraggio",
        "cautela",
        "somministrazione"
    ]

    unclassified = []

    for sentence in split_document_sentences(section_text):
        cleaned_sentence = clean_document_text(sentence)

        if not cleaned_sentence:
            continue

        if cleaned_sentence in candidate_texts:
            continue

        lower_sentence = cleaned_sentence.lower()

        if any(term in lower_sentence for term in trigger_terms):
            unclassified.append({
                "source_section": "4.5 Interazioni con altri medicinali ed altre forme di interazione",
                "review_status": "needs_review",
                "sentence_text": cleaned_sentence
            })

    return unclassified[:20]




def extract_food_candidates_from_rcp_url(url: str) -> dict:
    pdf_path = download_pdf_to_temp(url)
    text = extract_pdf_text(pdf_path)
    section = extract_rcp_section_45(text)
    candidates = find_food_candidates_in_section(section, url) if section else []
    unclassified_sentences = find_unclassified_interaction_sentences(section, candidates) if section else []

    return {
        "source_url": url,
        "section_found": bool(section),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "unclassified_sentence_count": len(unclassified_sentences),
        "unclassified_sentences": unclassified_sentences
    }

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def database_exists():
    return DB_PATH.exists()

@app.get("/")
def root():
    return {
        "app": "ENIA Interaction Check",
        "status": "running",
        "checked_at": now_rome()
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "api",
        "database_exists": database_exists(),
        "checked_at": now_rome()
    }

@app.get("/api/database/version")
def database_version():
    if not database_exists():
        return {
            "configured": False,
            "message": "Database AIFA non ancora importato."
        }

    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                source_name,
                source_url,
                imported_at,
                rows_imported,
                version_label
            FROM database_versions
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

    if row is None:
        return {
            "configured": False,
            "message": "Database presente, ma versione non trovata."
        }

    return {
        "configured": True,
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "imported_at": row["imported_at"],
        "rows_imported": row["rows_imported"],
        "version_label": row["version_label"]
    }

@app.get("/api/sources")
def get_sources():
    aifa_configured = database_exists()

    return {
        "checked_at": now_rome(),
        "sources": [
            {
                "id": "aifa_registry",
                "name": "AIFA Anagrafica Farmaci",
                "description": "Fonte per identificare farmaci autorizzati in Italia, AIC, principio attivo, ATC, forma e confezione.",
                "source_type": "official_registry",
                "enabled": True,
                "configured": aifa_configured,
                "clinical_interaction_source": False
            },
            {
                "id": "aifa_rcp_fi",
                "name": "AIFA RCP e Foglio Illustrativo",
                "description": "Fonte documentale per Riassunto delle Caratteristiche del Prodotto e Foglio Illustrativo.",
                "source_type": "official_document",
                "enabled": True,
                "configured": aifa_configured,
                "clinical_interaction_source": False
            },
            {
                "id": "enia_validated_kb",
                "name": "ENIA Knowledge Base validata",
                "description": "Fonte interna strutturata per interazioni validate da medico o farmacista.",
                "source_type": "validated_internal_knowledge_base",
                "enabled": True,
                "configured": False,
                "clinical_interaction_source": True
            },
            {
                "id": "commercial_provider",
                "name": "Provider clinico commerciale",
                "description": "Fonte esterna opzionale per interazioni cliniche, configurabile in futuro.",
                "source_type": "external_clinical_provider",
                "enabled": False,
                "configured": False,
                "clinical_interaction_source": True
            },
            {
                "id": "controlled_chatbot",
                "name": "Assistente ENIA controllato",
                "description": "Interfaccia conversazionale che può spiegare solo dati strutturati restituiti dal backend.",
                "source_type": "controlled_llm_interface",
                "enabled": True,
                "configured": False,
                "clinical_interaction_source": False
            }
        ]
    }

@app.get("/api/drugs/search")
def search_drugs(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=50)):
    if not database_exists():
        return {
            "query": q,
            "count": 0,
            "results": [],
            "message": "Database AIFA non ancora importato."
        }

    normalized_query = normalize_text(q)
    like_query = f"%{normalized_query}%"
    raw_like_query = f"%{q.strip()}%"

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                id,
                aic_code,
                commercial_name,
                package_description,
                marketing_authorisation_holder,
                administrative_status,
                pharmaceutical_form,
                atc_code,
                active_ingredient,
                supply_regime,
                leaflet_url,
                rcp_url,
                source,
                source_url,
                source_updated_at
            FROM drugs
            WHERE
                normalized_commercial_name LIKE ?
                OR normalized_active_ingredient LIKE ?
                OR aic_code LIKE ?
                OR commercial_name LIKE ?
            ORDER BY commercial_name ASC
            LIMIT ?
        """, (
            like_query,
            like_query,
            raw_like_query,
            raw_like_query,
            limit
        )).fetchall()

    results = []

    for row in rows:
        results.append({
            "id": row["id"],
            "aic_code": row["aic_code"],
            "commercial_name": row["commercial_name"],
            "package_description": row["package_description"],
            "marketing_authorisation_holder": row["marketing_authorisation_holder"],
            "administrative_status": row["administrative_status"],
            "pharmaceutical_form": row["pharmaceutical_form"],
            "atc_code": row["atc_code"],
            "active_ingredient": row["active_ingredient"],
            "supply_regime": row["supply_regime"],
            "leaflet_url": row["leaflet_url"],
            "rcp_url": row["rcp_url"],
            "source": row["source"],
            "source_url": row["source_url"],
            "source_updated_at": row["source_updated_at"]
        })

    return {
        "query": q,
        "normalized_query": normalized_query,
        "count": len(results),
        "results": results
    }



def extract_rcp_section_47(text: str) -> str:
    compact = clean_document_text(text)

    patterns = [
        r"4\s*[\.\)]\s*7\s+Effetti.*?(?=4\s*[\.\)]\s*8\s+|5\s*[\.\)]\s*1\s+|$)",
        r"4\.7\s+Effetti.*?(?=4\.8\s+|5\.1\s+|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, compact, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_document_text(match.group(0))

    return ""


def extract_section_47_from_rcp_url(url: str) -> dict:
    pdf_path = download_pdf_to_temp(url)
    text = extract_pdf_text(pdf_path)
    section = extract_rcp_section_47(text)

    return {
        "source_url": url,
        "section_found": bool(section),
        "section_text": section,
        "character_count": len(section)
    }

DRUG_INTERACTION_CLASS_TERMS = [
    "anticoagulanti orali",
    "anticoagulanti",
    "antiepilettici",
    "farmaci antiepilettici",
    "induttori enzimatici",
    "induttori delle monossigenasi epatiche",
    "induzione delle monossigenasi epatiche",
    "inibitori enzimatici",
    "inibitori del cyp",
    "substrati del cyp",
    "farmaci epatotossici",
    "farmaci nefrotossici",
    "contraccettivi orali",
    "diuretici",
    "fans",
    "antiinfiammatori non steroidei",
    "antibiotici",
    "macrolidi",
    "fluorochinoloni",
    "antidepressivi",
    "ssri",
    "benzodiazepine",
    "oppioidi",
    "corticosteroidi",
    "immunosoppressori",
    "statine",
    "antiaritmici",
    "antidiabetici",
    "ipoglicemizzanti",
    "antipertensivi"
]


DRUG_INTERACTION_STOP_TERMS = {
    "",
    "acqua",
    "alcool",
    "alcol",
    "calcio",
    "ferro",
    "zinco",
    "magnesio",
    "potassio",
    "sodio",
    "glucosio",
    "lattosio",
    "saccarosio",
    "amido",
    "gelatina",
    "silice",
    "titanio"
}


def normalise_drug_match(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value


def split_active_ingredient_terms(value: str) -> list[str]:
    value = value or ""
    parts = re.split(r"\+|,|;|/|\be\b", value, flags=re.IGNORECASE)
    cleaned = []

    for part in parts:
        part = normalise_drug_match(part)
        part = re.sub(r"\([^)]*\)", "", part).strip()

        if len(part) < 4:
            continue

        if part in DRUG_INTERACTION_STOP_TERMS:
            continue

        cleaned.append(part)

    return cleaned


@lru_cache(maxsize=1)
def load_aifa_active_ingredient_terms() -> tuple[str, ...]:
    if not database_exists():
        return tuple()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT active_ingredient
            FROM drugs
            WHERE active_ingredient IS NOT NULL
              AND active_ingredient != ''
            """
        ).fetchall()

    terms = set()

    for row in rows:
        active_ingredient = row["active_ingredient"]
        for term in split_active_ingredient_terms(active_ingredient):
            terms.add(term)

    return tuple(sorted(terms, key=len, reverse=True))


def find_drug_interaction_candidates_in_section(
    section_text: str,
    source_url: str,
    source_active_ingredient: str = ""
) -> list[dict]:
    candidates = []
    sentences = split_document_sentences(section_text)

    source_terms = set(split_active_ingredient_terms(source_active_ingredient))
    aifa_terms = list(load_aifa_active_ingredient_terms())
    all_terms = DRUG_INTERACTION_CLASS_TERMS + aifa_terms

    for index, sentence in enumerate(sentences, start=1):
        sentence = clean_document_text(sentence)

        if len(sentence) < 40:
            continue

        sentence_lower = normalise_drug_match(sentence)
        matched_terms = []

        for term in all_terms:
            term_normalised = normalise_drug_match(term)

            if term_normalised in source_terms:
                continue

            pattern = r"(?<![a-zà-ü0-9])" + re.escape(term_normalised) + r"(?![a-zà-ü0-9])"

            if re.search(pattern, sentence_lower):
                matched_terms.append(term)

        matched_terms = sorted(set(matched_terms), key=len, reverse=True)

        candidates.append({
            "matched_terms": matched_terms[:15],
            "source_name": "AIFA RCP",
            "source_url": source_url,
            "source_section": "4.5 Interazioni con altri medicinali ed altre forme di interazione",
            "validation_status": "candidate_from_document",
            "candidate_type": "drug_interaction_candidate",
            "candidate_text": sentence,
            "sequence_in_section": index,
            "recognition_status": "recognised_terms" if matched_terms else "unclassified_section_45_text"
        })

    return candidates


def extract_drug_interaction_candidates_from_rcp_url(
    url: str,
    source_active_ingredient: str = ""
) -> dict:
    pdf_path = download_pdf_to_temp(url)
    text = extract_pdf_text(pdf_path)
    section = extract_rcp_section_45(text)
    candidates = find_drug_interaction_candidates_in_section(
        section,
        url,
        source_active_ingredient
    ) if section else []

    return {
        "source_url": url,
        "section_found": bool(section),
        "candidate_count": len(candidates),
        "candidates": candidates
    }

@app.post("/api/interactions/food/suggested")
def suggest_food_interactions(payload: dict):
    selected_drugs = payload.get("selected_drugs", [])
    selected_sources = payload.get("selected_sources", [])

    interactions = []
    rcp_sources_checked = []

    use_aifa_rcp = "aifa_rcp_fi" in selected_sources
    use_enia_kb = "enia_validated_kb" in selected_sources

    for drug in selected_drugs:
        rcp_url = drug.get("rcp_url")
        leaflet_url = drug.get("leaflet_url")
        source_status = "source_available" if rcp_url or leaflet_url else "source_not_available"
        extraction_status = "not_requested"
        candidate_count = 0
        unclassified_sentence_count = 0

        if use_aifa_rcp and rcp_url:
            try:
                extraction_result = extract_food_candidates_from_rcp_url(rcp_url)
                extraction_status = "section_found" if extraction_result.get("section_found") else "section_not_found"
                candidate_count = extraction_result.get("candidate_count", 0)
                unclassified_sentence_count = extraction_result.get("unclassified_sentence_count", 0)

                for index, candidate in enumerate(extraction_result.get("candidates", []), start=1):
                    matched_terms = candidate.get("matched_terms", [])

                    interactions.append({
                        "id": f"rcp-{drug.get('aic_code')}-{index}",
                        "commercial_name": drug.get("commercial_name"),
                        "aic_code": drug.get("aic_code"),
                        "active_ingredient": drug.get("active_ingredient"),
                        "food_or_substance": ", ".join(matched_terms),
                        "interaction_summary": candidate.get("candidate_text"),
                        "severity": "non classificata",
                        "evidence_level": "testo RCP AIFA",
                        "mechanism": "",
                        "recommendation": "Valutare clinicamente prima di includere nel report finale.",
                        "patient_explanation": "",
                        "clinician_explanation": candidate.get("candidate_text"),
                        "source_name": candidate.get("source_name"),
                        "source_url": candidate.get("source_url"),
                        "source_section": candidate.get("source_section"),
                        "validation_status": candidate.get("validation_status"),
                        "candidate_type": "document_candidate",
                        "matched_terms": matched_terms
                    })

            except Exception:
                extraction_status = "extraction_error"

        rcp_sources_checked.append({
            "commercial_name": drug.get("commercial_name"),
            "aic_code": drug.get("aic_code"),
            "active_ingredient": drug.get("active_ingredient"),
            "rcp_url": rcp_url,
            "leaflet_url": leaflet_url,
            "source_name": "AIFA RCP e Foglio Illustrativo",
            "status": source_status,
            "extraction_status": extraction_status,
            "candidate_count": candidate_count,
            "unclassified_sentence_count": unclassified_sentence_count
        })

    if use_enia_kb and database_exists():
        with get_conn() as conn:
            for drug in selected_drugs:
                active_ingredient = drug.get("active_ingredient")
                normalized_active_ingredient = normalize_text(active_ingredient)

                if not normalized_active_ingredient:
                    continue

                rows = conn.execute(
                    """
                    SELECT
                        id,
                        active_ingredient,
                        food_or_substance,
                        interaction_summary,
                        severity,
                        evidence_level,
                        mechanism,
                        recommendation,
                        patient_explanation,
                        clinician_explanation,
                        source_name,
                        source_url,
                        source_section,
                        validation_status,
                        validated_by,
                        validated_at
                    FROM enia_food_interactions
                    WHERE normalized_active_ingredient = ?
                    ORDER BY food_or_substance ASC
                    """,
                    (normalized_active_ingredient,)
                ).fetchall()

                for row in rows:
                    interaction = dict(row)
                    interaction["commercial_name"] = drug.get("commercial_name")
                    interaction["aic_code"] = drug.get("aic_code")
                    interaction["candidate_type"] = "validated_kb"
                    interactions.append(interaction)

    if interactions:
        message = f"Trovate {len(interactions)} interazioni o candidate interaction nelle fonti configurate."
    else:
        message = "Nessuna interazione alimentare strutturata disponibile nelle fonti configurate."

    return {
        "checked_at": now_rome(),
        "selected_drug_count": len(selected_drugs),
        "selected_sources": selected_sources,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "rcp_sources_checked": rcp_sources_checked,
        "message": message,
        "clinical_safety_note": "Il sistema non genera interazioni alimentari tramite AI. Le interazioni validate provengono dalla Knowledge Base ENIA. I risultati da RCP AIFA sono candidati documentali e richiedono valutazione clinica prima dell'inclusione nel report."
    }


@app.post("/api/interactions/drugs/suggested")
def suggest_drug_interactions(payload: dict):
    selected_drugs = payload.get("selected_drugs", [])
    selected_sources = payload.get("selected_sources", [])

    interactions = []
    rcp_sources_checked = []

    use_aifa_rcp = "aifa_rcp_fi" in selected_sources

    for drug in selected_drugs:
        rcp_url = drug.get("rcp_url")
        leaflet_url = drug.get("leaflet_url")
        active_ingredient = drug.get("active_ingredient")

        source_status = "source_available" if rcp_url or leaflet_url else "source_not_available"
        extraction_status = "not_requested"
        candidate_count = 0

        if use_aifa_rcp and rcp_url:
            try:
                extraction_result = extract_drug_interaction_candidates_from_rcp_url(
                    rcp_url,
                    active_ingredient or ""
                )

                extraction_status = "section_found" if extraction_result.get("section_found") else "section_not_found"
                candidate_count = extraction_result.get("candidate_count", 0)

                for index, candidate in enumerate(extraction_result.get("candidates", []), start=1):
                    matched_terms = candidate.get("matched_terms", [])

                    interactions.append({
                        "id": f"drug-rcp-{drug.get('aic_code')}-{index}",
                        "commercial_name": drug.get("commercial_name"),
                        "aic_code": drug.get("aic_code"),
                        "active_ingredient": active_ingredient,
                        "interacting_drug_or_class": ", ".join(matched_terms) if matched_terms else "testo sezione 4.5 da revisionare",
                        "interaction_summary": candidate.get("candidate_text"),
                        "source_name": candidate.get("source_name"),
                        "source_url": candidate.get("source_url"),
                        "source_section": candidate.get("source_section"),
                        "validation_status": candidate.get("validation_status"),
                        "candidate_type": candidate.get("candidate_type"),
                        "matched_terms": matched_terms,
                        "recognition_status": candidate.get("recognition_status"),
                        "sequence_in_section": candidate.get("sequence_in_section"),
                        "recommendation": "Valutare clinicamente prima di includere nel report finale."
                    })

            except Exception:
                extraction_status = "extraction_error"

        rcp_sources_checked.append({
            "commercial_name": drug.get("commercial_name"),
            "aic_code": drug.get("aic_code"),
            "active_ingredient": active_ingredient,
            "rcp_url": rcp_url,
            "leaflet_url": leaflet_url,
            "source_name": "AIFA RCP e Foglio Illustrativo",
            "status": source_status,
            "extraction_status": extraction_status,
            "candidate_count": candidate_count
        })

    if interactions:
        message = f"Trovati {len(interactions)} candidati documentali di interazione farmaco farmaco dalla sezione 4.5 RCP."
    else:
        message = "Nessun candidato documentale di interazione farmaco farmaco trovato nella sezione 4.5 RCP."

    return {
        "checked_at": now_rome(),
        "selected_drug_count": len(selected_drugs),
        "selected_sources": selected_sources,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "rcp_sources_checked": rcp_sources_checked,
        "message": message,
        "clinical_safety_note": "I risultati da RCP AIFA sono candidati documentali. Devono essere valutati dal medico prima dell'inclusione nel report."
    }


@app.post("/api/rcp/section-47")
def get_rcp_section_47(payload: dict):
    selected_drugs = payload.get("selected_drugs", [])
    selected_sources = payload.get("selected_sources", [])

    results = []

    use_aifa_rcp = "aifa_rcp_fi" in selected_sources

    for drug in selected_drugs:
        rcp_url = drug.get("rcp_url")
        leaflet_url = drug.get("leaflet_url")
        section_found = False
        section_text = ""
        character_count = 0
        extraction_status = "not_requested"

        if use_aifa_rcp and rcp_url:
            try:
                extraction_result = extract_section_47_from_rcp_url(rcp_url)
                section_found = extraction_result.get("section_found", False)
                section_text = extraction_result.get("section_text", "")
                character_count = extraction_result.get("character_count", 0)
                extraction_status = "section_found" if section_found else "section_not_found"
            except Exception:
                extraction_status = "extraction_error"

        results.append({
            "commercial_name": drug.get("commercial_name"),
            "aic_code": drug.get("aic_code"),
            "active_ingredient": drug.get("active_ingredient"),
            "rcp_url": rcp_url,
            "leaflet_url": leaflet_url,
            "source_name": "AIFA RCP",
            "source_section": "4.7 Effetti sulla capacità di guidare veicoli e sull'uso di macchinari",
            "section_found": section_found,
            "section_text": section_text,
            "character_count": character_count,
            "extraction_status": extraction_status
        })

    return {
        "checked_at": now_rome(),
        "selected_drug_count": len(selected_drugs),
        "selected_sources": selected_sources,
        "section": "4.7 Effetti sulla capacità di guidare veicoli e sull'uso di macchinari",
        "result_count": len(results),
        "results": results,
        "message": "Estrazione letterale sezione 4.7 completata per i farmaci selezionati.",
        "clinical_safety_note": "Il testo della sezione 4.7 è estratto dal RCP AIFA e non viene interpretato automaticamente."
    }

