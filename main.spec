# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['main.py'],
             pathex=['\\fcefactory1\\PROGRAMAS_DE_PRODUCCION\\6.Planificacion\\BotCreacionDePedidos'],
             binaries=[],
             datas=[('C:\\Users\\IYX8A9R\\Documents\\Bot-Creacion-de-Pedidos\\venv\\Lib\\site-packages\\ttkbootstrap', 'ttkbootstrap'),],
             hiddenimports=['ttkbootstrap', 'importlib.resources', 'PIL.ImageFont', 'tkinter.font', 'openpyxl', 'pymssql'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
splash = Splash('\\\\fcefactory1\\PROGRAMAS_DE_PRODUCCION\\6.Planificacion\\BotCreacionDePedidos\\ProjectFiles\\Resources\\SPLASH.jpg',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=None,
                text_size=12,
                minify_script=True)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          splash,
          splash.binaries,
          [],
          name='AutomatizacionSAP_latest_release',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon="\\\\fcefactory1\\PROGRAMAS_DE_PRODUCCION\\6.Planificacion\\BotCreacionDePedidos\\ProjectFiles\\Resources\\application.ico")

