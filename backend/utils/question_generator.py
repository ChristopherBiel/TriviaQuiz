"""AI-powered trivia question generation using Claude API."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a trivia question generator. Given example trivia questions, generate new \
questions that match their overall topic area and difficulty level.

Rules:
- Do NOT duplicate or rephrase the example questions.
- Each question needs only a correct answer. Do NOT generate incorrect answer options.
- Keep the same language as the examples unless instructed otherwise.
- IMPORTANT — Diversity: Do not just create minor variations of the examples \
(e.g. swapping out one country/name/year for another in the same question pattern). \
At most half of the generated questions may follow a pattern from the examples. \
The rest should be genuinely different questions that cover other aspects of the \
same broad topic area, using different question structures and angles.
- IMPORTANT — Difficulty: Study the difficulty of the provided examples carefully. \
The generated questions should match that difficulty level consistently. \
Avoid trivially easy questions (like "What is the capital of France?") unless \
the examples are at that level. Aim for the same level of specificity and \
knowledge required as the examples demonstrate.

Output a JSON array of objects. Each object must have these fields:
- "question": the question text
- "answer": the correct answer
- "tags": array of relevant lowercase tags
- "points": integer 1-10 matching the difficulty
- "source_note": brief note on the topic area

Output ONLY the JSON array, no other text."""


class GenerationError(Exception):
    """Raised when question generation fails."""


class QuestionGenerator:
    """Generates trivia questions using Claude API."""

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(
        self,
        examples: list[dict],
        count: int,
        language: str | None = None,
        topic: str | None = None,
        extra_instructions: str | None = None,
    ) -> list[dict]:
        """Generate new questions based on examples.

        Returns a list of dicts with question fields.
        Raises GenerationError on failure.
        """
        example_text = self.format_examples_text(examples)

        parts = [f"Here are {len(examples)} example trivia questions:\n\n{example_text}"]
        parts.append(f"\nGenerate exactly {count} new trivia questions in the same style.")

        if language:
            parts.append(f"Language: {language}")
        if topic:
            parts.append(f"Topic area: {topic}")
        if extra_instructions:
            parts.append(f"Additional instructions: {extra_instructions}")

        user_msg = "\n".join(parts)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            text = response.content[0].text.strip()
            if not text:
                raise GenerationError("LLM returned an empty response")

            # Strip markdown code fences
            if text.startswith("```"):
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text).strip()

            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise GenerationError("LLM response is not a JSON array")

            # Validate required fields
            validated = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                if "question" not in item or "answer" not in item:
                    continue
                item.setdefault("incorrect_answers", [])
                item.setdefault("tags", [])
                item.setdefault("points", 1)
                item.setdefault("source_note", "AI-generated")
                validated.append(item)

            if not validated:
                raise GenerationError("LLM generated no valid questions")

            return validated

        except GenerationError:
            raise
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse LLM generation response: %s", exc)
            raise GenerationError("Failed to parse AI response as JSON") from exc
        except Exception as exc:
            logger.exception("Question generation failed")
            raise GenerationError(f"AI generation failed: {exc}") from exc

    @staticmethod
    def format_examples_text(examples: list[dict]) -> str:
        """Format example questions as readable text for clipboard or LLM input."""
        lines = []
        for i, q in enumerate(examples, 1):
            lines.append(f"--- Question {i} ---")
            lines.append(f"Q: {q.get('question', '')}")
            lines.append(f"A: {q.get('answer', '')}")
            incorrect = q.get("incorrect_answers", [])
            if incorrect:
                lines.append(f"Wrong answers: {', '.join(incorrect)}")
            topic = q.get("question_topic", "")
            if topic:
                lines.append(f"Topic: {topic}")
            tags = q.get("tags", [])
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            lang = q.get("language", "")
            if lang:
                lines.append(f"Language: {lang}")
            points = q.get("points", 1)
            if points != 1:
                lines.append(f"Points: {points}")
            lines.append("")
        return "\n".join(lines)


def get_generator() -> QuestionGenerator | None:
    """Return a QuestionGenerator if LLM is configured, else None."""
    from backend.core.settings import get_settings

    settings = get_settings()
    if not settings.llm_eval_enabled or not settings.llm_eval_api_key:
        return None
    return QuestionGenerator(
        api_key=settings.llm_eval_api_key,
        model=settings.llm_gen_model,
    )
