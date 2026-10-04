import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client

from .classifier import classify
from .rules import apply_rules, can_auto_answer, can_investigate
from .answerer import answer_from_kb
from .investigator import investigate, compose_reply
from fastapi.middleware.cors import CORSMiddleware
from .staff import build_router

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
app = FastAPI(title="Support AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(build_router(db))


class IncomingMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # DEMO ONLY: in production this must come from the authenticated session (JWT),
    # never from the request body, or anyone could pass someone else's ID.
    customer_id: str | None = None
    channel: str = "web"


@app.post("/api/messages")
def handle_message(body: IncomingMessage):
    try:
        result = classify(body.message)
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")

    final, overrides = apply_rules(result, body.message)

    reply, rag_log, tool_log, recommended = None, None, None, None

    if can_auto_answer(final):
        # --- FAQ branch: only for safe categories, only from the knowledge base ---
        try:
            ans = answer_from_kb(db, body.message, final.language)
            rag_log = {"hits": ans.hits, "reason": ans.reason}
            if ans.answered:
                reply = ans.reply
            else:
                overrides.append(f"auto-answer declined: {ans.reason}")
        except Exception as e:
            overrides.append(f"auto-answer failed: {str(e)[:150]}")
        if reply is None:
            final = final.model_copy(update={"requires_human": True})

    elif can_investigate(final, body.message):
        # --- Payment branch: read-only lookups, deterministic diagnosis ---
        try:
            finding = investigate(db, body.customer_id, final.extracted)
            reply = compose_reply(finding.points, final.language)
            recommended = finding.recommended_action
            tool_log = {"kind": finding.kind, "facts": finding.facts}
            if finding.requires_human:
                final = final.model_copy(update={"requires_human": True})
        except Exception as e:
            overrides.append(f"investigation failed: {str(e)[:150]}")
            final = final.model_copy(update={"requires_human": True})

    if final.requires_human:
        status = "needs_human"
    elif reply:
        status = "ai_resolved"
    else:
        status = "open"

    ticket = db.table("tickets").insert({
        "customer_id": body.customer_id,
        "channel": body.channel,
        "category": final.category,
        "priority": final.priority,
        "sentiment": final.sentiment,
        "language": final.language,
        "requires_human": final.requires_human,
        "status": status,
        "summary": final.summary,
        "extracted": final.extracted.model_dump(),
        "recommended_action": recommended,
    }).execute().data[0]

    messages = [{"ticket_id": ticket["id"], "role": "customer", "content": body.message}]
    if reply:
        messages.append({"ticket_id": ticket["id"], "role": "ai", "content": reply})
    db.table("messages").insert(messages).execute()

    logs = [{"ticket_id": ticket["id"], "step": "classify",
             "input": {"message": body.message}, "output": result.model_dump()}]
    if rag_log:
        logs.append({"ticket_id": ticket["id"], "step": "rag", "output": rag_log})
    if tool_log:
        logs.append({"ticket_id": ticket["id"], "step": "tool_call", "output": tool_log})
    if reply:
        logs.append({"ticket_id": ticket["id"], "step": "reply", "output": {"reply": reply}})
    if overrides:
        logs.append({"ticket_id": ticket["id"], "step": "override", "output": {"reasons": overrides}})
    db.table("agent_logs").insert(logs).execute()

    return {"ticket_id": ticket["id"], "status": status, "reply": reply,
            "recommended_action": recommended,
            "classification": final.model_dump(), "overrides": overrides}