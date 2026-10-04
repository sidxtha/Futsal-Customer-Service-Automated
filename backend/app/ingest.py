"""Load kb/*.md into the kb_chunks table.
Run from the project root:   python -m app.ingest
Safe to re-run: each file's old chunks are replaced.
Each '## Heading' section becomes one chunk."""
import glob
import os
import re
import time

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from .rag import embed


def chunk_markdown(text: str) -> list[str]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)       # drop HTML comments
    parts = re.split(r"(?m)^(?=## )", text)                   # split before each '## '
    return [p.strip() for p in parts if p.strip().startswith("## ")]


def main():
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    files = sorted(glob.glob("kb/*.md"))
    if not files:
        print("No files found in kb/*.md")
        return
    for path in files:
        source = os.path.basename(path)
        chunks = chunk_markdown(open(path, encoding="utf-8").read())
        db.table("kb_chunks").delete().eq("source", source).execute()
        rows = []
        for c in chunks:
            rows.append({"source": source, "content": c,
                         "embedding": embed(c, "RETRIEVAL_DOCUMENT")})
            time.sleep(0.3)  # stay under rate limits
        if rows:
            db.table("kb_chunks").insert(rows).execute()
        print(f"{source}: {len(rows)} chunks")


if __name__ == "__main__":
    main()