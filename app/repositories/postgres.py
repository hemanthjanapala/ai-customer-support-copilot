"""PostgreSQL persistence (Phase 2).

Implements the schema from ARCHITECTURE.md section 8:
conversations, messages, model_requests.

The store accepts any SQLAlchemy URL. PostgreSQL is used in production
(via docker compose); SQLite is used only for fast unit tests.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.records import ModelCallRecord
from app.models.schemas import Message


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class DBMessage(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ModelRequest(Base):
    __tablename__ = "model_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    request_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True
    )
    stage: Mapped[str] = mapped_column(String(16))  # intent | response
    model: Mapped[str] = mapped_column(String(64))
    prompt_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))  # ok | timeout | error | fallback
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PostgresConversationService:
    """Same interface as the in-memory ConversationService, backed by SQL."""

    def __init__(self, db_url: str, history_window: int | None = None) -> None:
        kwargs: dict = {}
        if db_url.startswith("sqlite"):
            # Single shared connection so :memory: tables survive across sessions.
            kwargs = {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            }
        self._engine = create_engine(db_url, **kwargs)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._history_window = history_window or settings.history_window

    @staticmethod
    def _to_message(row: DBMessage) -> Message:
        created = row.created_at
        iso = created.isoformat() if isinstance(created, datetime) else str(created)
        return Message(role=row.role, content=row.content, intent=row.intent, created_at=iso)  # type: ignore[arg-type]

    def get_or_create(self, conversation_id: str | None, customer_id: str) -> str:
        import uuid as _uuid

        with self._Session() as s:
            if conversation_id:
                existing = s.get(Conversation, conversation_id)
                if existing:
                    return conversation_id
                conv_id = conversation_id
            else:
                conv_id = f"conv-{_uuid.uuid4().hex[:8]}"
            s.add(Conversation(id=conv_id, customer_id=customer_id))
            s.commit()
            return conv_id

    def add_message(
        self, conversation_id: str, role: str, content: str, intent: str | None = None
    ) -> None:
        with self._Session() as s:
            s.add(
                DBMessage(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    intent=intent,
                )
            )
            s.commit()

    def save_exchange(
        self, conversation_id: str, user_content: str, assistant_content: str, intent: str
    ) -> None:
        """Write user + assistant messages atomically (one transaction)."""
        with self._Session() as s:
            s.add(
                DBMessage(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_content,
                    intent=intent,
                )
            )
            s.add(
                DBMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    intent=intent,
                )
            )
            s.commit()

    def _messages_query(self, conversation_id: str, limit: int | None = None):
        stmt = (
            select(DBMessage)
            .where(DBMessage.conversation_id == conversation_id)
            .order_by(DBMessage.id)
        )
        return stmt

    def history(self, conversation_id: str) -> list[Message]:
        with self._Session() as s:
            rows = s.execute(self._messages_query(conversation_id)).scalars().all()
            return [self._to_message(r) for r in rows[-self._history_window :]]

    def all_messages(self, conversation_id: str) -> list[Message] | None:
        with self._Session() as s:
            if s.get(Conversation, conversation_id) is None:
                return None
            rows = s.execute(self._messages_query(conversation_id)).scalars().all()
            return [self._to_message(r) for r in rows]

    def customer_of(self, conversation_id: str) -> str | None:
        with self._Session() as s:
            conv = s.get(Conversation, conversation_id)
            return None if conv is None else conv.customer_id

    def log_model_call(
        self, conversation_id: str | None, record: ModelCallRecord
    ) -> None:
        with self._Session() as s:
            s.add(
                ModelRequest(
                    conversation_id=conversation_id,
                    request_id=record.request_id,
                    idempotency_key=record.idempotency_key,
                    stage=record.stage,
                    model=record.model,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    latency_ms=record.latency_ms,
                    status=record.status,
                )
            )
            s.commit()
