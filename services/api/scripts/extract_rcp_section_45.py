import re
import sys
import tempfile
import urllib.request
from pathlib import Path

from pypdf import PdfReader


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def download_pdf(url: str) -> Path:
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
        text = page.extract_text() or ""
        pages.append(f"\n\n--- PAGE {index} ---\n\n{text}")

    return clean_text("\n".join(pages))


def extract_section_45(text: str) -> str:
    compact = clean_text(text)

    patterns = [
        r"4\s*[\.\)]\s*5\s+Interazioni.*?(?=4\s*[\.\)]\s*6\s+|5\s*[\.\)]\s*1\s+|$)",
        r"4\.5\s+Interazioni.*?(?=4\.6\s+|5\.1\s+|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, compact, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(0))

    return ""


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python3 scripts/extract_rcp_section_45.py <URL_RCP_PDF>")

    url = sys.argv[1].strip()

    print("Scarico PDF RCP...")
    pdf_path = download_pdf(url)

    print(f"PDF scaricato: {pdf_path}")
    print("Estraggo testo...")

    text = extract_pdf_text(pdf_path)
    section = extract_section_45(text)

    print(f"Caratteri testo totale: {len(text)}")
    print(f"Caratteri sezione 4.5: {len(section)}")

    if not section:
        print("Sezione 4.5 non trovata.")
        return

    print("\n=== SEZIONE 4.5 ESTRATTA, ANTEPRIMA ===\n")
    print(section[:3000])


if __name__ == "__main__":
    main()
