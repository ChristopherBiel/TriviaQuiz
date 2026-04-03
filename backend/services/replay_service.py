from backend.models.replay import ReplayAttemptModel
from backend.storage import get_event_store, get_media_store, get_question_store, get_replay_store
from backend.utils.answer_eval import HybridEvaluator


_evaluator = HybridEvaluator()


def start_replay(event_id: str) -> dict | None:
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None

    question_store = get_question_store()
    media_store = get_media_store()
    questions = []
    total_points = 0
    for qid in event.question_ids:
        q = question_store.get_by_id(qid)
        if q:
            media_url = media_store.get_url(q.media_path) if q.media_path else None
            questions.append({
                "question_id": q.question_id,
                "question": q.question,
                "media_path": media_url,
                "media_text": q.media_text,
                "points": q.points,
            })
            total_points += q.points

    return {
        "event_id": event.event_id,
        "name": event.name,
        "description": event.description,
        "total": total_points,
        "question_count": len(questions),
        "questions": questions,
    }


def _load_questions(question_store, user_answers: list[dict]) -> dict:
    """Pre-load all referenced questions into a dict keyed by question_id."""
    questions = {}
    for entry in user_answers:
        qid = entry.get("question_id", "")
        if qid and qid not in questions:
            q = question_store.get_by_id(qid)
            if q:
                questions[qid] = q
    return questions


def _batch_evaluate(user_answers: list[dict], questions: dict) -> list:
    """Run evaluate_batch for all entries that need it (no override, question exists).
    Returns a list of EvalResult|None aligned with user_answers indices."""
    eval_indices = []
    eval_items = []
    for i, entry in enumerate(user_answers):
        qid = entry.get("question_id", "")
        override = entry.get("override")
        q = questions.get(qid)
        if override is None and q:
            user_answer = entry.get("user_answer") or entry.get("answer", "")
            eval_indices.append(i)
            eval_items.append((q.question, q.answer, user_answer, q.points))

    batch_results = _evaluator.evaluate_batch(eval_items) if eval_items else []
    result_map = {idx: result for idx, result in zip(eval_indices, batch_results)}
    return result_map


def _resolve_override(override, max_points: int) -> int:
    """Resolve an override value to points awarded.
    Accepts bool (True=full points, False=0) or int (specific point value)."""
    if isinstance(override, bool):
        return max_points if override else 0
    if isinstance(override, int):
        return max(0, min(override, max_points))
    # Try to parse as int, fall back to bool-like
    try:
        val = int(override)
        return max(0, min(val, max_points))
    except (TypeError, ValueError):
        return max_points if override else 0


def evaluate_replay(event_id: str, user_answers: list[dict]) -> dict | None:
    """Evaluate answers without saving to DB. Returns score and per-question details."""
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None

    question_store = get_question_store()
    questions = _load_questions(question_store, user_answers)
    result_map = _batch_evaluate(user_answers, questions)

    answers_detail = []
    score = 0
    total_points = 0

    for i, entry in enumerate(user_answers):
        qid = entry.get("question_id", "")
        user_answer = entry.get("user_answer") or entry.get("answer", "")
        override = entry.get("override")
        question = questions.get(qid)

        if not question:
            answers_detail.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": "",
                "is_correct": False,
                "points_awarded": 0,
                "max_points": 1,
            })
            total_points += 1
            continue

        max_pts = question.points
        total_points += max_pts
        explanation = None

        if override is not None:
            points_awarded = _resolve_override(override, max_pts)
            is_correct = (points_awarded == max_pts)
        else:
            result = result_map[i]
            is_correct = result.is_correct
            points_awarded = result.points_awarded
            explanation = result.explanation

        score += points_awarded

        detail = {
            "question_id": qid,
            "user_answer": user_answer,
            "correct_answer": question.answer,
            "is_correct": is_correct,
            "points_awarded": points_awarded,
            "max_points": max_pts,
        }
        if explanation:
            detail["explanation"] = explanation
        answers_detail.append(detail)

    return {
        "score": score,
        "total": total_points,
        "answers": answers_detail,
    }


def submit_replay(
    event_id: str,
    user_answers: list[dict],
    user_id: str | None = None,
    display_name: str | None = None,
) -> ReplayAttemptModel | None:
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None

    question_store = get_question_store()
    questions = _load_questions(question_store, user_answers)
    result_map = _batch_evaluate(user_answers, questions)

    answers_detail = []
    score = 0
    total_points = 0

    for i, entry in enumerate(user_answers):
        qid = entry.get("question_id", "")
        user_answer = entry.get("user_answer") or entry.get("answer", "")
        override = entry.get("override")
        question = questions.get(qid)

        if not question:
            answers_detail.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": "",
                "is_correct": False,
                "points_awarded": 0,
                "max_points": 1,
            })
            total_points += 1
            continue

        max_pts = question.points
        total_points += max_pts
        explanation = None

        if override is not None:
            points_awarded = _resolve_override(override, max_pts)
            is_correct = (points_awarded == max_pts)
        else:
            result = result_map[i]
            is_correct = result.is_correct
            points_awarded = result.points_awarded
            explanation = result.explanation

        # Update question stats
        question_store.update(qid, {
            "times_asked": question.times_asked + 1,
            **({"times_correct": question.times_correct + 1} if is_correct else {"times_incorrect": question.times_incorrect + 1}),
        })

        score += points_awarded

        detail = {
            "question_id": qid,
            "user_answer": user_answer,
            "correct_answer": question.answer,
            "is_correct": is_correct,
            "points_awarded": points_awarded,
            "max_points": max_pts,
        }
        if explanation:
            detail["explanation"] = explanation
        answers_detail.append(detail)

    replay = ReplayAttemptModel(
        event_id=event_id,
        user_id=user_id,
        display_name=display_name,
        score=score,
        total=total_points,
        answers=answers_detail,
    )

    replay_store = get_replay_store()
    replay_store.save(replay)

    # Update event best_score if this is a new high
    if event.best_score is None or score > event.best_score:
        get_event_store().update(event_id, {"best_score": float(score)})

    return replay


def get_leaderboard(event_id: str, limit: int = 10) -> list[dict]:
    replays = get_replay_store().get_leaderboard(event_id, limit=limit)
    return [
        {
            "replay_id": r.replay_id,
            "user_id": r.user_id,
            "display_name": r.display_name or "Anonymous",
            "score": r.score,
            "total": r.total,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in replays
    ]


def has_played_event(event_id: str, user_id: str) -> bool:
    return get_replay_store().has_user_played(event_id, user_id)


def get_user_replays(user_id: str) -> list[dict]:
    replays = get_replay_store().list_by_user(user_id)
    return [
        {
            "replay_id": r.replay_id,
            "event_id": r.event_id,
            "score": r.score,
            "total": r.total,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in replays
    ]


def get_replay_detail(replay_id: str) -> dict | None:
    """Return full replay details including per-question answers."""
    replay = get_replay_store().get_by_id(replay_id)
    if not replay:
        return None
    return {
        "replay_id": replay.replay_id,
        "event_id": replay.event_id,
        "user_id": replay.user_id,
        "display_name": replay.display_name or "Anonymous",
        "score": replay.score,
        "total": replay.total,
        "answers": replay.answers,
        "completed_at": replay.completed_at.isoformat() if replay.completed_at else None,
    }


def delete_replay(replay_id: str, event_id: str) -> bool:
    """Delete a replay and recalculate the event's best_score."""
    replay_store = get_replay_store()
    if not replay_store.delete(replay_id):
        return False

    # Recalculate best_score from remaining replays
    remaining = replay_store.list_by_event(event_id, limit=1)
    new_best = float(remaining[0].score) if remaining else None
    get_event_store().update(event_id, {"best_score": new_best})
    return True
