# Tree rendering — walk, prune, and render the directory structure as ASCII art.
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

"""Tree building and rendering — walk a directory tree and render it as text."""

from __future__ import annotations

import re
from pathlib import Path

from project_tree_gen._comment import dir_comment, file_comment
from project_tree_gen._defaults import DEFAULT_EXCLUDE

# Box-drawing constants.
CONNECTOR_BRANCH = "├── "
CONNECTOR_LAST = "└── "
INDENT_CONT = "│   "


def is_excluded(
    rel_path: Path, ignores: list[str], exclude_from_tree: list[str]
) -> bool:
    """True if *rel_path* should be excluded.

    All patterns (default + config) are matched as regex against both the
    basename and the full relative path.
    """
    all_patterns = DEFAULT_EXCLUDE + tuple(ignores) + tuple(exclude_from_tree)
    name = rel_path.name
    return any(re.search(p, name) for p in all_patterns) or \
           any(re.search(p, str(rel_path)) for p in all_patterns)


def sort_key(p: Path) -> tuple[int, str]:
    """Dirs first, then files, both alphabetical (case-insensitive)."""
    return (0 if p.is_dir() else 1, p.name.lower())


class Node:
    """Tree node: a directory or file with an optional comment.

    For directories, *comment* is resolved by ``dir_comment`` (sidecar override →
    mod.rs/lib.rs/main.rs ``//!`` → AGENTS.md/README.md heading). For files, it
    is resolved by ``file_comment`` (``.rs`` ``//!`` line or ``.md`` first heading,
    nothing for other extensions). An empty/``None`` comment is rendered as a
    bare name with no ``# `` suffix.

    *capped* is True when the directory has children on disk but we stopped
    recursing because the depth limit was reached. The render layer uses this
    to suppress the "has children" indent and the pruning layer uses it to
    keep the node visible.
    """

    __slots__ = ("name", "comment", "children", "is_dir", "capped")

    def __init__(self, name: str, is_dir: bool, comment: str | None) -> None:
        self.name = name
        self.is_dir = is_dir
        self.comment = comment
        self.children: list[Node] = []
        self.capped = False


def _drop_child_duplicate(comment: str, node: Node) -> str | None:
    """Return *comment* unless a direct child file's comment is identical.

    A directory's comment is noise if the same words also appear as the
    comment for a file in that directory (e.g. ``gentree/ README.md`` echoes
    the ``gentree/`` folder's description verbatim). Comparison is
    case-insensitive on the stripped forms.
    """
    if not node.children:
        return comment
    for child in node.children:
        if child.is_dir:
            continue
        if not child.comment:
            continue
        if child.comment.strip().lower() == comment.strip().lower():
            return None
    return comment


def build_tree(
    root: Path,
    depth: int,
    ignores: list[str],
    overrides: dict[str, str],
    comment_sources: list[str],
    exclude_from_tree: list[str],
) -> list[Node]:
    """Build the top-level Node list representing the tree at *root*.

    The synthetic root node (named ``.``) is returned as a list containing a
    single Node, so renderers can walk it like any other subtree.
    """
    root_node = Node(".", True, None)
    _populate(
        root_node, root, root, depth, ignores, overrides, comment_sources,
        exclude_from_tree,
    )
    root_node.children = prune_empty(root_node.children)
    return [root_node]


def _populate(
    node: Node,
    dir_path: Path,
    root: Path,
    remaining: int,
    ignores: list[str],
    overrides: dict[str, str],
    comment_sources: list[str],
    exclude_from_tree: list[str],
) -> None:
    if remaining <= 0:
        return
    for entry in sorted(dir_path.iterdir(), key=sort_key):
        rel = entry.relative_to(root)
        if is_excluded(rel, ignores, exclude_from_tree):
            continue
        if entry.is_dir():
            child = Node(
                entry.name + "/",
                True,
                dir_comment(entry, str(rel), overrides, comment_sources),
            )
            node.children.append(child)
            if remaining - 1 <= 0:
                has_visible = any(
                    not is_excluded(c.relative_to(root), ignores, exclude_from_tree)
                    for c in entry.iterdir()
                )
                if has_visible:
                    child.capped = True
            else:
                _populate(
                    child, entry, root, remaining - 1, ignores, overrides,
                    comment_sources, exclude_from_tree,
                )
            if child.comment is not None:
                child.comment = _drop_child_duplicate(child.comment, child)
        else:
            comment = overrides.get(entry.name, file_comment(entry))
            node.children.append(Node(entry.name, False, comment))


def prune_empty(nodes: list[Node]) -> list[Node]:
    """Recursively drop directory nodes whose children list is empty.

    ``capped`` directories are never pruned even if their children list is
    empty: they have children on disk, we just didn't render them because
    the depth limit was reached.
    """
    kept: list[Node] = []
    for n in nodes:
        if n.is_dir:
            n.children = prune_empty(n.children)
            if not n.children and not n.capped:
                continue
        kept.append(n)
    return kept


def render(nodes: list[Node]) -> str:
    """Render a tree starting from *nodes* (typically the synthetic root)."""
    lines: list[str] = []
    global_width = _global_line_width(nodes) + 1
    for node in nodes:
        if node.name == ".":
            lines.append("./")
            if node.children:
                child_prefix = ""
                for i, child in enumerate(node.children):
                    _render_node(
                        child,
                        child_prefix,
                        i == len(node.children) - 1,
                        lines,
                        global_width,
                    )
        else:
            _render_node(node, "", True, lines, global_width)
    return "\n".join(lines) + "\n"


def _global_line_width(nodes: list[Node]) -> int:
    """Max width of ``prefix + connector + name`` across the whole tree."""
    width = 0
    stack: list[tuple[Node, str]] = [(n, "") for n in nodes]
    while stack:
        node, prefix = stack.pop()
        line_len = len(prefix) + len(CONNECTOR_BRANCH) + len(node.name)
        if line_len > width:
            width = line_len
        child_prefix = prefix + INDENT_CONT
        for child in node.children:
            stack.append((child, child_prefix))
    return width


def _render_node(
    node: Node, prefix: str, is_last: bool, out: list[str], pad_width: int
) -> None:
    connector = CONNECTOR_LAST if is_last else CONNECTOR_BRANCH
    base = f"{prefix}{connector}{node.name}"
    pad = max(pad_width - len(base), 0)
    if node.comment:
        out.append(f"{base}{' ' * pad} # {node.comment}")
    else:
        out.append(base)

    if not node.children:
        return
    child_prefix = prefix + (INDENT_CONT if not is_last else "    ")
    for i, child in enumerate(node.children):
        _render_node(child, child_prefix, i == len(node.children) - 1, out, pad_width)
