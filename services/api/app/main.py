from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3
import unicodedata
import re

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
def suggested_food_interactions(payload: dict):
    selected_drugs = payload.get("selected_drugs", [])
    selected_sources = payload.get("selected_sources", [])

    return {
        "checked_at": now_rome(),
        "selected_drug_count": len(selected_drugs),
        "selected_sources": selected_sources,
        "interaction_count": 0,
        "interactions": [],
        "message": "Nessuna interazione alimentare strutturata disponibile nelle fonti configurate.",
        "clinical_safety_note": "Il sistema non genera interazioni alimentari tramite AI. Le interazioni saranno mostrate solo se presenti in una fonte strutturata e tracciabile."
    }

