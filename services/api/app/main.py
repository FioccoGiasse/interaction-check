from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo

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
        "checked_at": now_rome()
    }

@app.get("/api/sources")
def get_sources():
    return {
        "checked_at": now_rome(),
        "sources": [
            {
                "id": "aifa_registry",
                "name": "AIFA Anagrafica Farmaci",
                "description": "Fonte per identificare farmaci autorizzati in Italia, AIC, principio attivo, ATC, forma e confezione.",
                "source_type": "official_registry",
                "enabled": True,
                "configured": False,
                "clinical_interaction_source": False
            },
            {
                "id": "aifa_rcp_fi",
                "name": "AIFA RCP e Foglio Illustrativo",
                "description": "Fonte documentale per Riassunto delle Caratteristiche del Prodotto e Foglio Illustrativo.",
                "source_type": "official_document",
                "enabled": True,
                "configured": False,
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
