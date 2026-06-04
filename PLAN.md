# Knowledge Graph Notebook — Improvement Plan

Comprehensive audit of the codebase across backend, frontend, security, architecture, and developer experience.

---

## ✅ Completed Fixes

| # | Severity | Issue | File(s) |
|---|----------|-------|---------|
| 1 | 🔴 Critical | ~~XSS in chat response rendering~~ | workspace.html |
| 2 | 🔴 Critical | ~~Windows-only font path~~ | pdf_generator.py |
| 3 | 🟠 Medium | ~~Only first span occurrence highlighted~~ | doc_analyzer.py |
| 4 | 🟠 Medium | ~~No temperature validation~~ | app.py |
| 6 | 🟠 Medium | ~~Stale CLAUDE.md~~ | CLAUDE.md |
| 14 | 🟠 Medium | ~~No API timeout~~ | graph_extractor.py |
| 10 | 🟡 Low | ~~Document tab overflow~~ | workspace.html |
| 16 | 🟡 Low | ~~O(n²) edge generation in fallback extractor~~ | fallback_extractor.py |
| 18 | 🔵 DX | ~~No .env.example~~ | .env.example |
| 21 | 🔵 DX | ~~Binary PDF tracked in git~~ | .gitignore |

---

## 🔲 Remaining Fixes & Improvements

### 🟠 Medium — Architecture

#### #5. Split `app.py` into Flask Blueprints

**File**: [app.py](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/app.py) (613 lines)

The file mixes workspace routes, studio routes, chat, search, upload, export, and extraction. As the app grows, this becomes unmaintainable.

**Action**: Refactor into Blueprints:
```
routes/
├── workspace.py   # /, /workspace, /api/analyze, /api/chat, /api/search, /api/export-pdf
├── studio.py      # /studio, /api/templates, /api/extract, /api/save
└── upload.py      # /api/upload
```

> [!WARNING]
> This is a significant refactor. Should be done in isolation with a verification pass against all routes.

---

### 🟡 Low — Cleanup

#### #7. Remove dead directories

`langextract-gui/` contains a separate `.git`, `.gitmodules`, and `AGENTS.md` — a legacy submodule or copy. `front-end-reference/` has old HTML mockups. Neither is referenced by the running app.

**Action**: Decide to either:
- Remove both directories entirely
- Add them to `.gitignore` if they serve as local reference
- If `langextract-gui/` is a submodule, re-register it properly with `git submodule add`

---

#### #8. Deduplicate `escapeHtml` / `escapeHTML`

**Files**:
- [workspace.html](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/templates/workspace.html) → `function escapeHtml(str)`
- [studio.js](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/static/studio.js) → `function escapeHTML(str)`

Both perform identical HTML escaping with different casing. Divergence will cause bugs.

**Action**: Create `static/utils.js` with a single exported `escapeHtml()`, then import it from both workspace.html and studio.js via `<script src>`.

---

#### #9. Consolidate vis.js to single source

**File**: [workspace.html](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/templates/workspace.html#L154)

Currently loads from CDN (`unpkg.com/vis-network`) while a local copy exists at `lib/vis-9.1.2/`. This risks version mismatches and breaks offline development.

**Action**: Switch `workspace.html` to the local copy:
```html
<script src="/lib/vis-9.1.2/vis-network.min.js"></script>
```

---

#### #11. Audit and remove unused `index.css`

**File**: [static/index.css](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/static/index.css) (371 lines)

Defines a complete dark-theme design system (`.app-layout`, `.left-panel`, `.right-panel`, modals, etc.) but `workspace.html` uses Tailwind exclusively. This appears to be from an earlier iteration.

**Action**: Search all templates for `index.css` references. If none, remove the file. If used by a page (e.g., a previous dark-mode workspace), archive it under `front-end-reference/`.

---

#### #12. Replace hardcoded user profile

**File**: [workspace.html](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/templates/workspace.html#L233-L239)

The header displays a static "Alex Chen / Pro Plan" with a real Google-hosted profile image URL. This is misleading for any deployment.

**Action**: Replace with a generic avatar (initials-based SVG or Material icon) and placeholder name, or wire up to a real auth system.

---

#### #17. Move or remove `download_screens.py`

**File**: [download_screens.py](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/download_screens.py) (1.5KB)

An orphan utility script at the project root. Not referenced by the application.

**Action**: Move to `scripts/download_screens.py` if it's still useful, or delete it.

---

### 🟡 Low — Frontend Quality

#### #13. Add `<meta name="description">` to all pages

**Files**: All templates in `templates/`

No HTML page has a meta description. This hurts SEO and is a best practice for any public-facing page.

**Action**: Add to each template's `<head>`:
```html
<!-- home.html -->
<meta name="description" content="langextract — AI-powered knowledge graph extraction and visualization from text and PDFs.">

<!-- workspace.html -->
<meta name="description" content="langextract Workspace — Interactive knowledge graph editor with AI chat and semantic search.">

<!-- studio.html -->
<meta name="description" content="langextract HCI Studio — Schema-constrained document extraction with visual grounding and undo/redo.">

<!-- features.html -->
<meta name="description" content="langextract Features — Explore AI knowledge graph extraction, semantic search, and PDF export capabilities.">

<!-- pricing.html -->
<meta name="description" content="langextract Pricing — Plans for AI-powered knowledge graph extraction and document analysis.">
```

---

### 🟡 Low — Performance

#### #15. Optimize graph context in chat/search requests

**File**: [workspace.html](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/templates/workspace.html#L580-L593)

Every chat message serializes ALL nodes and edges and sends them as JSON. With a large graph (hundreds of nodes), this wastes bandwidth and increases latency.

**Action** (pick one):
1. **Cap the context**: Send at most 50 nodes + their connected edges
2. **Server-side session**: Store graph state in a Flask session or in-memory dict keyed by session ID; only send the session ID per request
3. **Incremental updates**: Send only new/changed nodes since the last request

---

---

### 🔵 DX — Developer Experience

#### #19. Add a test suite

No tests exist. For an app with extraction pipelines, fallback logic, and multiple API integrations, this is a significant risk.

**Action**: Create `tests/` directory with:

| Test file | What it covers | API needed? |
|-----------|---------------|-------------|
| `test_fallback_extractor.py` | Rule-based extraction, edge generation, highlights | No |
| `test_pdf_generator.py` | PDF generation doesn't crash with various inputs | No |
| `test_app_routes.py` | Flask test client — status codes, response shapes | No (mock Gemini) |

Add to `requirements.txt`:
```
pytest>=8.0.0
```

---

#### #20. Clean `__pycache__/` from git tracking

The `__pycache__/` directory at the project root may have been committed before the `.gitignore` rule was added.

**Action**:
```bash
git rm -r --cached __pycache__/
git rm -r --cached core/__pycache__/
git commit -m "chore: remove cached bytecode from tracking"
```

---

## Summary

| Status | Count | Items |
|--------|-------|-------|
| ✅ Done | 10 | #1, #2, #3, #4, #6, #10, #14, #16, #18, #21 |
| 🔲 Remaining | 11 | #5, #7, #8, #9, #11, #12, #13, #15, #17, #19, #20 |

### Priority order for remaining work:

1. **#5** Blueprint refactor (🟠 architectural debt — prevents scale)
2. **#19** Test suite (🔵 prevents regressions as you refactor)
3. **#8** Deduplicate escapeHtml (🟡 maintenance hazard)
4. **#9** Consolidate vis.js (🟡 offline reliability)
5. **#13** Meta descriptions (🟡 SEO, quick win)
6. **#15** Optimize graph context (🟡 performance at scale)
7. **#7, #11, #12, #17, #20** — Cleanup tasks (batch together)
