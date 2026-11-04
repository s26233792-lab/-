"""Install the self-contained Codex skill without overwriting an existing skill."""
import argparse
import os
import shutil
from pathlib import Path


def install(destination=None):
    repository = Path(__file__).resolve().parents[1]
    skill = repository / "skills" / "content-workbench"
    parent = Path(destination).expanduser().resolve() if destination else Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve() / "skills"
    target = parent / skill.name
    if target.exists():
        raise ValueError(f"Skill already exists at {target}; choose a new destination or explicitly archive the old version yourself")
    if target == skill or skill in target.parents:
        raise ValueError("Installation must be outside the source skill directory")
    parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copy2(repository / "LICENSE", target / "LICENSE")
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination", help="Parent directory containing installed skills")
    args = p.parse_args()
    print(install(args.destination))
