def get_random_question(seen_ids=None, filters=None):
    from backend.services.question_service import get_random_question_filtered
    q = get_random_question_filtered(seen_ids or [], filters or {})
    return q.model_dump(mode="json") if q else None


def get_all_questions():
    from backend.services.question_service import get_all_questions as _svc_get_all
    return [q.model_dump(mode="json") for q in _svc_get_all(limit=None)]


def add_question(question, answer, added_by, question_topic=None, question_source=None, answer_source=None,
                 media_file=None, language=None, incorrect_answers=None, tags=None, review_status=None):
    from backend.services.question_service import create_question as _svc_create
    payload = {
        "question": question,
        "answer": answer,
        "added_by": added_by,
        "question_topic": question_topic,
        "question_source": question_source,
        "answer_source": answer_source,
        "language": language,
        "incorrect_answers": incorrect_answers or [],
        "tags": tags or [],
        "review_status": review_status if review_status is not None else False,
    }
    if media_file:
        payload["media_file"] = media_file
    created = _svc_create(payload)
    return created.question_id if created else None


def delete_question(question_id, question_topic=None):
    from backend.services.question_service import delete_question as _svc_delete
    return _svc_delete(question_id)


def approve_question(question_id, question_topic=None):
    from backend.services.question_service import update_question as _svc_update
    return bool(_svc_update(question_id, {"review_status": True}))


def reject_question(question_id, question_topic=None):
    from backend.services.question_service import update_question as _svc_update
    return bool(_svc_update(question_id, {"review_status": False}))


def get_question_metadata():
    from backend.services.question_service import get_all_questions as _svc_get_all
    items = _svc_get_all({"review_status": True}, limit=None)
    languages = sorted({q.language for q in items if q.language})
    topics = sorted({q.question_topic for q in items if q.question_topic})
    tags = sorted({tag for q in items for tag in (q.tags or [])})
    return {"languages": languages, "topics": topics, "tags": tags}


__all__ = [
    "get_random_question",
    "get_all_questions",
    "add_question",
    "delete_question",
    "approve_question",
    "reject_question",
    "get_question_metadata",
]
