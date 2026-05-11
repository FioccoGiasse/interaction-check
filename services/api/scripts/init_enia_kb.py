import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "enia.db"

def now_rome():
    return datetime.now(ZoneInfo("Europe/Rome")).isoformat()

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database non trovato: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enia_food_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                active_ingredient TEXT NOT NULL,
                normalized_active_ingredient TEXT NOT NULL,
                food_or_substance TEXT NOT NULL,
                normalized_food_or_substance TEXT NOT NULL,
                interaction_summary TEXT NOT NULL,
                severity TEXT,
                evidence_level TEXT,
                mechanism TEXT,
                recommendation TEXT,
                patient_explanation TEXT,
                clinician_explanation TEXT,
                source_name TEXT NOT NULL,
                source_url TEXT,
                source_section TEXT,
                validation_status TEXT NOT NULL,
                validated_by TEXT,
                validated_at TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_enia_food_active
            ON enia_food_interactions(normalized_active_ingredient)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_enia_food_substance
            ON enia_food_interactions(normalized_food_or_substance)
        """)

        conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM enia_food_interactions"
        ).fetchone()[0]

    finally:
        conn.close()

    print("ENIA Knowledge Base inizializzata.")
    print(f"Record interazioni alimentari presenti: {count}")
    print(f"Database: {DB_PATH}")

if __name__ == "__main__":
    main()
