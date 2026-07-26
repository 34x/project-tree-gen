# Config loading — read gentree.toml into structured data.
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

"""Config loading — read gentree.toml into structured data."""

from __future__ import annotations

import re
from pathlib import Path

# Default comment-source patterns (used when gentree.toml has no
# [comment_sources] section). <dirname> is replaced with the actual
# directory name at runtime.
_DEFAULT_COMMENT_SOURCES = ["mod.rs", "<dirname>.rs", "lib.rs", "main.rs"]


def load_config(config_path: Path) -> tuple[
    list[str], dict[str, str], dict[str, int], list[str], list[str]
]:
    """Read a gentree.toml → (exclude_patterns, comment_overrides, depth_config, comment_sources, exclude_from_tree).

    The file has five sections:

        [depth]
        default = 2
        "AGENTS.md" = 3

        [exclude]
        patterns = ["docs/tasks/*", "*.log"]

        [exclude_from_tree]
        patterns = ["mod.rs", "__init__.py"]

        [comments]
        ".agents" = "agent skills (auto-loaded by clients)"
        "crates/rudy" = "core LLM agent"

        [comment_sources]
        patterns = ["mod.rs", "<dirname>.rs", "lib.rs", "main.rs"]

    Uses Python's stdlib tomllib (3.11+) and falls back to a minimal regex
    parser for older interpreters so the script works on either.
    """
    if not config_path.exists():
        return [], {}, {"default": 2}, list(_DEFAULT_COMMENT_SOURCES), []

    text = config_path.read_text(encoding="utf-8")

    try:
        import tomllib  # type: ignore[import-not-found]

        data = tomllib.loads(text)
        excludes: list[str] = list(data.get("exclude", {}).get("patterns", []))
        comments: dict[str, str] = {
            str(k): str(v) for k, v in data.get("comments", {}).items()
        }
        depth_raw = data.get("depth", {})
        depth_config: dict[str, int] = {
            str(k): int(v) for k, v in depth_raw.items()
        }
        depth_config.setdefault("default", 2)
        cs_raw = data.get("comment_sources", {})
        comment_sources: list[str] = list(
            cs_raw.get("patterns", _DEFAULT_COMMENT_SOURCES)
        )
        eft_raw = data.get("exclude_from_tree", {})
        exclude_from_tree: list[str] = list(eft_raw.get("patterns", []))
        return excludes, comments, depth_config, comment_sources, exclude_from_tree
    except ImportError:
        pass

    # Minimal fallback: parse sections manually.
    excludes: list[str] = []
    comments: dict[str, str] = {}
    depth_config: dict[str, int] = {"default": 2}
    comment_sources: list[str] = list(_DEFAULT_COMMENT_SOURCES)
    exclude_from_tree: list[str] = []
    section: str | None = None
    in_array = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            m = re.match(r'^\[([^\]]+)\]', line)
            section = m.group(1) if m else None
            in_array = False
            continue
        if section == "depth":
            m = re.match(r'^"([^"]+)"\s*=\s*(\d+)\s*$', line)
            if m:
                depth_config[m.group(1)] = int(m.group(2))
            elif line.startswith("default"):
                m2 = re.match(r'^default\s*=\s*(\d+)\s*$', line)
                if m2:
                    depth_config["default"] = int(m2.group(1))
        elif section in ("exclude", "exclude_from_tree"):
            if line.startswith("patterns"):
                in_array = "[" in line
                for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
                    if section == "exclude_from_tree":
                        exclude_from_tree.append(m.group(1))
                    else:
                        excludes.append(m.group(1))
            elif in_array:
                for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
                    if section == "exclude_from_tree":
                        exclude_from_tree.append(m.group(1))
                    else:
                        excludes.append(m.group(1))
                if "]" in line:
                    in_array = False
        elif section == "comments":
            m = re.match(
                r'^([A-Za-z0-9_./\-"\']+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', line
            )
            if m:
                comments[m.group(1).strip("\"'")] = m.group(2)
        elif section == "comment_sources":
            if line.startswith("patterns"):
                in_array = "[" in line
                for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
                    comment_sources.append(m.group(1))
            elif in_array:
                for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
                    comment_sources.append(m.group(1))
                if "]" in line:
                    in_array = False
    return excludes, comments, depth_config, comment_sources, exclude_from_tree
