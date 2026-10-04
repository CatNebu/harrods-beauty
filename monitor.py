"""
Моніторинг наявності Harrods Beauty Advent Calendar 2026.
Відкриває сторінку в headless-браузері (статус наявності сайт підвантажує
динамічно) і надсилає повідомлення в Telegram, якщо товар з'явився.
"""
import os
import re
import requests
from playwright.sync_api import sync_playwright

URL = os.environ.get(
    "PRODUCT_URL",
    "https://www.harrods.com/en-gb/p/harrods-of-london-the-harrods-beauty-advent-calendar-2026-000000000000284475",
)
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TEST_MODE = os.environ.get("TEST_MODE", "").lower() == "true"

IN_STOCK = re.compile(r"add to (bag|basket)", re.I)
OUT_OF_STOCK = re.compile(r"out of stock|sold out|notify me|email me when", re.I)
BLOCKED = re.compile(r"access denied|captcha|are you a robot|verify you are human", re.I)


def send(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )


def check() -> tuple[str, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
            ),
            locale="en-GB",
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)  # даємо сайту підвантажити статус
        body = page.inner_text("body")
        buttons = " | ".join(t.strip() for t in page.locator("button").all_inner_texts() if t.strip())
        browser.close()

    if BLOCKED.search(body):
        return "blocked", buttons
    if IN_STOCK.search(buttons) and not OUT_OF_STOCK.search(buttons):
        return "in_stock", buttons
    if OUT_OF_STOCK.search(body):
        return "out_of_stock", buttons
    return "unknown", buttons


def main() -> None:
    try:
        status, buttons = check()
    except Exception as e:  # noqa: BLE001
        status, buttons = "error", str(e)[:300]

    print(f"Status: {status}\nButtons: {buttons[:500]}")

    if status == "in_stock":
        send(f"🎄 Harrods Beauty Advent Calendar — В НАЯВНОСТІ!\nШвидше: {URL}")
    elif TEST_MODE:
        send(f"Тест моніторингу.\nСтатус: {status}\nКнопки на сторінці: {buttons[:300]}")


if __name__ == "__main__":
    main()
