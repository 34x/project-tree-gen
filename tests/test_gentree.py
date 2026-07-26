# Test suite — unit tests for tree generation, comment extraction, and config loading.
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

"""pytest tests for project-tree-gen helpers, grouped per concern."""

from __future__ import annotations

import tempfile
import tomllib
from pathlib import Path

from project_tree_gen._comment import (
    _strip_agent_guidelines_suffix,
    _clean_heading,
    _drop_redundant,
    file_comment,
)
from project_tree_gen._config import load_config
from project_tree_gen._tree import (
    _drop_child_duplicate,
    is_excluded,
    Node,
    prune_empty,
    render,
)
from project_tree_gen._cli import _resolve_depth


# ── strip_suffix ──────────────────────────────────────────────────────────────


def test_strip_suffix() -> None:
    cases = (
        ("rudy-common -- Agent Guidelines", "rudy-common"),
        ("rudy-tg-bot - Agent guidelines", "rudy-tg-bot"),
        ("Foo", "Foo"),
        ("`bar`", "`bar`"),
    )
    for raw, want in cases:
        assert _strip_agent_guidelines_suffix(raw) == want, f"strip({raw!r})"


# ── clean_heading ─────────────────────────────────────────────────────────────


def test_clean_heading() -> None:
    assert _clean_heading("`rudy-common` -- Agent Guidelines") == "rudy-common"


# ── is_excluded ───────────────────────────────────────────────────────────────


def test_is_excluded() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.log").write_text("x")
        (root / "Cargo.lock").write_text("x")
        (root / "docs").mkdir()
        (root / "docs" / "tasks").mkdir()
        (root / "docs" / "tasks" / "00001-x").mkdir()

        assert is_excluded(Path("a.log"), ["*.log"], [])
        assert is_excluded(Path("Cargo.lock"), [], [])
        assert is_excluded(Path("docs/tasks/00001-x"), ["docs/tasks/*"], [])
        assert not is_excluded(Path("docs/healthcheck"), ["docs/tasks/*"], [])


# ── load_config ───────────────────────────────────────────────────────────────


def test_load_config() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "gentree.toml"
        cfg.write_text(
            "[depth]\n"
            'default = 2\n'
            '"AGENTS.md" = 3\n'
            "\n"
            "[exclude]\n"
            'patterns = ["*.log", "docs/tasks/*"]\n'
            "\n"
            "[exclude_from_tree]\n"
            'patterns = ["mod.rs", "__init__.py"]\n'
            "\n"
            "[comments]\n"
            '"crates/rudy" = "core crate"\n'
            '"docs" = "workspace docs"\n'
            "\n"
            "[comment_sources]\n"
            'patterns = ["mod.rs", "<dirname>.rs", "lib.rs", "main.rs"]\n'
        )
        (excludes, overrides, depth_cfg, comment_sources, exclude_from_tree) = load_config(cfg)

        assert "*.log" in excludes
        assert "docs/tasks/*" in excludes
        assert overrides.get("crates/rudy") == "core crate"
        assert overrides.get("docs") == "workspace docs"
        assert depth_cfg.get("default") == 2
        assert depth_cfg.get("AGENTS.md") == 3
        assert "mod.rs" in comment_sources
        assert "mod.rs" in exclude_from_tree
        assert "__init__.py" in exclude_from_tree


# ── resolve_depth ────────────────────────────────────────────────────────────


def test_resolve_depth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        Path(root / "AGENTS.md").touch()
        Path(root / "crates" / "rudy").mkdir(parents=True)
        Path(root / "crates" / "rudy" / "AGENTS.md").touch()
        cfg = {"./AGENTS.md": 4, "default": 2}
        root_md = root / "AGENTS.md"
        crate_md = root / "crates" / "rudy" / "AGENTS.md"

        assert _resolve_depth(root_md, cfg, None, root) == 4
        assert _resolve_depth(crate_md, cfg, None, root) == 2
        assert _resolve_depth(crate_md, cfg, 7, root) == 7


# ── prune_empty ──────────────────────────────────────────────────────────────


def test_prune_empty() -> None:
    leaf = Node("leaf/", True, None)
    leaf.capped = True
    parent = Node("parent/", True, None)
    parent.children = [leaf]
    kept = prune_empty([parent])
    assert len(kept) == 1 and kept[0].children == [leaf]

    not_capped = Node("x/", True, None)
    assert prune_empty([not_capped]) == []


# ── drop_redundant ─────────────────────────────────────────────────────────────


def test_drop_redundant() -> None:
    assert _drop_redundant("rudy-common", "rudy-common") is None
    assert _drop_redundant("Rudy-Common", "rudy-common") is None
    assert _drop_redundant("Pure helpers", "rudy-common") == "Pure helpers"


# ── drop_child_duplicate ──────────────────────────────────────────────────────


def test_drop_child_duplicate() -> None:
    desc = "gentree -- regenerate the tree block"
    dir_node = Node("gentree/", True, desc)
    matching_child = Node("README.md", False, desc)
    other_child = Node("main.py", False, "entry point")

    # No children yet: cannot match any file comment, so the dir's comment is kept.
    assert _drop_child_duplicate(desc, dir_node) == desc

    dir_node.children = [matching_child]
    assert _drop_child_duplicate(desc, dir_node) is None

    dir_node.children = [matching_child, other_child]
    assert _drop_child_duplicate(desc, dir_node) is None

    # Case-insensitive: with matching child present, must drop.
    case_ins_dir = Node("gentree/", True, desc)
    case_ins_dir.children = [Node("README.md", False, "GENTREE -- regenerate the tree block")]
    assert _drop_child_duplicate(desc, case_ins_dir) is None

    dir_node.children = [other_child]
    assert _drop_child_duplicate(desc, dir_node) == desc


# ── file_comment ──────────────────────────────────────────────────────────────


def test_file_comment() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rs = root / "text.rs"
        rs.write_text("//! text helpers\n\npub fn x() {}\n")
        md = root / "README.md"
        md.write_text("# Notes -- Agent Guidelines\n\nbody\n")
        bare = root / "data.json"
        bare.write_text("{}")

        assert file_comment(rs) == "text helpers"
        assert file_comment(md) == "Notes"
        assert file_comment(bare) is None

        stem_match = root / "Notes.md"
        stem_match.write_text("# Notes -- Agent Guidelines\n\nbody\n")
        assert file_comment(stem_match) is None


# ── render ───────────────────────────────────────────────────────────────────


def test_render() -> None:
    tree = [
        Node("a/", True, "alpha"),
        Node("b/", True, "beta is longer"),
        Node("c.rs", False, "c-comment"),
    ]
    tree[1].children = [Node("very_long_inner_name.rs", False, "deep comment")]
    rendered = render(tree)
    hash_cols = [line.index("#") for line in rendered.splitlines() if "#" in line]
    assert len(set(hash_cols)) == 1

    bare_tree = [Node("x/", True, None), Node("y.rs", False, None)]
    assert "#" not in render(bare_tree)
