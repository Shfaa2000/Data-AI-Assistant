"""
يشغل رحلة FinOps RAG الكاملة:
يجهز Gemini، ويحمل الفهرس أو يبنيه，
ثم يعيد جوابًا موثقًا مع المصادر.
"""

import os

from dotenv import load_dotenv
from google import genai

from src.config import (
    RAG_DOCUMENTS_DIR,
    RAG_INDEX_PATH,
)

from src.finops_rag.document_loader import (
    build_chunks,
    load_documents,
)

from src.finops_rag.rag_service import (
    answer_rag_question,
)

from src.finops_rag.retriever import (
    build_index,
    load_index,
)

DEFAULT_ANSWER_MODEL = (
    "gemini-3.5-flash-lite"
)

DEFAULT_EMBEDDING_MODEL = (
    "gemini-embedding-001"
)

DEFAULT_TOP_K = 3

SOURCE_URLS = {
    "What-is-FOCUS-December-2025.pdf": (
        "https://focus.finops.org/"
        "wp-content/uploads/2025/12/"
        "What-is-FOCUS-December-2025.pdf"
    ),
    "FinOps-with-Azure.pdf": (
        "https://azure.microsoft.com/mediahandler/"
        "files/resourcefiles/"
        "finops-with-azure-bringing-finops-to-life-"
        "through-organizational-and-cultural-alignment/"
        "bringing-finops-to-life-through-organizational-"
        "and-cultural-alignment.pdf"
    ),
    "Cloud-FinOps-Shared-Services-Cost-Allocation.pdf": (
        "https://services.google.com/fh/files/misc/"
        "cloud_finops_shared_services_cost_allocation_"
        "whitepaper.pdf"
    ),
}

# يقرأ متغيرًا إلزاميًا ويرفض التشغيل إذا كان مفقودًا.
def require_environment_variable(
    variable_name: str,
) -> str:
    value = os.getenv(
        variable_name,
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            f"{variable_name} is missing."
        )

    return value

# يحول قيمة البيئة النصية إلى True أو False.
def read_boolean_environment_variable(
    variable_name: str,
    default: bool = False,
) -> bool:
    default_text = (
        "true"
        if default
        else "false"
    )

    value = os.getenv(
        variable_name,
        default_text,
    ).strip().lower()

    if value not in {
        "true",
        "false",
    }:
        raise ValueError(
            f"{variable_name} must be "
            "true or false."
        )

    return value == "true"

# يبني الفهرس عند الحاجة أو يحمل النسخة المحلية.
# يستخدم client لإنشاء Embeddings عند إعادة بناء الفهرس.
def prepare_rag_index(
    client,
    embedding_model_name: str,
    rebuild_index: bool,
) -> list[dict]:
    if (
        RAG_INDEX_PATH.exists()
        and not rebuild_index
    ):
        index_records = load_index(
            index_path=RAG_INDEX_PATH
        )

        if not index_records:
            raise RuntimeError(
                "The saved RAG index is empty."
            )

        print("RAG index loading: PASS")
        print(
            f"Indexed chunks: "
            f"{len(index_records)}"
        )

        return index_records

    documents = load_documents(
        directory=RAG_DOCUMENTS_DIR,
        source_urls=SOURCE_URLS,
    )

    if not documents:
        raise RuntimeError(
            "No readable PDF pages were found."
        )

    print("RAG document loading: PASS")
    print(
        f"Loaded PDF pages: "
        f"{len(documents)}"
    )

    chunks = build_chunks(
        documents=documents,
        chunk_size=1000,
        chunk_overlap=150,
    )

    if not chunks:
        raise RuntimeError(
            "No RAG chunks were created."
        )

    print("RAG document chunking: PASS")
    print(
        f"Created chunks: "
        f"{len(chunks)}"
    )

    index_records = build_index(
        # نحتاج client عند بناء الفهرس لإرسال نصوص الـChunks إلى Google وإنشاء Embeddings.
        client=client,
        chunks=chunks,
        index_path=RAG_INDEX_PATH,
        model_name=embedding_model_name,
    )

    print("RAG index build: PASS")
    print(
        f"Indexed chunks: "
        f"{len(index_records)}"
    )

    print(
        f"Index path: "
        f"{RAG_INDEX_PATH}"
    )
    # يجهز قاعدة البحث: يحمل الفهرس المحفوظ أو يبنيه من ملفات PDF.
    return index_records

# يشغل رحلة RAG كاملة ويعيد النتيجة
# من دون قراءة input أو طباعة الجواب النهائي.
def answer_finops_rag_question(
    question: str,
) -> dict:
    normalized_question = (
        question.strip()
    )

    if not normalized_question:
        raise ValueError(
            "The question is required."
        )

    load_dotenv()

    gemini_api_key = (
        require_environment_variable(
            "GEMINI_API_KEY"
        )
    )

    answer_model_name = os.getenv(
        "GEMINI_MODEL",
        DEFAULT_ANSWER_MODEL,
    ).strip()

    embedding_model_name = os.getenv(
        "RAG_EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    ).strip()

    top_k = int(
        os.getenv(
            "RAG_TOP_K",
            str(DEFAULT_TOP_K),
        )
    )

    rebuild_index = (
        read_boolean_environment_variable(
            "RAG_REBUILD_INDEX",
            default=False,
        )
    )

    client = genai.Client(
        api_key=gemini_api_key
    )

    index_records = prepare_rag_index(
        client=client,
        embedding_model_name=(
            embedding_model_name
        ),
        rebuild_index=rebuild_index,
    )
    # يستخدم الفهرس الجاهز لاسترجاع الأدلة ثم توليد الجواب والمصادر.
    return answer_rag_question(
        client=client,
        question=normalized_question,
        index_records=index_records,
        embedding_model_name=(
            embedding_model_name
        ),
        answer_model_name=(
            answer_model_name
        ),
        top_k=top_k,
    )
