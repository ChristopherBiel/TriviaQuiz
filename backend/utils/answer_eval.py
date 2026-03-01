from abc import ABC, abstractmethod
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import string


@dataclass
class EvalResult:
    is_correct: bool
    confidence: float
    explanation: str | None = None


class AnswerEvaluator(ABC):
    @abstractmethod
    def evaluate(self, question: str, correct_answer: str, user_answer: str) -> EvalResult:
        raise NotImplementedError


class SimpleEvaluator(AnswerEvaluator):
    FUZZY_THRESHOLD = 0.85

    def evaluate(self, question: str, correct_answer: str, user_answer: str) -> EvalResult:
        norm_correct = self._normalize(correct_answer)
        norm_user = self._normalize(user_answer)

        if not norm_user:
            return EvalResult(is_correct=False, confidence=1.0, explanation="No answer provided")

        if norm_correct == norm_user:
            return EvalResult(is_correct=True, confidence=1.0)

        ratio = SequenceMatcher(None, norm_correct, norm_user).ratio()
        if ratio >= self.FUZZY_THRESHOLD:
            return EvalResult(
                is_correct=True,
                confidence=round(ratio, 3),
                explanation=f"Fuzzy match ({ratio:.0%} similarity)",
            )

        return EvalResult(is_correct=False, confidence=round(1.0 - ratio, 3))

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[" + re.escape(string.punctuation) + r"]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text


class LLMEvaluator(AnswerEvaluator):
    def evaluate(self, question: str, correct_answer: str, user_answer: str) -> EvalResult:
        raise NotImplementedError("LLM-based evaluation is not yet implemented")
