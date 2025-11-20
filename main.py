import os
import time
import re
import json
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright
from openai import OpenAI

QUERY = "iso web designer"
SCROLL_PAGES = 6
SERVICE_ACCOUNT_PATH = "service_account.json"
MODEL = "gpt-4o-mini"   # or gpt-4.1 or gpt-5.1 if you want

# ---------------- HELPERS ----------------

def load_openai_key():
    with open(SERVICE_ACCOUNT_PATH, "r") as f:
        data = json.load(f)

    if "openai_key" not in data:
        raise KeyError(
            "No 'openai_key' found in service_account.json.\n"
            "Add:  \"openai_key\": \"sk-...\""
        )

    return data["openai_key"]


def clean_text(txt):
    if not txt:
        return ""
    return re.sub(r"\s+", " ", txt).strip()


# ---------------- COOKIE LOADING ----------------

def load_cookies(context):
    if not os.path.exists("cookies.json"):
        raise Exception("cookies.json not found! Run save_facebook_cookies.py first.")
    with open("cookies.json", "r") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    print("[INFO] Cookies loaded. Logged into Facebook.")


# ---------------- FACEBOOK SEARCH ----------------

def fb_search(page):
    from urllib.parse import quote_plus
    encoded = quote_plus(QUERY)
    url = f"https://www.facebook.com/search/posts/?q={encoded}"
    print(f"[ACTION] Opening search URL: {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(3)


# ---------------- OPENAI VISION ----------------

def call_openai_batch(images_b64, client):
    """
    Send ALL screenshots at once to OpenAI Vision.
    This saves a TON of credits.
    """

    print(f"\n[SENDING] {len(images_b64)} images → OpenAI Vision in ONE request...\n")

    content_blocks = [
        {
            "type": "text",
            "text": """
Extract ALL visible **real Facebook posts** from these screenshots.

Return ONLY valid JSON in the format:

{
  "posts": [
    {
      "author": "...",
      "snippet": "...",
      "timestamp": "...",
      "permalink_hint": "..."
    }
  ]
}

NO markdown.  
NO commentary.  
NO made-up posts.
"""
        }
    ]

    # Add every image to the same request
    for img in images_b64:
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        })

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": content_blocks
        }]
    )

    raw = response.choices[0].message.content

    # Clean markdown if model tries to add it
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        print("\n[ERROR] Failed to decode JSON. RAW OUTPUT:\n", raw)
        return {"posts": []}


# ---------------- MAIN ----------------

def main():
    OPENAI_KEY = load_openai_key()
    client = OpenAI(api_key=OPENAI_KEY)

    all_posts = []
    all_images = []
    seen_snippets = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        load_cookies(context)

        page = context.new_page()
        fb_search(page)

        print("[ACTION] Collecting screenshots...")

        # ----- PHASE 1: Collect all screenshots locally -----
        for i in range(SCROLL_PAGES):
            print(f"[SCROLL] {i+1}/{SCROLL_PAGES}")
            page.mouse.wheel(0, 3000)
            time.sleep(1.5)

            screenshot_path = f"fb_screenshot_{i+1}.png"
            print(f"[ACTION] Taking screenshot → {screenshot_path}")
            page.screenshot(path=screenshot_path)

            with open(screenshot_path, "rb") as f:
                all_images.append(base64.b64encode(f.read()).decode())

        # ----- PHASE 2: ONE OpenAI Vision Call -----
        result = call_openai_batch(all_images, client)

        posts = result.get("posts", [])

        # Deduplicate by snippet
        for post in posts:
            snippet = clean_text(post.get("snippet", ""))
            if snippet and snippet not in seen_snippets:
                seen_snippets.add(snippet)
                all_posts.append(post)

        # Final output
        output = {
            "query": QUERY,
            "collected_at": datetime.utcnow().isoformat(),
            "posts": all_posts
        }

        print("\n===== FINAL JSON OUTPUT =====")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print("=================================\n")

        input("Press Enter to CLOSE browser...")
        browser.close()

        print("[DONE] Finished scraping.")


if __name__ == "__main__":
    main()
