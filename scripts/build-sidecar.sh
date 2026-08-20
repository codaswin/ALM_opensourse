#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_dir}/backend"

# PATH first (CI installs pyinstaller directly, no project venv), falling
# back to the repo's own .venv (Unix and Windows layouts) for local dev.
if command -v pyinstaller >/dev/null 2>&1; then
  pyinstaller_bin="pyinstaller"
elif [[ -x "${repo_dir}/.venv/bin/pyinstaller" ]]; then
  pyinstaller_bin="${repo_dir}/.venv/bin/pyinstaller"
elif [[ -x "${repo_dir}/.venv/Scripts/pyinstaller.exe" ]]; then
  pyinstaller_bin="${repo_dir}/.venv/Scripts/pyinstaller.exe"
else
  echo "pyinstaller not found on PATH or in .venv" >&2
  exit 1
fi
"${pyinstaller_bin}" --clean --noconfirm desktop_backend.spec

rustc_path="$(command -v rustc || true)"
if [[ -z "${rustc_path}" ]]; then
  rust_tool_dir="${CARGO_HOME:-${HOME}/.cargo}/bin"
  rustc_path="${rust_tool_dir}/rustc"
fi
if [[ ! -x "${rustc_path}" ]]; then
  echo "rustc is required to determine the native Tauri target tuple" >&2
  exit 1
fi
target_triple="$("${rustc_path}" --print host-tuple)"
extension=""
if [[ "${OS:-}" == "Windows_NT" ]]; then
  extension=".exe"
fi
destination="${repo_dir}/src-tauri/binaries/ai-linkedin-backend-${target_triple}${extension}"
cp "${repo_dir}/backend/dist/ai-linkedin-backend${extension}" "${destination}"
echo "Built ${destination}"
