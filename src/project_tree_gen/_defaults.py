# Default exclude patterns for file system traversal (regex).

"""Always-excluded directory/file patterns (project-wide). Matched against
individual path components (basenames), not full paths."""

DEFAULT_EXCLUDE = (
    r"^\.(git|venv)$",
    r"^target$",
    r"^node_modules$",
    r"^snapshots$",
    r"^__pycache__$",
    r"\.(pytest_cache|egg-info)$",
    r".*(-lock|\.lock)(\..*)?$",
)
