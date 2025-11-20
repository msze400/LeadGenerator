import base64
import json
from openai import OpenAI
import os

SERVICE_ACCOUNT_PATH = "service_account.json"
IMAGE_PATH = "fb_screenshot.png"

def load_openai_key():
    with open(SERVICE_ACCOUNT_PATH, "r") as f:
        data = json.load(f)

    if "openai_key" not in data:
        raise KeyError(
            "No 'openai_key' field found in service_account.json.\n"
            "Add:  \"openai_key\": \"sk-...\""
        )

    return data["openai_key"]


def run_test():
    # Load OpenAI key from JSON
    OPENAI_KEY = load_openai_key()
    client = OpenAI(api_key=OPENAI_KEY)

    print("[TEST] Sending image to OpenAI Vision...\n")

    # Encode image
    with open(IMAGE_PATH, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode("utf-8")

    # Build request
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # You can use 5.1 or 4.1 if you want
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe exactly what appears in this screenshot. Return JSON."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded_image}"}
                    }
                ]
            }
        ]
    )

    print("===== MODEL OUTPUT =====")
    print(response.choices[0].message.content)
    print("========================")


if __name__ == "__main__":
    run_test()
