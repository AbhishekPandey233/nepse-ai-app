"""assert-based self-check for ml/llm_explainer.py — run with: python tests/test_llm_explainer.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.ml.llm_explainer as llm  # noqa: E402
from app.ml.llm_explainer import (  # noqa: E402
    PROMPT_RULES,
    _build_detailed_factors_prompt,
    _build_prompt,
    _max_drawdown_pct,
    _summarize_bundle,
    _top_factors,
    _trim_long_arrays,
    _use_rupees,
    generate_sectioned_explanation,
)


def _sample_results():
    return {
        "volatility": {"conditional_volatility": [0.01, 0.012, 0.02, 0.015, 0.018]},
        "predict": {
            "metrics": {"rmse": 0.009, "directional_accuracy": 53.2},
            "next_day_forecast": {"predicted_return": 0.0123, "as_of_date": "2026-07-07"},
        },
    }


def _sample_history():
    return {
        "close": [100.0, 110.0, 90.0, 105.0, 102.0],
        "summary": {
            "period_start": "2024-01-01",
            "period_end": "2024-06-01",
            "overall_return_pct": 2.0,
            "highest_close": {"price": 110.0, "date": "2024-02-01"},
            "lowest_close": {"price": 90.0, "date": "2024-03-01"},
            "top_gains": [{"date": "2024-02-01", "return_pct": 9.5}],
            "top_losses": [{"date": "2024-03-01", "return_pct": -18.2}],
            "high_volatility_periods": [{"start": "2024-02-01", "end": "2024-02-10"}],
            "high_volatility_threshold": 0.02,
        },
    }


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
    assert "Q: What was the directional accuracy?" in prompt_with_question
    assert prompt_with_question.rstrip().endswith("A:")

    prompt_no_question = _build_prompt(results, None)
    assert "natural-language summary" in prompt_no_question
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


def test_summarize_bundle_trims_heavy_arrays_and_is_non_mutating():
    bundle = {
        "efficiency": {"verdict": "eff"},  # already compact -> untouched
        "explain": {"base_value": 0.0001, "per_row_shap": [{"rsi_14": 0.1, "ma_10": -0.2}] * 50},
        "predict": {
            "metrics": {"rmse": 0.01, "directional_accuracy": 53.0},
            "next_day_forecast": {"predicted_return": 0.01, "as_of_date": "2026-07-07"},
            "predictions": [0.1] * 500,
            "actual": [0.1] * 500,
            "dates": ["2024-01-01", "2026-07-07"],
        },
        "volatility": {"params": {"alpha[1]": 0.1, "beta[1]": 0.8}, "conditional_volatility": [0.01, 0.03], "forecast": [0.02] * 10},
        "backtest": {"strategy_total_return": -0.05, "buy_hold_total_return": 0.09, "n_trades": 38,
                     "transaction_cost_pct": 0.5, "outperformed": False, "verdict": "did not outperform",
                     "strategy_cumulative": [0.0] * 300},
        "current_conditional_volatility_garch": 0.0126,  # non-module scalar -> passed through
    }
    out = _summarize_bundle(bundle)

    # heavy per-day arrays are gone, headline numbers kept
    assert "per_row_shap" not in out["explain"]
    assert out["explain"]["top_factors_latest_prediction"], out["explain"]
    assert "predictions" not in out["predict"] and out["predict"]["metrics"]["rmse"] == 0.01
    assert out["predict"]["test_period"] == {"from": "2024-01-01", "to": "2026-07-07"}
    assert "conditional_volatility" not in out["volatility"]
    assert out["volatility"]["current_conditional_volatility"] == 0.03
    assert "strategy_cumulative" not in out["backtest"] and out["backtest"]["n_trades"] == 38
    assert out["efficiency"] == {"verdict": "eff"}
    assert out["current_conditional_volatility_garch"] == 0.0126

    # original bundle must not be mutated (shared cache object in production)
    assert "per_row_shap" in bundle["explain"]
    print("test_summarize_bundle_trims_heavy_arrays_and_is_non_mutating passed")


def test_use_rupees_converts_dollar_symbols_and_words():
    assert _use_rupees("The highest close was $419 on that day.") == "The highest close was Rs 419 on that day."
    assert _use_rupees("worth $ 101.5 tomorrow") == "worth Rs 101.5 tomorrow"
    assert _use_rupees("about 5 dollars") == "about 5 rupees"
    assert _use_rupees("just one Dollar") == "just one rupee"
    assert _use_rupees("no currency mentioned here") == "no currency mentioned here"
    print("test_use_rupees_converts_dollar_symbols_and_words passed")


def test_max_drawdown_pct():
    assert abs(_max_drawdown_pct([100, 110, 90, 105]) - (-18.181818)) < 1e-4
    assert _max_drawdown_pct([100, 101, 102]) == 0.0  # only-up series never draws down
    print("test_max_drawdown_pct passed")


def test_sectioned_explanation_grounded_and_non_overlapping():
    # make Ollama return the prompt it received, so we can inspect exactly what each section saw
    orig = llm._ollama_generate
    llm._ollama_generate = lambda prompt, **kw: prompt  # noqa: ARG005
    try:
        out = generate_sectioned_explanation(_sample_results(), _sample_history())
    finally:
        llm._ollama_generate = orig

    assert set(out) == {"risk_analysis", "historical_trends", "future_outlook"}
    for section in out.values():
        assert isinstance(section["key_points"], list) and len(section["key_points"]) >= 3
        assert isinstance(section["narrative"], str) and section["narrative"]

    risk = out["risk_analysis"]["narrative"]
    trends = out["historical_trends"]["narrative"]
    outlook = out["future_outlook"]["narrative"]

    # each section is grounded in its OWN numbers...
    assert "-18.2" in risk  # max drawdown
    assert "9.5" in trends  # biggest up day
    assert "1.23" in outlook and "53.2" in outlook  # forecast % + accuracy
    assert "not a guarantee" in outlook  # honesty caveat is mandatory

    # ...and does NOT leak the forecast number into the risk/history sections (non-overlap)
    assert "1.23" not in risk
    assert "1.23" not in trends

    # key_points carry the correct figures deterministically
    assert any("-18.2%" in kp for kp in out["risk_analysis"]["key_points"])
    assert any("53.2%" in kp for kp in out["future_outlook"]["key_points"])
    print("test_sectioned_explanation_grounded_and_non_overlapping passed")


if __name__ == "__main__":
    test_trim_long_arrays_leaves_short_lists_alone()
    test_trim_long_arrays_truncates_long_lists()
    test_trim_long_arrays_recurses_into_nested_dicts()
    test_build_prompt_includes_rules_examples_and_data()
    test_top_factors_sorted_by_absolute_shap_value()
    test_top_factors_empty_when_no_shap_data()
    test_build_detailed_factors_prompt_grounds_exact_values_no_swapping()
    test_summarize_bundle_trims_heavy_arrays_and_is_non_mutating()
    test_use_rupees_converts_dollar_symbols_and_words()
    test_max_drawdown_pct()
    test_sectioned_explanation_grounded_and_non_overlapping()
