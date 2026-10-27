# Construction de l'exécutable :
#   python -m PyInstaller --clean "PDF Toolkit 2.spec"
# Résultat : dist\PDF Toolkit 2.exe (un seul fichier, sans console).
#
# Taille réduite :
# - modules Qt superflus retirés (QML, Quick, réseau, OpenGL, PDF de Qt), rendu OpenGL logiciel,
#   SSL, plugins d'images, styles et traductions de Qt ;
# - modules Python jamais chargés par l'application retirés (vérifié en exécutant les tests) ;
# - bytecode sans docstrings ni assertions (optimize=2).
#
# Pas de compression UPX : sur d'autres PC, les antivirus (Windows Defender, Contrôle intelligent des
# applications de Windows 11) bloquaient les DLL compressées une fois extraites, et l'application
# s'arrêtait au lancement (« No module named 'PySide6.QtCore' »).

# -*- mode: python ; coding: utf-8 -*-

EXCLUDED_MODULES = [
    "tkinter", "unittest", "pydoc", "doctest", "xmlrpc", "sqlite3", "lib2to3",
    "ssl", "_ssl", "_hashlib",  # hashlib se rabat sur ses implémentations intégrées
    "numpy", "PIL",
    # Jamais chargés par l'application ni par PyMuPDF (bz2, lzma, zstd et decimal, eux, le sont).
    "email", "http", "urllib", "xml", "html.parser", "multiprocessing", "asyncio", "concurrent",
    "socket", "_socket", "select", "selectors", "gzip", "json", "csv", "pickle", "subprocess",
    "difflib", "unicodedata", "ctypes", "_ctypes",
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtOpenGL",
    "PySide6.QtPdf", "PySide6.QtSvg", "PySide6.QtDBus",
]

# Fichiers binaires ou de données à écarter (comparaison sur le chemin, en minuscules).
EXCLUDED_FILES = [
    "opengl32sw.dll", "d3dcompiler", "qt6quick", "qt6qml", "qt6pdf", "qt6network",
    "qt6opengl", "qt6svg", "qt6virtualkeyboard", "libcrypto", "libssl",
    "plugins\\imageformats", "plugins\\iconengines", "plugins\\tls",
    "plugins\\networkinformation", "plugins\\generic", "plugins\\styles",
    "plugins\\platforminputcontexts", "qdirect2d", "qminimal", "qoffscreen",
    "translations",
]


# Informations de version de l'exécutable (Propriétés → Détails) : nom, version, éditeur, copyright.
# Un exécutable qui en est dépourvu est plus souvent signalé par les antivirus. Nom et version sont lus dans
# le programme (APP_NAME, APP_VERSION) : il n'y a qu'un endroit à mettre à jour.
import os
import re

with open("main.py", encoding="utf-8") as source:
    CONSTANTS = dict(re.findall(r'^(APP_\w+) = "([^"]*)"', source.read(), re.M))
NAME, VERSION = CONSTANTS["APP_NAME"], CONSTANTS["APP_VERSION"]
NUMBERS = tuple((list(map(int, re.findall(r"\d+", VERSION))) + [0, 0, 0, 0])[:4])
VERSION_FILE = os.path.join("build", "version_info.txt")
os.makedirs("build", exist_ok=True)
with open(VERSION_FILE, "w", encoding="utf-8") as fichier:
    fichier.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={NUMBERS}, prodvers={NUMBERS}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040C04B0', [
      StringStruct('CompanyName', 'Yannick Buchet'),
      StringStruct('FileDescription', '{NAME} — éditeur de PDF'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('LegalCopyright', '© 2026 Yannick Buchet — licence GNU AGPL v3'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{NAME}'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x040C, 1200])])
  ]
)
""")


def keep(entry):
    name = entry[0].lower().replace("/", "\\")
    return not any(pattern in name for pattern in EXCLUDED_FILES)


a = Analysis(
    ["main.py"],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
    optimize=2,
)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

OPTIONS = dict(name="PDF Toolkit 2", debug=False, strip=False, upx=False, console=False,
               icon="PDF Toolkit 2.ico",  # produite par : python make_icon.py
               version=VERSION_FILE)

if os.environ.get("CONSTRUCTION") == "dossier":
    # Version en dossier, pour l'installateur (installer\PDF Toolkit 2.iss) : dist\PDF Toolkit 2\.
    # Rien n'est extrait au lancement, ce qui évite aussi les alertes des antivirus.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **OPTIONS)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PDF Toolkit 2")
else:
    # Un seul fichier, portable : dist\PDF Toolkit 2.exe.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **OPTIONS)
