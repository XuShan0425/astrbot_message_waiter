import asyncio
import contextlib
from dataclasses import dataclass, field

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import CustomFilter
from astrbot.api.star import Context, Star, register


class WakeMessageFilter(CustomFilter):
    """Allow the handler only for messages that already woke AstrBot."""

    def filter(self, event: AstrMessageEvent, cfg: AstrBotConfig) -> bool:
        """Check whether AstrBot would normally process the message.

        Args:
            event: Incoming AstrBot message event.
            cfg: Active AstrBot configuration.

        Returns:
            ``True`` when the message is a private message, mention, or wake command.
        """
        return event.is_at_or_wake_command


@dataclass
class PendingMessage:
    """Track buffered text and the active debounce task for one conversation."""

    generation: int = 0
    texts: list[str] = field(default_factory=list)
    latest_event: AstrMessageEvent | None = None
    task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@register(
    "message_waiter",
    "Tong",
    "Wait for consecutive user messages and merge them before invoking AstrBot AI.",
    "0.1.0",
)
class MessageWaiter(Star):
    """Debounce consecutive messages so AstrBot replies after the user finishes."""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        """Initialize plugin state and configuration.

        Args:
            context: AstrBot plugin context.
            config: Plugin configuration loaded from ``_conf_schema.json``.
        """
        super().__init__(context)
        self.config = config
        self._pending: dict[str, PendingMessage] = {}
        self._closed = False

    @filter.event_message_type(filter.EventMessageType.ALL, priority=99999)
    @filter.custom_filter(WakeMessageFilter)
    async def wait_for_more_messages(self, event: AstrMessageEvent) -> None:
        """Buffer a normal AI message and let only the newest event continue.

        Args:
            event: Incoming AstrBot message event.
        """
        if self._closed or not self.config.get("enabled", True):
            return
        if event.get_extra("provider_request"):
            return

        text = event.get_message_str().strip()
        if not text:
            return
        if self.config.get("ignore_commands", True):
            prefixes = self.config.get("command_prefixes", ["/", "!"])
            if any(text.startswith(str(prefix)) for prefix in prefixes if prefix):
                return

        session_key = event.unified_msg_origin
        if event.is_group_chat():
            session_key = f"{session_key}:{event.get_sender_id()}"

        pending = self._pending.setdefault(session_key, PendingMessage())
        async with pending.lock:
            pending.generation += 1
            generation = pending.generation
            pending.texts.append(text)
            pending.latest_event = event
            if pending.task and not pending.task.done():
                pending.task.cancel()
            pending.task = asyncio.create_task(
                self._release_after_wait(session_key, pending, generation)
            )

        # The current pipeline is held here. A newer message cancels this task,
        # stops the older event, and becomes the only event allowed to call AI.
        try:
            await pending.task
        except asyncio.CancelledError:
            event.stop_event()

    async def _release_after_wait(
        self,
        session_key: str,
        pending: PendingMessage,
        generation: int,
    ) -> None:
        """Wait for silence, optionally check semantics, then release one event.

        Args:
            session_key: Conversation key, including sender ID for group chats.
            pending: Mutable pending state for the conversation.
            generation: Message generation owned by this task.
        """
        try:
            wait_seconds = max(float(self.config.get("wait_seconds", 2.5)), 0.1)
            await asyncio.sleep(wait_seconds)

            combined = "\n".join(pending.texts).strip()
            if self.config.get("semantic_check", False) and len(combined) >= int(
                self.config.get("semantic_min_chars", 6)
            ):
                complete = True
                try:
                    provider = None
                    provider_id = str(
                        self.config.get("semantic_provider_id", "")
                    ).strip()
                    if provider_id:
                        provider = self.context.get_provider_by_id(provider_id)
                    if provider is None and pending.latest_event is not None:
                        provider = await self.context.get_using_provider_async(
                            umo=pending.latest_event.unified_msg_origin
                        )
                    if provider is not None:
                        response = await provider.text_chat(
                            prompt=(
                                "Determine whether the user has finished entering a message. "
                                "Reply with exactly COMPLETE or INCOMPLETE. Treat an unfinished "
                                "sentence, trailing connector, open list, or explicit request to "
                                "wait as INCOMPLETE. Otherwise reply COMPLETE.\n\n"
                                f"User input:\n{combined}"
                            ),
                            system_prompt=(
                                "You are a strict message-completion classifier. Output only "
                                "COMPLETE or INCOMPLETE."
                            ),
                        )
                        answer = (response.completion_text or "").strip().upper()
                        complete = answer.startswith("COMPLETE")
                except Exception:
                    logger.warning(
                        "Semantic completion check failed; releasing buffered message.",
                        exc_info=True,
                    )

                if not complete:
                    max_wait_seconds = max(
                        float(self.config.get("max_wait_seconds", 10.0)),
                        wait_seconds,
                    )
                    extension = min(
                        max(
                            float(self.config.get("semantic_extend_seconds", 2.0)),
                            0.1,
                        ),
                        max_wait_seconds - wait_seconds,
                    )
                    if extension > 0:
                        await asyncio.sleep(extension)

            async with pending.lock:
                if generation != pending.generation or pending.latest_event is None:
                    return
                event = pending.latest_event
                combined = "\n".join(pending.texts).strip()
                event.message_str = combined
                event.message_obj.message_str = combined
                self._pending.pop(session_key, None)
                logger.debug(
                    "Released %s buffered message part(s) for session %s.",
                    len(pending.texts),
                    event.unified_msg_origin,
                )
        except asyncio.CancelledError:
            raise

    async def terminate(self) -> None:
        """Cancel pending debounce tasks when the plugin is unloaded."""
        self._closed = True
        tasks = [state.task for state in self._pending.values() if state.task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        for task in tasks:
            if task:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._pending.clear()
