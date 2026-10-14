"""
يبني جوابًا موثقًا من المقاطع المسترجعة فقط，ويرجع الجواب مع قائمة المصادر المستخدمة.
"""

from src.finops_rag.retriever import (
    retrieve_chunks,
)

# يحول السؤال والمقاطع المسترجعة إلى تعليمات واضحة لنموذج Gemini.
def build_rag_prompt(
    question: str,
    matches: list[dict],
) -> str:
    context_parts = []

    for match in matches:
        context_parts.append(
            (
                f"Chunk ID: {match['chunk_id']}\n"
                f"Source: {match['source_name']}\n"
                f"Page: {match['page_number']}\n"
                f"Text: {match['text']}"
            )
        )

    context = "\n\n---\n\n".join(
        context_parts
    )

    return (
    "Answer the user's question in English "
    "using only the provided context.\n"
    "Do not use outside knowledge.\n"
    "Do not invent facts, numbers, or sources.\n"
    "If the context is insufficient, return "
    "exactly: INSUFFICIENT_EVIDENCE\n\n"
    f"User question:\n{question}\n\n"
    f"Context:\n{context}"
)

# يسترجع الأدلة الأقرب ثم يولد جوابًا موثقًا ويعيد مصادره.
def answer_rag_question(
    client,
    question: str,
    index_records: list[dict],
    embedding_model_name: str,
    answer_model_name: str,
    top_k: int = 3,
) -> dict:
    matches = retrieve_chunks(
        client=client,
        question=question,
        index_records=index_records,
        model_name=embedding_model_name,
        top_k=top_k,
    )

    if not matches:
        return {
            "status": "not_found",
            "answer": (
                "No relevant document "
                "evidence was found."
            ),
            "sources": [],
        }

    prompt = build_rag_prompt(
        question=question,
        matches=matches,
    )
    # response هو كائن الاستجابة الكامل الذي أعادته مكتبة Gemini، وقد يحتوي على النص وبيانات إضافية.
    response = client.models.generate_content(
        model=answer_model_name,
        contents=prompt,
    )
    # يستخرج نص الجواب فقط من كائن استجابة Gemini الكامل.
    answer = (
        response.text
        or ""
    ).strip()
    if not answer:
        raise RuntimeError(
            "Gemini returned an empty RAG answer."
        )

    normalized_answer = (answer.upper().rstrip("."))

    if normalized_answer == "INSUFFICIENT_EVIDENCE":
        return {
            "status": "not_found",
            "answer": (
                "The available documents do not "
                "contain enough information."
            ),
            "sources": [],
        }

    sources = [
        {
            "chunk_id": match["chunk_id"],
            "source_name": match[
                "source_name"
            ],
            "page_number": match[
                "page_number"
            ],
            "source_url": match[
                "source_url"
            ],
            "score": match["score"],
        }
        for match in matches
    ]

    return {
    "status": "answered",
    "answer": answer,
    "sources": sources,
}

