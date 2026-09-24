# يعرّف قواعد مشتركة تمنع الحقول المجهولة وتنظف النصوص داخل نماذج Schema Catalog.
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class QueryCatalogError(ValueError):
    """يُرفع عندما لا يحتوي الكتالوج على جدول أو عمود مطلوب."""


class StrictCatalogModel(BaseModel):
    """قاعدة مشتركة لكل نماذج Physical Schema."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

# يمثل عمود BigQuery فعليًا ويحفظ اسمه ونوعه وقابليته لـNULL وترتيبه.
class PhysicalColumn(StrictCatalogModel):
    """يمثل عمودًا فعليًا واحدًا كما وصفته BigQuery."""

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    is_nullable: bool
    ordinal_position: int | None = Field(
        default=None,
        ge=1,
    )

    @field_validator("data_type")
    @classmethod
    def normalize_data_type(
        cls,
        value: str,
    ) -> str:
        """توحيد أسماء أنواع BigQuery لتسهيل المقارنة."""

        aliases = {
            "FLOAT": "FLOAT64",
            "INTEGER": "INT64",
            "BOOLEAN": "BOOL",
        }

        normalized = value.upper()
        return aliases.get(
            normalized,
            normalized,
        )

# يجمع هوية جدول BigQuery وأعمدته ويتأكد من عدم تكرار أسماء الأعمدة.
class PhysicalTable(StrictCatalogModel):
    """يمثل جدول BigQuery مسموحًا مع أعمدته الفعلية."""

    project_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    columns: list[PhysicalColumn] = Field(
        min_length=1,
    )

    @property
    def full_table_id(self) -> str:
        """إرجاع الاسم الكامل للجدول."""

        return (
            f"{self.project_id}."
            f"{self.dataset_id}."
            f"{self.table_id}"
        )

    @model_validator(mode="after")
    def reject_duplicate_columns(
        self,
    ) -> "PhysicalTable":
        """رفض تكرار اسم العمود داخل الجدول."""

        normalized_names = [
            column.name.casefold()
            for column in self.columns
        ]

        if len(normalized_names) != len(
            set(normalized_names)
        ):
            raise ValueError(
                "Physical table contains duplicate columns."
            )

        return self

    def get_column(
        self,
        column_name: str,
    ) -> PhysicalColumn:
        """إيجاد عمود فعلي مع الحفاظ على اسمه الأصلي."""

        wanted = column_name.casefold()

        for column in self.columns:
            if column.name.casefold() == wanted:
                return column

        raise QueryCatalogError(
            "Physical column is not allowed: "
            f"{column_name}"
        )

# يجمع الجداول المسموحة ويوفر بحثًا حتميًا عن أي جدول مطلوب.
class QuerySchemaCatalog(StrictCatalogModel):
    """يمثل مجموعة جداول BigQuery المسموحة فقط."""

    tables: list[PhysicalTable] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def reject_duplicate_tables(
        self,
    ) -> "QuerySchemaCatalog":
        """رفض تكرار الجدول داخل الكتالوج."""

        normalized_ids = [
            table.full_table_id.casefold()
            for table in self.tables
        ]

        if len(normalized_ids) != len(
            set(normalized_ids)
        ):
            raise ValueError(
                "Schema catalog contains duplicate tables."
            )

        return self

    def get_table(
        self,
        full_table_id: str,
    ) -> PhysicalTable:
        """إيجاد جدول مسموح باسمه الكامل."""

        wanted = full_table_id.casefold()

        for table in self.tables:
            if table.full_table_id.casefold() == wanted:
                return table

        raise QueryCatalogError(
            "Physical table is not allowed: "
            f"{full_table_id}"
        )