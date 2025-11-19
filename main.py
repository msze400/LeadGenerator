# main.py
import os
import time
import re
import json
from datetime import datetime
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

QUERY = "iso web designer"
SCROLL_PAGES = 6


# ---------------- HELPERS ----------------

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def load_cookies(context):
    if not os.path.exists("cookies.json"):
        raise Exception("cookies.json not found! Run save_facebook_cookies.py first.")
    with open("cookies.json", "r") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    print("[INFO] Cookies loaded.")


# ---------------- SEARCH ----------------

def fb_search(page):
    encoded = quote_plus(QUERY)
    url = f"https://www.facebook.com/search/posts/?q={encoded}"
    print(f"[ACTION] Go to: {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(3)


# ---------------- SCRAPING VIA VISUAL ANCHORS ----------------

def get_post_candidates(page):
    """
    Finds posts using visible UI anchors.
    This avoids depending on obfuscated class names.
    """

    anchors = [
        "Like",
        "Comment",
        "Share",
    ]

    locs = []
    for a in anchors:
        locs.extend(page.get_by_text(a).all())

    unique_posts = set()
    post_elements = []

    for loc in locs:
        try:
            post = loc.locator("xpath=ancestor::div[contains(@role,'article')]").first

            if post.count() == 0:
                continue

            box = post.bounding_box()

            # Use bounding box as a unique identifier
            if box:
                key = (round(box["x"]), round(box["y"]))
                if key not in unique_posts:
                    unique_posts.add(key)
                    post_elements.append(post)
        except:
            pass

    print(f"[INFO] Found ~{len(post_elements)} post candidates")
    return post_elements


def extract_post(post):
    """
    Extracts author, snippet, and permalink from a post container.
    Everything uses visual/role/text anchors, not classnames.
    """

    # ---------- AUTHOR ----------
    author = ""
    try:
        author_loc = post.locator("a[role='link']").first
        if author_loc.count():
            author = clean_text(author_loc.inner_text())
    except:
        pass

    # ---------- SNIPPET ----------
    snippet = ""
    try:
        msg = post.locator("div[dir='auto']").first
        if msg.count():
            snippet = clean_text(msg.inner_text())
    except:
        pass

    # ---------- PERMALINK ----------
    permalink = ""
    try:
        link = post.locator("a[href*='/posts/'], a[href*='/groups/'], a[href*='/permalink/']").first
        if link.count():
            permalink = link.get_attribute("href")
    except:
        pass

    return {
        "author": author,
        "snippet": snippet,
        "permalink": permalink or ""
    }


def scrape_posts(page):
    posts = get_post_candidates(page)

    extracted = []
    seen_snippets = set()

    for p in posts:
        data = extract_post(p)
        if not data["snippet"]:
            continue

        # Deduplicate by text
        if data["snippet"] not in seen_snippets:
            seen_snippets.add(data["snippet"])
            extracted.append(data)

    print(f"[INFO] Extracted {len(extracted)} unique posts")
    return extracted


# ---------------- MAIN ----------------

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        load_cookies(context)
        page = context.new_page()

        fb_search(page)

        print("[ACTION] Scrolling…")
        for i in range(SCROLL_PAGES):
            page.mouse.wheel(0, 3000)
            time.sleep(1.5)

        results = scrape_posts(page)

        output = {
            "query": QUERY,
            "collected_at": datetime.utcnow().isoformat(),
            "posts": results
        }

        print(json.dumps(output, indent=2, ensure_ascii=False))

        input("\nPress ENTER to close browser…")
        browser.close()


if __name__ == "__main__":
    main()
