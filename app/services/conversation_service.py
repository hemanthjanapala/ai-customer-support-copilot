"""Conversation persistence.

Phase 1: in-memory store so the API runs without Postgres.
Phase 2: PostgresConversationService (app/repositories/postgres.py) is used
automatically when DATABASE_URL is set. Both stores share the same interface.

The module-level `conversation_service` singleton is built once at import
from the current environment: DATABASE_URL set -> Postgres, otherwise
in-memory (tests and local dev without Docker).
"""

import time
import uuid

from app.config import settings
from app.models.records import ModelCallRecord
from app.models.schemas import Message


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ConversationService:
    """In-memory store. Same interface as PostgresConversationService."""

    def __init__(self, history_window: int = 10) -> None:
        self._store: dict[str, dict] = {}
        self._model_calls: list[tuple[str | None, ModelCallRecord]] = []
        self._history_window = history_window

    def get_or_create(self, conversation_id: str | None, customer_id: str) -> str:
        if conversation_id and conversation_id in self._store:
            return conversation_id
        new_id = conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        self._store.setdefault(new_id, {"customer_id": customer_id, "messages": []})
        return new_id

    def add_message(
        self, conversation_id: str, role: str, content: str, intent: str | None = None
    ) -> None:
        self._store[conversation_id]["messages"].append(
            Message(role=role, content=content, intent=intent, created_at=_now_iso())  # type: ignore[arg-type]
        )

    def save_exchange(
        self, conversation_id: str, user_content: str, assistant_content: str, intent: str
    ) -> None:
        self.add_message(conversation_id, "user", user_content, intent)
        self.add_message(conversation_id, "assistant", assistant_content, intent)

    def history(self, conversation_id: str) -> list[Message]:
        return self._store[conversation_id]["messages"][-self._history_window :]

    def all_messages(self, conversation_id: str) -> list[Message] | None:
        conv = self._store.get(conversation_id)
        return None if conv is None else conv["messages"]

    def customer_of(self, conversation_id: str) -> str | None:
        conv = self._store.get(conversation_id)
        return None if conv is None else conv["customer_id"]

    def log_model_call(
        self, conversation_id: str | None, record: ModelCallRecord
    ) -> None:
        self._model_calls.append((conversation_id, record))


def build_conversation_service():
    """Factory: Postgres when DATABASE_URL is set, else in-memory."""
    if settings.database_url:
        from app.repositories.postgres import PostgresConversationService

        return PostgresConversationService(settings.database_url)
    return ConversationService(history_window=settings.history_window)


conversation_service = build_conversation_service()
