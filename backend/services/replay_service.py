from backend.models.replay import ReplayAttemptModel
from backend.storage import get_event_store, get_question_store, get_replay_store
from backend.utils.answer_eval import SimpleEvaluator


_evaluator = SimpleEvaluator()


def start_replay(event_id: str) -> dict | None:
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None

    question_store = get_question_store()
    questions = []
    for qid in event.question_ids:
        q = question_store.get_by_id(qid)
        if q:
            questions.append({
                "question_id": q.question_id,
                "question": q.question,
                "media_path": q.media_path,
            })

    return {
        "event_id": event.event_id,
        "name": event.name,
        "description": event.description,
        "total": len(questions),
        "questions": questions,
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
    answers_detail = []
    score = 0

    for entry in user_answers:
        qid = entry.get("question_id", "")
        user_answer = entry.get("user_answer") or entry.get("answer", "")
        override = entry.get("override")  # True/False/None

        question = question_store.get_by_id(qid)
        if not question:
            answers_detail.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": "",
                "is_correct": False,
            })
            continue

        if override is not None:
            is_correct = bool(override)
        else:
            result = _evaluator.evaluate(question.question, question.answer, user_answer)
            is_correct = result.is_correct

        # Update question stats
        question_store.update(qid, {
            "times_asked": question.times_asked + 1,
            **({"times_correct": question.times_correct + 1} if is_correct else {"times_incorrect": question.times_incorrect + 1}),
        })

        if is_correct:
            score += 1

        answers_detail.append({
            "question_id": qid,
            "user_answer": user_answer,
            "correct_answer": question.answer,
            "is_correct": is_correct,
        })

    total = len(event.question_ids)
    replay = ReplayAttemptModel(
        event_id=event_id,
        user_id=user_id,
        display_name=display_name,
        score=score,
        total=total,
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
