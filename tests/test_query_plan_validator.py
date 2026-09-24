import pytest

from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QuerySchemaCatalog,
)
from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    MetricSelection,
    QueryFilter,
    QueryStatus,
)
from src.finops_query.query_plan_validator import (
    QueryPlanValidationError,
    validate_query_plan_against_schema,
)
from src.finops_query.query_schema import (
    AggregationName,
    DimensionName,
    MetricName,
)


PROJECT_ID = "data-ai-assistant-training"
DATASET_ID = "cloud_finops"
TABLE_ID = "billing_pipeline_day2"

FULL_TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)


def make_catalog() -> QuerySchemaCatalog:
    return QuerySchemaCatalog(
        tables=[
            PhysicalTable(
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID,
                table_id=TABLE_ID,
                columns=[
                    PhysicalColumn(
                        name="BilledCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=1,
                    ),
                    PhysicalColumn(
                        name="EffectiveCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=2,
                    ),
                    PhysicalColumn(
                        name="ProviderName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=3,
                    ),
                    PhysicalColumn(
                        name="ServiceName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=4,
                    ),
                    PhysicalColumn(
                        name="BillingCurrency",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=5,
                    ),
                    PhysicalColumn(
                        name="BillingPeriodStart",
                        data_type="TIMESTAMP",
                        is_nullable=True,
                        ordinal_position=6,
                    ),
                ],
            )
        ]
    )


def make_ready_plan(
    aggregation: AggregationName = (
        AggregationName.SUM
    ),
) -> FinOpsQueryPlan:
    return FinOpsQueryPlan(
        status=QueryStatus.READY,
        intent="Total billed cost for AWS",
        metrics=[
            MetricSelection(
                name=MetricName.BILLED_COST,
                aggregation=aggregation,
            )
        ],
        dimensions=[
            DimensionName.PROVIDER
        ],
        filters=[
            QueryFilter(
                column=DimensionName.PROVIDER,
                operator="eq",
                value="AWS",
            )
        ],
    )


def test_ready_plan_matches_schema():
    validate_query_plan_against_schema(
        plan=make_ready_plan(),
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )


def test_non_ready_plan_does_not_reach_sql():
    plan = FinOpsQueryPlan(
        status=(
            QueryStatus.NEEDS_CLARIFICATION
        ),
        intent="Ambiguous provider question",
        clarification_question=(
            "Which provider do you mean?"
        ),
    )

    with pytest.raises(
        QueryPlanValidationError,
        match="Only ready",
    ):
        validate_query_plan_against_schema(
            plan=plan,
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
        )


def test_disallowed_aggregation_is_rejected():
    plan = FinOpsQueryPlan(
        status=QueryStatus.READY,
        intent="Count negative billed cost",
        metrics=[
            MetricSelection(
                name=(
                    MetricName.NEGATIVE_BILLED_COST
                ),
                aggregation=AggregationName.COUNT,
            )
        ],
    )

    with pytest.raises(
        QueryPlanValidationError,
        match="not allowed",
    ):
        validate_query_plan_against_schema(
            plan=plan,
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
        )