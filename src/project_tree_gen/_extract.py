# Source extraction — pull the first doc line from various file types.
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

"""File-type comment extractors — dispatch by filename or extension."""

from __future__ import annotations

import re
from pathlib import Path


def _extract_by_prefix(
    text: str, prefixes: list[str], skip_shebang: bool = False
) -> str | None:
    """Find the first non-empty line matching one of the given prefixes.

    If *skip_shebang* is True, lines starting with ``#!`` are skipped.
    If the first non-empty line does not match any prefix, returns None.
    """
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if skip_shebang and stripped.startswith("#!"):
            continue
        for prefix in prefixes:
            if stripped.startswith(prefix):
                v = stripped[len(prefix) :].strip()
                return v or None
        return None
    return None


def extract_rs(text: str) -> str | None:
    """First ``//!`` or ``///`` doc comment line from a Rust source file."""
    return _extract_by_prefix(text, ["//! ", "//!", "/// ", "///", "// ", "//"])


def extract_py(text: str) -> str | None:
    """First docstring or ``#`` comment line from a Python file.

    Docstrings (``\"\"\"`` / ``'''``) are preferred over ``#`` comments so that
    the module-level docstring is used instead of a license header.
    """
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#!"):
            continue
        for delim in ('"""', "'''"):
            if stripped.startswith(delim):
                v = stripped[len(delim) :]
                if v.endswith(delim) and len(v) >= len(delim):
                    v = v[: -len(delim)]
                v = v.strip()
                return v or None
        # No docstring found on the first non-empty line — fall through to # comment.
        if stripped.startswith("#"):
            v = stripped[1:].strip()
            return v or None
        return None
    return None


def extract_sh(text: str) -> str | None:
    """First ``#`` comment from a shell script (skipping the shebang)."""
    return _extract_by_prefix(text, ["# ", "#"], skip_shebang=True)


def extract_jinja(text: str) -> str | None:
    """First ``{#`` or ``#`` comment from a Jinja2 template."""
    return _extract_by_prefix(text, ["{# ", "{#", "# ", "#"])


def extract_md(text: str) -> str | None:
    """First ``#`` heading from a Markdown file, skipping YAML front matter."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                start = i + 1
                break
    for raw in lines[start:]:
        m = re.match(r"\s*#\s+(.*)", raw)
        if m:
            v = m.group(1).strip()
            return v or None
    return None


def extract_toml(text: str) -> str | None:
    """First ``#`` comment from a TOML file."""
    return _extract_by_prefix(text, ["# ", "#"])


def extract_yaml(text: str) -> str | None:
    """First ``#`` comment from a YAML file."""
    return _extract_by_prefix(text, ["# ", "#"])


def extract_justfile(text: str) -> str | None:
    """First ``#`` comment from a justfile."""
    return _extract_by_prefix(text, ["# ", "#"])


extract_yml = extract_yaml


_EXTRACTORS: dict[str, callable[[str], str | None]] = {
    ".rs": extract_rs,
    ".py": extract_py,
    ".sh": extract_sh,
    ".jinja": extract_jinja,
    ".md": extract_md,
    ".toml": extract_toml,
    ".yaml": extract_yaml,
    ".yml": extract_yml,
    "justfile": extract_justfile,
}


def first_doc_line(path: Path) -> str | None:
    """First comment line of a file, dispatched by filename then extension.

    Looks up the extractor for ``path.name`` first (for files like
    ``justfile`` that have no suffix), then ``path.suffix``. Returns None
    for unregistered filenames and suffixes.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    extractor = _EXTRACTORS.get(path.name) or _EXTRACTORS.get(path.suffix)
    if extractor is None:
        return None
    return extractor(text)
