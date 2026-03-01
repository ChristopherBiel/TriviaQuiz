from __future__ import annotations

from flask import Blueprint, Response, abort, stream_with_context

from backend.storage import get_media_store

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.route("/<path:object_key>", methods=["GET"])
def fetch_media(object_key: str):
    store = get_media_store()
    if not hasattr(store, "download"):
        abort(404)
    try:
        body, content_type, content_length = store.download(object_key)
    except FileNotFoundError:
        abort(404)

    def generate():
        for chunk in body.iter_chunks(chunk_size=1024 * 1024):
            if chunk:
                yield chunk

    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if content_length is not None:
        headers["Content-Length"] = str(content_length)

    return Response(stream_with_context(generate()), headers=headers)
