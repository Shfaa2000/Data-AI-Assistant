"""
واجهة CLI بسيطة لرحلة FinOps Assistant.

تقرأ سؤال المستخدم من Terminal، وترسله إلى Assistant Service،
ثم تعرض النتيجة المنظمة دون أن تكرر منطق Gemini أو BigQuery.
"""

from src.finops_query.assistant_service import (
    FinOpsAssistantResult,
    answer_finops_question,
)


# يعرض مراحل النتيجة المشتركة بطريقة مناسبة للـTerminal.
def print_assistant_result(result: FinOpsAssistantResult) -> None:
    print("Assistant Core: PASS")
    print(f"Status: {result.status}")
    print(f"BigQuery location: {result.location}")
    print("BigQuery schema catalog: PASS")
    print(f"Allowed table: {result.allowed_table}")
    print(f"Gemini model: {result.model_name}")
    print(f"User question: {result.user_question}")

    print("Real Gemini query generation: PASS")
    print(result.query_generation.model_dump_json(indent=2))

    if result.query_generation.sql_proposal is None:
        print("BigQuery execution was skipped.")
        print(f"Message: {result.message}")
        return

    print("Local SQL validation: PASS")

    if result.dry_run_report is not None:
        print("BigQuery Dry Run: PASS")
        print(
            "Estimated bytes: "
            f"{result.dry_run_report.total_bytes_processed}"
        )

    if result.status == "dry_run_only":
        print("Execution stopped safely after Dry Run.")
        print("Set FINOPS_EXECUTE_QUERIES=true to execute the query.")
        return

    print("BigQuery execution: PASS")
    print("Query result validation: PASS")

    if result.dynamic_evidence is not None:
        print("Dynamic Evidence: PASS")
        print(result.dynamic_evidence.model_dump_json(indent=2))

    if result.final_answer is not None:
        print("Final answer generation: PASS")
        print("Final answer validation: PASS")
        print()
        print("Final Answer:")
        print(result.final_answer.answer)
        print()
        print("Final Answer Contract:")
        print(result.final_answer.model_dump_json(indent=2))


# يقرأ السؤال ويستدعي القلب المشترك ثم يعرض النتيجة.
def main() -> int:
    user_question = input(
        "Enter an English financial question: "
    ).strip()

    if not user_question:
        print("FinOps assistant: FAIL")
        print("Error type: ValueError")
        print("Error message: The user question is required.")
        return 1

    try:
        result = answer_finops_question(user_question)
    except Exception as exc:
        print("FinOps assistant: FAIL")
        print(f"Error type: {type(exc).__name__}")
        print(f"Error message: {exc}")
        return 1

    print_assistant_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

