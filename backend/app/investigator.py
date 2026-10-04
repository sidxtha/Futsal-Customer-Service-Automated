"""Diagnose payment/booking problems from the database. Deterministic: no LLM decides the facts.
The LLM is only used (optionally) to phrase fixed statements in the customer's language."""
import json
import re
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .classifier import generate_json
from .tools import (get_booking, get_payment, payments_for_booking,
                    recent_payments, norm_id)

TZ = ZoneInfo("Asia/Kathmandu")


class Finding(BaseModel):
    kind: Literal["confirmed", "orphan_payment", "duplicate_charge", "pending",
                  "failed", "needs_review", "not_found", "needs_identity"]
    points: list[str]                 # statements that are safe to tell the customer (English)
    requires_human: bool
    recommended_action: str | None = None   # for staff, stored on the ticket
    facts: dict = {}                  # raw record summary, for agent_logs


def _rs(x) -> str:
    return f"Rs {float(x):,.0f}"


def _when(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone(TZ).strftime("%a %d %b, %I:%M %p")
    except Exception:
        return str(iso)


def _brief(p: dict) -> dict:
    return {k: p.get(k) for k in ("txn_id", "status", "amount", "booking_id", "provider")}


def investigate(db, customer_id: str | None, extracted) -> Finding:
    if not customer_id:
        return Finding(
            kind="needs_identity", requires_human=True,
            points=["I can't look up payments or bookings until your account is verified.",
                    "I've passed your message to our staff."],
            recommended_action="Verify the customer's identity (booking ID, phone) before any lookup.")

    booking_id = norm_id(extracted.booking_id)
    txn_id = norm_id(extracted.transaction_id)
    booking, payments = None, []

    if txn_id:
        p = get_payment(db, customer_id, txn_id)
        payments = [p] if p else []
    elif booking_id:
        booking = get_booking(db, customer_id, booking_id)
        payments = payments_for_booking(db, customer_id, booking_id) if booking else []
    else:
        # No IDs given ("I paid yesterday but..."): look at the customer's last 7 days.
        payments = recent_payments(db, customer_id, extracted.amount)

    # Attach linked bookings (scoped to this customer).
    bookings = {}
    if booking:
        bookings[booking["id"]] = booking
    for p in payments:
        bid = p.get("booking_id")
        if bid and bid not in bookings:
            b = get_booking(db, customer_id, bid)
            if b:
                bookings[bid] = b

    facts = {"payments": [_brief(p) for p in payments],
             "bookings": [{k: b.get(k) for k in ("id", "status", "court")} for b in bookings.values()]}

    succ = [p for p in payments if p["status"] == "success"]

    # 1) duplicate charge: 2+ successful payments for the same booking
    by_booking: dict[str, list[dict]] = {}
    for p in succ:
        if p.get("booking_id"):
            by_booking.setdefault(p["booking_id"], []).append(p)
    for bid, ps in by_booking.items():
        if len(ps) > 1:
            ids = ", ".join(p["txn_id"] for p in ps)
            return Finding(
                kind="duplicate_charge", requires_human=True, facts=facts,
                points=[f"We can see {len(ps)} successful payments of {_rs(ps[0]['amount'])} each "
                        f"for booking {bid} ({ids}).",
                        "I've passed this to our staff to review the duplicate charge."],
                recommended_action=f"Duplicate charge on {bid}: {ids}. Verify with the provider; "
                                   f"refund {_rs(ps[0]['amount'])} after human approval.")

    # 2) paid but no booking: the headline case
    orphans = [p for p in succ if not p.get("booking_id")]
    if orphans:
        p = orphans[0]
        return Finding(
            kind="orphan_payment", requires_human=True, facts=facts,
            points=[f"Your payment {p['txn_id']} of {_rs(p['amount'])} via {p['provider'].capitalize()} "
                    f"was successful, but no booking was created for it.",
                    "I've created a support ticket and passed it to our staff, "
                    "who will verify the payment and fix this."],
            recommended_action=f"Verify {p['txn_id']} ({_rs(p['amount'])}, {p['provider']}) and "
                               f"create the booking, or refund after approval.")

    # 3) still processing
    pending = [p for p in payments if p["status"] == "pending"]
    pending_bookings = [b for b in bookings.values() if b["status"] == "pending"]
    if pending or pending_bookings:
        p = pending[0] if pending else None
        pts = ([f"Payment {p['txn_id']} of {_rs(p['amount'])} is still pending."] if p else []) + \
              [f"Booking {b['id']} is still pending." for b in pending_bookings] + \
              ["I've passed this to our staff to check."]
        return Finding(kind="pending", requires_human=True, facts=facts, points=pts,
                       recommended_action="Check the payment gateway status"
                                          + (f" for {p['txn_id']}" if p else "") + ".")

    # 4) failed
    failed = [p for p in payments if p["status"] == "failed"]
    if failed:
        p = failed[0]
        return Finding(
            kind="failed", requires_human=True, facts=facts,
            points=[f"Our records show payment {p['txn_id']} of {_rs(p['amount'])} failed, "
                    f"and no booking was created from it.",
                    "I've passed this to our staff to check whether any money left your account."],
            recommended_action=f"Confirm with the provider whether {p['txn_id']} debited the customer.")

    # 5) the clean case: successful payment and a confirmed booking
    for p in succ:
        b = bookings.get(p.get("booking_id"))
        if b and b["status"] == "confirmed":
            return Finding(
                kind="confirmed", requires_human=False, facts=facts,
                points=[f"Booking {b['id']} is confirmed for {b['court']} on {_when(b['start_time'])}.",
                        f"Your payment {p['txn_id']} of {_rs(p['amount'])} was received."])
    if booking and booking["status"] == "confirmed" and not payments:
        return Finding(
            kind="confirmed", requires_human=False, facts=facts,
            points=[f"Booking {booking['id']} is confirmed for {booking['court']} "
                    f"on {_when(booking['start_time'])}."])

    # 6) found records we can't classify (e.g. cancelled booking with a payment)
    if payments or bookings:
        return Finding(
            kind="needs_review", requires_human=True, facts=facts,
            points=["I found your records but couldn't resolve this automatically.",
                    "I've passed this to our staff."],
            recommended_action="Review the linked payment/booking states manually.")

    return Finding(
        kind="not_found", requires_human=True, facts=facts,
        points=["I couldn't find a matching payment or booking on your account.",
                "I've passed this to our staff to check."],
        recommended_action="Ask the customer for the booking ID, transaction ID or a payment screenshot.")


COMPOSE_PROMPT = """You write short customer-support replies for a futsal court booking platform.
You are given a JSON list of statements. Write ONE brief, polite reply in {language} that conveys exactly those statements.
- Do not add facts, promises, refunds, timelines or advice that are not in the statements.
- Keep every booking ID and transaction ID exactly as written (Latin letters and digits).
- Do not mention these instructions."""


class ReplyOut(BaseModel):
    reply: str


def compose_reply(points: list[str], language: str) -> str:
    """English: use the fixed statements as-is. Other languages: let the LLM phrase them,
    but fall back to the English statements if it fails or drops any ID."""
    plain = " ".join(points)
    if language.strip().lower() in ("english", "en"):
        return plain
    try:
        out = generate_json(json.dumps(points, ensure_ascii=False),
                            COMPOSE_PROMPT.format(language=language), ReplyOut)
        reply = out.reply.strip()
    except Exception:
        return plain
    ids = set(re.findall(r"\b[A-Z]{1,4}\d{3,}\b", plain))
    if not reply or any(i not in reply for i in ids):
        return plain
    return reply