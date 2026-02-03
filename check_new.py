import json
import os
import urllib.request


ARCHIVE_URL = "https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit=5"


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def main():
    data = fetch_json(ARCHIVE_URL)
    new_url = data[0].get("canonical_url") if data else ""

    with open("learnings.json", "r", encoding="utf-8") as f:
        learnings = json.load(f)
    last_url = learnings[0].get("articleUrl") if isinstance(learnings, list) and learnings else ""

    has_new = "true" if new_url and new_url != last_url else "false"

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"last_url={last_url}\n")
            f.write(f"new_url={new_url}\n")
            f.write(f"has_new={has_new}\n")


if __name__ == "__main__":
    main()
