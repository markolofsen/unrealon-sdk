"""
Parser notifications via Telegram.

Generic notifier class - credentials must be provided at initialization.

Usage:
    from unrealon.parsers.utils import ParserNotifier

    notifier = ParserNotifier(
        source_code="myparser",
        bot_token="123:ABC...",
        chat_id="-123456",
    )

    notifier.started(pages=10)
    notifier.progress(50, 100)
    notifier.completed(items=100, success=98, failed=2)
"""
from __future__ import annotations

import logging
from typing import Any

from sdkrouter_tools.telegram import (
    MessagePriority,
    ParseMode,
    TelegramSender,
)

log = logging.getLogger(__name__)


class ParserNotifier:
    """
    Telegram notifier for parser status updates.

    Sends formatted messages about parser progress, completion, and errors.
    """

    def __init__(
        self,
        source_code: str,
        bot_token: str,
        chat_id: str,
        *,
        fail_silently: bool = True,
    ):
        """
        Initialize notifier.

        Args:
            source_code: Parser identifier for message prefix
            bot_token: Telegram bot token
            chat_id: Telegram chat ID (can be negative for groups)
            fail_silently: If True, swallow send errors
        """
        self.source_code = source_code
        self.fail_silently = fail_silently
        self.sender = TelegramSender(bot_token=bot_token, chat_id=chat_id)

    def _send(self, text: str, priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        """Send message. Returns True if sent successfully."""
        try:
            self.sender.send_message(
                text,
                parse_mode=ParseMode.HTML,
                priority=priority,
                fail_silently=self.fail_silently,
            )
            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            log.debug("Failed to send notification: %s", e)
            return False

    def started(self, pages: int = 0, limit: int = 0, **extra: Any) -> None:
        """Parser started."""
        parts = [f"<b>{self.source_code}</b> started"]
        if pages:
            parts.append(f"pages={pages}")
        if limit:
            parts.append(f"limit={limit}")
        for k, v in extra.items():
            parts.append(f"{k}={v}")
        self._send(f"🚀 {' | '.join(parts)}")

    def progress(self, current: int, total: int, **extra: Any) -> None:
        """Progress update."""
        pct = int(current / total * 100) if total else 0
        text = f"📊 <b>{self.source_code}</b>: {current}/{total} ({pct}%)"
        if extra:
            text += "\n" + " | ".join(f"{k}={v}" for k, v in extra.items())
        self._send(text, priority=MessagePriority.LOW)

    def completed(
        self,
        items: int,
        success: int = 0,
        failed: int = 0,
        photos: int = 0,
        duration: str = "",
    ) -> None:
        """Parser completed successfully."""
        parts = [f"items={items}"]
        if success:
            parts.append(f"success={success}")
        if failed:
            parts.append(f"failed={failed}")
        if photos:
            parts.append(f"photos={photos}")
        if duration:
            parts.append(f"duration={duration}")
        self._send(f"✅ <b>{self.source_code}</b> done\n{' | '.join(parts)}")

    def failed(self, error: str, **context: Any) -> None:
        """Parser failed."""
        text = f"❌ <b>{self.source_code}</b> failed\n{error}"
        if context:
            text += "\n" + " | ".join(f"{k}={v}" for k, v in context.items())
        self._send(text, priority=MessagePriority.HIGH)

    def warning(self, message: str, **context: Any) -> None:
        """Warning message."""
        text = f"⚠️ <b>{self.source_code}</b>\n{message}"
        if context:
            text += "\n" + " | ".join(f"{k}={v}" for k, v in context.items())
        self._send(text, priority=MessagePriority.HIGH)

    def info(self, message: str, **data: Any) -> None:
        """Info message."""
        text = f"ℹ️ <b>{self.source_code}</b>\n{message}"
        if data:
            text += "\n" + " | ".join(f"{k}={v}" for k, v in data.items())
        self._send(text)
