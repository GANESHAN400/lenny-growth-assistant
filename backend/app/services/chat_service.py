"""Chat service - orchestrates agent, RAG, and persistence for chat operations."""
import json
import re
from collections.abc import AsyncIterator
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.growth_agent import AgentStreamEvent, GrowthAgent
from app.models.chat_session import ChatSession
from app.models.message import ChatMessage as ChatMessageModel
from app.providers.base import BaseLLMProvider, ChatMessage
from app.providers import get_provider
from app.rag.retriever import get_retriever
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import ChatMessageRepository
from app.schemas.session import SessionCreate


class ChatService:
    """Orchestrates chat: session management, agent invocation, persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.session_repo = ChatSessionRepository(db)
        self.message_repo = ChatMessageRepository(db)

    def _get_provider(self, provider_name: str, model: str | None = None) -> BaseLLMProvider:
        """Get the appropriate LLM provider."""
        return get_provider(provider_name)

    def _build_history(self, messages: list[ChatMessageModel]) -> list[ChatMessage]:
        """Convert ORM messages to provider ChatMessage format."""
        return [
            ChatMessage(role=m.role, content=m.content)
            for m in messages
            if m.role in ("user", "assistant")
        ]

    async def stream_chat(
        self,
        session_id: UUID | None,
        user_message: str,
        provider_name: str = "ollama",
        model: str | None = None,
        skill: str | None = None,
    ) -> AsyncIterator[str]:
        """Main entry point for streaming chat.
        
        Yields Server-Sent Events (SSE) formatted strings.
        """
        # 1. Get or create session
        if session_id:
            session = self.session_repo.get_by_id(session_id)
            if not session:
                session = self.session_repo.create_session(
                    provider=provider_name,
                    model_name=model or "qwen2.5:7b",
                )
        else:
            model_name = model or ("qwen2.5:7b" if provider_name == "ollama" else "claude-3-5-haiku-20241022")
            session = self.session_repo.create_session(
                provider=provider_name,
                model_name=model_name,
            )

        session_id = session.id

        # Emit session metadata
        yield self._sse_event({
            "type": "session",
            "session_id": str(session_id),
        })

        # 2. Save user message
        self.message_repo.add_message(
            session_id=session_id,
            role="user",
            content=user_message,
        )

        # 3. Load history
        history_msgs = self.message_repo.get_recent_messages(session_id, limit=20)
        # Remove the just-added user message (it's the last one)
        history = self._build_history(history_msgs[:-1])

        # 4. Initialize agent
        provider = self._get_provider(provider_name, model)
        retriever = get_retriever()
        agent = GrowthAgent(provider=provider, retriever=retriever)

        # 5. Stream agent response
        full_response = ""
        detected_skill = "chat"
        detected_artifact_type: str | None = None
        artifact_content: str | None = None

        try:
            async for event in agent.stream_response(user_message, history, skill):
                if event.type == "metadata":
                    detected_skill = event.skill
                    detected_artifact_type = event.artifact_type
                    yield self._sse_event({
                        "type": "metadata",
                        "skill": detected_skill,
                        "artifact_type": detected_artifact_type,
                        "session_id": str(session_id),
                    })

                elif event.type == "token":
                    full_response += event.content
                    yield self._sse_event({
                        "type": "token",
                        "content": event.content,
                    })

                elif event.type == "artifact_ready":
                    artifact_content = event.content
                    yield self._sse_event({
                        "type": "artifact_ready",
                        "content": event.content,
                        "artifact_type": event.artifact_type,
                    })

                elif event.type == "error":
                    yield self._sse_event({
                        "type": "error",
                        "error": event.error or "Unknown error",
                    })

                elif event.type == "done":
                    break

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield self._sse_event({"type": "error", "error": str(e)})

        # 6. Persist assistant response
        if full_response:
            # Extract artifact from response if markers present
            if not artifact_content:
                artifact_match = re.search(
                    r"<ARTIFACT_START[^>]*>(.*?)</ARTIFACT_START>",
                    full_response,
                    re.DOTALL,
                )
                if artifact_match:
                    artifact_content = artifact_match.group(1).strip()

            self.message_repo.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                skill_used=detected_skill,
                artifact_type=detected_artifact_type,
                artifact_content=artifact_content,
            )

            # 7. Auto-generate title if first response
            msg_count = self.message_repo.count_session_messages(session_id)
            if msg_count <= 2:  # Just user + assistant
                try:
                    title = await agent.generate_session_title(user_message, full_response)
                    self.session_repo.update_title(session, title)
                    yield self._sse_event({
                        "type": "title_update",
                        "title": title,
                        "session_id": str(session_id),
                    })
                except Exception as e:
                    logger.warning(f"Title generation failed: {e}")

        yield self._sse_event({"type": "done", "session_id": str(session_id)})

    def _sse_event(self, data: dict) -> str:
        """Format a dict as an SSE data line."""
        return f"data: {json.dumps(data)}\n\n"

    def get_history(self, session_id: UUID) -> list[ChatMessageModel]:
        """Get conversation history for a session."""
        return self.message_repo.get_session_messages(session_id)
