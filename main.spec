# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['e:/Usuarios/tferreira/snmp_dispositivo'],
    binaries=[],
    datas=[
        # Apenas pyasn1, pois pysnmp é puro Python e não precisa ser incluído manualmente
        ('snmpenv2/Lib/site-packages/pyasn1', 'pyasn1'),
    ],
    hiddenimports=[
        # pysnmp e pyasn1 essenciais para API síncrona
        'pysnmp',
        'pysnmp.hlapi',
        'pysnmp.entity',
        'pysnmp.entity.engine',
        'pysnmp.entity.config',
        'pysnmp.proto',
        'pysnmp.proto.api',
        'pysnmp.proto.rfc1902',
        'pysnmp.proto.rfc1905',
        'pysnmp.smi',
        'pysnmp.smi.rfc1902',
        'pysnmp.smi.rfc1905',
        'pysnmp.smi.mibs',
        'pysnmp.smi.view',
        'pyasn1',
        'pyasn1.type',
        'pyasn1.compat',
        'pyasn1.compat.octets',
        'pyasn1.codec',
        'pyasn1.codec.ber',
        'pyasn1.codec.ber.decoder',
        'pyasn1.codec.ber.encoder',
        'pyasn1.codec.der',
        'pyasn1.codec.der.decoder',
        'pyasn1.codec.der.encoder',
    ],
    hookspath=['.'],
    runtime_hooks=[],
    excludes=['asyncio', 'twisted'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
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

