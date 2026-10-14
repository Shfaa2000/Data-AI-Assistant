"""
واجهة CLI موحدة لمساري
FinOps Query وFinOps RAG.
"""

from src.finops_assistant.service import (
    answer_finops_assistant,
)

# يعرض العقد الموحد ومصادره
# بطريقة مناسبة للـTerminal.
def print_result(
    result: dict,
) -> None:
    print()
    print(
        f"Status: {result['status']}"
    )
    print(
        f"Route: {result['route']}"
    )

    print()
    print("Answer:")
    print(result["answer"])

    sources = result["sources"]

    if not sources:
        return

    print()
    print("Sources:")

    for number, source in enumerate(
        sources,
        start=1,
    ):
        print()
        print(f"Source {number}:")

        for key, value in source.items():
            if value is not None:
                print(
                    f"  {key}: {value}"
                )

# يقرأ سؤال المستخدم ويشغل
# الرحلة الموحدة كاملة.
def main() -> int:
    try:
        question = input(
            "Enter a FinOps question: "
        ).strip()

        result = answer_finops_assistant(
            question
        )

        print_result(result)

        return 0

    except Exception as exc:
        print()
        print("FinOps Assistant: FAIL")
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