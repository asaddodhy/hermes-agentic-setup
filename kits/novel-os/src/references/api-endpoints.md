# Novel-OS REST API Reference

Base URL: `http://localhost:8000` (configurable via `VITE_API_BASE` env var in the web UI).

## Health

```
GET  /api/health
→ { "status": "ok", "version": "0.2.0" }
```

## Projects

### List all projects
```
GET  /api/projects
→ [
    {
      "id": "the-last-ember",
      "title": "The Last Ember",
      "genre": "Fantasy",
      "chapter_count": 0,
      "status": "in_progress"
    }
  ]
```

### Create project
```
POST /api/projects
Body: { "title": "The Last Ember", "genre": "Fantasy", "author": "" }
→ { "id": "the-last-ember", "title": "...", "genre": "...", "chapter_count": 0, "status": "in_progress" }
```
Triggers `orchestrator.init_project()` under the hood.

### Get project detail
```
GET  /api/projects/{project_id}
→ {
    "id": "the-last-ember",
    "title": "The Last Ember",
    "genre": "Fantasy",
    "author": "",
    "chapter_count": 0,
    "status": "in_progress",
    "style": { "tone": "...", "point_of_view": "...", "prose_style": "..." }
  }
```

### Export manuscript
```
GET  /api/projects/{project_id}/export
→ Markdown text (prefers final > revised > draft per chapter)
```

## Chapters

### List chapters
```
GET  /api/projects/{project_id}/chapters
→ [
    {
      "number": 1,
      "title": "Chapter One",
      "status": "draft",
      "word_count": 2450,
      "pov": "Kael"
    }
  ]
```

### Get chapter detail
```
GET  /api/projects/{project_id}/chapters/{number}
→ {
    "number": 1,
    "title": "Chapter One",
    "status": "draft",
    "word_count": 2450,
    "pov": "Kael",
    "outline": "# Chapter 1...",        # markdown text or null
    "draft": "The forest...",            # markdown text or null
  }
```

### Get chapter stages (full pipeline lineage)
```
GET  /api/projects/{project_id}/chapters/{number}/stages
→ {
    "number": 1,
    "status": "draft",
    "outline": "markdown | null",
    "draft": "markdown | null",
    "revised": "markdown | null",
    "final": "markdown | null",
    "continuity": { ... } | null         # continuity_checks dict from story_state
  }
```

### Save/promote Final

**Promote** — seed Final from revised (or draft if no revised exists). Idempotent unless force=true.
```
POST /api/projects/{project_id}/chapters/{number}/final/promote
Body: { "force": true }  # optional, default false
→ { "final": "markdown text", "word_count": 2500 }
```

**Save** — human edit of the Final.
```
PUT  /api/projects/{project_id}/chapters/{number}/final
Body: { "text": "Revised final text..." }
→ { "final": "...", "word_count": 2500 }
```
Writes `chapter_NNN_final.md` atomically (temp file + os.replace).

Characters

### List characters
```
GET  /api/projects/{project_id}/characters
→ [
    { "id": "char_abc123", "full_name": "Kael", "role": "protagonist" }
  ]
```

### Add character
```
POST /api/projects/{project_id}/characters
Body: { "name": "Kael", "role": "protagonist" }
→ [ { "id": "...", "full_name": "Kael", "role": "protagonist" }, ... ]
```

## Pipeline (run phases)

### Run a pipeline phase (async)
```
POST /api/projects/{project_id}/run
Body: { "stage": "write", "params": { "number": 1 } }
→ {
    "job_id": "job_abc123",
    "kind": "write",
    "status": "running",
    "error": null,
    "started_at": "2026-06-17T...",
    "finished_at": null
  }
```

Valid stages (maps to PHASES dict in `api/services.py`):

| Stage | params | What it runs |
|-------|--------|--------------|
| `plan_outline` | `{ "chapters": N, "words": N }` | Archiect outlines |
| `plan_chapter` | `{ "number": N, "pov": "Char" }` | Architect plans chapter |
| `write` | `{ "number": N }` | Scribe drafts |
| `edit` | `{ "number": N, "mode": "line" }` | Editor refines |
| `validate` | `{ "number": N }` | Guardian validates |
| `approve` | `{ "number": N }` | Approval gate |

### Get job status
```
GET  /api/jobs/{job_id}
→ { "job_id": "...", "kind": "write", "status": "done|error|running", "error": null, ... }
```

## Snapshots

### List snapshots for a chapter
```
GET  /api/projects/{project_id}/chapters/{number}/snapshots
→ [
    {
      "id": "snap_abc",
      "label": "Before big edit",
      "created_at": "2026-06-17T...",
      "word_count": 2400,
      "source": "final"
    }
  ]
```

### Create snapshot
```
POST /api/projects/{project_id}/chapters/{number}/snapshots
Body: { "label": "Before big edit" }
→ { "id": "...", "label": "...", "created_at": "...", "word_count": 2400, "source": "final" }
```
Snapshots are stored in the SQLite DB, not on the filesystem.

### Get snapshot text
```
GET  /api/projects/{project_id}/chapters/{number}/snapshots/{snapshot_id}
→ { "id": "...", "label": "...", "created_at": "...", "word_count": 2400, "source": "final", "text": "..." }
```

### Restore snapshot
```
POST /api/projects/{project_id}/chapters/{number}/snapshots/{snapshot_id}/restore
→ { "final": "...", "word_count": 2400 }
```
Overwrites the current Final with the snapshot's text.

### Delete snapshot
```
DELETE /api/projects/{project_id}/chapters/{number}/snapshots/{snapshot_id}
→ 204 No Content
```

## Comments

### List comments
```
GET  /api/projects/{project_id}/chapters/{number}/comments
→ [
    {
      "id": "cmt_abc",
      "body": "This sentence needs work",
      "quote": "The old man...",
      "created_at": "...",
      "resolved": false
    }
  ]
```

### Add comment
```
POST /api/projects/{project_id}/chapters/{number}/comments
Body: { "body": "This feels too slow", "quote": "He walked..." }
→ { "id": "...", "body": "...", "quote": "...", "created_at": "...", "resolved": false }
```

### Update comment (resolve/unresolve)
```
PATCH /api/projects/{project_id}/chapters/{number}/comments/{comment_id}
Body: { "resolved": true }
→ { "id": "...", "body": "...", "resolved": true, ... }
```

### Delete comment
```
DELETE /api/projects/{project_id}/chapters/{number}/comments/{comment_id}
→ 204 No Content
```

## Notes

- `project_id` is the folder slug (e.g. `the-last-ember`), not a UUID.
- The API reads `NOVEL_OS_PROJECTS_DIR` env var to locate project folders. Default: `./projects` relative to cwd.
- Orchestrator jobs run in-process via `concurrent.futures` (not a separate worker). They block the API process but return a 202 immediately — the frontend polls the job status.
- The SQLite DB is at `./novel_os.db` (configurable via `NOVEL_OS_DB` env var).
