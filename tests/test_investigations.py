import pandas as pd

from src.investigations import (
    flag_billed_cost_outliers_by_service,
)


def test_outliers_are_calculated_inside_each_service():
    data = pd.DataFrame({
        "ProviderName": (
            ["AWS"] * 5
            + ["AWS"] * 5
            + ["Microsoft"] * 3
        ),
        "ServiceName": (
            ["Service A"] * 5
            + ["Service B"] * 5
            + ["Small Service"] * 3
        ),
        "BilledCost": [
            10, 10, 10, 11, 100,
            1000, 1000, 1000, 1001, 1010,
            1, 1, 100,
        ],
    })
    # result عبارة عن Boolean Series، أي قيم من نوع True/False.
    result = (
        flag_billed_cost_outliers_by_service(
            data,
            min_group_size=4,
        )
    )

    assert result.iloc[4]
    assert result.iloc[9]

    assert not result.iloc[12]
    # يتأكد أن العدد النهائي للـOutliers هو اثنان فقط.
    assert result.sum() == 2