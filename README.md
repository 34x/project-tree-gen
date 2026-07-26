# project-tree-gen

Regenerate the `## Folder structure` tree block in `AGENTS.md` files.
A silent workspace hygiene tool — the tree blocks it produces are checked into
the repo, and a drifting tree is caught at code review (or by a future CI hookup).
### Problem & Solution

**The Problem:** Project trees in documentation drift out of sync with the actual codebase, and LLM-generated trees often suffer from inconsistent indentation or hallucinated descriptions. Additionally, asking an LLM to update multiple files is slow and costly.

**The Solution:** `project-tree-gen` automates this workflow using a deterministic CLI tool. It parses the actual filesystem to guarantee 100% accuracy, enriches the tree with real descriptions from module docstrings (or config), and instantly updates all `AGENTS.md` files in one command.

## Installation

**UV - simplest, suggested**

```bash
uv tool install git+https://github.com/34x/project-tree-gen.git
```

**Pip**

```bash
git clone git@github.com:34x/project-tree-gen.git
cd project-tree-gen
pip install -e ".[dev]"
```

## Usage

```bash
# Update every AGENTS.md in the project — depth from config (default = 2).
project-tree-gen --config gentree.toml

# Update a specific file with a different depth (CLI overrides config).
project-tree-gen --config gentree.toml crates/rudy-common/AGENTS.md --depth 3

# Run as a module
python -m project_tree_gen --config gentree.toml

# Run self-tests
pytest
```

## How it works

The script walks the project tree, finds every `AGENTS.md` file, and replaces
the fenced code block immediately following a `## Folder structure` heading.
The script **aborts** if the heading is missing — add it manually the first
time a file adopts the convention, and the script will fill in the block on
the next run.

### Comment sources

For each directory in the tree, the comment is resolved in this order (first
match wins):

1. **Sidecar override** — entry in `gentree.toml` `[comments]` section.
2. **First `//!` line** of `mod.rs`, or `<dirname>.rs`.
3. **First `//!` line** of `lib.rs` / `main.rs`.
4. **First `#` heading** of a co-located `AGENTS.md` (with the
   `— Agent Guidelines` boilerplate suffix stripped).
5. **First `#` heading** of a co-located `README.md`.
6. **No comment** — directory appears without a description (unless the
   resolved comment is identical to the directory name, case-insensitive,
   in which case it is dropped to avoid redundancy).

For each file (only `.rs` and `.md` get comments by default):

- `.rs` → first `//!` line
- `.md` → first `#` heading (with the `— Agent Guidelines` boilerplate
  suffix stripped)
- other extensions → no comment

A file comment that ends up identical to the file stem is dropped.

### Comment-source patterns

`gentree.toml` `[comment_sources].patterns` controls which files inside a
directory are inspected for the parent directory's comment (steps 2–3 above).
Defaults: `mod.rs`, `<dirname>.rs`, `lib.rs`, `main.rs`. The `<dirname>`
placeholder is replaced with the actual directory name at runtime, so
`<dirname>.rs` matches `foo.rs` inside `foo/`.

### Alignment

All comments in the tree align to a **single global column** — the longest
`name` in the entire tree, plus one space before the ` # ` separator. The
padding is the global max minus the current `name`'s length, so every ` #`
across the whole tree sits at the same column.

### Skip rules

The tool always skips a set of default patterns (defined in [`src/project_tree_gen/_defaults.py`](src/project_tree_gen/_defaults.py)): `.git/`, `target/`, `node_modules/`, `snapshots/`, `.venv/`, `__pycache__/`, and all lock files (`Cargo.lock`, `uv.lock`, `package-lock.json`, etc.).

Plus anything matching `gentree.toml` `[exclude].patterns`. Patterns are
**regular expressions** matched against both the basename and the full
relative path, so `'.*\.log$'` matches any file ending in `.log` at any level.

`AGENTS.md` is **not** hard-excluded — list it in `[exclude].patterns` to
drop it from a tree.

## Configuration (`gentree.toml`)

A fully annotated example config lives at
[`gentree.toml.example`](gentree.toml.example) — copy it to your project root
and adapt:

```bash
cp gentree.toml.example gentree.toml
```

Key sections at a glance:

  - **`[depth]`** — controls how many directory levels the tree shows.
    - `default = 2` → root + immediate children + grandchildren.
    - `default = 1` → only immediate children of the root.
    - `default = 5` → five levels deep.
    - CLI `--depth` overrides the config value for that run.
    - **Per-file depth overrides** let you set a different depth for a specific
      `AGENTS.md` file. The key is the file's path relative to the project root:
      ```toml
      [depth]
      default = 2
      "crates/rudy/AGENTS.md" = 4
      ```
      This means: the root `AGENTS.md` uses depth 2, but when the generator
      processes `crates/rudy/AGENTS.md`, it starts from the **directory
      containing that file** (`crates/rudy/`) and traverses **4 levels down**
      from there. So `crates/rudy/` shows its children, grandchildren,
      great-grandchildren, and great-great-grandchildren — a deeper view of
      that subtree than the root tree provides.
  - **`[exclude]`** — regex patterns for files/directories to skip entirely
    (matched against both basename and full relative path).
  - **`[exclude_from_tree]`** — regex patterns for files hidden from the
    rendered tree but still read as comment sources (e.g. `mod.rs`,
    `__init__.py`).
  - **`[comment_sources]`** — literal filenames (not regex) whose first
    docstring line becomes the parent directory's tree annotation. The
    `<dirname>` placeholder is replaced with the actual directory name at
    runtime.
  - **`[comments]`** — sidecar overrides for directory comments. These take
    highest priority, winning over any docstring or README/AGENTS.md heading.

## Tests

```bash
uv run pytest
```

Exercises the parser, aligner, and tree walker against a temporary fixture
tree.

## License

GNU General Public License v3.0 or later. See `LICENSE`.
