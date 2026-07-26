# CLI entry point — argument parsing and orchestration.
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

"""CLI entry point — argument parsing and orchestration."""

from __future__ import annotations

from pathlib import Path

from project_tree_gen._agents import find_agents_files, update_agents
from project_tree_gen._config import load_config
from project_tree_gen._tree import is_excluded, Node, prune_empty, render


def _resolve_depth(
    path: Path, depth_config: dict[str, int], cli_depth: int | None, root: Path
) -> int:
    """Resolve depth for *path*: CLI arg wins, then per-file config, then default.

    Config keys are matched first as the path relative to the project root
    (with optional ``./`` prefix), then by basename.
    """
    if cli_depth is not None:
        return cli_depth
    try:
        rel = path.resolve().relative_to(root.resolve())
        rel_str = str(rel)
        if rel_str in depth_config:
            return depth_config[rel_str]
        if f"./{rel_str}" in depth_config:
            return depth_config[f"./{rel_str}"]
    except ValueError:
        pass
    name = path.name
    if name in depth_config:
        return depth_config[name]
    return depth_config.get("default", 2)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Regenerate the `## Folder structure` tree block in AGENTS.md files."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to gentree.toml configuration file",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory (default: current working directory)",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="AGENTS.md",
        help="One or more AGENTS.md files to update. If omitted, all AGENTS.md files under --root are updated.",
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=int,
        default=None,
        help="Optional depth override (overrides config file depth for the given file(s))",
    )
    args = parser.parse_args()

    config_path = args.config
    root = args.root.resolve()
    _, _, depth_config, _, _ = load_config(config_path)

    if args.files:
        files = [Path(f) for f in args.files]
        cli_depth = args.depth
    else:
        files = find_agents_files(root, config_path)
        cli_depth = None

    for f in files:
        depth = _resolve_depth(f, depth_config, cli_depth, root)
        update_agents(f, depth, config_path, root)
        print(f"updated: {f} (depth={depth})")


if __name__ == "__main__":
    main()
