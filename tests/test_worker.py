from sqlalchemy import select

from orderdesk import db
from orderdesk.models import Order, OrderStatus
from orderdesk.worker import process_batch


def _seed(session, n, quantity=1):
    for i in range(n):
        session.add(Order(customer_email=f"c{i}@example.com", item="widget", quantity=quantity))
    session.commit()


def test_worker_processes_pending_orders():
    with db.SessionLocal() as session:
        _seed(session, 4)
        assert process_batch(session, batch_size=10) == 4
        statuses = list(session.scalars(select(Order.status)))
    assert statuses == [OrderStatus.processed] * 4


def test_worker_respects_batch_size():
    with db.SessionLocal() as session:
        _seed(session, 5)
        assert process_batch(session, batch_size=2) == 2
        assert process_batch(session, batch_size=2) == 2
        assert process_batch(session, batch_size=2) == 1
        assert process_batch(session, batch_size=2) == 0


def test_worker_marks_failures_without_stopping():
    with db.SessionLocal() as session:
        _seed(session, 1, quantity=999)
        _seed(session, 1)
        assert process_batch(session, batch_size=10) == 2
        rows = list(session.scalars(select(Order).order_by(Order.id)))
    assert rows[0].status == OrderStatus.failed
    assert "limit" in (rows[0].note or "")
    assert rows[1].status == OrderStatus.processed
