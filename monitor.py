import requests
import time
import json
from pathlib import Path
from datetime import datetime


import os

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]


TOKEN_URL = "https://singaporegp.sg/api/getToken/"

API_URL = "https://singaporegp.sg/ws/items/tickets?fields=slug,ticket_status,ticket_status_text,ticket_category.slug,ticket_category.group,prices.phase,prices.ticket_status,prices.ticket_status_text&filter=%7B%22_and%22%3A%5B%7B%22status%22%3A%7B%22_eq%22%3A%22published%22%7D%2C%22ticketing_date%22%3A%7B%22_between%22%3A%5B%222025-12-31T16%3A00%3A00.000Z%22%2C%222026-12-30T16%3A00%3A00.000Z%22%5D%7D%7D%5D%7D&sort=slug&limit=-1"



SEEN_FILE = "seen.json"

if Path(SEEN_FILE).exists():
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
else:
    seen = set()

NO_AVAILABILITY_SENT = False


def send_startup():
    requests.post(
        DISCORD_WEBHOOK,
        json={
            "content": "✅ Singapore GP Sunday Ticket Monitor Started"
        },
        timeout=30
    )


def send_no_availability():

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    payload = {
        "embeds": [
            {
                "title": "🏁 Singapore GP Sunday Ticket Check",
                "color": 16711680,
                "fields": [
                    {
                        "name": "Status",
                        "value": "❌ No Sunday Grandstand tickets available"
                    },
                    {
                        "name": "Checked",
                        "value": timestamp
                    }
                ]
            }
        ]
    }

    requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=30
    )


def send_discord(ticket):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    payload = {
        "embeds": [
            {
                "title": "🏁 Singapore GP Sunday Ticket Available",
                "color": 65280,
                "fields": [
                    {
                        "name": "Ticket",
                        "value": ticket["slug"],
                        "inline": False
                    },
                    {
                        "name": "Status",
                        "value": str(
                            ticket.get(
                                "ticket_status_text"
                            ) or "Available"
                        ),
                        "inline": True
                    },
                    {
                        "name": "Detected",
                        "value": timestamp,
                        "inline": True
                    }
                ]
            }
        ]
    }

    requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=30
    ).raise_for_status()


def get_token():

    response = requests.get(
        TOKEN_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()["token"]


def get_tickets(token):

    response = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()["data"]


def main():

    try:

        token = get_token()

        tickets = get_tickets(token)

        print(f"Retrieved {len(tickets)} tickets")

        available_found = False

        for ticket in tickets:

            slug = ticket.get("slug", "").lower()

            category = ticket.get(
                "ticket_category",
                {}
            ).get(
                "slug",
                ""
            )

            if category != "grandstands":
                continue

            if not slug.endswith("-sunday"):
                continue

            status = str(
                ticket.get(
                    "ticket_status_text"
                ) or ""
            ).lower()

            print(
                slug,
                ticket.get(
                    "ticket_status_text"
                )
            )

            if status in [
                "available",
                "selling fast"
            ]:

                available_found = True

                key = f"{slug}:{status}"

                if key not in seen:

                    send_discord(ticket)

                    seen.add(key)

                    with open(SEEN_FILE, "w") as f:
                        json.dump(
                            list(seen),
                            f
                        )

        if not available_found:
            send_no_availability()

        print(
            f"{datetime.now()} checked successfully"
        )

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
