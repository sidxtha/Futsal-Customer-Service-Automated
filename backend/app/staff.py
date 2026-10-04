"""Staff API for the dashboard. Protected by a shared STAFF_TOKEN from .env (fails closed if unset)."""
import os
import secrets
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field


def require_staff(authorization: str = Header(default="")):
    token = os.environ.get("STAFF_TOKEN", "")
    given = authorization.removeprefix("Bearer ").strip()
    if not token or not secrets.compare_digest(given.encode(), token.encode()):
        raise HTTPException(401, "Staff authentication required")


class StatusUpdate(BaseModel):
    status: Literal["in_progress", "closed"]


class StaffMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def build_router(db) -> APIRouter:
    r = APIRouter(prefix="/api/tickets", dependencies=[Depends(require_staff)])

    def one(ticket_id: int) -> dict:
        rows = db.table("tickets").select("*").eq("id", ticket_id).execute().data
        if not rows:
            raise HTTPException(404, "Ticket not found")
        return rows[0]

    @r.get("")
    def list_tickets(status: str | None = None, priority: str | None = None,
                     category: str | None = None, limit: int = Query(50, ge=1, le=200)):
        q = db.table("tickets").select("*")
        for col, val in (("status", status), ("priority", priority), ("category", category)):
            if val:
                q = q.eq(col, val)
        return q.order("created_at", desc=True).limit(limit).execute().data

    @r.get("/{ticket_id}")
    def get_ticket(ticket_id: int):
        t = one(ticket_id)
        t["messages"] = db.table("messages").select("*").eq("ticket_id", ticket_id).order("created_at").execute().data
        t["logs"] = db.table("agent_logs").select("*").eq("ticket_id", ticket_id).order("created_at").execute().data
        return t

    @r.patch("/{ticket_id}")
    def update_status(ticket_id: int, body: StatusUpdate):
        one(ticket_id)
        return (db.table("tickets")
                .update({"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", ticket_id).execute().data[0])

    @r.post("/{ticket_id}/messages")
    def staff_reply(ticket_id: int, body: StaffMessage):
        try:  # one query instead of two: the foreign key rejects unknown tickets
            return (db.table("messages")
                    .insert({"ticket_id": ticket_id, "role": "staff", "content": body.content})
                    .execute().data[0])
        except Exception as e:
            if "23503" in str(e):
                raise HTTPException(404, "Ticket not found")
            raise

    return r
