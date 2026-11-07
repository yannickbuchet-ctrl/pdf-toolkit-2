# Construction de l'exécutable :
#   python -m PyInstaller --clean "PDF Toolkit 2.spec"
# Résultat : dist\PDF Toolkit 2.exe (un seul fichier, sans console).
#
# Taille réduite :
# - modules Qt superflus retirés (QML, Quick, réseau, OpenGL, PDF de Qt), rendu OpenGL logiciel,
#   SSL, plugins d'images, styles et traductions de Qt ; de Pillow, seuls le cœur et le WebP sont gardés ;
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
    "numpy",
    # Pillow et pillow-heif lisent le WebP et le HEIC des iPhone (read_image) : seuls le cœur de Pillow et son
    # module WebP servent. AVIF (7,9 Mo), polices, Tk et Qt de Pillow sont retirés. pillow-heif impose la DLL de
    # l'encodeur x265 (22 Mo, 4 Mo compressée) : libheif ne se charge pas sans elle.
    "PIL._avif", "PIL.AvifImagePlugin", "PIL._imagingft", "PIL.ImageFont", "PIL._imagingtk", "PIL.ImageTk",
    "PIL.ImageQt",
    # Jamais chargés par l'application ni par PyMuPDF (bz2, lzma, zstd et decimal, eux, le sont).
    # difflib, lui, est nécessaire : il sert à la comparaison de deux PDF.
    "email", "http", "urllib", "xml", "html.parser", "multiprocessing", "asyncio", "concurrent",
    "socket", "_socket", "select", "selectors", "gzip", "json", "csv", "pickle", "subprocess",
    "unicodedata", "ctypes", "_ctypes",
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


# Données de langue de la reconnaissance de texte (OCR) : modèles « best_int » de Tesseract (Apache 2.0), suivis dans
# le dépôt et placés dans le dossier tessdata de l'exécutable (sys._MEIPASS), en un seul fichier comme en dossier.
# Leur empreinte est vérifiée : une construction n'embarque jamais un fichier abîmé ou remplacé.
import hashlib

TESSDATA_SHA256 = {
    "fra.traineddata": "bf83833fa957ff0076f6aa93f69e3bdf7b014dea829ea0c0d6be6b48a3ceef6d",
    "eng.traineddata": "5dc5d8d640a212c9d6184921ba103b186f50e0fed9ee716c53e6b312b400d747",
}
for tessdata_name, tessdata_hash in TESSDATA_SHA256.items():
    with open(os.path.join("tessdata", tessdata_name), "rb") as tessdata_file:
        if hashlib.sha256(tessdata_file.read()).hexdigest() != tessdata_hash:
            raise SystemExit(f"tessdata\\{tessdata_name} : empreinte SHA-256 inattendue (fichier abîmé ou remplacé).")

a = Analysis(
    ["main.py"],
    datas=[(os.path.join("tessdata", name), "tessdata") for name in (*TESSDATA_SHA256, "LICENSE")],
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
