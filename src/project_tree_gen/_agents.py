# AGENTS.md integration — locate, validate, and update the folder-structure tree block.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""AGENTS.md integration — locate, validate, and update the folder-structure tree block."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from project_tree_gen._config import load_config
from project_tree_gen._tree import build_tree, render


def update_agents(path: Path, depth: int, config_path: Path, root: Path) -> None:
    """Replace the ``## Folder structure`` fenced block in *path*.

    *depth* is the resolved depth for this file (config override, CLI arg,
    or config default — already decided by the caller).
    *config_path* is the path to the gentree.toml configuration file.
    *root* is the project root directory for relative path resolution.
    """
    text = path.read_text(encoding="utf-8")
    heading_re = re.compile(r"^##\s+Folder\s+structure\s*\n", re.MULTILINE)
    m = heading_re.search(text)
    if not m:
        print(f"skipping {path}: no '## Folder structure' heading", file=sys.stderr)
        return
    fence_re = re.compile(r"```[^\n]*\n(?:.*?\n)?```", re.DOTALL)
    fence = fence_re.search(text, m.end())
    if not fence:
        print(
            f"error: {path}: no fenced code block after '## Folder structure'",
            file=sys.stderr,
        )
        sys.exit(1)

    ignores, overrides, _depth_config, comment_sources, exclude_from_tree = load_config(config_path)
    tree_nodes = build_tree(
        root, depth, ignores, overrides, comment_sources, exclude_from_tree,
    )
    tree = render(tree_nodes).rstrip("\n")

    new_block = f"```\n{tree}\n```"
    new_text = text[: fence.start()] + new_block + text[fence.end() :]
    path.write_text(new_text, encoding="utf-8")


def find_agents_files(root: Path, config_path: Path) -> list[Path]:
    """Find every AGENTS.md under *root*, excluding gentree.toml [exclude] matches."""
    ignores, _overrides, _depth_config, _comment_sources, _exclude_from_tree = load_config(config_path)
    out: list[Path] = []
    for p in sorted(root.rglob("AGENTS.md")):
        if any(p.match(g) for g in ignores):
            continue
        out.append(p)
    return out
