import re
import fitz  # PyMuPDF


def pdf_to_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def clean_text(raw_text):
    # Remove page numbers and headers/footers
    cleaned = re.sub(r"\n\d+\n", "\n", raw_text)
    cleaned = re.sub(r"Chapter \d+", "", cleaned)
    # Remove 'www.fx1618.com' and its hyperlink patterns
    cleaned = re.sub(r"\[?www\.fx1618\.com\]?\(https?://www\.fx1618\.com\)|www\.fx1618\.com", "", cleaned)
    # Remove extra whitespace and blank lines
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    cleaned = cleaned.replace('\xa0', ' ')  # Replace non-breaking spaces
    return cleaned

text = pdf_to_text("book.pdf")
cleaned_text = clean_text(text)
with open("cleaned_book.txt", "w", encoding="utf-8") as f:
    f.write(cleaned_text)
