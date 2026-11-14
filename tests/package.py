"""Checks the plugin's files against each other and writes dist/<name>-<version>.difypkg (a zip of the runtime files)."""

import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ["manifest.yaml", "main.py", "requirements.txt", "README.md", "PRIVACY.md", "_assets", "provider", "tools"]
SKIP_DIRS = {"__pycache__"}


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    problems: list[str] = []
    manifest = load(ROOT / "manifest.yaml")
    for name in ("version", "author", "name", "icon", "privacy", "repo", "contact"):
        if not manifest.get(name):
            problems.append(f"manifest.{name} is empty")
    if not (ROOT / "_assets" / manifest["icon"]).is_file():
        problems.append("icon file missing")
    if not (ROOT / manifest["privacy"]).is_file():
        problems.append("privacy file missing")
    tool_count = 0
    for provider_path in manifest["plugins"]["tools"]:
        provider = load(ROOT / provider_path)
        if provider["identity"]["author"] != manifest["author"]:
            problems.append("provider author differs from manifest author")
        if not (ROOT / provider["extra"]["python"]["source"]).is_file():
            problems.append("provider source missing")
        for tool_path in provider["tools"]:
            tool = load(ROOT / tool_path)
            tool_count += 1
            source = ROOT / tool["extra"]["python"]["source"]
            if not source.is_file():
                problems.append(f"{tool_path}: source missing")
            if tool["identity"]["author"] != manifest["author"]:
                problems.append(f"{tool_path}: author differs")
            for text in (tool["description"]["human"]["en_US"], tool["description"]["llm"]):
                if not text or len(text) < 30:
                    problems.append(f"{tool_path}: thin description")
            names = [p["name"] for p in tool.get("parameters", [])]
            if len(names) != len(set(names)):
                problems.append(f"{tool_path}: duplicate parameter")
            for p in tool.get("parameters", []):
                for field in ("type", "label", "human_description", "form"):
                    if field not in p:
                        problems.append(f"{tool_path}: {p['name']} lacks {field}")
                if p["form"] == "llm" and not p.get("llm_description"):
                    problems.append(f"{tool_path}: {p['name']} lacks llm_description")
    if problems:
        print("\n".join(problems))
        return 1

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{manifest['name']}-{manifest['version']}.difypkg"
    files: list[Path] = []
    for entry in RUNTIME:
        path = ROOT / entry
        if path.is_file():
            files.append(path)
        else:
            files.extend(p for p in sorted(path.rglob("*")) if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.suffix != ".pyc")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, path.relative_to(ROOT).as_posix())
    print(f"{tool_count} tools, {len(files)} files, {out.stat().st_size} bytes -> {out}")
    for path in files:
        print("  ", path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
