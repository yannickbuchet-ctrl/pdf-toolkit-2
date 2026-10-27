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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PDF Toolkit 2",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="PDF Toolkit 2.ico",  # produite par : python make_icon.py
)
