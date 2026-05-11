import json
import re
import sys
from pathlib import Path

from extract_rcp_section_45 import download_pdf, extract_pdf_text, extract_section_45, clean_text


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


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    parts = re.split(r"(?<=[\.\;\:])\s+(?=[A-ZÀ-Ü0-9])", text)
    return [part.strip() for part in parts if part.strip()]


def find_food_candidates(section_text: str, source_url: str) -> list[dict]:
    candidates = []
    sentences = split_sentences(section_text)

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


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python3 scripts/extract_rcp_food_candidates.py <URL_RCP_PDF>")

    url = sys.argv[1].strip()

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

    candidates = find_food_candidates(section, url)

    print(json.dumps({
        "source_url": url,
        "section_found": True,
        "candidate_count": len(candidates),
        "candidates": candidates
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
