# save_facebook_cookies.py
import json
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        page = context.new_page()
        page.goto("https://www.facebook.com/login")

        print("\n[INFO] Log into Facebook manually.")
        input("Press ENTER after login is complete...")

        cookies = context.cookies()
        with open("cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print("[INFO] cookies.json saved.")
        browser.close()

if __name__ == "__main__":
    main()
