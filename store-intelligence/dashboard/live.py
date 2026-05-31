"""Part E live dashboard — open in browser after API is running."""

from __future__ import annotations

import argparse
import webbrowser

DEFAULT_URL = "http://127.0.0.1:8000/dashboard"


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Store Intelligence live dashboard")
    parser.add_argument("--url", default=DEFAULT_URL, help="Dashboard URL")
    parser.add_argument("--no-open", action="store_true", help="Print URL only")
    args = parser.parse_args()
    print(f"Dashboard: {args.url}")
    print("Click 'Live replay' to stream data/events.jsonl into the API and watch metrics update.")
    if not args.no_open:
        webbrowser.open(args.url)


if __name__ == "__main__":
    main()
