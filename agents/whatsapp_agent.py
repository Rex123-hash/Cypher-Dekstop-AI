"""
WhatsApp Agent — sends messages via Playwright on WhatsApp Web.
"""
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


class WhatsAppAgent:
    name = "whatsapp"

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._ready = False

    async def initialize(self):
        """Launch WhatsApp Web — user must scan QR on first launch."""
        if self._ready:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir="E:/NEXUS/data/whatsapp_session",
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        pages = self._browser.pages
        self._page = pages[0] if pages else await self._browser.new_page()
        await self._page.goto("https://web.whatsapp.com")

        # Wait for WhatsApp to load (up to 60s for QR scan)
        try:
            await self._page.wait_for_selector(
                'div[data-testid="chat-list"]', timeout=90_000
            )
            self._ready = True
        except Exception:
            self._ready = False

    async def send_message(self, contact: str, message: str) -> str:
        try:
            if not self._ready:
                await self.initialize()
            if not self._ready:
                return "WhatsApp Web failed to load. Please scan QR code first."

            # Search for contact
            search = await self._page.wait_for_selector(
                'div[data-testid="search-container"] input', timeout=10_000
            )
            await search.click()
            await search.fill(contact)
            await asyncio.sleep(1.5)

            # Click first result
            result = await self._page.wait_for_selector(
                'div[data-testid="cell-frame-container"]', timeout=5_000
            )
            await result.click()
            await asyncio.sleep(0.8)

            # Type and send message
            msg_box = await self._page.wait_for_selector(
                'div[data-testid="conversation-compose-box-input"]', timeout=5_000
            )
            await msg_box.click()
            await msg_box.fill(message)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(0.5)

            return f"WhatsApp message sent to {contact}: {message[:50]}{'...' if len(message) > 50 else ''}"
        except Exception as e:
            return f"WhatsApp error: {e}"

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._ready = False

    async def handle(self, command: str) -> str:
        # Pattern: "send [message] to [contact]" or "message [contact] [message]"
        send_match = re.search(
            r'send\s+(.+?)\s+to\s+(.+)', command, re.IGNORECASE
        )
        msg_match = re.search(
            r'(?:message|whatsapp)\s+(\w+)\s+(.+)', command, re.IGNORECASE
        )

        if send_match:
            message, contact = send_match.group(1), send_match.group(2)
            return await self.send_message(contact.strip(), message.strip())
        if msg_match:
            contact, message = msg_match.group(1), msg_match.group(2)
            return await self.send_message(contact.strip(), message.strip())

        return (
            "WhatsApp command not understood. Try: "
            "'send [message] to [contact]' or 'message [contact] [text]'"
        )


whatsapp_agent = WhatsAppAgent()
