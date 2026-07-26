# Project Tree Gen

## Folder structure

```
./
├── src/
│   └── project_tree_gen/      # Silent automation tool that regenerates `## Folder structure` tree blocks in AGENTS.md files.
│       ├── __main__.py        # Module invocation entry point — runs the CLI when invoked via `python -m`.
│       ├── _agents.py         # AGENTS.md integration — locate, validate, and update the folder-structure tree block.
│       ├── _cli.py            # CLI entry point — argument parsing and orchestration.
│       ├── _comment.py        # Comment resolution — resolve directory and file comments from source files.
│       ├── _config.py         # Config loading — read gentree.toml into structured data.
│       ├── _defaults.py       # Default exclude patterns for file system traversal (regex).
│       ├── _extract.py        # Source extraction — pull the first doc line from various file types.
│       └── _tree.py           # Tree rendering — walk, prune, and render the directory structure as ASCII art.
├── tests/
│   └── test_gentree.py        # Test suite — unit tests for tree generation, comment extraction, and config loading.
├── AGENTS.md                  # Instructions for LLM agents
├── gentree.toml               # Project configuration — tree depth, exclusions, and per-directory annotations for AGENTS.md regeneration.
├── gentree.toml.example       # Example configuration with custom descriptions and annotations
├── LICENSE
├── pyproject.toml
└── README.md                  # project-tree-gen
```
