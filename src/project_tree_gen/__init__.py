# Silent automation tool that regenerates `## Folder structure` tree blocks in AGENTS.md files.
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

"""Package entry point — re-exports the public API."""

from project_tree_gen._agents import update_agents, find_agents_files
from project_tree_gen._config import load_config
from project_tree_gen._tree import build_tree, render, Node, prune_empty
from project_tree_gen._cli import main

__all__ = [
    "main",
    "update_agents",
    "find_agents_files",
    "load_config",
    "build_tree",
    "render",
    "Node",
    "prune_empty",
]
