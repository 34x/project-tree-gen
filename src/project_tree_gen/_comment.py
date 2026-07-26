# Comment resolution — resolve directory and file comments from source files.
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

"""Comment resolution — resolve directory and file comments from source files."""

from __future__ import annotations

from pathlib import Path

from project_tree_gen._extract import first_doc_line


# Suffixes stripped from AGENTS.md headings before using them as a comment.
# Order matters: longest / most specific first.
_AGENT_GUIDELINES_SUFFIXES: tuple[str, ...] = (
    " -- Agent Guidelines",
    " - Agent Guidelines",
    " -- agent guidelines",
    " - agent guidelines",
    " -- Agent guidelines",
    " - Agent guidelines",
)


def _strip_agent_guidelines_suffix(heading: str) -> str:
    """Remove a trailing ``-/-- Agent Guidelines`` boilerplate from a heading."""
    for suffix in _AGENT_GUIDELINES_SUFFIXES:
        if heading.endswith(suffix):
            return heading[: -len(suffix)].rstrip()
    return heading


def _clean_heading(heading: str) -> str:
    """Strip surrounding backticks and AGENTS.md boilerplate from a heading.

    The result is a human-readable description suitable for the rendered tree
    (e.g. `` `rudy-common` -- Agent Guidelines `` → ``rudy-common``).
    """
    s = heading.strip()
    s = _strip_agent_guidelines_suffix(s)
    if s.startswith("`") and s.endswith("`") and len(s) >= 2:
        s = s[1:-1].strip()
    return s


def _drop_redundant(comment: str, dirname: str) -> str | None:
    """Return *comment* unless it merely restates *dirname*.

    A comment like ``rudy-common`` for the ``rudy-common/`` directory is noise —
    the name is already on the line. Comparison is case-insensitive.
    """
    if comment.strip().lower() == dirname.strip().lower():
        return None
    return comment


def dir_comment(
    d: Path, rel_path: str, overrides: dict[str, str], comment_sources: list[str]
) -> str | None:
    """Best comment for directory *d* (comment-source files, AGENTS.md, README.md).

    Lookup order (first match wins):
      1. Sidecar override (key = *rel_path*)
      2. First comment line of a comment-source file (patterns from config,
         with ``<dirname>`` replaced by ``d.name``)
      3. AGENTS.md ``#`` heading (boilerplate suffix stripped)
      4. README.md ``#`` heading

    A resolved comment that just repeats the directory name is suppressed.
    Sidecar overrides always win.
    """
    if rel_path in overrides:
        return overrides[rel_path]
    for pattern in comment_sources:
        filename = pattern.replace("<dirname>", d.name)
        candidate = d / filename
        if candidate.is_file():
            comment = first_doc_line(candidate)
            if comment:
                return _drop_redundant(comment, d.name)
    for candidate in (d / "AGENTS.md", d / "README.md"):
        if candidate.is_file():
            heading = first_doc_line(candidate)
            if heading:
                cleaned = _clean_heading(heading)
                if cleaned:
                    return _drop_redundant(cleaned, d.name)
    return None


def file_comment(path: Path) -> str | None:
    """Best comment for a single file (extension-based prefix stripping).

    Returns ``None`` for extensions we don't document, or when the file has
    no top-level comment. A comment that matches the file stem is dropped.
    """
    line = first_doc_line(path)
    if line is None:
        return None
    if path.suffix == ".md":
        line = _clean_heading(line)
        if not line:
            return None
    return _drop_redundant(line, path.stem)
