from __future__ import annotations

import math

import pytest
from fable5_backtester.preprocessing import (
    PreprocessingInputError,
    SampleValue,
    TrainOnlyFitRequest,
    fit_train_only_standardizer,
    transform_with_fit,
)


def test_fit_records_exact_train_ids_hash_and_fold_scoped_statistics() -> None:
    fold_one = fit_train_only_standardizer(
        TrainOnlyFitRequest(
            fold_id="outer-1",
            train_values=(SampleValue("b", 2.0), SampleValue("a", 0.0)),
            permitted_train_ids=("a", "b"),
            ddof=0,
        )
    )
    fold_two = fit_train_only_standardizer(
        TrainOnlyFitRequest(
            fold_id="outer-2",
            train_values=(
                SampleValue("a", 0.0),
                SampleValue("b", 2.0),
                SampleValue("c", 100.0),
            ),
            permitted_train_ids=("a", "b", "c"),
            ddof=0,
        )
    )

    assert fold_one.train_ids == ("a", "b")
    assert fold_one.mean == 1.0
    assert fold_one.standard_deviation == 1.0
    assert len(fold_one.train_ids_sha256) == 64
    assert fold_two.train_ids == ("a", "b", "c")
    assert fold_two.mean == 34.0
    assert fold_two.standard_deviation == pytest.approx(math.sqrt(6536.0 / 3.0))
    assert fold_one.train_ids_sha256 != fold_two.train_ids_sha256
    assert fold_one.fit_sha256 != fold_two.fit_sha256
    assert fold_one.fit_id != fold_two.fit_id


def test_test_only_values_cannot_influence_or_enter_fit() -> None:
    request = TrainOnlyFitRequest(
        fold_id="outer-1",
        train_values=(SampleValue("train-a", 0.0), SampleValue("train-b", 2.0)),
        permitted_train_ids=("train-a", "train-b"),
        ddof=0,
    )
    fit_before = fit_train_only_standardizer(request)
    transformed_first = transform_with_fit(fit_before, (SampleValue("test", 10.0),))
    transformed_outlier = transform_with_fit(fit_before, (SampleValue("test", 1e12),))
    fit_after = fit_train_only_standardizer(request)

    assert fit_before == fit_after
    assert transformed_first[0].value == 9.0
    assert transformed_outlier[0].value == pytest.approx(1e12 - 1.0)
    assert fit_before.mean == 1.0
    assert fit_before.standard_deviation == 1.0

    contaminated = TrainOnlyFitRequest(
        fold_id="outer-1",
        train_values=(*request.train_values, SampleValue("test", 1e12)),
        permitted_train_ids=request.permitted_train_ids,
        ddof=0,
    )
    with pytest.raises(PreprocessingInputError, match=r"unexpected=\('test',\)"):
        fit_train_only_standardizer(contaminated)


def test_fit_is_deterministic_across_train_input_order() -> None:
    first = fit_train_only_standardizer(
        TrainOnlyFitRequest(
            fold_id="outer-order",
            train_values=(SampleValue("a", -1.0), SampleValue("b", 1.0)),
            permitted_train_ids=("a", "b"),
            ddof=0,
        )
    )
    second = fit_train_only_standardizer(
        TrainOnlyFitRequest(
            fold_id="outer-order",
            train_values=(SampleValue("b", 1.0), SampleValue("a", -1.0)),
            permitted_train_ids=("b", "a"),
            ddof=0,
        )
    )
    assert first == second


@pytest.mark.parametrize(
    "fit_request,error",
    [
        (
            TrainOnlyFitRequest(
                fold_id="constant",
                train_values=(SampleValue("a", 1.0), SampleValue("b", 1.0)),
                permitted_train_ids=("a", "b"),
                ddof=0,
            ),
            "standard deviation",
        ),
        (
            TrainOnlyFitRequest(
                fold_id="missing",
                train_values=(SampleValue("a", 1.0), SampleValue("b", 2.0)),
                permitted_train_ids=("a", "b", "c"),
                ddof=0,
            ),
            r"missing=\('c',\)",
        ),
    ],
)
def test_fit_fails_closed_on_uncomputable_or_incomplete_train_data(
    fit_request: TrainOnlyFitRequest, error: str
) -> None:
    with pytest.raises(PreprocessingInputError, match=error):
        fit_train_only_standardizer(fit_request)
