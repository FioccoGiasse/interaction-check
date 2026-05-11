import csv
import sqlite3
import urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import unicodedata
import re

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "enia.db"
CSV_PATH = DATA_DIR / "aifa_confezioni_fornitura.csv"

AIFA_CSV_URL = "https://drive.aifa.gov.it/farmaci/confezioni_fornitura.csv"

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

def download_csv():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Scarico file AIFA...")
    urllib.request.urlretrieve(AIFA_CSV_URL, CSV_PATH)
    print(f"File scaricato: {CSV_PATH}")
    print(f"Dimensione file: {CSV_PATH.stat().st_size} bytes")

def create_schema(conn):
    conn.execute("DROP TABLE IF EXISTS drugs")
    conn.execute("DROP TABLE IF EXISTS database_versions")

    conn.execute("""
        CREATE TABLE drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aic_code TEXT,
            medicine_code TEXT,
            package_code TEXT,
            commercial_name TEXT,
            normalized_commercial_name TEXT,
            package_description TEXT,
            company_code TEXT,
            marketing_authorisation_holder TEXT,
            administrative_status TEXT,
            procedure_type TEXT,
            pharmaceutical_form TEXT,
            atc_code TEXT,
            active_ingredient TEXT,
            normalized_active_ingredient TEXT,
            supply_regime TEXT,
            leaflet_url TEXT,
            rcp_url TEXT,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE database_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            rows_imported INTEGER NOT NULL,
            version_label TEXT NOT NULL
        )
    """)

    conn.execute("CREATE INDEX idx_drugs_aic ON drugs(aic_code)")
    conn.execute("CREATE INDEX idx_drugs_commercial ON drugs(normalized_commercial_name)")
    conn.execute("CREATE INDEX idx_drugs_active ON drugs(normalized_active_ingredient)")
    conn.execute("CREATE INDEX idx_drugs_atc ON drugs(atc_code)")

def import_csv(conn):
    imported_at = now_rome()
    rows_imported = 0

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        print("Colonne trovate:")
        print(reader.fieldnames)

        for row in reader:
            commercial_name = row.get("DENOMINAZIONE", "")
            active_ingredient = row.get("PA_ASSOCIATI", "")

            conn.execute("""
                INSERT INTO drugs (
                    aic_code,
                    medicine_code,
                    package_code,
                    commercial_name,
                    normalized_commercial_name,
                    package_description,
                    company_code,
                    marketing_authorisation_holder,
                    administrative_status,
                    procedure_type,
                    pharmaceutical_form,
                    atc_code,
                    active_ingredient,
                    normalized_active_ingredient,
                    supply_regime,
                    leaflet_url,
                    rcp_url,
                    source,
                    source_url,
                    source_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("CODICE_AIC", ""),
                row.get("COD_FARMACO", ""),
                row.get("COD_CONFEZIONE", ""),
                commercial_name,
                normalize_text(commercial_name),
                row.get("DESCRIZIONE", ""),
                row.get("CODICE_DITTA", ""),
                row.get("RAGIONE_SOCIALE", ""),
                row.get("STATO_AMMINISTRATIVO", ""),
                row.get("TIPO_PROCEDURA", ""),
                row.get("FORMA", ""),
                row.get("CODICE_ATC", ""),
                active_ingredient,
                normalize_text(active_ingredient),
                row.get("FORNITURA", ""),
                row.get("LINK_FI", ""),
                row.get("LINK_RCP", ""),
                "AIFA Anagrafica Farmaci",
                AIFA_CSV_URL,
                imported_at
            ))

            rows_imported += 1

    conn.execute("""
        INSERT INTO database_versions (
            source_name,
            source_url,
            imported_at,
            rows_imported,
            version_label
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        "AIFA Anagrafica Farmaci",
        AIFA_CSV_URL,
        imported_at,
        rows_imported,
        "aifa_registry_import"
    ))

    return rows_imported

def main():
    download_csv()

    conn = sqlite3.connect(DB_PATH)

    try:
        create_schema(conn)
        rows_imported = import_csv(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"Import completato. Righe importate: {rows_imported}")
    print(f"Database creato: {DB_PATH}")

if __name__ == "__main__":
    main()
