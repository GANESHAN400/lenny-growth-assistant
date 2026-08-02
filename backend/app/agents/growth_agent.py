"""Lenny Growth Agent - orchestrates skills, RAG, and LLM calls.

Three Skills:
  1. Q&A       - RAG-grounded answers strictly from Lenny's transcripts
  2. Ship30    - Ship30for30 style essay generation (~1250 words)
  3. Artifact  - Generates HTML/CSS or Markdown artifacts with an in-app viewer
"""
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

from loguru import logger

from app.prompts.system import get_system_prompt, get_title_generation_prompt
from app.providers.base import BaseLLMProvider, ChatMessage, StreamChunk
from app.rag.retriever import BM25Retriever, format_retrieved_context

# ────────────────────────────────────────────────────────────────
# Skill prompts
# ────────────────────────────────────────────────────────────────

QA_SKILL_PROMPT = """You are answering a question STRICTLY based on Lenny's podcast transcripts.

## Retrieved Context from Lenny's Transcripts
{context}

## Instructions
- Answer ONLY using insights from the context above
- Quote or paraphrase specific insights from the transcripts
- If the context doesn't contain enough information, say so clearly
- Reference specific episodes/guests when possible
- Be specific and actionable, not generic

## User Question
{question}

## Your Answer (grounded in the transcripts):"""

SHIP30_SKILL_PROMPT = """You are writing a Ship30for30-style essay based on Lenny's podcast insights.

## Retrieved Context from Lenny's Transcripts
{context}

## Ship30for30 Style Requirements
- **Hook**: Start with ONE powerful, pattern-interrupting sentence that stops the reader cold
- **Opening**: 2-3 sentences expanding the hook into the core tension or insight
- **Body**: 4-6 main sections, each with:
  - A bold subheading
  - 2-4 bullet points with specific, concrete details
  - Numbers, percentages, and real company examples when possible
- **Length**: Approximately 1,250 words
- **Format**: Heavy use of bullet points, bold text, short paragraphs (2-3 sentences max)
- **Skimmability**: Every section should deliver standalone value when skimmed
- **Ending**: Clear takeaway/call-to-action in 2-3 sentences

## Topic
{topic}

## Write the complete Ship30for30 essay now:"""

ARTIFACT_SKILL_PROMPT = """You are generating a {artifact_type} artifact based on the conversation context.

## Context
{context}

## Requirements
- Generate a complete, self-contained {artifact_type} artifact
- For HTML: Include full HTML, inline CSS, and any necessary inline JavaScript
- For Markdown: Use rich markdown with headers, tables, code blocks, and formatting
- Make it visually impressive and production-ready
- The artifact should directly address: {request}

## IMPORTANT: Wrap your artifact in these exact markers:
<ARTIFACT_START type="{artifact_type}">
[Your complete artifact here]
</ARTIFACT_START>

Generate the artifact now:"""

SKILL_DETECTION_PROMPT = """Analyze this user message and determine which skill to use.

User message: "{message}"

Classify into exactly one skill:
- "qa": User is asking a question about product growth, wanting information from Lenny's transcripts
- "ship30": User wants content written in Ship30for30 essay format, or asks to "write an essay", "create content", "write a post"
- "artifact": User wants to generate an HTML page, UI component, markdown document, template, or visual artifact
- "chat": General conversation, follow-up, or clarification (use regular chat)

Respond with JSON only: {{"skill": "qa"|"ship30"|"artifact"|"chat", "artifact_type": "html"|"markdown"|null}}"""


# ────────────────────────────────────────────────────────────────
# Agent result dataclass
# ────────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    content: str
    skill_used: str
    artifact_type: str | None = None
    artifact_content: str | None = None


@dataclass
class AgentStreamEvent:
    type: str  # "token" | "metadata" | "done" | "error"
    content: str = ""
    skill: str = "chat"
    artifact_type: str | None = None
    error: str | None = None


# ────────────────────────────────────────────────────────────────
# Growth Agent
# ────────────────────────────────────────────────────────────────

class GrowthAgent:
    """Lenny Growth Agent with Q&A, Ship30, and Artifact skills."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        retriever: BM25Retriever | None = None,
    ) -> None:
        self.provider = provider
        self.retriever = retriever

    async def detect_skill(
        self, message: str, forced_skill: str | None = None
    ) -> tuple[str, str | None]:
        """Detect which skill to use. Returns (skill, artifact_type)."""
        if forced_skill:
            artifact_type = "html" if forced_skill == "artifact" else None
            return forced_skill, artifact_type

        # Check for explicit artifact request keywords
        lower = message.lower()
        if any(k in lower for k in ["html", "css", "webpage", "ui component", "landing page", "create a page"]):
            return "artifact", "html"
        if any(k in lower for k in ["markdown document", "create a doc", "write a document", "generate a report"]):
            return "artifact", "markdown"
        if any(k in lower for k in ["ship30", "essay", "write a post", "write an article", "atomic essay"]):
            return "ship30", None

        # Use LLM for nuanced detection
        try:
            detection_prompt = SKILL_DETECTION_PROMPT.format(message=message[:500])
            result = await self.provider.chat(
                messages=[ChatMessage(role="user", content=detection_prompt)],
                temperature=0.1,
                max_tokens=100,
            )
            # Parse JSON response
            # Find JSON in response
            json_match = re.search(r'\{[^}]+\}', result)
            if json_match:
                parsed = json.loads(json_match.group())
                skill = parsed.get("skill", "qa")
                artifact_type = parsed.get("artifact_type")
                return skill, artifact_type
        except Exception as e:
            logger.warning(f"Skill detection failed, defaulting to qa: {e}")

        return "qa", None

    def _get_context(self, query: str, top_k: int = 5) -> str:
        """Retrieve relevant context from the RAG index."""
        if not self.retriever or not self.retriever.is_loaded:
            return "No transcript context available."
        results = self.retriever.retrieve(query, top_k=top_k)
        return format_retrieved_context(results, max_tokens=2000)

    def _build_messages(
        self,
        history: list[ChatMessage],
        system_override: str | None = None,
    ) -> list[ChatMessage]:
        """Build the full message list with system prompt."""
        system = system_override or get_system_prompt()
        return [ChatMessage(role="system", content=system)] + history

    async def stream_response(
        self,
        user_message: str,
        history: list[ChatMessage],
        skill: str | None = None,
    ) -> AsyncIterator[AgentStreamEvent]:
        """Stream a response with the appropriate skill."""
        # Detect skill
        detected_skill, artifact_type = await self.detect_skill(user_message, skill)

        # Emit metadata event
        yield AgentStreamEvent(
            type="metadata",
            skill=detected_skill,
            artifact_type=artifact_type,
        )

        try:
            if detected_skill == "qa":
                async for event in self._qa_stream(user_message, history):
                    yield event

            elif detected_skill == "ship30":
                async for event in self._ship30_stream(user_message, history):
                    yield event

            elif detected_skill == "artifact":
                async for event in self._artifact_stream(
                    user_message, history, artifact_type or "html"
                ):
                    yield event

            else:  # "chat" - regular conversation
                async for event in self._chat_stream(user_message, history):
                    yield event

        except Exception as e:
            logger.error(f"Agent error: {e}")
            yield AgentStreamEvent(type="error", error=str(e))

        yield AgentStreamEvent(type="done", skill=detected_skill, artifact_type=artifact_type)

    async def _qa_stream(
        self, question: str, history: list[ChatMessage]
    ) -> AsyncIterator[AgentStreamEvent]:
        """Q&A skill - RAG-grounded answers."""
        context = self._get_context(question, top_k=6)
        prompt = QA_SKILL_PROMPT.format(context=context, question=question)
        messages = self._build_messages(
            history[-8:],  # Keep last 8 messages for context
            system_override=get_system_prompt(),
        )
        messages.append(ChatMessage(role="user", content=prompt))

        async for chunk in self.provider.chat_stream(messages, temperature=0.3):
            if chunk.content:
                yield AgentStreamEvent(type="token", content=chunk.content, skill="qa")

    async def _ship30_stream(
        self, topic: str, history: list[ChatMessage]
    ) -> AsyncIterator[AgentStreamEvent]:
        """Ship30for30 skill - essay generation."""
        context = self._get_context(topic, top_k=8)
        prompt = SHIP30_SKILL_PROMPT.format(context=context, topic=topic)
        messages = self._build_messages(history[-4:])
        messages.append(ChatMessage(role="user", content=prompt))

        async for chunk in self.provider.chat_stream(
            messages, temperature=0.7, max_tokens=3000
        ):
            if chunk.content:
                yield AgentStreamEvent(type="token", content=chunk.content, skill="ship30")

    async def _artifact_stream(
        self, request: str, history: list[ChatMessage], artifact_type: str
    ) -> AsyncIterator[AgentStreamEvent]:
        """Artifact skill - generate HTML/CSS or Markdown artifacts."""
        context = self._get_context(request, top_k=4)
        prompt = ARTIFACT_SKILL_PROMPT.format(
            artifact_type=artifact_type,
            context=context,
            request=request,
        )
        messages = self._build_messages(history[-6:])
        messages.append(ChatMessage(role="user", content=prompt))

        full_content = ""
        async for chunk in self.provider.chat_stream(
            messages, temperature=0.5, max_tokens=4000
        ):
            if chunk.content:
                full_content += chunk.content
                yield AgentStreamEvent(
                    type="token",
                    content=chunk.content,
                    skill="artifact",
                    artifact_type=artifact_type,
                )

        # Extract artifact content from markers
        artifact_match = re.search(
            r"<ARTIFACT_START[^>]*>(.*?)</ARTIFACT_START>",
            full_content,
            re.DOTALL,
        )
        if artifact_match:
            yield AgentStreamEvent(
                type="artifact_ready",
                content=artifact_match.group(1).strip(),
                skill="artifact",
                artifact_type=artifact_type,
            )

    async def _chat_stream(
        self, message: str, history: list[ChatMessage]
    ) -> AsyncIterator[AgentStreamEvent]:
        """Regular chat - general conversation."""
        messages = self._build_messages(history[-10:])
        messages.append(ChatMessage(role="user", content=message))

        async for chunk in self.provider.chat_stream(messages, temperature=0.7):
            if chunk.content:
                yield AgentStreamEvent(type="token", content=chunk.content, skill="chat")

    async def generate_session_title(self, first_message: str, response: str) -> str:
        """Generate a concise title for the chat session."""
        snippet = f"User: {first_message[:200]}\nAssistant: {response[:200]}"
        prompt = get_title_generation_prompt(snippet)
        try:
            title = await self.provider.chat(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.3,
                max_tokens=30,
            )
            return title.strip().strip('"').strip("'")[:60] or "Growth Strategy Chat"
        except Exception:
            return "Growth Strategy Chat"
