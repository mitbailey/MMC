# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['mmc.py'],
    pathex=['./'],
    binaries=[('ui/digital-7 (mono).ttf', '.'), ('ui/digital-7 (mono italic).ttf', '.')],
    datas=[('ui/mainwindow_mk2.ui', '.'), ('ui/grating_input.ui', '.')], # this line has been edited, and mainwindow ui resource has been added
    # execute pyinstaller mmc.spec to compile exe directly 
    # if pyinstaller --onefile --windowed mmc.py is used, it is going to overwrite the spec file
    # and create a malfunctioning exe that does not include the ui file
    hiddenimports=[],
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
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mmc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
