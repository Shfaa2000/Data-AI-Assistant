# يعرّف العقد المنظم لاستجابة Gemini المالية.
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

#أي قيمة من نوع MetricName يجب أن تكون واحدة من هذه الأسماء الثلاثة فقط.
MetricName = Literal[
    "billed_cost",
    "effective_cost",
    "negative_billed_cost",
]


class NarrativeResponse(BaseModel):
    """الشكل المنظم للجزء اللغوي الذي يولده نموذج Gemini."""

    # هذا إعداد عام يطبّق على كل حقول NarrativeResponse.
    model_config = ConfigDict(
        # يعني: إذا أعاد النموذج حقلًا لم نعرّفه، يرفض Pydantic الاستجابة.
        extra="forbid",
        str_strip_whitespace=True,
    )

    status: Literal[
        "answered",
        "unsupported",
    ] = Field(
        description=(
            "answered إذا كانت البيانات كافية، "
            "وunsupported إذا لم تكن كافية."
        )
    )

    answer: str = Field(
        min_length=1,
        description=(
            "الجواب الموجه للمستخدم، باستخدام "
            "البيانات المرسلة فقط."
        ),
    )

    used_metrics: list[MetricName] = Field(
        default_factory=list,
        description=(
            "أسماء المقاييس التي استُخدمت لبناء الجواب، "
            "وليس قيمًا مالية جديدة."
        ),
    )

    limitations: list[str] = Field(
        min_length=1,
        description=(
            "حدود البيانات والاستنتاجات التي يجب توضيحها "
            "للمستخدم."
        ),
    )

    unsupported_reason: Optional[str] = Field(
        default=None,
        description=(
            "سبب عدم القدرة على تقديم جواب مدعوم. "
            "يكون فارغًا عندما تكون الحالة answered."
        ),
    )
    # شغّل هذا التحقق بعد قراءة كل الحقول وإنشاء الكائن.
    @model_validator(mode="after")
    def validate_status_consistency(
        self,
    ) -> "NarrativeResponse":
        """التحقق من التوافق بين الحالة وبقية الحقول."""

        if (
            self.status == "answered"
            and not self.used_metrics
        ):
            raise ValueError(
                "answered requires at least one used metric."
            )

        if (
            self.status == "answered"
            and self.unsupported_reason
        ):
            raise ValueError(
                "answered must not include unsupported_reason."
            )

        if (
            self.status == "unsupported"
            and not self.unsupported_reason
        ):
            raise ValueError(
                "unsupported requires unsupported_reason."
            )
        if (
            self.status == "unsupported"
            and self.used_metrics):
            raise ValueError(
                "unsupported must not include "
                "used_metrics."
            )
        # لأن Pydantic يحتاج استعادة الكائن بعد نجاح جميع التحققات.
        return self
