"""
واجهة CLI لمسار FinOps RAG:
تقرأ سؤال المستخدم، وتستدعي خدمة RAG，
ثم تعرض الجواب والمصادر.
"""

from src.finops_rag.assistant_service import (
    answer_finops_rag_question,
)


# يعرض عقد الجواب والمصادر بشكل مناسب للـCLI.
def print_rag_result(
    result: dict,
) -> None:
    print()
    print(
        f"Status: {result['status']}"
    )

    print()
    print("Answer:")
    print(result["answer"])

    sources = result["sources"]

    if not sources:
        return

    print()
    print("Retrieved Sources:")

    for source_number, source in enumerate(
        sources,
        start=1,
    ):
        print()
        print(f"Source {source_number}:")
        print(
            f"  File: "
            f"{source['source_name']}"
        )
        print(
            f"  Page: "
            f"{source['page_number']}"
        )
        print(
            f"  Chunk: "
            f"{source['chunk_id']}"
        )
        print(
            f"  URL: "
            f"{source['source_url']}"
        )
        print(
            f"  Similarity: "
            f"{source['score']:.4f}"
        )


# يقرأ سؤال المستخدم، ويستدعي خدمة RAG، ثم يعرض النتيجة.
def main() -> int:

    try:
        question = input(
            "Enter a FinOps documentation "
            "question: "
        ).strip()

        if not question:
            raise ValueError(
                "The question is required."
            )


        result = answer_finops_rag_question(question)

        print("RAG retrieval: PASS")

        if result["status"] == "answered":
            print(
                "RAG answer generation: PASS"
            )
        else:
            print(
                "RAG answer generation: "
                "NO EVIDENCE"
            )

        print_rag_result(result)

        return 0

    except Exception as exc:
        print("FinOps RAG: FAIL")
        print(
            f"Error type: "
            f"{type(exc).__name__}"
        )
        print(
            f"Error message: {exc}"
        )

        return 1

if __name__ == "__main__":
    raise SystemExit(main())