# utils/helpers.py
import re
import time
from playwright.sync_api import Locator

# ---------------- CLEANING UTILS ----------------

def clean_text(text: str) -> str:
    """Normalize whitespace and strip text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def unique_list(items):
    """Return unique items while preserving order."""
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------- SAFE ACCESS HELPERS ----------------

def safe_get_text(locator: Locator) -> str:
    """Return text_content safely without raising errors."""
    try:
        if locator.count() > 0:
            txt = locator.first.text_content()
            return clean_text(txt)
    except:
        pass
    return ""


def safe_get_attribute(locator: Locator, attr: str) -> str:
    """Safely get an attribute."""
    try:
        if locator.count() > 0:
            return locator.first.get_attribute(attr) or ""
    except:
        pass
    return ""


def visible_text_or_empty(locator: Locator) -> str:
    """Returns visible text if available, else empty string."""
    try:
        if locator.count() > 0:
            text = locator.first.inner_text()
            return clean_text(text)
    except:
        pass
    return ""


# ---------------- SCROLL HELPERS ----------------

def scroll_page(page, times=6, delay=1.5, amount=3000):
    """Scroll the page downward several times."""
    for i in range(times):
        print(f"[DEBUG] Scrolling {i+1}/{times}…")
        page.mouse.wheel(0, amount)
        time.sleep(delay)


def wait_for_stable_scroll(page, steps=6):
    """
    Keeps scrolling until scrolling no longer moves the page
    (useful when FB throttles or caps results).
    """
    last_height = None

    for i in range(steps):
        page.mouse.wheel(0, 3000)
        time.sleep(1.5)

        height = page.evaluate("document.body.scrollHeight")

        print(f"[DEBUG] Scroll iteration {i+1}, height={height}")

        if height == last_height:
            print("[INFO] Page height stabilized — no more posts loading.")
            break

        last_height = height


# ---------------- OPTIONAL: OCR HELPERS (IF YOU WANT) ----------------

try:
    import pytesseract
    from PIL import Image
    import io

    def screenshot_to_text(page) -> str:
        """
        Take a viewport screenshot and return OCR text.
        """
        png = page.screenshot(full_page=False)
        img = Image.open(io.BytesIO(png))
        return pytesseract.image_to_string(img)

except Exception as e:
    # If OCR isn't installed, keep the scraper functional.
    def screenshot_to_text(page):
        print("[WARNING] OCR helpers unavailable (pytesseract not installed).")
        return ""
