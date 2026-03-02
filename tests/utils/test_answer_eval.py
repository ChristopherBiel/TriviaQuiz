import json
from unittest.mock import MagicMock, patch

import pytest

from backend.utils.answer_eval import (
    EvalResult,
    HybridEvaluator,
    LLMEvaluator,
    SimpleEvaluator,
)


# ---------------------------------------------------------------------------
# SimpleEvaluator (unchanged behaviour)
# ---------------------------------------------------------------------------

@pytest.fixture
def evaluator():
    return SimpleEvaluator()


class TestSimpleEvaluator:
    def test_exact_match(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "Paris")
        assert result.is_correct is True
        assert result.confidence == 1.0

    def test_case_insensitive(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "paris")
        assert result.is_correct is True
        assert result.confidence == 1.0

    def test_whitespace_handling(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "  Paris  ")
        assert result.is_correct is True

    def test_punctuation_ignored(self, evaluator):
        result = evaluator.evaluate("Q", "U.S.A.", "USA")
        assert result.is_correct is True

    def test_fuzzy_match_close(self, evaluator):
        result = evaluator.evaluate("Q", "Beethoven", "Bethoveen")
        assert result.is_correct is True
        assert result.confidence < 1.0

    def test_wrong_answer(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "London")
        assert result.is_correct is False

    def test_empty_answer(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "")
        assert result.is_correct is False
        assert "No answer" in result.explanation

    def test_empty_answer_spaces(self, evaluator):
        result = evaluator.evaluate("Q", "Paris", "   ")
        assert result.is_correct is False

    def test_completely_different(self, evaluator):
        result = evaluator.evaluate("Q", "Photosynthesis", "42")
        assert result.is_correct is False


# ---------------------------------------------------------------------------
# LLMEvaluator
# ---------------------------------------------------------------------------

def _make_anthropic_response(text: str):
    """Build a mock Anthropic Messages response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_llm_evaluator(mock_client):
    """Create an LLMEvaluator with a mock client injected."""
    with patch("anthropic.Anthropic", return_value=mock_client):
        ev = LLMEvaluator(api_key="test-key", model="test-model")
    return ev


class TestLLMEvaluator:
    def test_correct_answer(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_anthropic_response(
            json.dumps({"correct": True, "explanation": "Last name matches"})
        )
        ev = _make_llm_evaluator(mock_client)

        result = ev.evaluate(
            "Who developed the theory of relativity?",
            "Albert Einstein",
            "Einstein",
        )
        assert result.is_correct is True
        assert "LLM" in result.explanation

    def test_incorrect_answer(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_anthropic_response(
            json.dumps({"correct": False, "explanation": "Completely different person"})
        )
        ev = _make_llm_evaluator(mock_client)

        result = ev.evaluate("Q", "Albert Einstein", "Isaac Newton")
        assert result.is_correct is False

    def test_invalid_json_returns_none(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_anthropic_response("not json")
        ev = _make_llm_evaluator(mock_client)

        result = ev.evaluate("Q", "Paris", "London")
        assert result is None

    def test_api_error_returns_none(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")
        ev = _make_llm_evaluator(mock_client)

        result = ev.evaluate("Q", "Paris", "London")
        assert result is None


# ---------------------------------------------------------------------------
# HybridEvaluator
# ---------------------------------------------------------------------------

class TestHybridEvaluator:
    def test_simple_match_skips_llm(self):
        """When SimpleEvaluator says correct, LLM is never called."""
        hybrid = HybridEvaluator()
        mock_llm = MagicMock()
        hybrid._llm = mock_llm
        hybrid._llm_init_attempted = True

        result = hybrid.evaluate("Q", "Paris", "paris")
        assert result.is_correct is True
        mock_llm.evaluate.assert_not_called()

    def test_simple_fail_calls_llm(self):
        """When SimpleEvaluator says wrong and LLM is available, LLM is called."""
        hybrid = HybridEvaluator()
        mock_llm = MagicMock()
        mock_llm.evaluate.return_value = EvalResult(
            is_correct=True, confidence=0.95, explanation="LLM: partial name match"
        )
        hybrid._llm = mock_llm
        hybrid._llm_init_attempted = True

        result = hybrid.evaluate(
            "Who developed relativity?", "Albert Einstein", "Einstein"
        )
        assert result.is_correct is True
        assert "LLM" in result.explanation
        mock_llm.evaluate.assert_called_once()

    def test_simple_fail_no_llm_returns_simple_result(self):
        """When LLM is not configured, falls back to SimpleEvaluator result."""
        hybrid = HybridEvaluator()
        hybrid._llm = None
        hybrid._llm_init_attempted = True

        result = hybrid.evaluate("Q", "Albert Einstein", "Einstein")
        assert result.is_correct is False  # SimpleEvaluator rejects this

    def test_llm_failure_falls_back_to_simple(self):
        """When LLM returns None (error), falls back to SimpleEvaluator result."""
        hybrid = HybridEvaluator()
        mock_llm = MagicMock()
        mock_llm.evaluate.return_value = None
        hybrid._llm = mock_llm
        hybrid._llm_init_attempted = True

        result = hybrid.evaluate("Q", "Albert Einstein", "Einstein")
        assert result.is_correct is False  # SimpleEvaluator result

    def test_lazy_init_disabled(self):
        """When settings say disabled, _get_llm returns None."""
        hybrid = HybridEvaluator()

        mock_settings = MagicMock()
        mock_settings.llm_eval_enabled = False
        mock_settings.llm_eval_api_key = ""

        with patch(
            "backend.core.settings.get_settings", return_value=mock_settings
        ):
            llm = hybrid._get_llm()

        assert llm is None
        assert hybrid._llm_init_attempted is True
