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


def extract_food_candidates_from_rcp_url(url: str) -> dict:
    pdf_path = download_pdf_to_temp(url)
    text = extract_pdf_text(pdf_path)
    section = extract_rcp_section_45(text)
    candidates = find_food_candidates_in_section(section, url) if section else []

    return {
        "source_url": url,
        "section_found": bool(section),
        "candidate_count": len(candidates),
        "candidates": candidates
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

@app.post("/api/interactions/food/suggested")
def suggest_food_interactions(payload: dict):
    selected_drugs = payload.get("selected_drugs", [])
    selected_sources = payload.get("selected_sources", [])

    interactions = []
    rcp_sources_checked = []

    for drug in selected_drugs:
        rcp_url = drug.get("rcp_url")
        leaflet_url = drug.get("leaflet_url")

        rcp_sources_checked.append({
            "commercial_name": drug.get("commercial_name"),
            "aic_code": drug.get("aic_code"),
            "active_ingredient": drug.get("active_ingredient"),
            "rcp_url": rcp_url,
            "leaflet_url": leaflet_url,
            "source_name": "AIFA RCP e Foglio Illustrativo",
            "status": "source_available" if rcp_url or leaflet_url else "source_not_available"
        })

    if database_exists():
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
                    interactions.append(interaction)

    if interactions:
        message = f"Trovate {len(interactions)} interazioni alimentari strutturate nelle fonti configurate."
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
        "clinical_safety_note": "Il sistema non genera interazioni alimentari tramite AI. Le interazioni sono mostrate solo se presenti nella Knowledge Base ENIA strutturata e tracciabile o recuperate da fonti documentali AIFA tracciabili."
    }
