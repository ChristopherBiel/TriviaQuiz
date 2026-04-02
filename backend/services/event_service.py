from backend.models.event import EventModel
from backend.storage import get_event_store, get_question_store, get_media_store


def create_event(data: dict, username: str) -> EventModel | None:
    data["created_by"] = username
    event = EventModel(**data)
    success = get_event_store().add(event)
    return event if success else None


def get_event(event_id: str) -> EventModel | None:
    return get_event_store().get_by_id(event_id)


def can_see_event(event: EventModel, username: str | None, role: str) -> bool:
    """Return True if the user is allowed to see this event."""
    if event.is_published:
        return True
    if role == "admin":
        return True
    if username and event.created_by == username:
        return True
    return False


def list_events(
    filters: dict | None = None,
    limit: int = 50,
    offset: int = 0,
    username: str | None = None,
    role: str = "user",
) -> tuple[list[EventModel], int]:
    if role == "admin":
        return get_event_store().list(filters=filters, limit=limit, offset=offset)

    # For non-admins, fetch with is_published filter first
    pub_filters = dict(filters or {})
    pub_filters["is_published"] = True
    published, pub_total = get_event_store().list(
        filters=pub_filters, limit=limit, offset=offset,
    )

    # Also fetch the user's own unpublished events
    if username:
        own_filters = dict(filters or {})
        own_filters["created_by"] = username
        own_filters["is_published"] = False
        own_events, own_total = get_event_store().list(
            filters=own_filters, limit=limit, offset=0,
        )
    else:
        own_events, own_total = [], 0

    # Merge: own unpublished + published (deduplicated)
    seen_ids = {e.event_id for e in own_events}
    merged = list(own_events)
    for e in published:
        if e.event_id not in seen_ids:
            merged.append(e)
    # Sort by created_at descending
    merged.sort(key=lambda e: e.created_at, reverse=True)
    total = pub_total + own_total
    return merged[:limit], total


def update_event(
    event_id: str,
    updates: dict,
    username: str,
    role: str,
) -> EventModel | None:
    event = get_event_store().get_by_id(event_id)
    if not event:
        return None
    if event.created_by != username and role != "admin":
        return None
    return get_event_store().update(event_id, updates)


def delete_event(
    event_id: str,
    username: str,
    role: str,
    delete_questions: bool = False,
) -> bool:
    event_store = get_event_store()
    event = event_store.get_by_id(event_id)
    if not event:
        return False
    if event.created_by != username and role != "admin":
        return False

    if delete_questions and event.question_ids:
        question_store = get_question_store()
        media_store = get_media_store()
        for qid in event.question_ids:
            question = question_store.get_by_id(qid)
            if question and question.media_path:
                media_store.delete(question.media_path)
            question_store.delete(qid)

    return event_store.delete(event_id)


def add_question_to_event(event_id: str, question_id: str) -> bool:
    event_store = get_event_store()
    question_store = get_question_store()

    event = event_store.get_by_id(event_id)
    if not event:
        return False

    question = question_store.get_by_id(question_id)
    if not question:
        return False

    if question_id not in event.question_ids:
        new_ids = list(event.question_ids) + [question_id]
        event_store.update(event_id, {"question_ids": new_ids})

    question_store.update(question_id, {"event_id": event_id})
    return True


def remove_question_from_event(event_id: str, question_id: str) -> bool:
    event_store = get_event_store()
    question_store = get_question_store()

    event = event_store.get_by_id(event_id)
    if not event:
        return False

    if question_id in event.question_ids:
        new_ids = [qid for qid in event.question_ids if qid != question_id]
        event_store.update(event_id, {"question_ids": new_ids})

    question = question_store.get_by_id(question_id)
    if question and question.event_id == event_id:
        question_store.update(question_id, {"event_id": None})

    return True


def reorder_event_questions(event_id: str, question_ids: list[str]) -> bool:
    event_store = get_event_store()
    event = event_store.get_by_id(event_id)
    if not event:
        return False
    # Validate that the provided list is a permutation of the existing list
    if set(question_ids) != set(event.question_ids):
        return False
    event_store.update(event_id, {"question_ids": question_ids})
    return True


def get_event_questions(event_id: str):
    from backend.models.question import QuestionModel

    event = get_event_store().get_by_id(event_id)
    if not event:
        return []

    question_store = get_question_store()
    questions: list[QuestionModel] = []
    for qid in event.question_ids:
        q = question_store.get_by_id(qid)
        if q:
            questions.append(q)
    return questions
