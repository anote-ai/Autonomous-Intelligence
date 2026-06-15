# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['../backend/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../backend/api_endpoints', 'api_endpoints'),
        ('../backend/services', 'services'),
        ('../backend/middleware', 'middleware'),
        ('../backend/agents', 'agents'),
        ('../backend/database', 'database'),
    ],
    hiddenimports=[
        'flask',
        'flask_jwt_extended',
        'flask_cors',
        'anthropic',
        'openai',
        'bcrypt',
        'sklearn',
        'chromadb',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='anote-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
