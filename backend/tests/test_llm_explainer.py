"""assert-based self-check for ml/llm_explainer.py — run with: python tests/test_llm_explainer.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.llm_explainer import PROMPT_RULES, _build_prompt, _trim_long_arrays  # noqa: E402


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


if __name__ == "__main__":
    test_trim_long_arrays_leaves_short_lists_alone()
    test_trim_long_arrays_truncates_long_lists()
    test_trim_long_arrays_recurses_into_nested_dicts()
    test_build_prompt_includes_rules_examples_and_data()
