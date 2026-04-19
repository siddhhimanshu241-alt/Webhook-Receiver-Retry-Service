# Webhook-Receiver-Retry-Service

Small FastAPI application that ingests webhook events, persists them to SQLite, applies deterministic processing rules, and supports manual retries.

## Features

- **POST `/webhooks`** — Accept `event_id`, `event_type`, and JSON `payload`; deduplicate by `event_id`.
- **GET `/webhooks`** — List events with optional `status` filter and `limit` / `offset` pagination.
- **POST `/webhooks/{event_id}/retry`** — Re-run processing for non-processed events.
- **SQLite** — Local file database (`webhooks.db` at project root when running the app).

## Processing rules

On each processing attempt (initial receive or retry):

1. `attempts` is incremented by 1.
2. If `event_type` contains the substring `fail` **and** `payload.force_success` is not truthy → status `failed` and `last_error` is set.
3. Otherwise → status `processed` and `last_error` is cleared.

Duplicate `event_id` values return `{"message": "Duplicate ignored"}` without inserting a second row.

## Requirements

- Python 3.12+ (as used in the bundled venv in this workspace)

Dependencies are pinned in `requirements.txt`:

- FastAPI, Uvicorn, SQLAlchemy, pytest, httpx

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
