"""assert-based self-check for ml/llm_explainer.py — run with: python tests/test_llm_explainer.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.llm_explainer import (  # noqa: E402
    PROMPT_RULES,
    _build_detailed_factors_prompt,
    _build_prompt,
    _top_factors,
    _trim_long_arrays,
)


def test_trim_long_arrays_leaves_short_lists_alone():
    data = {"metrics": {"rmse": 0.0096, "directional_accuracy": 54.3}, "small_list": [1, 2, 3]}
    assert _trim_long_arrays(data) == data
    print("test_trim_long_arrays_leaves_short_lists_alone passed")


def test_trim_long_arrays_truncates_long_lists():
    long_list = list(range(200))
    trimmed = _trim_long_arrays({"dates": long_list})

    assert len(trimmed["dates"]) == 7  # 3 head + 1 marker + 3 tail
    assert trimmed["dates"][:3] == [0, 1, 2]
    assert trimmed["dates"][-3:] == [197, 198, 199]
    assert "omitted" in trimmed["dates"][3]
    print("test_trim_long_arrays_truncates_long_lists passed")


def test_trim_long_arrays_recurses_into_nested_dicts():
    nested = {"predict": {"dates": list(range(100)), "metrics": {"rmse": 0.01}}}
    trimmed = _trim_long_arrays(nested)

    assert len(trimmed["predict"]["dates"]) == 7
    assert trimmed["predict"]["metrics"] == {"rmse": 0.01}
    print("test_trim_long_arrays_recurses_into_nested_dicts passed")


def test_build_prompt_includes_rules_examples_and_data():
    results = {"metrics": {"directional_accuracy": 54.3}}

    prompt_with_question = _build_prompt(results, "What was the directional accuracy?")
    assert "DATA:" in prompt_with_question
    assert "directional_accuracy" in prompt_with_question
    assert PROMPT_RULES in prompt_with_question
    assert "With the data currently available, the following means:" in prompt_with_question
    assert "Q: What was the directional accuracy?" in prompt_with_question
    assert prompt_with_question.rstrip().endswith("A:")

    prompt_no_question = _build_prompt(results, None)
    assert "4-6 sentence" in prompt_no_question
    assert prompt_no_question.rstrip().endswith("A:")

    print("test_build_prompt_includes_rules_examples_and_data passed")


def test_top_factors_sorted_by_absolute_shap_value():
    explain_result = {
        "per_row_shap": [
            {"rsi_14": 0.0001},  # earlier row, must be ignored -- only the LATEST row counts
            {"rsi_14": -0.0005, "ma_10": 0.0009, "diff_pct": 0.0002},
        ]
    }
    factors = _top_factors(explain_result, top_n=3)

    assert [f["feature"] for f in factors] == ["ma_10", "rsi_14", "diff_pct"], factors
    assert factors[0]["direction"] == "UP" and factors[1]["direction"] == "DOWN"
    assert all(f["meaning"] for f in factors), "every known feature must have a real glossary entry"
    print("test_top_factors_sorted_by_absolute_shap_value passed")


def test_top_factors_empty_when_no_shap_data():
    assert _top_factors({}) == []
    assert _top_factors({"per_row_shap": []}) == []
    print("test_top_factors_empty_when_no_shap_data passed")


def test_build_detailed_factors_prompt_grounds_exact_values_no_swapping():
    predict_result = {
        "metrics": {"rmse": 0.009, "mae": 0.006, "directional_accuracy": 52.5},
        "next_day_forecast": {"predicted_return": 0.0123, "as_of_date": "2026-07-07"},
    }
    explain_result = {
        "base_value": 0.00012,
        "per_row_shap": [{"lag_return_1": 0.0013, "diff_pct": -0.0009, "ma_10": -0.0007}],
    }

    prompt = _build_detailed_factors_prompt("NABIL", predict_result, explain_result)

    assert "NABIL" in prompt
    assert "0.00012" in prompt  # base_value
    assert "52.5" in prompt  # directional accuracy
    # forecast is converted to a percentage (easier for the model to quote verbatim) and the
    # prompt must explicitly forbid claiming it's unavailable
    import math

    expected_pct = round((math.exp(0.0123) - 1) * 100, 3)
    assert f"{expected_pct}%" in prompt
    assert "never say it is unknown or unavailable" in prompt
    # each factor's exact value must appear verbatim, not swapped with another factor's
    assert "0.0013" in prompt
    assert "-0.0009" in prompt
    assert "-0.0007" in prompt
    assert "AT LEAST 5 full paragraphs" in prompt
    assert "do not" in prompt and "swap values" in prompt

    print("test_build_detailed_factors_prompt_grounds_exact_values_no_swapping passed")


if __name__ == "__main__":
    test_trim_long_arrays_leaves_short_lists_alone()
    test_trim_long_arrays_truncates_long_lists()
    test_trim_long_arrays_recurses_into_nested_dicts()
    test_build_prompt_includes_rules_examples_and_data()
    test_top_factors_sorted_by_absolute_shap_value()
    test_top_factors_empty_when_no_shap_data()
    test_build_detailed_factors_prompt_grounds_exact_values_no_swapping()
