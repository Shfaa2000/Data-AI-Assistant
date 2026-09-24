"""يبني نسخة مصغرة وآمنة من Schema Catalog تحتوي فقط على الحقول والقواعد اللازمة لتوليد Query Plan وSQL."""
from src.finops_query.query_catalog import (
    QuerySchemaCatalog,
)
from src.finops_query.query_mapping import (
    QUERY_FIELD_MAPPINGS,
    QueryFieldMapping,
)

# يعرض لـGemini الحقول المسموحة فقط من دون Credentials أو بيانات الصفوف.
def build_query_schema_context(
    catalog: QuerySchemaCatalog,
    full_table_id: str,
    mappings: dict[
        str,
        QueryFieldMapping,
    ] = QUERY_FIELD_MAPPINGS,
) -> dict:
    """بناء Schema Context آمنة ومصغرة."""

    table = catalog.get_table(
        full_table_id
    )

    fields = []

    for semantic_name, mapping in mappings.items():
        physical_column = table.get_column(
            mapping.physical_column
        )

        fields.append(
            {
                "semantic_name": semantic_name,
                "kind": mapping.kind.value,
                "physical_column": (
                    physical_column.name
                ),
                "data_type": (
                    physical_column.data_type
                ),
                "allowed_aggregations": [
                    aggregation.value
                    for aggregation
                    in mapping.allowed_aggregations
                ],
                "value_scope": (
                    mapping.value_scope.value
                ),
            }
        )

    return {
        "allowed_table": (
            table.full_table_id
        ),
        "fields": fields,
    }

