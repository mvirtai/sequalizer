# Sequalizer — Design Document

## 1. Vision

Sequalizer is a terminal-based SQL practice tool.
It presents the user with randomized exercises and provides an interactive
SQL input with real-time keyword highlighting. Queries run against the
Chinook sample database and results are displayed in a clean, formatted view.

The goal is to make SQL practice feel like using a lightweight IDE in the
terminal — immediate, colorful, and focused.

### Target User

Someone learning SQL who wants hands-on practice with a real relational
database, with instant feedback in the terminal.

---

## 2. Core Features (MVP)

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Random exercises** | Display a random SQL exercise as a natural-language prompt |
| 2 | **Syntax-highlighted input** | SQL keywords (SELECT, FROM, WHERE, etc.) are colored as the user types |
| 3 | **Query execution** | Run the user's query against Chinook and show results |
| 4 | **Result display** | Show query results in a formatted table with row count |
| 5 | **Exercise flow** | After results, show the reference solution, then offer the next exercise |

### Out of Scope (for now)

- Automatic answer validation (comparing user query output to expected output)
- Difficulty levels / scoring
- Query history persistence
- Multi-database support

---

## 3. Technical Decisions

### 3.1 Why `prompt_toolkit` for input?

The key requirement is **real-time syntax highlighting as the user types**.
Standard `input()` only returns text after Enter is pressed — there is no way
to color individual characters during typing.

`prompt_toolkit` is a Python library for building interactive command-line
applications. It supports:

- **Custom lexers / syntax highlighting** — integrates directly with Pygments
- **Multi-line input** — SQL queries often span multiple lines
- **Key bindings** — e.g. Enter for newline, Alt+Enter or Ctrl+D to submit
- **History** — previous inputs accessible with arrow keys

This is the same library that powers IPython, pgcli, and litecli.

**Trade-off:** It is a meaningful dependency (~15k lines), but it is
well-maintained, widely used, and teaches you how real CLI tools work.

### 3.2 Why `pygments` for the SQL lexer?

Pygments provides a battle-tested `SqlLexer` that correctly tokenizes SQL
keywords, strings, numbers, operators, and comments. Writing a custom lexer
would be educational but error-prone and not the focus of this project.

`prompt_toolkit` has built-in Pygments integration, so combining them is
straightforward.

### 3.3 Why `rich` for output?

Rich provides formatted tables, panels, and colored text for displaying
query results and exercise prompts. It is already familiar from other
projects in this workspace.

### 3.4 Database access

SQLite via the Python standard library `sqlite3`. No ORM — raw SQL is the
whole point. The existing `DatabaseManager` context manager pattern from
`chinook_dataset` will be adapted for this project.

---

## 4. Architecture

```
sequalizer/
├── docs/
│   ├── DESIGN.md              # This document
│   └── EXERCISES.md           # Exercise design guide (Phase 2)
├── data/
│   └── Chinook_Sqlite.sqlite  # Chinook database (copied from chinook_dataset)
├── src/
│   └── sequalizer/
│       ├── __init__.py
│       ├── app.py             # Main application loop
│       ├── database.py        # Database connection manager
│       ├── exercises.py       # Exercise definitions and selection
│       └── display.py         # Result formatting and output
├── pyproject.toml
└── README.md
```

### Module Responsibilities

#### `app.py` — Main Application Loop

The entry point. Orchestrates the exercise–input–execute–display cycle:

```
┌─────────────────────────────────────────┐
│  1. Show welcome message                │
│  2. Pick random exercise                │
│  3. Display exercise prompt             │
│  4. Accept SQL input (highlighted)      │
│  5. Execute query against Chinook       │
│  6. Display results                     │
│  7. Show reference solution             │
│  8. Ask: next exercise or quit?         │
│  └── Loop back to step 2               │
└─────────────────────────────────────────┘
```

#### `database.py` — Database Connection Manager

A context manager wrapping `sqlite3`. Responsibilities:

- Resolve path to the SQLite file
- Open/close connections cleanly
- Execute queries and return results with column names
- Handle SQL errors gracefully (return error message, don't crash)

#### `exercises.py` — Exercise Definitions

Stores exercise data and handles random selection. Each exercise is a
data structure containing:

```python
{
    "id": "artist_starts_with",
    "prompt": "Find all artist names that start with the letter 'B'.",
    "hint": "Use the LIKE operator with a wildcard.",
    "tables": ["Artist"],
    "difficulty": "easy",
    "reference_sql": "SELECT Name FROM Artist WHERE Name LIKE 'B%';",
    "concepts": ["SELECT", "WHERE", "LIKE"]
}
```

#### `display.py` — Result Formatting

Handles all output rendering using Rich:

- Exercise prompt panel
- Query result tables (with column headers)
- Error messages
- Reference solution display

---

## 5. Data Flow

```
User sees exercise prompt
        │
        ▼
User types SQL ──► prompt_toolkit ──► real-time highlighting
        │                               (Pygments SqlLexer)
        │
   Ctrl+D / Alt+Enter (submit)
        │
        ▼
  database.py executes query
        │
        ├── Success ──► display.py shows result table
        │                    │
        │                    ▼
        │               Show reference SQL
        │                    │
        │                    ▼
        │               Next exercise? (y/n)
        │
        └── Error ──► display.py shows error message
                           │
                           ▼
                      Try again (same exercise)
```

---

## 6. Key Bindings

| Key | Action |
|-----|--------|
| Regular typing | SQL input with live highlighting |
| Enter | New line (SQL queries are often multi-line) |
| Alt+Enter | Submit the query |
| Ctrl+D | Submit the query (alternative) |
| Ctrl+C | Cancel current input / exit |

**Why multi-line by default?**
SQL queries often span multiple lines for readability. Single-line input
would force users to write everything on one line, which is bad practice.
`prompt_toolkit` handles this naturally.

---

## 7. Implementation Phases

Each phase is a self-contained, working increment. Complete one phase
fully before starting the next.

### Phase 1: Project Setup

**Goal:** Working project structure with dependencies, runnable entry point.

Tasks:
- [ ] Initialize project with `uv init`
- [ ] Add dependencies: `prompt_toolkit`, `pygments`, `rich`
- [ ] Copy Chinook database to `data/`
- [ ] Create package structure (`src/sequalizer/`)
- [ ] Create `__init__.py`
- [ ] Create minimal `app.py` that prints "Sequalizer" and exits
- [ ] Verify: `uv run python -m sequalizer.app` works

**Learning focus:** Project structure, package layout, dependency management.

---

### Phase 2: Database Module

**Goal:** A clean database module that can execute queries and return results.

Tasks:
- [ ] Create `database.py` with a context manager class
- [ ] Implement `execute_query(sql)` → returns `(columns, rows)` or error
- [ ] Handle `sqlite3.OperationalError` gracefully
- [ ] Test manually: connect, run `SELECT * FROM Artist LIMIT 5`

**Learning focus:** Context managers (`__enter__`/`__exit__`), error handling,
`sqlite3` cursor metadata (`.description` for column names).

---

### Phase 3: Highlighted SQL Input

**Goal:** A prompt that accepts multi-line SQL with colored keywords.

Tasks:
- [ ] Create `sql_input.py` (or integrate into `app.py`)
- [ ] Set up `prompt_toolkit.PromptSession` with Pygments `SqlLexer`
- [ ] Configure multi-line mode (Enter = newline, Alt+Enter = submit)
- [ ] Add a visible prompt indicator (e.g., `SQL> ` on first line, `...` on continuation)
- [ ] Test: type `SELECT * FROM Artist` and verify keywords are colored

**Learning focus:** How `prompt_toolkit` works, what a lexer does, how
terminal applications handle key events.

---

### Phase 4: Exercise Definitions

**Goal:** A set of exercises that can be randomly selected and displayed.

Tasks:
- [ ] Define the exercise data structure (dataclass or TypedDict)
- [ ] Write 10–15 exercises covering different SQL concepts:
  - Basic SELECT
  - WHERE with conditions
  - LIKE / wildcards
  - ORDER BY
  - LIMIT
  - COUNT / aggregate functions
  - JOIN (two tables)
  - GROUP BY / HAVING
- [ ] Implement random selection (avoid repeats until all shown)
- [ ] Create `display.py` with exercise prompt rendering

**Learning focus:** Data modeling, dataclasses, the Chinook schema,
Rich panels/formatting.

---

### Phase 5: Main Loop (MVP Complete)

**Goal:** Wire everything together into the full exercise loop.

Tasks:
- [ ] Implement the main loop in `app.py` (see Section 4 flow)
- [ ] Show exercise → accept input → execute → show results
- [ ] Show reference solution after the user's attempt
- [ ] Handle errors (bad SQL) by letting the user retry
- [ ] Add quit command (Ctrl+C or typing `quit`)
- [ ] Add welcome/goodbye messages

**Learning focus:** Application architecture, control flow, user
experience in CLI tools.

---

### Phase 6: Polish

**Goal:** Make it feel good to use.

Tasks:
- [ ] Add `schema` command to show available tables and columns
- [ ] Add `hint` command to show exercise hint
- [ ] Improve result table formatting (truncate long values, align columns)
- [ ] Add exercise counter ("Exercise 3/15")
- [ ] Handle edge cases (empty results, very large results)

---

## 8. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `prompt_toolkit` | latest | Interactive input with syntax highlighting |
| `pygments` | latest | SQL tokenizer/lexer for highlighting |
| `rich` | latest | Output formatting (tables, panels, colors) |

All other functionality uses the Python standard library (`sqlite3`,
`dataclasses`, `random`, `pathlib`).

---

## 9. Open Questions

These are decisions to make as we build:

1. **Exercise validation** — Should we compare query *output* to expected
   output, or just show the reference SQL and let the user self-assess?
   (MVP: self-assess. Future: auto-validate.)

2. **Exercise storage** — Python dicts in code, or a separate JSON/YAML file?
   (Start with Python dicts. Move to file if the list grows large.)

3. **Scoring** — Track correct/incorrect? (Out of scope for MVP.)

4. **Entry point** — `python -m sequalizer` or a CLI command via
   `pyproject.toml` scripts? (Start with module, add CLI entry point later.)
