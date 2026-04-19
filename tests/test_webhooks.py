def test_success_processing(client):
    resp = client.post("/webhooks", json={
        "event_id": "evt-1",
        "event_type": "order.created",
        "payload": {"order_id": 123},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["attempts"] == 1
    assert data["last_error"] is None


def test_fail_processing(client):
    resp = client.post("/webhooks", json={
        "event_id": "evt-2",
        "event_type": "payment.fail",
        "payload": {"amount": 50},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["attempts"] == 1
    assert data["last_error"] is not None


def test_idempotency_no_duplicates(client):
    payload = {
        "event_id": "evt-dup",
        "event_type": "order.created",
        "payload": {},
    }
    resp1 = client.post("/webhooks", json=payload)
    assert resp1.status_code == 200
    assert "event_id" in resp1.json()

    resp2 = client.post("/webhooks", json=payload)
    assert resp2.status_code == 200
    assert resp2.json() == {"message": "Duplicate ignored"}


def test_retry_success_using_force_success(client):
    # Create a failed event with force_success in payload
    client.post("/webhooks", json={
        "event_id": "evt-fail-retry",
        "event_type": "sync.fail",
        "payload": {"force_success": True},
    })

    # Even though event_type contains 'fail', force_success=True makes it succeed
    resp = client.get("/webhooks")
    evt = [e for e in resp.json() if e["event_id"] == "evt-fail-retry"][0]
    assert evt["status"] == "processed"

    # Also test: fail first, then retry with force_success
    client.post("/webhooks", json={
        "event_id": "evt-fail-then-retry",
        "event_type": "payment.fail",
        "payload": {"data": "abc"},
    })
    check = client.get("/webhooks", params={"status": "failed"})
    assert any(e["event_id"] == "evt-fail-then-retry" for e in check.json())

    # Retry still fails because payload doesn't have force_success
    retry1 = client.post("/webhooks/evt-fail-then-retry/retry")
    assert retry1.json()["status"] == "failed"
    assert retry1.json()["attempts"] == 2


def test_retry_not_found(client):
    resp = client.post("/webhooks/nonexistent/retry")
    assert resp.status_code == 404


def test_retry_already_processed(client):
    client.post("/webhooks", json={
        "event_id": "evt-ok",
        "event_type": "order.shipped",
        "payload": {},
    })
    resp = client.post("/webhooks/evt-ok/retry")
    assert resp.json() == {"message": "Event already processed"}


def test_list_with_pagination(client):
    for i in range(5):
        client.post("/webhooks", json={
            "event_id": f"evt-page-{i}",
            "event_type": "order.created",
            "payload": {},
        })
    resp = client.get("/webhooks", params={"limit": 2, "offset": 0})
    assert len(resp.json()) == 2

    resp2 = client.get("/webhooks", params={"limit": 10, "offset": 3})
    assert len(resp2.json()) == 2


def test_list_with_status_filter(client):
    client.post("/webhooks", json={"event_id": "e1", "event_type": "ok", "payload": {}})
    client.post("/webhooks", json={"event_id": "e2", "event_type": "fail.x", "payload": {}})

    resp = client.get("/webhooks", params={"status": "failed"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_id"] == "e2"
