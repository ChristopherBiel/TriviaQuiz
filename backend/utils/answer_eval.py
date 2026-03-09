from abc import ABC, abstractmethod
from dataclasses import dataclass
from difflib import SequenceMatcher
import json
import logging
import re
import string

logger = logging.getLogger(__name__)


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
            return EvalResult(is_correct=True, confidence=1.0, explanation="Exact match")

        ratio = SequenceMatcher(None, norm_correct, norm_user).ratio()
        if ratio >= self.FUZZY_THRESHOLD:
            return EvalResult(
                is_correct=True,
                confidence=round(ratio, 3),
                explanation=f"Fuzzy match ({ratio:.0%} similarity)",
            )

        return EvalResult(
            is_correct=False,
            confidence=round(1.0 - ratio, 3),
            explanation=f"No match ({ratio:.0%} similarity)",
        )

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[" + re.escape(string.punctuation) + r"]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text


_LLM_SYSTEM_PROMPT = (
    "You are a trivia quiz answer evaluator. Given a question, the reference answer, "
    "and a user's answer, determine if the user's answer is correct.\n\n"
    "Be lenient like a fair quizmaster:\n"
    "- Accept answers which show the user knew the correct answer, but might have mistyped"
    " or has a different formulation, but has provided the core essence of the answer)\n"
    "- Accept alternative phrasings and synonyms\n"
    "- If the reference answer lists multiple options (e.g. comma-separated), accept "
    "any single valid option from the list\n"
    "- Accept common abbreviations and title variations (Prof./Professor, Dr./Doctor)\n"
    "- However, if the question specifically requires a precise detail (e.g. a first name), "
    "do require it\n"
    "- Accept answers which provide one of multiple correct option (e.g. Q: Name one of the Beatles. A: John Lennon)\n\n"
    "Respond with ONLY a raw JSON object. No markdown, no code fences, no extra text:\n"
    '{\"correct\": true, \"explanation\": \"brief reason\"}'
)


class LLMEvaluator(AnswerEvaluator):
    """Evaluates answers using an LLM (Claude API) for semantic understanding."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def evaluate(self, question: str, correct_answer: str, user_answer: str) -> EvalResult:
        user_msg = (
            f"Question: {question}\n"
            f"Reference answer: {correct_answer}\n"
            f"User's answer: {user_answer}"
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                system=_LLM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            text = response.content[0].text.strip()
            if not text:
                logger.warning("LLM evaluator received empty response (stop_reason=%s) | prompt: %s", response.stop_reason, user_msg)
                return None
            if text.startswith("```"):
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text).strip()
            parsed = json.loads(text)
            is_correct = bool(parsed.get("correct", False))
            explanation = parsed.get("explanation", "")

            return EvalResult(
                is_correct=is_correct,
                confidence=0.95 if is_correct else 0.95,
                explanation=f"LLM: {explanation}" if explanation else "LLM evaluation",
            )
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("LLM evaluator failed to parse response: %s | raw text: %r | prompt: %s", exc, locals().get("text", "<not set>"), user_msg)
            return None
        except Exception as exc:
            logger.warning("LLM evaluator API error: %s | prompt: %s", exc, user_msg, exc_info=True)
            return None


class HybridEvaluator(AnswerEvaluator):
    """Runs SimpleEvaluator first; falls back to LLM for answers marked wrong."""

    def __init__(self):
        self._simple = SimpleEvaluator()
        self._llm: LLMEvaluator | None = None
        self._llm_init_attempted = False

    def _get_llm(self) -> LLMEvaluator | None:
        if self._llm_init_attempted:
            return self._llm

        self._llm_init_attempted = True
        try:
            from backend.core.settings import get_settings

            settings = get_settings()
            if settings.llm_eval_enabled and settings.llm_eval_api_key:
                self._llm = LLMEvaluator(
                    api_key=settings.llm_eval_api_key,
                    model=settings.llm_eval_model,
                )
                logger.info("LLM answer evaluator enabled (model=%s)", settings.llm_eval_model)
            else:
                logger.debug("LLM answer evaluator disabled")
        except Exception as exc:
            logger.warning("Failed to initialise LLM evaluator: %s", exc)
        return self._llm

    def evaluate(self, question: str, correct_answer: str, user_answer: str) -> EvalResult:
        simple_result = self._simple.evaluate(question, correct_answer, user_answer)

        # Simple match succeeded — no need to call the LLM
        if simple_result.is_correct:
            return simple_result

        # Simple match failed — try LLM if available
        llm = self._get_llm()
        if llm is None:
            return simple_result

        llm_result = llm.evaluate(question, correct_answer, user_answer)
        if llm_result is None:
            # LLM call failed; fall back to simple result with note
            simple_result.explanation = (simple_result.explanation or "") + " (LLM fallback: call failed)"
            return simple_result

        return llm_result
