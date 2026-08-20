from __future__ import annotations

import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
canonical = (root / "VERSION").read_text(encoding="utf-8").strip()
frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))["version"]
tauri = json.loads((root / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))["version"]
cargo_match = re.search(
    "^version = \\\"([^\\\"]+)\\\"",
    (root / "src-tauri/Cargo.toml").read_text(encoding="utf-8"),
    re.MULTILINE,
)
backend_match = re.search(
    "version=\\\"([^\\\"]+)\\\"",
    (root / "backend/app/main.py").read_text(encoding="utf-8"),
)
versions = {
    "VERSION": canonical,
    "frontend": frontend,
    "tauri": tauri,
    "cargo": cargo_match.group(1) if cargo_match else None,
    "backend": backend_match.group(1) if backend_match else None,
}
if any(version != canonical for version in versions.values()):
    raise SystemExit(f"Version mismatch: {versions}")
print(f"Version {canonical} is consistent across application manifests.")
