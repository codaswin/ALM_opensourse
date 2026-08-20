from PyInstaller.utils.hooks import collect_all, collect_submodules

faiss_data, faiss_binaries, faiss_hidden = collect_all("faiss")
hidden_imports = (
    collect_submodules("app")
    + collect_submodules("composio")
    + faiss_hidden
    + ["aiosqlite", "asyncpg", "keyring.backends", "uvicorn.logging"]
)

a = Analysis(
    ["desktop_entry.py"],
    pathex=["."],
    binaries=faiss_binaries,
    datas=faiss_data + [("alembic", "alembic"), ("alembic.ini", ".")],
    hiddenimports=hidden_imports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ai-linkedin-backend",
    console=True,
    strip=False,
    upx=False,
)
