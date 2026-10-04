"""Read-only lookup tools.

SECURITY: every query is scoped to the requesting customer_id, so a customer can never read
someone else's booking or payment, even by guessing IDs. These tools never write anything.
(Mutating tools like cancel_booking/refund must go through human approval, not live here.)
"""
import re
from datetime import datetime, timedelta, timezone


def norm_id(s: str | None) -> str | None:
    """'#f1001' / ' F1001 ' -> 'F1001'"""
    return re.sub(r"[\s#]", "", s).upper() if s else None


def get_booking(db, customer_id: str, booking_id: str) -> dict | None:
    rows = (db.table("bookings").select("*")
            .eq("id", norm_id(booking_id)).eq("customer_id", customer_id)
            .execute().data)
    return rows[0] if rows else None


def get_payment(db, customer_id: str, txn_id: str) -> dict | None:
    rows = (db.table("payments").select("*")
            .eq("txn_id", norm_id(txn_id)).eq("customer_id", customer_id)
            .execute().data)
    return rows[0] if rows else None


def payments_for_booking(db, customer_id: str, booking_id: str) -> list[dict]:
    return (db.table("payments").select("*")
            .eq("booking_id", norm_id(booking_id)).eq("customer_id", customer_id)
            .execute().data) or []


def recent_payments(db, customer_id: str, amount: float | None = None,
                    days: int = 7, limit: int = 10) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q = (db.table("payments").select("*")
         .eq("customer_id", customer_id).gte("created_at", since))
    if amount is not None:
        q = q.eq("amount", amount)
    return q.order("created_at", desc=True).limit(limit).execute().data or []