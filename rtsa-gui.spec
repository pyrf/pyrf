# -*- mode: python -*-
a = Analysis(['rtsa-gui.py'],
             pathex=['C:\\Users\\Mohammad\\Documents\\Python\\pyrf'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='rtsa-gui.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
