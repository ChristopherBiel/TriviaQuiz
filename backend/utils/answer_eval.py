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
    points_awarded: int = 0
    max_points: int = 1


class AnswerEvaluator(ABC):
    @abstractmethod
    def evaluate(self, question: str, correct_answer: str, user_answer: str, max_points: int = 1) -> EvalResult:
        raise NotImplementedError

    def evaluate_batch(self, items: list[tuple[str, str, str, int]]) -> list[EvalResult]:
        """Evaluate multiple (question, correct_answer, user_answer, max_points) tuples.
        Default implementation calls evaluate() in a loop; subclasses may override for efficiency.
        """
        return [self.evaluate(q, ca, ua, mp) for q, ca, ua, mp in items]


class SimpleEvaluator(AnswerEvaluator):
    FUZZY_THRESHOLD = 0.85

    def evaluate(self, question: str, correct_answer: str, user_answer: str, max_points: int = 1) -> EvalResult:
        norm_correct = self._normalize(correct_answer)
        norm_user = self._normalize(user_answer)

        if not norm_user:
            return EvalResult(is_correct=False, confidence=1.0, explanation="No answer provided",
                              points_awarded=0, max_points=max_points)

        if norm_correct == norm_user:
            return EvalResult(is_correct=True, confidence=1.0, explanation="Exact match",
                              points_awarded=max_points, max_points=max_points)

        ratio = SequenceMatcher(None, norm_correct, norm_user).ratio()
        if ratio >= self.FUZZY_THRESHOLD:
            return EvalResult(
                is_correct=True,
                confidence=round(ratio, 3),
                explanation=f"Fuzzy match ({ratio:.0%} similarity)",
                points_awarded=max_points,
                max_points=max_points,
            )

        return EvalResult(
            is_correct=False,
            confidence=round(1.0 - ratio, 3),
            explanation=f"No match ({ratio:.0%} similarity)",
            points_awarded=0,
            max_points=max_points,
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

_LLM_SYSTEM_PROMPT_BATCH = (
    "You are a trivia quiz answer evaluator. Evaluate each answer below.\n\n"
    "Be lenient like a fair quizmaster:\n"
    "- Accept answers that show the user knew the correct answer, even with different formulations or minor typos\n"
    "- Accept alternative phrasings and synonyms\n"
    "- If the reference answer lists multiple options, accept any single valid option\n"
    "- Accept common abbreviations and title variations (Prof./Professor, Dr./Doctor)\n"
    "- However, if the question requires a precise detail (e.g. a first name), require it\n"
    "- Accept answers that provide one of multiple correct options\n\n"
    "Respond with ONLY a raw JSON array, one object per answer in the same order. No markdown, no code fences:\n"
    '[{"correct": true, "explanation": "brief reason"}, ...]'
)

_LLM_SYSTEM_PROMPT_MULTIPOINT = (
    "You are a trivia quiz answer evaluator. Given a question, the reference answer, "
    "the maximum points, and a user's answer, determine how many points the user deserves.\n\n"
    "This question is worth {max_points} points. Award partial credit when the user got "
    "part of the answer right. For example, if a question asks for both an artist and a song "
    "title (2 points), and the user only got the artist right, award 1 point.\n\n"
    "Be lenient like a fair quizmaster:\n"
    "- Accept alternative phrasings, synonyms, and minor typos\n"
    "- Accept common abbreviations and title variations\n"
    "- However, if the question requires a precise detail, require it\n\n"
    "Respond with ONLY a raw JSON object. No markdown, no code fences, no extra text:\n"
    '{{\"points_awarded\": <0 to {max_points}>, \"explanation\": \"brief reason\"}}'
)

_LLM_SYSTEM_PROMPT_BATCH_MULTIPOINT = (
    "You are a trivia quiz answer evaluator. Evaluate each answer below.\n"
    "Each answer has a maximum number of points. Award partial credit when the user got "
    "part of the answer right.\n\n"
    "Be lenient like a fair quizmaster:\n"
    "- Accept alternative phrasings, synonyms, and minor typos\n"
    "- Accept common abbreviations and title variations\n"
    "- However, if the question requires a precise detail, require it\n\n"
    "Respond with ONLY a raw JSON array, one object per answer in the same order. No markdown, no code fences:\n"
    '[{"points_awarded": <0 to max_points>, "explanation": "brief reason"}, ...]'
)


class LLMEvaluator(AnswerEvaluator):
    """Evaluates answers using an LLM (Claude API) for semantic understanding."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def evaluate(self, question: str, correct_answer: str, user_answer: str, max_points: int = 1) -> EvalResult:
        results = self.evaluate_batch([(question, correct_answer, user_answer, max_points)])
        return results[0]

    def evaluate_batch(self, items: list[tuple[str, str, str, int]]) -> list[EvalResult]:
        if not items:
            return []

        if len(items) == 1:
            q, ca, ua, mp = items[0]
            result = self._evaluate_single(q, ca, ua, mp)
            return [result] if result is not None else [None]

        # Check if any items are multi-point
        has_multipoint = any(mp > 1 for _, _, _, mp in items)

        if has_multipoint:
            parts = [
                f"Answer {i}:\nQuestion: {q}\nReference: {ca}\nMax points: {mp}\nUser: {ua}"
                for i, (q, ca, ua, mp) in enumerate(items, 1)
            ]
            system_prompt = _LLM_SYSTEM_PROMPT_BATCH_MULTIPOINT
        else:
            parts = [
                f"Answer {i}:\nQuestion: {q}\nReference: {ca}\nUser: {ua}"
                for i, (q, ca, ua, mp) in enumerate(items, 1)
            ]
            system_prompt = _LLM_SYSTEM_PROMPT_BATCH

        user_msg = "\n\n".join(parts)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=min(80 * len(items), 4096),
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )

            text = response.content[0].text.strip()
            if not text:
                logger.warning("LLM batch evaluator received empty response")
                return [None] * len(items)
            if text.startswith("```"):
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text).strip()

            parsed = json.loads(text)
            if not isinstance(parsed, list) or len(parsed) != len(items):
                logger.warning(
                    "LLM batch evaluator returned %d results for %d items",
                    len(parsed) if isinstance(parsed, list) else -1,
                    len(items),
                )
                return [None] * len(items)

            results = []
            for entry, (_, _, _, mp) in zip(parsed, items):
                results.append(self._parse_llm_entry(entry, mp))
            return results

        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("LLM batch evaluator failed to parse response: %s | raw text: %r", exc, locals().get("text", "<not set>"))
            return [None] * len(items)
        except Exception as exc:
            logger.warning("LLM batch evaluator API error: %s", exc, exc_info=True)
            return [None] * len(items)

    def _evaluate_single(self, question: str, correct_answer: str, user_answer: str, max_points: int = 1) -> EvalResult | None:
        if max_points > 1:
            system_prompt = _LLM_SYSTEM_PROMPT_MULTIPOINT.format(max_points=max_points)
            user_msg = (
                f"Question: {question}\n"
                f"Reference answer: {correct_answer}\n"
                f"Max points: {max_points}\n"
                f"User's answer: {user_answer}"
            )
        else:
            system_prompt = _LLM_SYSTEM_PROMPT
            user_msg = (
                f"Question: {question}\n"
                f"Reference answer: {correct_answer}\n"
                f"User's answer: {user_answer}"
            )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=150,
                system=system_prompt,
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
            return self._parse_llm_entry(parsed, max_points)
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("LLM evaluator failed to parse response: %s | raw text: %r | prompt: %s", exc, locals().get("text", "<not set>"), user_msg)
            return None
        except Exception as exc:
            logger.warning("LLM evaluator API error: %s | prompt: %s", exc, user_msg, exc_info=True)
            return None

    @staticmethod
    def _parse_llm_entry(entry: dict, max_points: int) -> EvalResult:
        """Parse a single LLM JSON response entry into an EvalResult."""
        explanation = entry.get("explanation", "")
        explanation_str = f"LLM: {explanation}" if explanation else "LLM evaluation"

        if "points_awarded" in entry:
            pts = int(entry["points_awarded"])
            pts = max(0, min(pts, max_points))
            return EvalResult(
                is_correct=(pts == max_points),
                confidence=0.95,
                explanation=explanation_str,
                points_awarded=pts,
                max_points=max_points,
            )

        # Fallback: binary correct/incorrect (for 1-point questions or old-style responses)
        is_correct = bool(entry.get("correct", False))
        return EvalResult(
            is_correct=is_correct,
            confidence=0.95,
            explanation=explanation_str,
            points_awarded=max_points if is_correct else 0,
            max_points=max_points,
        )


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

    def evaluate(self, question: str, correct_answer: str, user_answer: str, max_points: int = 1) -> EvalResult:
        # Empty answer is always wrong — skip LLM entirely
        if not user_answer or not user_answer.strip():
            return EvalResult(is_correct=False, confidence=1.0, explanation="No answer provided",
                              points_awarded=0, max_points=max_points)

        simple_result = self._simple.evaluate(question, correct_answer, user_answer, max_points)

        # Simple match succeeded — no need to call the LLM (for 1-point questions)
        # For multi-point questions, simple can't do partial scoring, so always try LLM
        if simple_result.is_correct and max_points == 1:
            return simple_result

        # For multi-point questions with exact match, still return full points
        if simple_result.is_correct and max_points > 1:
            return simple_result

        # Simple match failed — try LLM if available
        llm = self._get_llm()
        if llm is None:
            return simple_result

        llm_result = llm._evaluate_single(question, correct_answer, user_answer, max_points)
        if llm_result is None:
            # LLM call failed; fall back to simple result with note
            simple_result.explanation = (simple_result.explanation or "") + " (LLM fallback: call failed)"
            return simple_result

        return llm_result

    def evaluate_batch(self, items: list[tuple[str, str, str, int]]) -> list[EvalResult]:
        if not items:
            return []

        # Run simple evaluator on all items
        results: list[EvalResult] = [self._simple.evaluate(q, ca, ua, mp) for q, ca, ua, mp in items]

        # Find indices that need LLM evaluation:
        # - Failed simple matching and have a non-empty answer
        # - OR multi-point questions that failed (for partial credit)
        llm_needed = [
            i for i, ((_, _, ua, mp), r) in enumerate(zip(items, results))
            if not r.is_correct and ua.strip()
        ]

        if not llm_needed:
            return results

        llm = self._get_llm()
        if llm is None:
            return results

        llm_items = [items[i] for i in llm_needed]
        llm_results = llm.evaluate_batch(llm_items)

        if len(llm_results) == len(llm_needed):
            for idx, llm_result in zip(llm_needed, llm_results):
                if llm_result is not None:
                    results[idx] = llm_result
                else:
                    results[idx].explanation = (results[idx].explanation or "") + " (LLM fallback: call failed)"
        else:
            logger.warning("LLM batch returned unexpected length %d (expected %d); keeping simple results", len(llm_results), len(llm_needed))

        return results
