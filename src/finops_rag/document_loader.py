"""
يقرأ مستندات PDF ويستخرج النص، ثم يقسمه إلى
مقاطع صغيرة مع الاحتفاظ بمعلومات المصدر والصفحة.
"""

from pathlib import Path
from pypdf import PdfReader

def normalize_text(text: str) -> str:
    return " ".join(
        text.split()
    )

def load_pdf(
    file_path: Path,
    source_url: str = "",
) -> list[dict]: # يعيد Dictionary تمثل صفحة واحدة
    pages = []

    reader = PdfReader(
        str(file_path)
    )

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""
        text = normalize_text(text)

        if not text:
            continue

        pages.append(
            {
                "text": text,
                "source_name": file_path.name,
                "source_type": "pdf",
                "page_number": page_number,
                "source_url": source_url,
            }
        )

    return pages

def load_documents(
    directory: Path,
    source_urls: dict[str, str] | None = None,
) -> list[dict]:
    documents = [] # - يجمع صفحات جميع الملفات داخل قائمة واحدة.
    source_urls = source_urls or {}

    pdf_files = sorted(
        directory.glob("*.pdf")
    )

    for file_path in pdf_files:

        source_url = source_urls.get(
            file_path.name,
            "",
        )
        # فتضيف العناصر واحدًا واحدًا
        documents.extend(
            load_pdf(
                file_path=file_path,
                source_url=source_url,
            )
        )

    return documents

def split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )

    if (chunk_overlap < 0 or chunk_overlap >= chunk_size):
        raise ValueError(
            "chunk_overlap must be between "
            "zero and chunk_size."
        )

    chunks = []
    start = 0

    while start < len(text):
        end = min(
            # نهاية الـChunk المطلوبة.
            start + chunk_size,
            len(text),
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - chunk_overlap

    return chunks

def build_chunks(
    documents: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict]:
    chunks = []

    for document in documents:
        text_chunks = split_text(
            text=document["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk_number, chunk_text in enumerate(
            text_chunks,
            start=1,
        ):
            page_number = document[
                "page_number"
            ]

            if page_number is None:
                location = "text"
            else:
                location = f"page-{page_number}"

            source_stem = Path(
                document["source_name"]
            ).stem

            chunk_id = (
                f"{source_stem}-"
                f"{location}-"
                f"chunk-{chunk_number}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "source_name": document[
                        "source_name"
                    ],
                    "source_type": document[
                        "source_type"
                    ],
                    "page_number": page_number,
                    "source_url": document[
                        "source_url"
                    ],
                }
            )

    return chunks

