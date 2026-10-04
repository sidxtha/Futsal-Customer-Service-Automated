-- Run once in the Supabase SQL editor (kb_chunks already exists in schema.sql)
create or replace function match_kb_chunks(
  query_embedding vector(768),
  match_count int default 4
)
returns table (id bigint, source text, content text, similarity float)
language sql stable
as $$
  select id, source, content, 1 - (embedding <=> query_embedding) as similarity
  from kb_chunks
  order by embedding <=> query_embedding
  limit match_count;
$$;