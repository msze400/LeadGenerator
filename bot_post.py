import os
import time
import re
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

QUERY = "iso web designer"
SCROLL_PAGES = 30

# ---- POST CONTAINER ----
POST_CONTAINER_SELECTOR = "div.x78zum5.xdt5ytf[data-virtualized='false']"

# ---- AUTHOR NAME SPAN (from earlier code) ----
NAME_SELECTOR = (
    "span.html-span.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu."
    "xyri2b.x18d9i69.x1c1uobl.x1hl2dhg.x16tdsg8.x1vvkbs"
)

# ---- POST TEXT ----
POST_TEXT_SELECTOR = "div.xdj266r.x14z9mp.xat24cr.x1lziwak.x1vvkbs"

# ---- YOU PROVIDED THIS <a> PROFILE LINK SELECTOR ----
PROFILE_LINK_SELECTOR = (
    "a.x1i10hfl.xjbqb8w.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl."
    "x972fbf.x10w94by.x1qhh985.x14e42zd.x9f619.x1ypdohk."
    "xt0psk2.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak."
    "xexx8yu.xyri2b.x18d9i69.x1c1uobl.x16tdsg8.x1hl2dhg."
    "xggy1nq.x1a2a7pz.xkrqix3.x1sur9pj.xzsf02u.x1s688f"
)

# ---- YOU PROVIDED THIS EXACT HOVER TARGET <span> ----
HOVER_TARGET_SELECTOR = (
    "span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.xlh3980.xvmahel."
    "x1n0sxbx.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i."
    "x1fgarty.x1943h6x.x4zkp8e.x676frb.x1nxh6w3.x1sibtaa."
    "xo1l8bm.xi81zsa.x1yc453h"
)

# ---- YOU PROVIDED THIS EXACT TOOLTIP SELECTOR ----
TOOLTIP_SELECTOR = (
    "span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.xlh3980.xvmahel."
    "x1n0sxbx.x1nxh6w3.x1sibtaa.xo1l8bm.xzsf02u"
)

COOKIES_PATH = "cookies.json"


# ---------------- HELPERS ----------------

def clean_text(txt: str) -> str:
    if not txt:
        return ""
    return re.sub(r"\s+", " ", txt).strip()


def load_cookies(context):
    if not os.path.exists(COOKIES_PATH):
        raise Exception("cookies.json not found!")
    cookies = json.load(open(COOKIES_PATH))
    context.add_cookies(cookies)
    print("[INFO] Cookies loaded.")


# ---------------- HOVER + EXTRACT TIMESTAMP ----------------

def hover_and_extract_timestamp(page, hover_elem):
    """
    Hover EXACTLY the span you provided, then wait for YOUR tooltip selector.
    """

    try:
        hover_elem.scroll_into_view_if_needed()
        time.sleep(0.3)

        box = hover_elem.bounding_box()
        if not box:
            print("[DEBUG] No bounding box.")
            return None

        print("[DEBUG] Hovering:", hover_elem.inner_text())
        print("[DEBUG] Box:", box)

        # Visible movement so you SEE it hover
        page.mouse.move(box["x"] + 5, box["y"] + 5, steps=20)
        time.sleep(0.15)
        page.mouse.move(box["x"] + 12, box["y"] + 8, steps=20)
        time.sleep(0.15)
        page.mouse.move(box["x"] + 7, box["y"] + 14, steps=20)
        time.sleep(0.15)

        # Facebook hover detection wiggle
        page.mouse.move(box["x"] + 8, box["y"] + 9, steps=10)

        # Wait for YOUR tooltip selector
        tooltip = page.locator(TOOLTIP_SELECTOR).first
        tooltip.wait_for(timeout=3000)

        full_timestamp = tooltip.inner_text().strip()
        print("[DEBUG] Tooltip:", full_timestamp)
        return full_timestamp

    except Exception as e:
        print("[DEBUG] Tooltip fail:", e)
        return None


# ---------------- SEARCH ----------------

def fb_search(page):
    from urllib.parse import quote_plus

    url = f"https://www.facebook.com/search/posts/?q={quote_plus(QUERY)}"
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(3)

    try:
        page.locator("text=All").click(timeout=3000)
        time.sleep(1)
        print("[ACTION] Switched to All tab.")
    except:
        print("[WARN] Could not click All tab.")


# ---------------- EXTRACT POSTS ----------------

def extract_posts_on_view(page):
    posts = []

    containers = page.query_selector_all(POST_CONTAINER_SELECTOR)
    print(f"[INFO] Found {len(containers)} posts...")

    for container in containers:
        try:
            # ---- PROFILE ANCHOR ----
            profile_anchor = container.query_selector(PROFILE_LINK_SELECTOR)

            if profile_anchor:
                profile_name = clean_text(profile_anchor.inner_text())
                profile_url = profile_anchor.get_attribute("href")
            else:
                profile_name = ""
                profile_url = ""

            if not profile_name:
                continue

            # ---- POST TEXT ----
            post_text_elem = container.query_selector(POST_TEXT_SELECTOR)
            post_text = clean_text(post_text_elem.inner_text()) if post_text_elem else ""

            if not post_text:
                continue

            # ---- HOVER TARGET ----
            hover_elem = container.query_selector(HOVER_TARGET_SELECTOR)

            if hover_elem:
                full_ts = hover_and_extract_timestamp(page, hover_elem)
            else:
                full_ts = None

            posts.append({
                "author": profile_name,
                "profile_url": profile_url,
                "post_text": post_text,
                "full_timestamp": full_ts
            })

        except Exception as e:
            print("[WARN] Error parsing post:", e)

    return posts


# ---------------- MAIN ----------------

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        load_cookies(context)

        page = context.new_page()
        fb_search(page)

        all_posts = []

        for i in range(SCROLL_PAGES):
            print(f"[SCROLL] {i+1}/{SCROLL_PAGES}")
            extracted = extract_posts_on_view(page)
            all_posts.extend(extracted)

            page.mouse.wheel(0, 2000)
            time.sleep(1.5)

        output = {
            "query": QUERY,
            "collected_at": datetime.utcnow().isoformat(),
            "posts": all_posts
        }

        print(json.dumps(output, indent=2, ensure_ascii=False))

        input("Press Enter to close...")
        browser.close()


if __name__ == "__main__":
    main()
