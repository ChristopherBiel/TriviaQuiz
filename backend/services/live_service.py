import random
import string

from backend.models.live import LiveAnswerModel, LiveParticipantModel, LiveSessionModel
from backend.storage import get_event_store, get_live_store, get_media_store, get_question_store
from backend.utils.answer_eval import HybridEvaluator


_evaluator = HybridEvaluator()


def _generate_join_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_live_session(
    event_id: str, username: str, show_questions_on_devices: bool = False
) -> LiveSessionModel | None:
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None

    live_store = get_live_store()
    # Generate a unique join code among active sessions
    for _ in range(20):
        code = _generate_join_code()
        if not live_store.get_session_by_code(code):
            break
    else:
        return None  # extremely unlikely

    session = LiveSessionModel(
        event_id=event_id,
        join_code=code,
        show_questions_on_devices=show_questions_on_devices,
        created_by=username,
    )
    if live_store.create_session(session):
        return session
    return None


def get_live_session(session_id: str) -> LiveSessionModel | None:
    return get_live_store().get_session(session_id)


def get_live_session_by_code(join_code: str) -> LiveSessionModel | None:
    return get_live_store().get_session_by_code(join_code.upper().strip())


def update_session_settings(
    session_id: str, username: str, updates: dict
) -> LiveSessionModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None
    allowed = {"show_questions_on_devices"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return session
    return live_store.update_session(session_id, filtered)


def advance_question(session_id: str, username: str) -> LiveSessionModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None
    if session.status == "finished":
        return None

    event = get_event_store().get_by_id(session.event_id)
    if not event:
        return None

    total_questions = len(event.question_ids)
    next_index = session.current_question_index + 1

    if next_index >= total_questions:
        return None  # no more questions, use finish_session instead

    updates = {}

    # Auto-lock previous question
    current_idx = session.current_question_index
    if current_idx >= 0 and current_idx not in session.locked_indices:
        new_locked = list(session.locked_indices) + [current_idx]
        updates["locked_indices"] = new_locked
        # Bulk-lock answers for previous question
        live_store.update_answers_bulk(session_id, current_idx, {"is_locked": True})

    updates["current_question_index"] = next_index
    if session.status == "lobby":
        updates["status"] = "active"

    return live_store.update_session(session_id, updates)


def lock_question(session_id: str, question_index: int, username: str) -> LiveSessionModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None
    if question_index in session.locked_indices:
        return session  # already locked

    new_locked = list(session.locked_indices) + [question_index]
    live_store.update_answers_bulk(session_id, question_index, {"is_locked": True})
    return live_store.update_session(session_id, {"locked_indices": new_locked})


def reveal_question(session_id: str, question_index: int, username: str) -> dict | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None
    if question_index in session.revealed_indices:
        return {"already_revealed": True}

    event = get_event_store().get_by_id(session.event_id)
    if not event or question_index >= len(event.question_ids):
        return None

    # Auto-lock if not already locked
    if question_index not in session.locked_indices:
        lock_question(session_id, question_index, username)
        # Refresh session after lock
        session = live_store.get_session(session_id)

    # Load the question for evaluation
    question_id = event.question_ids[question_index]
    question = get_question_store().get_by_id(question_id)
    if not question:
        return None

    # Get all answers for this question
    answers = live_store.get_answers(session_id, question_index)

    # Batch evaluate all answers
    eval_items = []
    for ans in answers:
        eval_items.append((question.question, question.answer, ans.answer_text, question.points))

    if eval_items:
        results = _evaluator.evaluate_batch(eval_items)
        for ans, result in zip(answers, results):
            live_store.update_answer(ans.answer_id, {
                "points_awarded": result.points_awarded,
                "max_points": result.max_points,
                "is_correct": result.is_correct,
                "explanation": result.explanation,
            })

    # Mark question as revealed
    new_revealed = list(session.revealed_indices) + [question_index]
    live_store.update_session(session_id, {"revealed_indices": new_revealed})

    return {
        "question_index": question_index,
        "correct_answer": question.answer,
        "results_count": len(answers),
    }


def finish_session(session_id: str, username: str) -> LiveSessionModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None
    if session.status == "finished":
        return session

    # Auto-lock the current question if active
    current_idx = session.current_question_index
    if current_idx >= 0 and current_idx not in session.locked_indices:
        lock_question(session_id, current_idx, username)

    return live_store.update_session(session_id, {"status": "finished"})


# ---------------------------------------------------------------------------
# Participant management
# ---------------------------------------------------------------------------

def join_session(
    join_code: str, display_name: str, user_id: str | None = None
) -> LiveParticipantModel | None:
    live_store = get_live_store()
    session = live_store.get_session_by_code(join_code.upper().strip())
    if not session:
        return None
    if session.status == "finished":
        return None

    participant = LiveParticipantModel(
        session_id=session.session_id,
        display_name=display_name,
        user_id=user_id,
    )
    if live_store.add_participant(participant):
        return participant
    return None


def get_participants(session_id: str) -> list[LiveParticipantModel]:
    return get_live_store().get_participants(session_id)


# ---------------------------------------------------------------------------
# Answer management
# ---------------------------------------------------------------------------

def override_answer_points(
    session_id: str, answer_id: str, points: float, username: str
) -> LiveAnswerModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.created_by != username:
        return None

    # Read the answer to validate ownership and get max_points
    answer = live_store.update_answer(answer_id, {})
    if not answer or answer.session_id != session_id:
        return None

    max_pts = answer.max_points if answer.max_points is not None else 1
    clamped = max(0.0, min(float(points), float(max_pts)))
    is_correct = clamped > 0

    return live_store.update_answer(answer_id, {
        "points_awarded": clamped,
        "is_correct": is_correct,
    })


def submit_answer(
    session_id: str,
    participant_id: str,
    question_index: int,
    answer_text: str,
) -> LiveAnswerModel | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session or session.status != "active":
        return None

    # Players can only answer the current question
    if question_index != session.current_question_index:
        return None

    # Reject if question is already locked
    if question_index in session.locked_indices:
        return None

    answer = LiveAnswerModel(
        session_id=session_id,
        participant_id=participant_id,
        question_index=question_index,
        answer_text=answer_text,
    )
    if live_store.save_answer(answer):
        return answer
    return None


# ---------------------------------------------------------------------------
# State & Leaderboard
# ---------------------------------------------------------------------------

def get_leaderboard(session_id: str) -> list[dict]:
    live_store = get_live_store()
    participants = live_store.get_participants(session_id)
    all_answers = live_store.get_answers(session_id)

    # Aggregate scores per participant
    scores: dict[str, float] = {}
    for ans in all_answers:
        if ans.points_awarded is not None:
            scores[ans.participant_id] = scores.get(ans.participant_id, 0) + ans.points_awarded

    participant_map = {p.participant_id: p for p in participants}
    board = []
    for pid, score in scores.items():
        p = participant_map.get(pid)
        if p:
            board.append({
                "participant_id": pid,
                "display_name": p.display_name,
                "score": score,
            })

    # Include participants with 0 score
    for p in participants:
        if p.participant_id not in scores:
            board.append({
                "participant_id": p.participant_id,
                "display_name": p.display_name,
                "score": 0,
            })

    board.sort(key=lambda x: x["score"], reverse=True)
    return board


def get_session_state(
    session_id: str, participant_id: str | None = None, is_presenter: bool = False
) -> dict | None:
    live_store = get_live_store()
    session = live_store.get_session(session_id)
    if not session:
        return None

    event = get_event_store().get_by_id(session.event_id)
    if not event:
        return None

    total_questions = len(event.question_ids)
    participants = live_store.get_participants(session_id)

    # Build current question data
    current_question = None
    current_idx = session.current_question_index
    if 0 <= current_idx < total_questions:
        qid = event.question_ids[current_idx]
        q = get_question_store().get_by_id(qid)
        if q:
            media_url = get_media_store().get_url(q.media_path) if q.media_path else None
            current_question = {
                "question_index": current_idx,
                "question": q.question if (session.show_questions_on_devices or is_presenter) else None,
                "media_path": media_url,
                "media_text": q.media_text,
                "points": q.points,
                "is_locked": current_idx in session.locked_indices,
                "is_revealed": current_idx in session.revealed_indices,
            }

    # Build revealed answers (correct answers for revealed questions)
    revealed_answers = {}
    for idx in session.revealed_indices:
        if 0 <= idx < total_questions:
            qid = event.question_ids[idx]
            q = get_question_store().get_by_id(qid)
            if q:
                revealed_answers[str(idx)] = {"correct_answer": q.answer, "points": q.points}

    state = {
        "session_id": session.session_id,
        "event_id": session.event_id,
        "event_name": event.name,
        "join_code": session.join_code,
        "status": session.status,
        "current_question_index": current_idx,
        "total_questions": total_questions,
        "show_questions_on_devices": session.show_questions_on_devices,
        "locked_indices": session.locked_indices,
        "revealed_indices": session.revealed_indices,
        "current_question": current_question,
        "revealed_answers": revealed_answers,
        "participants": [
            {"participant_id": p.participant_id, "display_name": p.display_name}
            for p in participants
        ],
        "leaderboard": get_leaderboard(session_id),
    }

    # Participant-specific data: their own answers
    if participant_id:
        my_answers = live_store.get_participant_answers(session_id, participant_id)
        state["my_answers"] = {}
        for ans in my_answers:
            entry = {
                "answer_text": ans.answer_text,
                "is_locked": ans.is_locked,
            }
            if ans.points_awarded is not None:
                entry["points_awarded"] = ans.points_awarded
                entry["max_points"] = ans.max_points
                entry["is_correct"] = ans.is_correct
                entry["explanation"] = ans.explanation
            state["my_answers"][str(ans.question_index)] = entry

    # Presenter-specific data: all answers for current question + answer counts
    if is_presenter:
        # Answer counts per question (how many participants answered)
        all_answers = live_store.get_answers(session_id)
        answer_counts = {}
        for ans in all_answers:
            idx = str(ans.question_index)
            answer_counts[idx] = answer_counts.get(idx, 0) + 1
        state["answer_counts"] = answer_counts

        # All answers for current question
        if current_idx >= 0:
            q_answers = live_store.get_answers(session_id, current_idx)
            participant_map = {p.participant_id: p.display_name for p in participants}
            state["current_answers"] = [
                {
                    "answer_id": a.answer_id,
                    "participant_id": a.participant_id,
                    "display_name": participant_map.get(a.participant_id, "?"),
                    "answer_text": a.answer_text,
                    "is_locked": a.is_locked,
                    "points_awarded": a.points_awarded,
                    "max_points": a.max_points,
                    "is_correct": a.is_correct,
                }
                for a in q_answers
            ]

    return state
