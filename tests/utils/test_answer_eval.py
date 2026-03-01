import pytest

from backend.utils.answer_eval import SimpleEvaluator, LLMEvaluator


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


class TestLLMEvaluator:
    def test_not_implemented(self):
        evaluator = LLMEvaluator()
        with pytest.raises(NotImplementedError):
            evaluator.evaluate("Q", "A", "B")
