import csv
import sqlite3
import unicodedata
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[2].parents[0]
API_DIR = Path(__file__).resolve().parents[1]
DB_PATH = API_DIR / "data" / "enia.db"
CSV_PATH = BASE_DIR / "docs" / "enia_food_interactions_template.csv"

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

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database non trovato: {DB_PATH}")

    if not CSV_PATH.exists():
        raise SystemExit(f"CSV non trovato: {CSV_PATH}")

    imported = 0
    skipped = 0
    created_at = now_rome()

    conn = sqlite3.connect(DB_PATH)

    try:
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                active_ingredient = (row.get("active_ingredient") or "").strip()
                food_or_substance = (row.get("food_or_substance") or "").strip()
                interaction_summary = (row.get("interaction_summary") or "").strip()
                source_name = (row.get("source_name") or "").strip()
                validation_status = (row.get("validation_status") or "").strip()

                required_missing = (
                    not active_ingredient
                    or not food_or_substance
                    or not interaction_summary
                    or not source_name
                    or not validation_status
                )

                if required_missing:
                    skipped += 1
                    continue

                conn.execute("""
                    INSERT INTO enia_food_interactions (
                        active_ingredient,
                        normalized_active_ingredient,
                        food_or_substance,
                        normalized_food_or_substance,
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
                        validated_at,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    active_ingredient,
                    normalize_text(active_ingredient),
                    food_or_substance,
                    normalize_text(food_or_substance),
                    interaction_summary,
                    row.get("severity", ""),
                    row.get("evidence_level", ""),
                    row.get("mechanism", ""),
                    row.get("recommendation", ""),
                    row.get("patient_explanation", ""),
                    row.get("clinician_explanation", ""),
                    source_name,
                    row.get("source_url", ""),
                    row.get("source_section", ""),
                    validation_status,
                    row.get("validated_by", ""),
                    row.get("validated_at", ""),
                    created_at
                ))

                imported += 1

        conn.commit()

    finally:
        conn.close()

    print(f"Import completato. Record importati: {imported}")
    print(f"Record saltati: {skipped}")

if __name__ == "__main__":
    main()
