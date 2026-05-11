import re
import sys

from extract_rcp_section_45 import download_pdf, extract_pdf_text, clean_text


def extract_section_47(text: str) -> str:
    compact = clean_text(text)

    patterns = [
        r"4\s*[\.\)]\s*7\s+Effetti.*?(?=4\s*[\.\)]\s*8\s+|5\s*[\.\)]\s*1\s+|$)",
        r"4\.7\s+Effetti.*?(?=4\.8\s+|5\.1\s+|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, compact, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(0))

    return ""


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python3 scripts/extract_rcp_section_47.py <URL_RCP_PDF>")

    url = sys.argv[1].strip()

    print("Scarico PDF RCP...")
    pdf_path = download_pdf(url)

    print(f"PDF scaricato: {pdf_path}")
    print("Estraggo testo...")

    text = extract_pdf_text(pdf_path)
    section = extract_section_47(text)

    print(f"Caratteri testo totale: {len(text)}")
    print(f"Caratteri sezione 4.7: {len(section)}")

    if not section:
        print("Sezione 4.7 non trovata.")
        return

    print("\n=== SEZIONE 4.7 ESTRATTA, TESTO LETTERALE ===\n")
    print(section)


if __name__ == "__main__":
    main()
