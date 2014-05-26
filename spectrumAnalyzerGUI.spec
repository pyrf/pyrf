# -*- mode: python -*-
a = Analysis(['spectrumAnalyzerGUI.py'],
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
          name='spectrumAnalyzerGUI.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
