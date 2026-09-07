"""Background worker: picks up pending orders and fulfils them.

Run forever:      python -m orderdesk.worker
Run one batch:    python -m orderdesk.worker --once
"""

import argparse
import logging
import sys
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from orderdesk import db
from orderdesk.models import Order, OrderStatus, utcnow
from orderdesk.settings import settings

log = logging.getLogger("orderdesk.worker")


def fulfil(order: Order) -> None:
    """Stand-in for the real work: reserve stock, notify the warehouse, email the customer."""
    if order.quantity > 500:
        raise ValueError("quantity above the single-shipment limit")
    time.sleep(0.05)


def process_batch(session: Session, batch_size: int) -> int:
    """Process up to batch_size pending orders. Rows are locked so several workers can run at once."""
    stmt = (
        select(Order)
        .where(Order.status == OrderStatus.pending)
        .order_by(Order.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    orders = list(session.scalars(stmt))
    for order in orders:
        try:
            fulfil(order)
            order.status = OrderStatus.processed
        except Exception as exc:
            log.warning("order %s failed: %s", order.id, exc)
            order.status = OrderStatus.failed
            order.note = str(exc)[:500]
        order.processed_at = utcnow()
    session.commit()
    return len(orders)


def run_forever(poll_seconds: float, batch_size: int) -> None:
    log.info("worker started, polling every %.1fs", poll_seconds)
    while True:
        with db.SessionLocal() as session:
            n = process_batch(session, batch_size)
        if n:
            log.info("processed %d order(s)", n)
        else:
            time.sleep(poll_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="process one batch and exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db.init_db()
    if args.once:
        with db.SessionLocal() as session:
            n = process_batch(session, settings.worker_batch_size)
        log.info("processed %d order(s)", n)
        return 0
    run_forever(settings.worker_poll_seconds, settings.worker_batch_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
