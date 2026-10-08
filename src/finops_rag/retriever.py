"""
ينشئ Embeddings للمقاطع، ويحفظ الفهرس محليًا，
ثم يسترجع المقاطع الأقرب دلاليًا إلى سؤال المستخدم.
"""

import json
from pathlib import Path

import numpy as np
from google.genai import types

# يحول قائمة النصوص إلى متجهات رقمية باستخدام نموذج Embedding.
def create_embeddings(
    client,
    texts: list[str],
    model_name: str,
    task_type: str,
) -> list[list[float]]:
    if not texts:
        return []
    result = client.models.embed_content(
        model=model_name,
        contents=texts,
        config=types.EmbedContentConfig(
            # الـtask_type يخبر نموذج الـEmbedding عن الغرض من النص الذي يحوله.
            task_type=task_type,
            output_dimensionality=768,
        ),
    )

    return [
        embedding.values
        for embedding in result.embeddings
    ]

# يحسب التقارب الدلالي بين متجهين من خلال اتجاههما.
def cosine_similarity(
    first_vector: list[float],
    second_vector: list[float],
) -> float:
    # حتى نستطيع تنفيذ العمليات الرياضية
    first = np.asarray(
        first_vector,
        dtype=float,
    )

    second = np.asarray(
        second_vector,
        dtype=float,
    )
    # حساب طول كل Vector
    denominator = (
        np.linalg.norm(first)
        * np.linalg.norm(second)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(first, second)
        / denominator
    )

# يحفظ كل Chunk مع معلومات مصدره والـEmbedding داخل ملف JSON.
def save_index(
    chunks: list[dict],
    embeddings: list[list[float]],
    index_path: Path,
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Chunks and embeddings count "
            "must match."
        )

    records = []

    for chunk, embedding in zip(
        chunks,
        embeddings,
    ):
        records.append(
            {
                **chunk,
                "embedding": embedding,
            }
        )

    index_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_path.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

def load_index(
    index_path: Path,
) -> list[dict]:
    return json.loads(
        index_path.read_text(
            encoding="utf-8"
        )
    )

# ينشئ Embeddings لجميع المقاطع ثم يحفظ الفهرس ويعيد تحميله.
def build_index(
    client,
    chunks: list[dict],
    index_path: Path,
    model_name: str,
) -> list[dict]:
    if not chunks:
        raise ValueError(
            "Cannot build an index without chunks."
        )

    chunk_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = create_embeddings(
        client=client,
        texts=chunk_texts,
        model_name=model_name,
        task_type="RETRIEVAL_DOCUMENT",
    )

    save_index(
        chunks=chunks,
        embeddings=embeddings,
        index_path=index_path,
    )

    return load_index(
        index_path=index_path
    )

# يحول سؤال المستخدم إلى Embedding ويعيد المقاطع الأعلى تشابهًا.
def retrieve_chunks(
    client,
    question: str,
    index_records: list[dict],
    model_name: str,
    top_k: int = 3,
) -> list[dict]:

    if not question.strip():
        raise ValueError(
            "The question is required."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero."
        )

    if not index_records:
        return []
    question_embedding = create_embeddings(
        client=client,
        texts=[question],
        model_name=model_name,
        task_type="QUESTION_ANSWERING",
    )[0]

    matches = []

    for record in index_records:
        score = cosine_similarity(
            question_embedding,
            record["embedding"],
        )

        match = {
            key: value
            for key, value in record.items()
            if key != "embedding"
        }

        match["score"] = score
        matches.append(match)

    matches.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches[:top_k]

