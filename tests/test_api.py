def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_fetch_order(client):
    r = client.post("/orders", json={"customer_email": "ana@example.com", "item": "desk lamp", "quantity": 2})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["processed_at"] is None

    r = client.get(f"/orders/{body['id']}")
    assert r.status_code == 200
    assert r.json()["item"] == "desk lamp"


def test_validation_rejects_bad_email(client):
    r = client.post("/orders", json={"customer_email": "not-an-email", "item": "x"})
    assert r.status_code == 422


def test_list_filters_by_status(client):
    for i in range(3):
        client.post("/orders", json={"customer_email": f"u{i}@example.com", "item": f"item {i}"})
    r = client.get("/orders", params={"status": "pending"})
    assert r.status_code == 200
    assert len(r.json()) == 3
    r = client.get("/orders", params={"status": "processed"})
    assert r.json() == []


def test_unknown_order_404(client):
    assert client.get("/orders/999999").status_code == 404
