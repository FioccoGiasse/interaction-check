import json
import re
import sqlite3
import sys
from pathlib import Path

from extract_rcp_section_45 import download_pdf, extract_pdf_text, extract_section_45, clean_text


API_DIR = Path(__file__).resolve().parents[1]
DB_PATH = API_DIR / "data" / "enia.db"


DRUG_CLASS_TERMS = [
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


STOP_TERMS = {
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


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    parts = re.split(r"(?<=[\.\;\:])\s+(?=[A-ZÀ-Ü0-9])", text)
    return [part.strip() for part in parts if part.strip()]


def normalise_match(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value


def split_active_ingredient(value: str) -> list[str]:
    value = value or ""
    parts = re.split(r"\+|,|;|/|\\be\\b", value, flags=re.IGNORECASE)
    cleaned = []

    for part in parts:
        part = normalise_match(part)
        part = re.sub(r"\([^)]*\)", "", part).strip()

        if len(part) < 4:
            continue

        if part in STOP_TERMS:
            continue

        cleaned.append(part)

    return cleaned


def load_aifa_drug_terms() -> list[str]:
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT DISTINCT active_ingredient
        FROM drugs
        WHERE active_ingredient IS NOT NULL
          AND active_ingredient != ''
    """).fetchall()

    conn.close()

    terms = set()

    for row in rows:
        active_ingredient = row["active_ingredient"]
        for term in split_active_ingredient(active_ingredient):
            terms.add(term)

    return sorted(terms, key=len, reverse=True)


def find_drug_candidates(section_text: str, source_url: str, source_active_ingredient: str = "") -> list[dict]:
    candidates = []
    sentences = split_sentences(section_text)

    source_terms = set(split_active_ingredient(source_active_ingredient))
    aifa_terms = load_aifa_drug_terms()
    all_terms = DRUG_CLASS_TERMS + aifa_terms

    for index, sentence in enumerate(sentences, start=1):
        sentence = clean_text(sentence)

        if len(sentence) < 40:
            continue

        sentence_lower = normalise_match(sentence)
        matched_terms = []

        for term in all_terms:
            term_normalised = normalise_match(term)

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


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python3 scripts/extract_rcp_drug_candidates.py <URL_RCP_PDF> [principio_attivo_da_escludere]")

    url = sys.argv[1].strip()
    source_active_ingredient = sys.argv[2].strip() if len(sys.argv) > 2 else ""

    print("Scarico PDF RCP...")
    pdf_path = download_pdf(url)

    print("Estraggo sezione 4.5...")
    text = extract_pdf_text(pdf_path)
    section = extract_section_45(text)

    if not section:
        print(json.dumps({
            "source_url": url,
            "section_found": False,
            "candidate_count": 0,
            "candidates": []
        }, indent=2, ensure_ascii=False))
        return

    candidates = find_drug_candidates(section, url, source_active_ingredient)

    print(json.dumps({
        "source_url": url,
        "section_found": True,
        "candidate_count": len(candidates),
        "candidates": candidates
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
