import json
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, get_db, Base
from app.models import WebhookEvent
from app.schemas import WebhookIn, WebhookOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Webhook Receiver + Retry Service")


def process_event(event: WebhookEvent) -> None:
    """Processing rule:
    - attempts += 1
    - If event_type contains 'fail' AND payload.force_success is not True → failed
    - Else → processed
    """
    event.attempts += 1
    payload = json.loads(event.payload) if isinstance(event.payload, str) else event.payload

    if "fail" in event.event_type and not payload.get("force_success"):
        event.status = "failed"
        event.last_error = f"Processing failed for event type: {event.event_type}"
    else:
        event.status = "processed"
        event.last_error = None


@app.post("/webhooks")
def receive_webhook(body: WebhookIn, db: Session = Depends(get_db)):
    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == body.event_id).first()
    if existing:
        return {"message": "Duplicate ignored"}

    event = WebhookEvent(
        event_id=body.event_id,
        event_type=body.event_type,
        payload=json.dumps(body.payload),
        status="received",
        attempts=0,
    )
    db.add(event)
    db.flush()

    process_event(event)
    db.commit()
    db.refresh(event)
    return WebhookOut.model_validate(_to_dict(event))


@app.get("/webhooks")
def list_webhooks(
    status: str | None = Query(None),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(WebhookEvent)
    if status:
        q = q.filter(WebhookEvent.status == status)
    events = q.order_by(WebhookEvent.created_at.desc()).offset(offset).limit(limit).all()
    return [WebhookOut.model_validate(_to_dict(e)) for e in events]


@app.post("/webhooks/{event_id}/retry")
def retry_webhook(event_id: str, db: Session = Depends(get_db)):
    event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status == "processed":
        return {"message": "Event already processed"}

    process_event(event)
    db.commit()
    db.refresh(event)
    return WebhookOut.model_validate(_to_dict(event))


def _to_dict(event: WebhookEvent) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "payload": json.loads(event.payload) if isinstance(event.payload, str) else event.payload,
        "status": event.status,
        "attempts": event.attempts,
        "last_error": event.last_error,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }
