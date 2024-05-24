# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['mmc.py'],
    pathex=['./', './ui'],
    binaries=[('fonts', 'fonts')],
    datas=[('ui', 'ui')], # this line has been edited, and mainwindow ui resource has been added
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
    [],
    exclude_binaries=True,
    name='MMCS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MMCS'
)