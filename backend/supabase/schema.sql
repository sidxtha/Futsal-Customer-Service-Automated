-- Run in Supabase SQL editor
create extension if not exists vector;

create table tickets (
  id bigint generated always as identity primary key,
  customer_id uuid,
  channel text not null default 'web',          -- web | whatsapp | email
  category text not null,
  priority text not null,                       -- low | medium | high | urgent
  sentiment text,
  language text,
  status text not null default 'open',          -- open | ai_resolved | needs_human | in_progress | closed
  requires_human boolean not null default false,
  summary text,
  extracted jsonb not null default '{}',
  recommended_action text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table messages (
  id bigint generated always as identity primary key,
  ticket_id bigint not null references tickets(id) on delete cascade,
  role text not null check (role in ('customer','ai','staff')),
  content text not null,
  created_at timestamptz not null default now()
);

-- Every LLM decision and tool call, so staff can see why the AI did something
create table agent_logs (
  id bigint generated always as identity primary key,
  ticket_id bigint references tickets(id) on delete cascade,
  step text not null,                           -- classify | tool_call | rag | reply | override
  input jsonb,
  output jsonb,
  created_at timestamptz not null default now()
);

-- RAG knowledge base (policies, FAQs). 768 dims = Gemini embeddings with output_dimensionality=768
create table kb_chunks (
  id bigint generated always as identity primary key,
  source text not null,
  content text not null,
  embedding vector(768)
);
create index on kb_chunks using hnsw (embedding vector_cosine_ops);
