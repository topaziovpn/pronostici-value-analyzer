from playwright.sync_api import sync_playwright
import hashlib

def slug(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]

def fetch_page(url: str, headless=True, timeout_ms=30000):
    """
    Usa Playwright per navigare sull'URL e restituire HTML e testo.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page.set_default_timeout(timeout_ms)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1500)
            html = page.content()
            text = page.locator("body").inner_text(timeout=timeout_ms)
            return {"url": url, "html": html, "text": text}
        except Exception as e:
            print(f"[Playwright] Errore fetch su {url}: {e}")
            return None
        finally:
            browser.close()
