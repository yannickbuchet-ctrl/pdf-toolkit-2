import glob
import hashlib
import html
import os
import re
import struct
import sys

import pymupdf
from PySide6.QtCore import QByteArray, QMimeData, QPoint, QRectF, QSize, Qt, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QDrag, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QLinearGradient,
    QPageLayout, QPainter, QPainterPath, QPen, QPixmap, QTransform,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "PDF Toolkit 2"
APP_VERSION = "1.0"
APP_DATE = "20 octobre 2026"
APP_AUTHOR = "Claude Code"
APP_AUTHOR_MODEL = "Claude Opus 5.5 (révision claude-opus-5-5)"
APP_DIRECTOR = "Yannick Buchet"

SYSTEM_FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
]
_system_fonts = None

MAX_UNDO = 50

# --- Thème -----------------------------------------------------------------

ACCENT = "#2563eb"
GREEN = "#16a34a"
RED = "#dc2626"
SLATE = "#475569"

# Symboles Unicode servant d'icônes : (caractère, couleur)
ICONS = {
    "move_back": ("⬅", ACCENT),
    "move_forward": ("➡", ACCENT),
    "rotate_cw": ("↻", GREEN),
    "rotate_ccw": ("↺", GREEN),
    "delete": ("🗑", RED),
    "reset": ("⟲", SLATE),
    "undo": ("↶", SLATE),
    "redo": ("↷", SLATE),
    "previous": ("▲", ACCENT),
    "next": ("▼", ACCENT),
    "replace": ("⇄", GREEN),
    "close": ("✕", SLATE),
    "search": ("🔍", SLATE),
    "add": ("✚", GREEN),
    "remove": ("✖", RED),
    "merge": ("📑", ACCENT),
    "open": ("📂", ACCENT),
    "save": ("💾", ACCENT),
    "edit": ("✎", ACCENT),
    "pages": ("▦", ACCENT),
    "zoom_in": ("⊕", SLATE),
    "zoom_out": ("⊖", SLATE),
    "print": ("🖶", ACCENT),
    "form": ("☑", ACCENT),
    "lock": ("🔒", ACCENT),
    "image": ("🖼", ACCENT),
    "signature": ("✍", ACCENT),
}

PRINT_DPI = 300  # au-delà, le fichier envoyé à l'imprimante grossit sans gain visible

# Compression proposée à l'enregistrement.
COMPRESS_NONE, COMPRESS_LOSSLESS, COMPRESS_IMAGES = "none", "lossless", "images"
COMPRESS_DPI = 150  # résolution des images réduites : nette à l'écran et à l'impression courante
# MuPDF divise la résolution par un facteur entier (÷2, ÷4…) tant que le résultat reste
# strictement au-dessus de la cible : viser un peu moins pour qu'une image à 300 ppp passe à 150.
COMPRESS_DPI_TARGET = 144
COMPRESS_JPEG_QUALITY = 75

APP_STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 10pt; color: #1e293b; }}
QMainWindow, QDialog {{ background: #f5f7fb; }}

QMenuBar {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: #eef2ff; color: #1d4ed8; }}
QMenu {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 7px 32px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: #eef2ff; color: #1d4ed8; }}
QMenu::item:disabled {{ color: #a0aec0; }}
QMenu::separator {{ height: 1px; background: #e2e8f0; margin: 5px 8px; }}
QMenu::icon {{ padding-left: 8px; }}

QToolBar {{ background: #ffffff; border: none; border-bottom: 1px solid #e2e8f0; padding: 4px 10px; spacing: 2px; }}
QToolBar::separator {{ width: 1px; background: #e2e8f0; margin: 8px 6px; }}
QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 4px 6px; font-size: 9pt; color: #334155; }}
QToolButton:hover {{ background: #f1f5f9; }}
QToolButton:pressed {{ background: #e2e8f0; }}
QToolButton:checked {{ background: #dbeafe; color: #1d4ed8; }}
QToolButton:disabled {{ color: #a0aec0; }}

QPushButton {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #f1f5f9; border-color: #b8c2d0; }}
QPushButton:pressed {{ background: #e2e8f0; }}
QPushButton:disabled {{ color: #a0aec0; background: #f8fafc; border-color: #e2e8f0; }}
QPushButton[primary="true"] {{ background: {ACCENT}; color: #ffffff; border-color: {ACCENT}; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: #1d4ed8; border-color: #1d4ed8; }}
QPushButton[primary="true"]:disabled {{ background: #93b4f5; border-color: #93b4f5; }}

QLineEdit {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: 8px; padding: 6px 10px;
             selection-background-color: #bfdbfe; selection-color: #1e293b; }}
QLineEdit:focus {{ border: 2px solid {ACCENT}; padding: 5px 9px; }}
QLineEdit[notfound="true"] {{ background: #fef2f2; border-color: #f87171; }}

QListWidget {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 6px; outline: none; }}
QListWidget::item {{ border-radius: 6px; padding: 6px; }}
QListWidget::item:hover {{ background: #f1f5f9; }}
QListWidget::item:selected {{ background: #dbeafe; color: #1e293b; }}

QCheckBox {{ spacing: 6px; }}
QStatusBar {{ background: #ffffff; border-top: 1px solid #e2e8f0; color: {SLATE}; }}
QToolTip {{ background: #1e293b; color: #ffffff; border: none; border-radius: 6px; padding: 6px 8px; }}
QScrollArea {{ border: none; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle {{ background: #c3cbd8; border-radius: 4px; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::handle:hover {{ background: #94a3b8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

#viewer, #welcome {{ background: #e5e9f0; }}
#searchbar {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; }}
#hero {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #7c3aed); border-radius: 16px; }}
#hero QLabel {{ color: #ffffff; background: transparent; }}
#featureCard {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }}
#featureCard QLabel {{ background: transparent; }}
#shortcut {{ color: {ACCENT}; background: #eff6ff; border-radius: 6px; padding: 2px 8px; font-size: 9pt; }}
#hint {{ color: {SLATE}; }}
"""


def make_icon(name):
    """Icône dessinée à partir d'un symbole Unicode (aucun fichier image nécessaire)."""
    glyph, color = ICONS[name]
    pixmap = QPixmap(64, 64)  # grande taille : reste net sur les écrans haute résolution
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    font = QFont("Segoe UI Symbol")
    font.setPixelSize(50)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    return QIcon(pixmap)


APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_app_icon(size):
    """Icône du logiciel : page PDF au coin replié, étiquette « PDF » et crayon, sans fond (posée sur le Bureau
    comme un document). Un contour gris et une ombre légère la gardent lisible sur un fond clair.

    Dessinée sur une grille de 256 × 256 puis mise à l'échelle : nette à toutes les tailles.
    """
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.scale(size / 256, size / 256)

    # Page blanche au coin replié : ombre douce, puis page bordée de gris.
    page = QPainterPath()
    page.moveTo(50, 14)
    page.lineTo(164, 14)
    page.lineTo(210, 60)
    page.lineTo(210, 238)
    page.lineTo(50, 238)
    page.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    for offset, alpha in ((7, 18), (4, 28)):
        p.setBrush(QColor(15, 23, 42, alpha))
        p.drawPath(page.translated(offset * 0.6, offset))
    p.setBrush(QColor("#ffffff"))
    p.setPen(QPen(QColor("#94a3b8"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(page)
    fold = QPainterPath()
    fold.moveTo(164, 14)
    fold.lineTo(164, 60)
    fold.lineTo(210, 60)
    fold.closeSubpath()
    p.setBrush(QColor("#e2e8f0"))
    p.drawPath(fold)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#cbd5e1"))
    for y, width in ((56, 70), (80, 110), (104, 92)):
        p.drawRoundedRect(QRectF(72, y, width, 12), 6, 6)

    # Étiquette « PDF », qui déborde à gauche de la page.
    label = QRectF(26, 150, 140, 60)
    p.setBrush(QColor(RED))
    p.drawRoundedRect(label, 12, 12)
    font = QFont("Segoe UI")
    font.setPixelSize(44)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#ffffff"))
    p.drawText(label, Qt.AlignmentFlag.AlignCenter, "PDF")

    # Crayon (édition), pointe vers le bas à gauche, détouré de blanc.
    p.translate(214, 150)
    p.rotate(135)
    outline = QPainterPath()
    outline.moveTo(-54, -14)
    outline.lineTo(28, -14)
    outline.lineTo(58, 0)
    outline.lineTo(28, 14)
    outline.lineTo(-54, 14)
    outline.closeSubpath()
    p.setPen(QPen(QColor("#ffffff"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(outline)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#f472b6"))
    p.drawRect(QRectF(-54, -14, 16, 28))
    p.setBrush(QColor(SLATE))
    p.drawRect(QRectF(-38, -14, 8, 28))
    p.setBrush(QColor("#f59e0b"))
    p.drawRect(QRectF(-30, -14, 58, 28))
    tip = QPainterPath()
    tip.moveTo(28, -14)
    tip.lineTo(58, 0)
    tip.lineTo(28, 14)
    tip.closeSubpath()
    p.setBrush(QColor("#fde68a"))
    p.drawPath(tip)
    lead = QPainterPath()
    lead.moveTo(47, -5)
    lead.lineTo(58, 0)
    lead.lineTo(47, 5)
    lead.closeSubpath()
    p.setBrush(QColor("#1e293b"))
    p.drawPath(lead)
    p.end()
    return image


def app_icon():
    icon = QIcon()
    for size in APP_ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(draw_app_icon(size)))
    return icon


def set_primary(button):
    """Met un bouton en avant (bouton d'action principal, en couleur)."""
    button.setProperty("primary", True)
    button.style().unpolish(button)
    button.style().polish(button)


def add_shadow(widget, blur=24, offset=4, alpha=45):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset)
    shadow.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(shadow)


def normalize_font_name(name):
    """Ramène un nom de police à une forme comparable.

    "ABCDEF+TimesNewRomanPS-BoldMT", "Times New Roman Bold" -> "timesnewromanbold"
    """
    name = name.split("+", 1)[-1].lower()
    name = re.sub(r"[^a-z0-9]", "", name)
    name = name.replace("regular", "").replace("oblique", "italic")
    name = re.sub(r"mt$", "", name)
    name = re.sub(r"ps(bold|italic|bolditalic)?$", r"\1", name)
    return name


STYLE_SUFFIXES = ("bolditalic", "bold", "italic", "normal", "book")

# Polices standard du PDF (et proches) -> équivalent installé sous Windows, aux mêmes dimensions.
FONT_SUBSTITUTES = {
    "helvetica": "arial", "helveticaneue": "arial", "arialmt": "arial",
    "times": "timesnewroman", "timesroman": "timesnewroman",
    "courier": "couriernew",
}


def font_family(name):
    """Famille d'une police, sans le style : "Arial-BoldMT" -> "arial", "Calibri0400" -> "calibri".

    (Certains logiciels, comme Qt, ajoutent la graisse en chiffres à la fin du nom.)
    """
    family = re.sub(r"\d+$", "", normalize_font_name(name))
    stripped = True
    while stripped:
        stripped = False
        for suffix in STYLE_SUFFIXES:
            if family.endswith(suffix) and len(family) > len(suffix):
                family, stripped = family[: -len(suffix)], True
    return family


def system_fonts():
    """Index des polices installées, construit une seule fois.

    Renvoie (nom normalisé -> fichier, (famille, gras, italique) -> fichier).
    """
    global _system_fonts
    if _system_fonts is None:
        by_name, by_style = {}, {}
        for folder in SYSTEM_FONT_DIRS:
            for path in glob.glob(os.path.join(folder, "*")):
                if not path.lower().endswith((".ttf", ".otf", ".ttc")):
                    continue
                try:
                    font = pymupdf.Font(fontfile=path)
                except Exception:
                    continue
                by_name.setdefault(normalize_font_name(font.name), path)
                by_style.setdefault((font_family(font.name), bool(font.is_bold), bool(font.is_italic)), path)
        _system_fonts = by_name, by_style
    return _system_fonts


def find_system_font(span):
    """Fichier de la police installée correspondant au texte d'origine, ou None.

    Cherche le nom exact, puis la même famille avec le même style (gras, italique), puis
    l'équivalent Windows des polices standard du PDF (Helvetica -> Arial, Times -> Times New Roman…).
    Renvoie (fichier, police de substitution ?).
    """
    by_name, by_style = system_fonts()
    name = normalize_font_name(span["font"])
    if name in by_name:
        return by_name[name], False
    family = font_family(span["font"])
    bold = bool(span["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in name
    italic = bool(span["flags"] & pymupdf.TEXT_FONT_ITALIC) or "italic" in name
    for candidate, substitute in ((family, False), (FONT_SUBSTITUTES.get(family), True)):
        path = by_style.get((candidate, bold, italic)) if candidate else None
        if path:
            return path, substitute
    return None, False


WEIGHTS = [  # du plus long au plus court : « extrabold » avant « bold »
    ("extralight", 200), ("ultralight", 200), ("semibold", 600), ("demibold", 600), ("extrabold", 800),
    ("ultrabold", 800), ("thin", 100), ("light", 300), ("regular", 400), ("normal", 400), ("book", 400),
    ("medium", 500), ("bold", 700), ("black", 900), ("heavy", 900),
]
SERIF_HINTS = ("times", "georgia", "garamond", "cambria", "baskerville", "palatino", "bookman", "caslon",
               "minion", "didot", "bodoni", "century", "constantia", "merriweather", "playfair", "lora",
               "serif", "roman")
MONO_HINTS = ("mono", "courier", "consol", "code", "typewriter")


def font_weight(name):
    """Graisse approximative d'après le nom de la police (400 = normal, 700 = gras)."""
    name = normalize_font_name(name)
    for word, weight in WEIGHTS:
        if word in name:
            return weight
    return 400


def base_family(name):
    """Famille sans graisse ni italique : "WorkSans-Medium" et "WorkSans-Regular" -> "worksans"."""
    family = re.sub(r"\d+$", "", normalize_font_name(name)).replace("italic", "")
    for word, _weight in WEIGHTS:
        family = family.replace(word, "")
    return family


def font_kind(name):
    """« mono », « serif » ou « sans » d'après le nom de la police.

    L'indication « police à empattements » des PDF est souvent fausse (Work Sans y est déclarée
    à empattements) : on se fie au nom, et une police inconnue est supposée sans empattements.
    """
    name = normalize_font_name(name)
    if any(hint in name for hint in MONO_HINTS):
        return "mono"
    if "sans" not in name and any(hint in name for hint in SERIF_HINTS):
        return "serif"
    return "sans"


def generic_system_font(name, italic):
    """Police installée courante la plus proche (Arial, Times New Roman ou Courier New, même style)."""
    family = {"mono": "couriernew", "serif": "timesnewroman", "sans": "arial"}[font_kind(name)]
    bold = font_weight(name) >= 600
    by_style = system_fonts()[1]
    return by_style.get((family, bold, italic)) or by_style.get((family, bold, False)) or by_style.get((family, False, False))


def refresh_system_fonts():
    """Oublie l'index des polices installées : une police installée entre-temps sera trouvée."""
    global _system_fonts
    _system_fonts = None


_qt_families = {}  # fichier de police -> famille déclarée à Qt


def qt_font_family(path):
    """Famille Qt d'une police installée (déclarée à Qt si besoin : une police installée après le
    lancement de l'application n'est pas connue de Qt). Renvoie None si le fichier est illisible."""
    if path not in _qt_families:
        families = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(path))
        _qt_families[path] = families[0] if families else None
    return _qt_families[path]


def font_names(buffer):
    """Textes de la table « name » d'une police TrueType / OpenType : {numéro: texte}.

    1 famille, 2 style, 4 nom complet, 5 version, 6 nom PostScript, 8 éditeur, 9 créateur,
    11 site de l'éditeur, 12 site du créateur, 13 licence, 14 lien de la licence, 0 copyright,
    16 / 17 famille et style typographiques. Le texte anglais de Windows est préféré.
    Renvoie {} pour une police sans cette table (Type 1, CFF seule).
    """
    data = bytes(buffer)
    try:
        start = struct.unpack(">I", data[12:16])[0] if data[:4] == b"ttcf" else 0
        if data[start:start + 4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
            return {}
        count = struct.unpack(">H", data[start + 4:start + 6])[0]
        for i in range(count):
            tag, _checksum, table, _length = struct.unpack(">4sIII", data[start + 12 + 16 * i:start + 28 + 16 * i])
            if tag == b"name":
                break
        else:
            return {}
        _format, records, strings = struct.unpack(">HHH", data[table:table + 6])
        names, ranks = {}, {}
        for i in range(records):
            platform, encoding, language, name_id, length, offset = struct.unpack(
                ">HHHHHH", data[table + 6 + 12 * i:table + 18 + 12 * i])
            raw = data[table + strings + offset:table + strings + offset + length]
            if platform in (0, 3):
                text, rank = raw.decode("utf-16-be", "replace"), 0 if language == 0x0409 else 1
            elif platform == 1 and encoding == 0:
                text, rank = raw.decode("mac_roman", "replace"), 2
            else:
                continue
            text = text.strip().strip("\x00")
            if text and rank < ranks.get(name_id, 9):
                names[name_id], ranks[name_id] = text, rank
        return names
    except (struct.error, IndexError):
        return {}


def readable_font_name(name):
    """Nom lisible d'une police d'après son nom dans le PDF : (famille, style).

    "ABCDEF+WorkSans-MediumItalic" -> ("Work Sans", "Medium Italic") ;
    "TimesNewRomanPS-BoldMT" -> ("Times New Roman", "Bold") ; "Arial,Bold" -> ("Arial", "Bold").
    """
    name = name.split("+", 1)[-1]
    family, _, style = name.partition("-")
    if not style:
        family, _, style = family.partition(",")
    family, style = re.sub(r"(PS|MT)$", "", family), re.sub(r"MT$", "", style)

    def spaced(text):
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", text).strip()

    return spaced(family), spaced(style)


# Ligne « <glyphe> <00A0> » d'une table ToUnicode (et non une plage, ni un numéro de glyphe 00A0).
NBSP_MAPPING = re.compile(rb"^(<[0-9A-Fa-f]{2,4}>[ \t]+)<00[Aa]0>([ \t]*)$", re.MULTILINE)


def fix_space_mapping(doc, page, fontname):
    """Fait relire les espaces comme des espaces, et non comme des espaces insécables.

    Dans la plupart des polices TrueType, l'espace et l'espace insécable partagent le même glyphe ;
    la table ToUnicode générée par PyMuPDF retient l'insécable, ce qui fausse la recherche et le
    copier-coller du texte remplacé. On corrige uniquement les lignes « glyphe -> U+00A0 ».
    """
    for xref, _ext, _type, _basefont, name, _encoding in page.get_fonts():
        if name != fontname:
            continue
        kind, value = doc.xref_get_key(xref, "ToUnicode")
        if kind != "xref":
            continue
        stream = int(value.split()[0])
        data = doc.xref_stream(stream)
        fixed = NBSP_MAPPING.sub(rb"\1<0020>\2", data)
        if fixed != data:
            doc.update_stream(stream, fixed)


def base14_font(flags):
    """Choisit la police standard PDF la plus proche du style du texte d'origine."""
    if flags & pymupdf.TEXT_FONT_MONOSPACED:
        names = ("cour", "coit", "cobo", "cobi")
    elif flags & pymupdf.TEXT_FONT_SERIFED:
        names = ("tiro", "tiit", "tibo", "tibi")
    else:
        names = ("helv", "heit", "hebo", "hebi")
    bold = 2 if flags & pymupdf.TEXT_FONT_BOLD else 0
    italic = 1 if flags & pymupdf.TEXT_FONT_ITALIC else 0
    return names[bold + italic]


def page_spans(page):
    """Renvoie les fragments de texte (spans) non vides de la page.

    "bbox" et "origin" sont en coordonnées de page non pivotée (celles qu'attendent
    les fonctions d'édition) ; "view" est le rectangle tel qu'affiché, rotation comprise.
    "chars" donne la position de chaque caractère (pour surligner une partie du texte).
    """
    data = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_TEXT)
    spans = []
    for block in data["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span["text"] = "".join(ch["c"] for ch in span["chars"])
                if span["text"].strip():
                    spans.append(span)
    for span in spans:
        span["matrix"] = page.rotation_matrix
        span["view"] = tuple(pymupdf.Rect(span["bbox"]) * page.rotation_matrix)
    return spans


FILLABLE_FIELDS = (
    pymupdf.PDF_WIDGET_TYPE_TEXT, pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON,
    pymupdf.PDF_WIDGET_TYPE_COMBOBOX, pymupdf.PDF_WIDGET_TYPE_LISTBOX,
)


def page_fields(page):
    """Champs de formulaire remplissables de la page (les champs en lecture seule sont ignorés).

    "view" est le rectangle tel qu'affiché, rotation comprise ; "on" la valeur d'une case cochée.
    """
    fields = []
    for widget in page.widgets():
        if widget.field_type not in FILLABLE_FIELDS or widget.field_flags & pymupdf.PDF_FIELD_IS_READ_ONLY:
            continue
        toggle = widget.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON)
        fields.append({
            "xref": widget.xref,
            "type": widget.field_type,
            "value": widget.field_value,
            "on": widget.on_state() if toggle else None,
            "choices": widget.choice_values or [],
            "fontsize": widget.text_fontsize,
            "view": tuple(widget.rect * page.rotation_matrix),
        })
    return fields


def unlock(doc, password):
    """Document protégé déverrouillé et déchiffré en mémoire (doc est refermé).

    Le chiffrement n'est réappliqué qu'à l'enregistrement : annulation, concaténation et
    compression travaillent ainsi sur un document ordinaire.
    """
    if not doc.needs_pass:
        return doc
    if not doc.authenticate(password):
        doc.close()
        raise ValueError("mot de passe incorrect")
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE)
    doc.close()
    return pymupdf.open("pdf", data)


# Signature : niveau de gris -> opacité. Le blanc (et le gris très clair du papier scanné) devient
# transparent, l'encre reste opaque, avec une transition douce entre les deux.
WHITE_TO_ALPHA = bytes(
    255 if g <= 170 else 0 if g >= 235 else round(255 * (235 - g) / 65) for g in range(256)
)


def load_image(path, transparent_white=False):
    """Image PNG ou JPG à insérer, lue par PyMuPDF (et non par Qt, dont le lecteur JPEG n'est pas inclus).

    Renvoie (pixmap RVB, fond blanc rendu transparent ?). Sans transparence ajoutée, le fichier
    d'origine est inséré tel quel (un JPEG reste compressé en JPEG dans le PDF).
    """
    pix = pymupdf.Pixmap(path)
    if pix.colorspace is not None and pix.colorspace.n != 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if transparent_white and not pix.alpha:
        gray = pymupdf.Pixmap(pymupdf.csGRAY, pix).samples
        with_alpha = pymupdf.Pixmap(pix, 1)
        with_alpha.set_alpha(gray.translate(WHITE_TO_ALPHA))
        return with_alpha, True
    return pix, False


def to_qimage(pix):
    """Pixmap PyMuPDF RVB (avec ou sans transparence) -> QImage."""
    fmt = QImage.Format.Format_RGBA8888_Premultiplied if pix.alpha else QImage.Format.Format_RGB888
    return QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()


def text_rect(span, start, end):
    """Rectangle affiché (rotation comprise) des caractères start..end d'un span."""
    rects = [pymupdf.Rect(ch["bbox"]) for ch in span["chars"][start:end]]
    rect = rects[0]
    for other in rects[1:]:
        rect |= other
    return tuple(rect * span["matrix"])


class InlineEditor(QLineEdit):
    """Champ de saisie posé sur le texte : Entrée valide, Échap ou clic ailleurs annule."""

    cancelled = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.cancelled.emit()


class PageWidget(QWidget):
    span_edited = Signal(int, object, str)
    font_info_requested = Signal(int, object)  # page, texte dont la police n'est pas installée
    field_edited = Signal(int, int, object)  # page, xref du champ de formulaire, nouvelle valeur
    image_placed = Signal(int, object)  # page, rectangle affiché (en points) de l'image placée
    placement_cancelled = Signal(int)
    rotate_requested = Signal(int, int)
    delete_requested = Signal(int)

    HANDLE = 10  # côté des poignées de redimensionnement, en pixels
    MIN_IMAGE_SIZE = 12  # en points

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.pixmap = QPixmap()
        self.spans = []
        self.fields = []
        self.zoom = 1.0
        self.edit_mode = False
        self.hovered = None
        self.hovered_field = None
        self.editor = None
        self.font_warning = None  # bandeau « police non installée » sous la zone d'édition
        self.highlights = []  # occurrences de la recherche (rectangles affichés, en points PDF)
        self.current_highlight = None
        # Image en cours de placement : {"image": QImage, "rect": [x0, y0, x1, y1] en points affichés}.
        self.placement = None
        self.drag = None  # pendant un déplacement ou un redimensionnement : (prise, départ, rectangle de départ)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Entrée / Échap pendant le placement
        self.setMouseTracking(True)

    def set_content(self, pixmap, spans, zoom, fields=()):
        self.close_editor()
        self.pixmap = pixmap
        self.spans = spans
        self.fields = list(fields)
        self.zoom = zoom
        self.hovered = None
        self.hovered_field = None
        self.setFixedSize(pixmap.size())
        self.update()

    def set_edit_mode(self, enabled):
        if not enabled:
            self.close_editor()
        self.edit_mode = enabled
        self.hovered = None
        self._update_cursor()
        self.update()

    def _update_cursor(self):
        if self.hovered_field is not None:
            text = self.hovered_field["type"] == pymupdf.PDF_WIDGET_TYPE_TEXT
            self.setCursor(Qt.CursorShape.IBeamCursor if text else Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor if self.edit_mode else Qt.CursorShape.ArrowCursor)

    def _field_at(self, pos):
        for field in self.fields:
            if self.to_widget(field["view"]).contains(pos):
                return field
        return None

    # --- Placement d'une image -------------------------------------------

    def start_placement(self, image, rect):
        self.close_editor()
        self.placement = {"image": image, "rect": list(rect)}
        self.drag = None
        self.setFocus()
        self.update()

    def end_placement(self, accepted):
        if self.placement is None:
            return
        rect = tuple(self.placement["rect"])
        self.placement = None
        self.drag = None
        self._update_cursor()
        self.update()
        if accepted:
            self.image_placed.emit(self.index, rect)
        else:
            self.placement_cancelled.emit(self.index)

    def _placement_corners(self):
        r = self.to_widget(self.placement["rect"])
        return [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]

    def _placement_buttons(self):
        """Boutons « Valider » et « Annuler », au-dessus de l'image (ou en dessous en haut de page)."""
        r = self.to_widget(self.placement["rect"])
        y = r.top() - 34 if r.top() >= 36 else r.bottom() + 8
        cancel = QRectF(max(2, r.right() - 88), y, 88, 26)
        ok = QRectF(max(2, cancel.left() - 100), y, 94, 26)
        return {"ok": ok, "cancel": cancel}

    def _placement_hit(self, pos):
        for key, rect in self._placement_buttons().items():
            if rect.contains(pos):
                return key
        size = self.HANDLE + 6
        for i, corner in enumerate(self._placement_corners()):
            if QRectF(corner.x() - size / 2, corner.y() - size / 2, size, size).contains(pos):
                return i
        if self.to_widget(self.placement["rect"]).contains(pos):
            return "move"
        return None

    def _drag_placement(self, pos, free_ratio):
        grip, start, (x0, y0, x1, y1) = self.drag
        dx, dy = (pos.x() - start.x()) / self.zoom, (pos.y() - start.y()) / self.zoom
        page_w, page_h = self.width() / self.zoom, self.height() / self.zoom
        if grip == "move":  # déplacement, sans sortir de la page
            dx = max(-x0, min(page_w - x1, dx))
            dy = max(-y0, min(page_h - y1, dy))
            self.placement["rect"] = [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
            return
        # Redimensionnement par un coin : le coin opposé reste fixe.
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        ax, ay = corners[(grip + 2) % 4]
        px, py = corners[grip][0] + dx, corners[grip][1] + dy
        w, h = max(self.MIN_IMAGE_SIZE, abs(px - ax)), max(self.MIN_IMAGE_SIZE, abs(py - ay))
        if not free_ratio:  # proportions de l'image conservées
            ratio = self.placement["image"].width() / max(1, self.placement["image"].height())
            w = max(w, h * ratio)
            h = w / ratio
        left = grip in (0, 3)
        top = grip in (0, 1)
        nx0, nx1 = (ax - w, ax) if left else (ax, ax + w)
        ny0, ny1 = (ay - h, ay) if top else (ay, ay + h)
        self.placement["rect"] = [nx0, ny0, nx1, ny1]

    def _paint_placement(self, painter):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.to_widget(self.placement["rect"])
        painter.drawImage(r, self.placement["image"])
        painter.setPen(QPen(QColor(ACCENT), 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(r)
        painter.setPen(QPen(QColor(ACCENT), 1.5))
        painter.setBrush(QColor("#ffffff"))
        for corner in self._placement_corners():
            painter.drawRect(QRectF(corner.x() - self.HANDLE / 2, corner.y() - self.HANDLE / 2,
                                    self.HANDLE, self.HANDLE))
        buttons = self._placement_buttons()
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        for key, text, background, color in (("ok", "✔ Valider", ACCENT, "#ffffff"),
                                             ("cancel", "✕ Annuler", "#ffffff", SLATE)):
            painter.setPen(QPen(QColor(ACCENT if key == "ok" else "#cbd5e1"), 1))
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(buttons[key], 6, 6)
            painter.setPen(QColor(color))
            painter.drawText(buttons[key], Qt.AlignmentFlag.AlignCenter, text)

    def _update_placement_cursor(self, pos):
        hit = self._placement_hit(pos)
        if hit in (0, 2):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif hit in (1, 3):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif hit == "move":
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        elif hit in ("ok", "cancel"):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, event):
        if self.placement is not None and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.end_placement(True)
        elif self.placement is not None and event.key() == Qt.Key.Key_Escape:
            self.end_placement(False)
        else:
            super().keyPressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drag is not None:
            self.drag = None

    def mouseDoubleClickEvent(self, event):
        if self.placement is not None and self._placement_hit(event.position()) == "move":
            self.end_placement(True)

    def set_highlights(self, rects, current):
        self.highlights = rects
        self.current_highlight = current
        self.update()

    def to_widget(self, rect):
        """Convertit un rectangle en points PDF (tel qu'affiché) en pixels du widget."""
        x0, y0, x1, y1 = rect
        z = self.zoom
        return QRectF(x0 * z, y0 * z, (x1 - x0) * z, (y1 - y0) * z)

    def _span_rect(self, span):
        return self.to_widget(span["view"])

    def _span_at(self, pos):
        for span in self.spans:
            if self._span_rect(span).contains(pos):
                return span
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        for rect in self.highlights:
            painter.fillRect(self.to_widget(rect), QColor(255, 220, 0, 110))
        if self.current_highlight is not None:
            rect = self.to_widget(self.current_highlight).adjusted(-1, -1, 1, 1)
            painter.fillRect(rect, QColor(255, 140, 0, 120))
            painter.setPen(QPen(QColor(230, 100, 0), 2))
            painter.drawRect(rect)
        # Champs de formulaire : légèrement teintés pour être repérés, encadrés au survol.
        for field in self.fields:
            painter.fillRect(self.to_widget(field["view"]), QColor(37, 99, 235, 28))
        if self.hovered_field is not None:
            painter.setPen(QPen(QColor(ACCENT), 2))
            painter.drawRect(self.to_widget(self.hovered_field["view"]))
        if self.edit_mode:
            painter.setPen(QPen(QColor(0, 120, 215, 90), 1))
            for span in self.spans:
                painter.drawRect(self._span_rect(span))
            if self.hovered is not None:
                painter.setPen(QPen(QColor(0, 120, 215), 2))
                painter.fillRect(self._span_rect(self.hovered), QColor(0, 120, 215, 40))
                painter.drawRect(self._span_rect(self.hovered))
        if self.placement is not None:
            self._paint_placement(painter)

    def mouseMoveEvent(self, event):
        if self.placement is not None:  # pendant le placement d'une image, la souris ne sert qu'à elle
            if self.drag is not None:
                free_ratio = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self._drag_placement(event.position(), free_ratio)
                self.update()
            else:
                self._update_placement_cursor(event.position())
            return
        field = self._field_at(event.position())
        if field is not self.hovered_field:
            self.hovered_field = field
            self._update_cursor()
            self.update()
        if not self.edit_mode:
            return
        span = None if field is not None else self._span_at(event.position())
        if span is not self.hovered:
            self.hovered = span
            self.update()

    def leaveEvent(self, event):
        if self.hovered is not None or self.hovered_field is not None:
            self.hovered = None
            self.hovered_field = None
            self._update_cursor()
            self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.placement is not None:
            hit = self._placement_hit(event.position())
            if hit in ("ok", "cancel"):
                self.end_placement(hit == "ok")
            elif hit is not None:
                x0, y0, x1, y1 = self.placement["rect"]
                self.drag = (hit, event.position(), (x0, y0, x1, y1))
            return
        field = self._field_at(event.position())
        if field is not None:
            self.activate_field(field, event.globalPosition().toPoint())
        elif self.edit_mode:
            span = self._span_at(event.position())
            if span is not None:
                self.open_editor(span)

    def activate_field(self, field, global_pos):
        """Remplit un champ de formulaire : saisie, case à cocher, bouton radio ou liste de choix."""
        kind = field["type"]
        if kind == pymupdf.PDF_WIDGET_TYPE_TEXT:
            rect = self.to_widget(field["view"]).toAlignedRect()
            font = QFont("Arial")
            size = field["fontsize"] or min(12, field["view"][3] - field["view"][1]) * 0.7  # 0 : taille auto
            font.setPixelSize(max(6, round(size * self.zoom)))
            self._open_line_editor(rect, font, str(field["value"] or ""),
                                   lambda text: self.field_edited.emit(self.index, field["xref"], text))
        elif kind == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
            self.field_edited.emit(self.index, field["xref"], field["value"] != field["on"])
        elif kind == pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON:
            if field["value"] != field["on"]:
                self.field_edited.emit(self.index, field["xref"], True)
        else:  # liste déroulante ou liste de choix
            if not field["choices"]:
                return
            menu = QMenu(self)
            for choice in field["choices"]:
                # Un choix peut être un couple (valeur enregistrée, texte affiché).
                value, label = choice if isinstance(choice, (list, tuple)) else (choice, choice)
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(value == field["value"])
                action.triggered.connect(lambda _checked=False, v=value: self.field_edited.emit(
                    self.index, field["xref"], v))
            menu.exec(global_pos)

    def contextMenuEvent(self, event):
        self.close_editor()
        menu = QMenu(self)
        if self.placement is not None:
            menu.addAction("✔ Valider l'emplacement", lambda: self.end_placement(True))
            menu.addAction("✕ Annuler l'insertion", lambda: self.end_placement(False))
            menu.exec(event.globalPos())
            return
        menu.addAction(make_icon("rotate_cw"), "Rotation horaire",
                       lambda: self.rotate_requested.emit(self.index, 90))
        menu.addAction(make_icon("rotate_ccw"), "Rotation anti-horaire",
                       lambda: self.rotate_requested.emit(self.index, -90))
        menu.addSeparator()
        menu.addAction(make_icon("delete"), "Supprimer la page",
                       lambda: self.delete_requested.emit(self.index))
        menu.exec(event.globalPos())

    def open_editor(self, span):
        rect = self._span_rect(span).adjusted(-3, -3, 3, 3).toAlignedRect()
        rect.setWidth(max(rect.width() + 60, 120))

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            path, _substitute = find_system_font(span)  # équivalent standard (Helvetica -> Arial) accepté
        finally:
            QApplication.restoreOverrideCursor()
        # Police installée : la saisie s'affiche dans cette police même (Qt ne la retrouve pas toujours d'après
        # le nom du PDF, « WorkSans » pour « Work Sans »).
        family = (qt_font_family(path) if path else None) or span["font"].split("+", 1)[-1].split("-")[0].split(",")[0]
        font = QFont(family)
        font.setPixelSize(max(6, round(span["size"] * self.zoom)))
        font.setBold(bool(span["flags"] & pymupdf.TEXT_FONT_BOLD))
        font.setItalic(bool(span["flags"] & pymupdf.TEXT_FONT_ITALIC))

        self._open_line_editor(rect, font, span["text"], lambda text: self.span_edited.emit(self.index, span, text))
        if not path:
            self._warn_missing_font(span, rect)

    def _warn_missing_font(self, span, rect):
        """Bandeau sous la zone d'édition : la police du texte n'est pas installée sur ce PC.

        La saisie s'affiche alors dans une police de remplacement, et le texte écrit dépendra de la version
        intégrée au PDF, souvent réduite aux seules lettres déjà présentes. Le lien « Infos sur la police »
        donne tout ce qu'il faut pour la retrouver et l'installer.
        """
        family, style = readable_font_name(span["font"])
        name = html.escape(f"{family} {style}".strip())
        warning = QLabel(f"⚠ Police « <b>{name}</b> » non installée sur ce PC : la saisie s'affiche dans une autre "
                         "police, et le texte sera écrit avec la police intégrée au PDF si elle contient vos "
                         "lettres, sinon avec une police proche. <a href='infos'>Infos sur la police…</a> "
                         "pour la retrouver et l'installer.", self)
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.linkActivated.connect(lambda _link: self.font_info_requested.emit(self.index, span))
        warning.setWordWrap(True)
        warning.setStyleSheet("background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; "
                              "border-radius: 4px; padding: 4px 8px;")
        width = min(max(rect.width(), 360), self.width())
        warning.setFixedWidth(width)
        warning.adjustSize()
        x = max(0, min(rect.left(), self.width() - width))
        y = rect.bottom() + 4
        if y + warning.height() > self.height():  # en bas de page : au-dessus de la zone d'édition
            y = rect.top() - warning.height() - 4
        warning.move(x, y)
        warning.show()
        self.font_warning = warning

    def _open_line_editor(self, rect, font, text, on_commit):
        """Champ de saisie posé sur la page ; on_commit(texte) est appelé si le texte a changé."""
        self.close_editor()
        editor = InlineEditor(text, self)
        editor.setFont(font)
        editor.setGeometry(rect)
        editor.setStyleSheet(f"background: white; border: 2px solid {ACCENT}; border-radius: 4px; padding: 0;")
        editor.selectAll()
        editor.returnPressed.connect(lambda: self._commit(text, on_commit))
        editor.cancelled.connect(self.close_editor)
        editor.show()
        editor.setFocus()
        self.editor = editor

    def _commit(self, original, on_commit):
        text = self.editor.text()
        self.close_editor()
        if text != original:
            on_commit(text)

    def close_editor(self):
        if self.editor is not None:
            editor, self.editor = self.editor, None
            editor.blockSignals(True)
            editor.hide()
            editor.deleteLater()
        if self.font_warning is not None:
            warning, self.font_warning = self.font_warning, None
            warning.hide()
            warning.deleteLater()


class PagesContainer(QWidget):
    """Fond de la zone de lecture : dessine une ombre douce sous chaque page.

    (Plus léger qu'un effet graphique par page, qui ralentirait l'affichage.)
    """

    BACKGROUND = QColor("#e5e9f0")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.BACKGROUND)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 8))
        for child in self.findChildren(PageWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            rect = QRectF(child.geometry()).translated(0, 3)
            if not child.isVisible() or not rect.adjusted(-10, -10, 10, 10).intersects(QRectF(event.rect())):
                continue
            for i in range(8, 0, -1):
                painter.drawRoundedRect(rect.adjusted(-i, -i, i, i), i, i)


class MergeDialog(QDialog):
    """Choix et ordre des PDF à concaténer."""

    CURRENT = object()  # repère le document actuellement ouvert

    def __init__(self, current_label=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Concaténer des PDF")
        self.resize(560, 400)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.model().rowsInserted.connect(self._update_ok)
        self.list.model().rowsRemoved.connect(self._update_ok)

        side = QVBoxLayout()
        for spec in (
            ("add", "Ajouter…", "Ajouter des fichiers PDF à la liste", self.add_files),
            ("remove", "Retirer", "Retirer les documents sélectionnés de la liste (les fichiers ne sont pas supprimés)",
             self.remove_selected),
            None,
            ("previous", "Monter", "Placer les documents sélectionnés plus tôt", lambda: self.move_selected(-1)),
            ("next", "Descendre", "Placer les documents sélectionnés plus tard", lambda: self.move_selected(1)),
        ):
            if spec is None:
                side.addSpacing(12)
                continue
            icon, text, tooltip, slot = spec
            button = QPushButton(make_icon(icon), text)
            button.setIconSize(QSize(20, 20))
            button.setToolTip(tooltip)
            button.setStyleSheet("text-align: left; padding: 7px 12px;")
            button.clicked.connect(slot)
            side.addWidget(button)
        side.addStretch()

        center = QHBoxLayout()
        center.addWidget(self.list)
        center.addLayout(side)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Concaténer")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setIcon(make_icon("merge"))
        set_primary(self.buttons.button(QDialogButtonBox.StandardButton.Ok))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Les documents seront assemblés dans cet ordre (glisser-déposer pour réordonner) :"))
        layout.addLayout(center)
        layout.addWidget(self.buttons)

        if current_label is not None:
            self._add_item(f"{current_label} (document actuel)", self.CURRENT)
        self._update_ok()

    def _add_item(self, text, data):
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, data)
        item.setToolTip(data if isinstance(data, str) else "Document actuellement ouvert, avec ses modifications")
        self.list.addItem(item)

    def _update_ok(self):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.list.count() >= 2)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ajouter des PDF", "", "Fichiers PDF (*.pdf)")
        for path in paths:
            self._add_item(os.path.basename(path), path)

    def remove_selected(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def move_selected(self, step):
        rows = sorted((self.list.row(item) for item in self.list.selectedItems()), reverse=step > 0)
        if not rows or not 0 <= rows[0] + step < self.list.count():
            return
        for row in rows:
            item = self.list.takeItem(row)
            self.list.insertItem(row + step, item)
            item.setSelected(True)

    def entries(self):
        """Chemins des fichiers dans l'ordre choisi (ou CURRENT pour le document ouvert)."""
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]


class CompressDialog(QDialog):
    """Proposé à l'enregistrement : compresser ou non le PDF."""

    CHOICES = [
        (COMPRESS_NONE, "Ne pas compresser",
         "Enregistrement normal, le plus rapide."),
        (COMPRESS_LOSSLESS, "Compression sans perte",
         "Réduit la taille sans aucune perte de qualité (nettoyage et compression des données)."),
        (COMPRESS_IMAGES, "Compression forte (images réduites)",
         f"Images recompressées en JPEG (qualité {COMPRESS_JPEG_QUALITY}) et, si elles sont très détaillées, "
         f"ramenées à environ {COMPRESS_DPI} ppp : idéal pour un envoi par e-mail. "
         "Le texte reste net et modifiable."),
    ]

    def __init__(self, current, remember, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enregistrer")

        layout = QVBoxLayout(self)
        title = QLabel("Voulez-vous compresser le PDF ?")
        title.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(title)
        layout.addSpacing(4)

        self.radios = {}
        for key, text, description in self.CHOICES:
            radio = QRadioButton(text)
            radio.setChecked(key == current)
            hint = QLabel(description)
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            hint.setContentsMargins(24, 0, 0, 6)
            layout.addWidget(radio)
            layout.addWidget(hint)
            self.radios[key] = radio

        self.remember_box = QCheckBox("Ne plus demander pour « Enregistrer » (jusqu'à la fermeture du logiciel)")
        self.remember_box.setChecked(remember)
        layout.addSpacing(4)
        layout.addWidget(self.remember_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setIcon(make_icon("save"))
        set_primary(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(6)
        layout.addWidget(buttons)
        self.setFixedWidth(480)

    def choice(self):
        return next(key for key, radio in self.radios.items() if radio.isChecked())

    def remember(self):
        return self.remember_box.isChecked()


class FontInfoDialog(QDialog):
    """Tout ce que l'on sait de la police d'origine d'un texte, pour la retrouver sur Internet et l'installer :
    modifier le texte avec cette police, et non une police de remplacement, demande qu'elle soit installée."""

    INSTALLED = 2  # code de retour : l'utilisateur indique avoir installé la police

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("Police d'origine")
        names = info["names"]
        layout = QVBoxLayout(self)

        title = QLabel(f"{info['family']} — {info['style']}")
        title.setStyleSheet("font-size: 13pt; font-weight: 600;")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title)
        hint = QLabel("Cette police n'est pas installée sur ce PC. Pour modifier le texte avec sa police d'origine, "
                      "installez-la : les informations ci-dessous, lues dans le PDF, aident à trouver exactement "
                      "la bonne (même famille, même style).")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(4)

        if not info["embedded"]:
            in_pdf = ("Non intégrée au PDF : le document compte sur la police installée de l'ordinateur qui "
                      "l'affiche.")
        elif info["subset"]:
            letters = info["letters"]
            shown = " ".join(letters) if len(letters) <= 80 else " ".join(letters[:80]) + " …"
            in_pdf = (f"Intégrée au PDF, mais réduite aux {len(letters)} caractères utilisés dans le document : "
                      "sans la police installée, seuls ceux-ci peuvent être écrits dans la police d'origine "
                      f"(les autres sont pris dans une police proche).\n{shown}")
        else:
            in_pdf = "Intégrée au PDF en entier : tous ses caractères peuvent être écrits."
        rows = [
            ("Nom exact", names.get(6) or info["pdf_name"]),
            ("Famille", info["family"]),
            ("Style", info["style"]),
            ("Nom complet", names.get(4)),
            ("Version", names.get(5)),
            ("Éditeur", names.get(8)),
            ("Créateur", names.get(9)),
            ("Site de l'éditeur", names.get(11)),
            ("Site du créateur", names.get(12)),
            ("Licence", names.get(13)),
            ("Lien de la licence", names.get(14)),
            ("Copyright", names.get(0)),
            ("Dans ce PDF", in_pdf),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        for row, (label, value) in enumerate((label, value) for label, value in rows if value):
            if len(value) > 400:  # texte de licence complet : le début suffit, le lien donne le reste
                value = value[:400].rsplit(" ", 1)[0] + "…"
            key = QLabel(label)
            key.setObjectName("hint")
            key.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            if re.match(r"^(https?://|www\.)\S+$", value):
                url = value if value.startswith("http") else "https://" + value
                text = QLabel(f"<a href='{html.escape(url, quote=True)}'>{html.escape(value)}</a>")
                text.setOpenExternalLinks(True)
            else:
                text = QLabel(value)
                text.setTextFormat(Qt.TextFormat.PlainText)
            text.setWordWrap(True)
            text.setTextInteractionFlags(text.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(key, row, 0)
            grid.addWidget(text, row, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addSpacing(8)

        steps = QLabel(
            "<b>Pour l'installer :</b><ol style='margin-left:-20px'>"
            "<li>Recherchez-la avec les boutons ci-dessous. Beaucoup de polices sont gratuites (Google Fonts…), "
            "d'autres payantes : vérifiez la licence.</li>"
            "<li>Téléchargez le fichier <b>.ttf</b> ou <b>.otf</b> du bon style, ouvrez-le et cliquez sur "
            "<b>Installer</b>.</li>"
            "<li>Revenez ici et cliquez sur <b>J'ai installé la police</b> : inutile de redémarrer.</li></ol>")
        steps.setWordWrap(True)
        layout.addWidget(steps)

        search = QHBoxLayout()
        for text, slot in (("Copier le nom", self._copy_name), ("Rechercher sur Internet", self._search_web),
                           ("Chercher sur Google Fonts", self._search_google_fonts)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            search.addWidget(button)
        if names.get(11) or names.get(12):
            button = QPushButton("Site de l'éditeur")
            button.clicked.connect(lambda: self._open(names.get(11) or names.get(12)))
            search.addWidget(button)
        search.addStretch(1)
        layout.addLayout(search)

        buttons = QDialogButtonBox()
        installed = buttons.addButton("J'ai installé la police", QDialogButtonBox.ButtonRole.AcceptRole)
        set_primary(installed)
        installed.clicked.connect(lambda: self.done(self.INSTALLED))
        buttons.addButton("Fermer", QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumWidth(560)

    def _search_text(self):
        return f"{self.info['family']} {self.info['style']}".strip()

    def _copy_name(self):
        QApplication.clipboard().setText(self._search_text())

    @staticmethod
    def _open(url):
        QDesktopServices.openUrl(QUrl(url if url.startswith("http") else "https://" + url))

    def _search_web(self):
        url = QUrl("https://www.google.com/search")
        query = QUrlQuery()
        query.addQueryItem("q", f'"{self.info["family"]}" {self.info["style"]} font')
        url.setQuery(query)
        QDesktopServices.openUrl(url)

    def _search_google_fonts(self):
        url = QUrl("https://fonts.google.com/")
        query = QUrlQuery()
        query.addQueryItem("query", self.info["family"])
        url.setQuery(query)
        QDesktopServices.openUrl(url)


class PasswordDialog(QDialog):
    """Protection du PDF par mot de passe : ajouter, changer ou retirer."""

    REMOVE = 2  # code de retour : retirer la protection

    def __init__(self, protected, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Protéger par mot de passe")

        layout = QVBoxLayout(self)
        title = QLabel("Changer le mot de passe du PDF" if protected else "Protéger le PDF par un mot de passe")
        title.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(title)
        hint = QLabel(
            "Le mot de passe sera demandé à chaque ouverture du document (chiffrement AES 256 bits). "
            "Conservez-le précieusement : il est impossible de le retrouver s'il est perdu.\n"
            "La protection est appliquée au prochain enregistrement."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(6)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Mot de passe")
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("Confirmer le mot de passe")
        for edit in (self.password_edit, self.confirm_edit):
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.textChanged.connect(self._validate)
            layout.addWidget(edit)
        self.show_box = QCheckBox("Afficher le mot de passe")
        self.show_box.toggled.connect(self._toggle_visible)
        layout.addWidget(self.show_box)
        self.error_label = QLabel()
        self.error_label.setStyleSheet(f"color: {RED};")
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Protéger")
        self.ok_button.setIcon(make_icon("lock"))
        set_primary(self.ok_button)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        if protected:
            remove = self.buttons.addButton("Retirer la protection", QDialogButtonBox.ButtonRole.DestructiveRole)
            remove.clicked.connect(lambda: self.done(self.REMOVE))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.setFixedWidth(460)
        self._validate()

    def _toggle_visible(self, visible):
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        for edit in (self.password_edit, self.confirm_edit):
            edit.setEchoMode(mode)

    def _validate(self):
        password, confirm = self.password_edit.text(), self.confirm_edit.text()
        mismatch = bool(confirm) and password != confirm
        self.error_label.setText("Les deux mots de passe ne correspondent pas." if mismatch else "")
        self.ok_button.setEnabled(bool(password) and password == confirm)

    def password(self):
        return self.password_edit.text()


def format_size(size):
    """Taille de fichier lisible, à la française : 1,4 Mo, 820 Ko."""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} Mo".replace(".", ",")
    return f"{max(1, round(size / 1024))} Ko"


class PageList(QListWidget):
    """Vignettes des pages : glisser-déposer d'une page ou d'un groupe de pages sélectionnées.

    Le déplacement est géré ici plutôt que par Qt, dont le glisser-déposer interne en mode icônes
    place mal (voire perd) les groupes de pages.
    """

    MIME_TYPE = "application/x-pdf-toolkit-pages"
    AUTOSCROLL_MARGIN = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        # Static (et non Free) : les vignettes restent rangées dans l'ordre des pages.
        self.setMovement(QListView.Movement.Static)
        # Clic gauche : sélection uniquement ; le déplacement se fait au clic droit (voir mousePressEvent).
        # Après setMovement, qui (en mode Static) fait refuser tout dépôt à la zone des vignettes.
        self.setDragEnabled(False)
        self.viewport().setAcceptDrops(True)
        self.drop_target = None  # pendant un glisser : (indice d'insertion, repère (x, haut, bas) ou None)
        self.right_press = None  # position de l'appui droit sur une vignette (glisser au clic droit)
        self.scroll_step = 0
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(30)
        self.scroll_timer.timeout.connect(
            lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().value() + self.scroll_step)
        )

    # Glisser au clic droit : Qt ne démarre un glisser qu'au bouton gauche, on le démarre donc ici.
    # Un appui droit sur une page déjà sélectionnée garde la sélection (tout le groupe est déplacé) ;
    # sur une autre page, il la sélectionne seule. Relâcher le bouton droit dépose les pages.

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.right_press = None
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton and self.itemAt(pos) is not None:
            self.right_press = pos

    def mouseMoveEvent(self, event):
        if self.right_press is None:
            super().mouseMoveEvent(event)
            return
        # Pas d'appel à Qt ici : il modifierait la sélection pendant le mouvement.
        distance = (event.position().toPoint() - self.right_press).manhattanLength()
        if event.buttons() & Qt.MouseButton.RightButton and distance >= QApplication.startDragDistance():
            self.right_press = None
            self.startDrag(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_press = None
        super().mouseReleaseEvent(event)

    def startDrag(self, actions):
        items = self.selectedItems()
        if not items:
            return
        current = self.currentItem()
        if current is None or not current.isSelected():
            current = items[0]
        pixmap = current.icon().pixmap(QSize(90, 135))
        size = pixmap.deviceIndependentSize()
        if len(items) > 1:  # pastille : nombre de pages déplacées
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            badge = QRectF(size.width() - 34, 2, 32, 32)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ACCENT))
            painter.drawEllipse(badge)
            font = QFont("Segoe UI")
            font.setPixelSize(15)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(len(items)))
            painter.end()
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, QByteArray())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(round(size.width() / 2), round(size.height() / 2)))
        drag.exec(Qt.DropAction.MoveAction)
        self._end_drag()

    def _accepts(self, event):
        return event.source() is self and event.mimeData().hasFormat(self.MIME_TYPE)

    def _drop_target(self, pos):
        """Indice où insérer les pages déposées en pos, et position du repère à dessiner.

        Les vignettes sont rangées de gauche à droite puis de haut en bas : on cherche la
        première vignette de la rangée du pointeur dont le centre est à sa droite.
        """
        spacing = self.spacing()
        last = None  # dernière vignette de la rangée du pointeur, à gauche de celui-ci
        index = self.count()
        for i in range(self.count()):
            rect = self.visualItemRect(self.item(i))
            if pos.y() < rect.top() - spacing:  # pointeur au-dessus de cette rangée
                index = i
                break
            if pos.y() <= rect.bottom() + spacing:  # même rangée
                if pos.x() < rect.center().x():
                    return i, (rect.left() - spacing, rect.top(), rect.bottom())
                last = rect
        if last is not None:
            return index, (last.right() + spacing, last.top(), last.bottom())
        if index < self.count():
            rect = self.visualItemRect(self.item(index))
            return index, (rect.left() - spacing, rect.top(), rect.bottom())
        return index, None

    def dragEnterEvent(self, event):
        if self._accepts(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._accepts(event):
            event.ignore()
            return
        event.acceptProposedAction()
        pos = event.position().toPoint()
        self.drop_target = self._drop_target(pos)
        # Défilement automatique près du haut ou du bas de la liste.
        height = self.viewport().height()
        if pos.y() < self.AUTOSCROLL_MARGIN:
            self.scroll_step = -(self.AUTOSCROLL_MARGIN - pos.y()) // 3 - 2
        elif pos.y() > height - self.AUTOSCROLL_MARGIN:
            self.scroll_step = (pos.y() - height + self.AUTOSCROLL_MARGIN) // 3 + 2
        else:
            self.scroll_step = 0
        if self.scroll_step:
            self.scroll_timer.start()
        else:
            self.scroll_timer.stop()
        self.viewport().update()

    def dragLeaveEvent(self, event):
        self._end_drag()

    def dropEvent(self, event):
        if not self._accepts(event):
            event.ignore()
            return
        index = self._drop_target(event.position().toPoint())[0]
        self._end_drag()
        event.acceptProposedAction()
        self.move_items(self.selectedItems(), index)

    def _end_drag(self):
        self.drop_target = None
        self.scroll_timer.stop()
        self.viewport().update()

    def move_items(self, items, index):
        """Place les éléments (dans leur ordre actuel) à l'indice donné de la liste d'avant le déplacement."""
        rows = sorted(self.row(item) for item in items)
        if not rows:
            return
        index -= sum(1 for row in rows if row < index)
        taken = [self.takeItem(row) for row in reversed(rows)][::-1]
        for offset, item in enumerate(taken):
            self.insertItem(index + offset, item)
        self.clearSelection()
        for item in taken:
            item.setSelected(True)
        self.scrollToItem(taken[0])

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drop_target is None or self.drop_target[1] is None:
            return
        x, top, bottom = self.drop_target[1]
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(ACCENT), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(x, top, x, bottom)
        painter.end()


class PageOrderDialog(QDialog):
    """Organisation des pages : ordre (glisser-déposer), rotation et suppression."""

    THUMB_WIDTH = 140
    INDEX_ROLE = Qt.ItemDataRole.UserRole
    ROTATION_ROLE = Qt.ItemDataRole.UserRole + 1
    PIXMAP_ROLE = Qt.ItemDataRole.UserRole + 2

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Organiser les pages")
        self.resize(900, 650)

        self.list = PageList()
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setWrapping(True)
        self.list.setSpacing(10)
        self.list.setIconSize(QSize(self.THUMB_WIDTH, round(self.THUMB_WIDTH * 1.5)))
        # Ctrl+clic, Maj+clic ou cadre tracé à la souris pour sélectionner plusieurs pages.
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setSelectionRectVisible(True)

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for i, page in enumerate(doc):
                zoom = self.THUMB_WIDTH / max(page.rect.width, 1)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(image)
                # Cadre gris pour distinguer les pages blanches du fond de la liste.
                painter = QPainter(pixmap)
                painter.setPen(QPen(QColor("#909090"), 1))
                painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
                painter.end()
                item = QListWidgetItem(QIcon(pixmap), f"Page {i + 1}")
                item.setData(self.INDEX_ROLE, i)
                item.setData(self.ROTATION_ROLE, 0)
                item.setData(self.PIXMAP_ROLE, pixmap)
                self.list.addItem(item)
        finally:
            QApplication.restoreOverrideCursor()
        # Garde une référence à tous les éléments, y compris ceux retirés de la liste.
        self.all_items = [self.list.item(i) for i in range(self.list.count())]

        side = QVBoxLayout()
        for spec in (
            ("move_back", "Avancer", "Déplacer les pages sélectionnées vers le début", lambda: self.move_selected(-1)),
            ("move_forward", "Reculer", "Déplacer les pages sélectionnées vers la fin", lambda: self.move_selected(1)),
            None,
            ("rotate_cw", "Rotation horaire", "Pivoter de 90° dans le sens horaire", lambda: self.rotate_selected(90)),
            ("rotate_ccw", "Rotation anti-horaire", "Pivoter de 90° dans le sens anti-horaire",
             lambda: self.rotate_selected(-90)),
            None,
            ("delete", "Supprimer", "Supprimer les pages sélectionnées", self.delete_selected),
            None,
            ("reset", "Tout réinitialiser", "Revenir à l'état de départ (ordre, rotations, pages)", self.reset_order),
        ):
            if spec is None:
                side.addSpacing(12)
                continue
            icon, text, tooltip, slot = spec
            button = QPushButton(make_icon(icon), text)
            button.setIconSize(QSize(20, 20))
            button.setToolTip(tooltip)
            button.setStyleSheet("text-align: left; padding: 7px 12px;")
            button.clicked.connect(slot)
            side.addWidget(button)
        side.addStretch()

        center = QHBoxLayout()
        center.addWidget(self.list)
        center.addLayout(side)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer")
        set_primary(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Clic gauche : sélectionner les pages (Ctrl+clic, Maj+clic ou cadre tracé à la souris pour en "
            "sélectionner plusieurs).\nClic droit maintenu : déplacer la sélection, puis relâcher à "
            "l'emplacement voulu. Les boutons à droite pivotent ou suppriment les pages sélectionnées."
        ))
        layout.addLayout(center)
        layout.addWidget(buttons)

    def move_selected(self, step):
        rows = sorted((self.list.row(item) for item in self.list.selectedItems()), reverse=step > 0)
        if not rows or not 0 <= rows[0] + step < self.list.count():
            return
        for row in rows:
            item = self.list.takeItem(row)
            self.list.insertItem(row + step, item)
            item.setSelected(True)
        self.list.scrollToItem(self.list.item(rows[-1] + step))

    def _set_rotation(self, item, rotation):
        item.setData(self.ROTATION_ROLE, rotation)
        pixmap = item.data(self.PIXMAP_ROLE).transformed(QTransform().rotate(rotation))
        item.setIcon(QIcon(pixmap))

    def rotate_selected(self, angle):
        for item in self.list.selectedItems():
            self._set_rotation(item, (item.data(self.ROTATION_ROLE) + angle) % 360)

    def delete_selected(self):
        items = self.list.selectedItems()
        if not items:
            return
        if len(items) >= self.list.count():
            QMessageBox.warning(self, "Suppression impossible", "Le document doit garder au moins une page.")
            return
        for item in items:
            self.list.takeItem(self.list.row(item))

    def reset_order(self):
        while self.list.count():
            self.list.takeItem(0)
        for item in self.all_items:
            self._set_rotation(item, 0)
            self.list.addItem(item)

    def result_pages(self):
        """Pages conservées dans le nouvel ordre : liste de (indice d'origine, rotation ajoutée)."""
        return [
            (item.data(self.INDEX_ROLE), item.data(self.ROTATION_ROLE))
            for item in (self.list.item(i) for i in range(self.list.count()))
        ]


class SearchBar(QWidget):
    """Barre de recherche (et de remplacement) affichée en haut de la fenêtre."""

    search_changed = Signal()
    find_next = Signal()
    find_previous = Signal()
    replace_one = Signal()
    replace_all = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Rechercher…")
        self.find_edit.setClearButtonEnabled(True)
        self.find_edit.textChanged.connect(self.search_changed)
        self.find_edit.returnPressed.connect(self._on_return)

        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Remplacer par…")
        self.replace_edit.returnPressed.connect(self.replace_one)

        self.case_box = QCheckBox("Respecter la casse")
        self.case_box.toggled.connect(self.search_changed)
        self.count_label = QLabel()
        self.count_label.setMinimumWidth(110)

        def button(icon, text, tooltip, signal):
            b = QPushButton(make_icon(icon), text)
            b.setIconSize(QSize(18, 18))
            b.setToolTip(tooltip)
            b.clicked.connect(signal)
            if not text:
                b.setFixedWidth(38)
            return b

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel(make_icon_label("🔍")))
        find_row.addWidget(self.find_edit, 1)
        find_row.addWidget(button("previous", "", "Occurrence précédente (Maj+F3)", self.find_previous))
        find_row.addWidget(button("next", "", "Occurrence suivante (Entrée ou F3)", self.find_next))
        find_row.addWidget(self.count_label)
        find_row.addWidget(self.case_box)
        find_row.addWidget(button("close", "", "Fermer la recherche (Échap)", self.close_bar))

        self.replace_row = QWidget()
        replace_row = QHBoxLayout(self.replace_row)
        replace_row.setContentsMargins(0, 0, 0, 0)
        replace_row.addWidget(QLabel(make_icon_label("⇄")))
        replace_row.addWidget(self.replace_edit, 1)
        replace_row.addWidget(button("replace", "Remplacer", "Remplacer l'occurrence sélectionnée", self.replace_one))
        replace_row.addWidget(button("replace", "Tout remplacer", "Remplacer toutes les occurrences", self.replace_all))
        replace_row.addSpacing(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addLayout(find_row)
        layout.addWidget(self.replace_row)
        self.hide()

    def open(self, replace):
        self.replace_row.setVisible(replace)
        self.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def close_bar(self):
        self.hide()
        self.closed.emit()

    def _on_return(self):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.find_previous.emit()
        else:
            self.find_next.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
        else:
            super().keyPressEvent(event)

    def set_count(self, current, total):
        if not self.find_edit.text():
            self.count_label.setText("")
        elif total == 0:
            self.count_label.setText("Aucun résultat")
        else:
            self.count_label.setText(f"{current + 1} sur {total}")
        missing = bool(self.find_edit.text()) and total == 0
        if self.find_edit.property("notfound") != missing:
            self.find_edit.setProperty("notfound", missing)
            self.find_edit.style().unpolish(self.find_edit)
            self.find_edit.style().polish(self.find_edit)


def make_icon_label(glyph):
    """Petit symbole affiché devant un champ de saisie."""
    return f'<span style="font-family: \'Segoe UI Symbol\'; font-size: 13pt; color: {SLATE};">{glyph}</span>'


# Fonctionnalités présentées sur l'écran d'accueil : (icône, titre, description, raccourcis)
FEATURES = [
    ("open", "Ouvrir, enregistrer et imprimer",
     "Ouvrez un PDF (ou glissez-le dans la fenêtre), enregistrez vos modifications ou une copie "
     "du document, compressé ou protégé par mot de passe si vous le souhaitez, et imprimez-le.",
     "Ctrl+O · Ctrl+S · Ctrl+Maj+S · Ctrl+P · Ctrl+W"),
    ("merge", "Concaténer des PDF",
     "Assemblez plusieurs fichiers en un seul document, dans l'ordre de votre choix. "
     "Un PDF glissé sur le document ouvert est ajouté à la fin.",
     "Ctrl+M"),
    ("edit", "Modifier le texte",
     "Activez le mode édition puis cliquez sur un texte. Entrée valide, Échap annule ; "
     "la police d'origine est conservée quand c'est possible.",
     "Ctrl+E"),
    ("form", "Remplir les formulaires",
     "Les champs d'un formulaire PDF sont teintés en bleu : cliquez dessus pour saisir du texte, "
     "cocher une case ou choisir dans une liste.",
     "Clic sur un champ"),
    ("image", "Images et signatures",
     "Insérez une image ou votre signature (PNG, JPG), déplacez-la et redimensionnez-la à la souris, "
     "puis validez. Le fond blanc d'une signature scannée devient transparent.",
     "Ctrl+I · Ctrl+Maj+I"),
    ("search", "Rechercher et remplacer",
     "Toutes les occurrences sont surlignées. Remplacez-les une par une ou toutes d'un coup.",
     "Ctrl+F · Ctrl+H · F3"),
    ("pages", "Organiser les pages",
     "Sélectionnez des pages au clic gauche, déplacez-les en les glissant au clic droit, "
     "pivotez-les ou supprimez-les. "
     "Un clic droit sur une page permet d'aller plus vite.",
     "Ctrl+R"),
    ("undo", "Annuler et rétablir",
     "Chaque opération (texte, pages, remplacements, concaténation) peut être annulée puis rétablie.",
     "Ctrl+Z · Ctrl+Y"),
    ("zoom_in", "Zoom et navigation",
     "Agrandissez ou réduisez l'affichage des pages, et allez directement à une page donnée "
     "(ou cliquez sur « Page 3 / 12 » en bas à droite).",
     "Ctrl++ · Ctrl+- · Ctrl+G"),
]


class WelcomeWidget(QWidget):
    """Écran d'accueil affiché tant qu'aucun document n'est ouvert."""

    def __init__(self, open_callback, merge_callback, parent=None):
        super().__init__(parent)

        # Bandeau d'en-tête : titre, accroche et actions principales.
        hero = QFrame()
        hero.setObjectName("hero")
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 26pt; font-weight: 700;")
        subtitle = QLabel("Modifiez, assemblez et organisez vos PDF en toute simplicité.")
        subtitle.setStyleSheet("font-size: 12pt;")

        open_button = QPushButton(make_icon("open"), "Ouvrir un PDF…")
        open_button.clicked.connect(open_callback)
        open_button.setStyleSheet(
            f"QPushButton {{ background: white; color: {ACCENT}; border: none; font-weight: 600; }}"
            "QPushButton:hover { background: #eff6ff; }"
        )
        merge_button = QPushButton(make_icon("merge"), "Concaténer des PDF…")
        merge_button.clicked.connect(merge_callback)
        merge_button.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.15); color: white;"
            " border: 1px solid rgba(255,255,255,0.6); font-weight: 600; }"
            "QPushButton:hover { background: rgba(255,255,255,0.28); }"
        )
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        for button in (open_button, merge_button):
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(42)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        buttons.addStretch()

        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(36, 30, 36, 30)
        hero_layout.setSpacing(6)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(16)
        hero_layout.addLayout(buttons)
        add_shadow(hero, blur=30, offset=6, alpha=60)

        # Cartes des fonctionnalités.
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, feature in enumerate(FEATURES):
            card = self._feature_card(*feature)
            span = 2 if i == len(FEATURES) - 1 and len(FEATURES) % 2 else 1
            grid.addWidget(card, i // 2, i % 2, 1, span)

        section = QLabel("Ce que vous pouvez faire")
        section.setStyleSheet("font-size: 13pt; font-weight: 600; background: transparent;")

        content = QWidget()
        content.setMaximumWidth(920)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 28, 0, 28)
        content_layout.setSpacing(14)
        content_layout.addWidget(hero)
        content_layout.addSpacing(10)
        content_layout.addWidget(section)
        content_layout.addLayout(grid)

        inner = QWidget()
        inner.setObjectName("welcome")
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(24, 0, 24, 0)
        inner_layout.addStretch()
        inner_layout.addWidget(content, 1, Qt.AlignmentFlag.AlignTop)
        inner_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    @staticmethod
    def _feature_card(icon, title, description, shortcuts):
        card = QFrame()
        card.setObjectName("featureCard")

        icon_label = QLabel()
        icon_label.setPixmap(make_icon(icon).pixmap(30, 30))
        icon_label.setFixedSize(46, 46)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: #eff6ff; border-radius: 10px;")

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        text_label = QLabel(description)
        text_label.setObjectName("hint")
        text_label.setWordWrap(True)
        shortcut_label = QLabel(shortcuts)
        shortcut_label.setObjectName("shortcut")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.addWidget(title_label)
        text_layout.addWidget(text_label)
        text_layout.addSpacing(4)
        text_layout.addWidget(shortcut_label, 0, Qt.AlignmentFlag.AlignLeft)
        text_layout.addStretch()

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_layout, 1)
        return card


class PdfEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1100, 950)

        self.doc = None
        self.path = None
        self.password = None  # mot de passe appliqué à l'enregistrement (None : PDF non protégé)
        # Chaque état du document reçoit un numéro ; il est modifié si son état diffère du dernier enregistré.
        # Annuler jusqu'à l'état enregistré le rend donc à nouveau « non modifié ».
        self.state_id = 0
        self.saved_id = 0
        self._last_state_id = 0
        self.zoom = 1.5
        self.pages = []
        # (libellé, contenu du PDF, chemin, numéro d'état, mot de passe) avant chaque opération / annulation
        self.undo_stack = []
        self.redo_stack = []
        self.matches = []  # occurrences de la recherche : (page, span, début, fin)
        self.match_index = -1
        self.pending_image = None  # image en cours de placement : {"path", "pixmap", "signature"}
        self.last_compression = COMPRESS_NONE  # choix présélectionné dans la fenêtre de compression
        self.remembered_compression = None  # choix gardé pour « Enregistrer » (« ne plus demander »)

        self.container = PagesContainer()
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("viewer")
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.container)

        # Accueil tant qu'aucun document n'est ouvert, puis affichage des pages.
        self.welcome = WelcomeWidget(self.open_dialog, self.merge_dialog)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.scroll)

        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(lambda: self.update_search(reset=True, scroll=True))
        self.search_bar.find_next.connect(lambda: self.find_step(1))
        self.search_bar.find_previous.connect(lambda: self.find_step(-1))
        self.search_bar.replace_one.connect(self.replace_current)
        self.search_bar.replace_all.connect(self.replace_all)
        self.search_bar.closed.connect(self.update_search)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.search_bar)
        central_layout.addWidget(self.stack)
        self.setCentralWidget(central)

        # Numéro de la page affichée, à droite de la barre d'état (cliquer dessus : aller à la page…).
        self.page_label = QPushButton()
        self.page_label.setFlat(True)
        self.page_label.setToolTip("Aller à la page… (Ctrl+G)")
        self.page_label.setStyleSheet("QPushButton { border: none; padding: 2px 10px; color: #475569; }"
                                      "QPushButton:hover { background: #f1f5f9; }")
        self.page_label.clicked.connect(self.go_to_page_dialog)
        self.statusBar().addPermanentWidget(self.page_label)
        self.scroll.verticalScrollBar().valueChanged.connect(self._update_page_label)

        self._create_menu()
        self.setAcceptDrops(True)  # PDF glissés depuis l'Explorateur
        self.statusBar().showMessage("Prêt.")
        self._update_page_label()
        self._update_title()

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&Fichier")

        self.open_action = QAction(make_icon("open"), "&Ouvrir…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_dialog)
        file_menu.addAction(self.open_action)

        self.merge_action = QAction(make_icon("merge"), "&Concaténer des PDF…", self)
        self.merge_action.setShortcut("Ctrl+M")
        self.merge_action.triggered.connect(self.merge_dialog)
        file_menu.addAction(self.merge_action)

        file_menu.addSeparator()

        self.save_action = QAction(make_icon("save"), "&Enregistrer", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Enregistrer &sous…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_as)
        file_menu.addAction(self.save_as_action)

        self.close_action = QAction(make_icon("close"), "&Fermer", self)
        self.close_action.setShortcuts([QKeySequence("Ctrl+W"), QKeySequence("Ctrl+F4")])
        self.close_action.triggered.connect(self.close_document)
        file_menu.addAction(self.close_action)

        file_menu.addSeparator()

        self.protect_action = QAction(make_icon("lock"), "&Protéger par mot de passe…", self)
        self.protect_action.triggered.connect(self.protect_dialog)
        file_menu.addAction(self.protect_action)

        file_menu.addSeparator()

        self.print_action = QAction(make_icon("print"), "&Imprimer…", self)
        self.print_action.setShortcut(QKeySequence.StandardKey.Print)
        self.print_action.triggered.connect(self.print_document)
        file_menu.addAction(self.print_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = self.menuBar().addMenu("&Édition")

        self.undo_action = QAction(make_icon("undo"), "&Annuler", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction(make_icon("redo"), "&Rétablir", self)
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        self.edit_action = QAction(make_icon("edit"), "Mode é&dition du texte", self)
        self.edit_action.setShortcut("Ctrl+E")
        self.edit_action.setCheckable(True)
        self.edit_action.toggled.connect(self.set_edit_mode)
        edit_menu.addAction(self.edit_action)

        self.reorder_action = QAction(make_icon("pages"), "&Organiser les pages…", self)
        self.reorder_action.setShortcut("Ctrl+R")
        self.reorder_action.triggered.connect(self.reorder_dialog)
        edit_menu.addAction(self.reorder_action)

        self.insert_image_action = QAction(make_icon("image"), "Insérer une &image…", self)
        self.insert_image_action.setShortcut("Ctrl+I")
        self.insert_image_action.triggered.connect(lambda: self.insert_image_dialog(signature=False))
        edit_menu.addAction(self.insert_image_action)

        self.insert_signature_action = QAction(make_icon("signature"), "Insérer une si&gnature…", self)
        self.insert_signature_action.setShortcut("Ctrl+Shift+I")
        self.insert_signature_action.triggered.connect(lambda: self.insert_image_dialog(signature=True))
        edit_menu.addAction(self.insert_signature_action)

        edit_menu.addSeparator()

        self.find_action = QAction(make_icon("search"), "&Rechercher…", self)
        self.find_action.setShortcut(QKeySequence.StandardKey.Find)
        self.find_action.triggered.connect(lambda: self.show_search(replace=False))
        edit_menu.addAction(self.find_action)

        self.replace_action = QAction(make_icon("replace"), "Rechercher et rem&placer…", self)
        self.replace_action.setShortcut("Ctrl+H")
        self.replace_action.triggered.connect(lambda: self.show_search(replace=True))
        edit_menu.addAction(self.replace_action)

        self.find_next_action = QAction("Occurrence &suivante", self)
        self.find_next_action.setShortcut(QKeySequence.StandardKey.FindNext)
        self.find_next_action.triggered.connect(lambda: self.find_step(1))
        edit_menu.addAction(self.find_next_action)

        self.find_previous_action = QAction("Occurrence &précédente", self)
        self.find_previous_action.setShortcut(QKeySequence.StandardKey.FindPrevious)
        self.find_previous_action.triggered.connect(lambda: self.find_step(-1))
        edit_menu.addAction(self.find_previous_action)

        view_menu = self.menuBar().addMenu("&Affichage")

        self.zoom_in_action = QAction(make_icon("zoom_in"), "Zoom &avant", self)
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self._zoom(1.25))
        view_menu.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction(make_icon("zoom_out"), "Zoom a&rrière", self)
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self._zoom(0.8))
        view_menu.addAction(self.zoom_out_action)

        view_menu.addSeparator()

        self.goto_action = QAction("&Aller à la page…", self)
        self.goto_action.setShortcut("Ctrl+G")
        self.goto_action.triggered.connect(self.go_to_page_dialog)
        view_menu.addAction(self.goto_action)

        help_menu = self.menuBar().addMenu("&Aide")
        about_action = QAction(f"À &propos de {APP_NAME}…", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        self._create_toolbar()
        self._update_actions()

    def show_about(self):
        QMessageBox.about(
            self,
            f"À propos de {APP_NAME}",
            f"<h2 style='color:{ACCENT}; margin-bottom:0;'>{APP_NAME}</h2>"
            f"<p style='margin-top:4px;'><b>Version {APP_VERSION}</b> — {APP_DATE}</p>"
            "<p>Éditeur de PDF : modification du texte, concaténation, organisation, rotation "
            "et suppression des pages, recherche et remplacement, annulation et rétablissement, impression.</p>"
            f"<p>Application écrite par <b>{APP_AUTHOR}</b><br>"
            f"<span style='color:{SLATE};'>Modèle : {APP_AUTHOR_MODEL}</span><br>"
            f"sous le commandement de <b>{APP_DIRECTOR}</b>.</p>",
        )

    def _create_toolbar(self):
        toolbar = QToolBar("Outils", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(22, 22))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(toolbar)

        groups = [
            [(self.open_action, "Ouvrir"), (self.merge_action, "Concaténer"), (self.save_action, "Enregistrer"),
             (self.print_action, "Imprimer"), (self.close_action, "Fermer")],
            [(self.undo_action, "Annuler"), (self.redo_action, "Rétablir")],
            [(self.edit_action, "Éditer le texte"), (self.reorder_action, "Pages"),
             (self.find_action, "Rechercher"), (self.replace_action, "Remplacer")],
            [(self.insert_image_action, "Image"), (self.insert_signature_action, "Signature")],
            [(self.zoom_out_action, "Zoom −")],
        ]
        for group in groups:
            if toolbar.actions():
                toolbar.addSeparator()
            for action, label in group:
                action.setIconText(label)
                shortcut = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
                tooltip = action.text().replace("&", "").rstrip("…")
                action.setToolTip(f"{tooltip} ({shortcut})" if shortcut else tooltip)
                toolbar.addAction(action)

        self.zoom_label = QLabel()
        self.zoom_label.setObjectName("hint")
        self.zoom_label.setMinimumWidth(52)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)
        self.zoom_in_action.setIconText("Zoom +")
        self.zoom_in_action.setToolTip("Zoom avant (Ctrl++)")
        toolbar.addAction(self.zoom_in_action)
        self._update_zoom_label()

    def _update_zoom_label(self):
        # Le rendu est fait à 72 points par pouce × zoom ; l'écran affiche 96 pixels par pouce.
        self.zoom_label.setText(f"{round(self.zoom * 72 / 96 * 100)} %" if self.doc is not None else "")

    def _update_actions(self):
        has_doc = self.doc is not None
        self.save_action.setEnabled(has_doc)
        self.save_as_action.setEnabled(has_doc)
        self.protect_action.setEnabled(has_doc)
        self.close_action.setEnabled(has_doc)
        self.print_action.setEnabled(has_doc)
        self.edit_action.setEnabled(has_doc)
        self.reorder_action.setEnabled(has_doc)
        for action in (self.find_action, self.replace_action, self.find_next_action, self.find_previous_action,
                       self.zoom_in_action, self.zoom_out_action, self.goto_action,
                       self.insert_image_action, self.insert_signature_action):
            action.setEnabled(has_doc)
        self._update_zoom_label()
        self.undo_action.setEnabled(bool(self.undo_stack))
        self.undo_action.setText(
            f"&Annuler : {self.undo_stack[-1][0]}" if self.undo_stack else "&Annuler"
        )
        self.redo_action.setEnabled(bool(self.redo_stack))
        self.redo_action.setText(
            f"&Rétablir : {self.redo_stack[-1][0]}" if self.redo_stack else "&Rétablir"
        )

    def _update_title(self):
        title = APP_NAME
        if self.path:
            title += f" — {self.path}"
        elif self.doc is not None:
            title += " — Sans titre"
        if self.doc is not None and self.password is not None:
            title += " (protégé par mot de passe)"
        if self.modified:
            title += " *"
        self.setWindowTitle(title)

    @property
    def modified(self):
        return self.state_id != self.saved_id

    def _set_modified(self, modified):
        """True : le document vient de changer (nouvel état) ; False : il correspond au fichier enregistré."""
        if modified:
            self._last_state_id += 1
            self.state_id = self._last_state_id
        else:
            self.saved_id = self.state_id
        self._update_title()

    def _zoom(self, factor):
        if self.doc is None:
            return
        self.zoom = max(0.25, min(6.0, self.zoom * factor))
        for i in range(len(self.pages)):
            self.render_page(i)
        self._update_zoom_label()

    # --- Affichage -------------------------------------------------------

    def render_page(self, index):
        page = self.doc[index]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        self.pages[index].set_content(QPixmap.fromImage(image), page_spans(page), self.zoom, page_fields(page))

    # --- Navigation -------------------------------------------------------

    def current_page(self):
        """Indice de la page affichée : celle qui occupe le haut de la zone de lecture."""
        if not self.pages:
            return 0
        top = self.scroll.verticalScrollBar().value() + self.scroll.viewport().height() // 3
        for i, widget in enumerate(self.pages):
            if widget.geometry().bottom() >= top:
                return i
        return len(self.pages) - 1

    def _update_page_label(self):
        self.page_label.setVisible(bool(self.pages))
        if self.pages:
            self.page_label.setText(f"Page {self.current_page() + 1} / {len(self.pages)}")

    def go_to_page_dialog(self):
        if self.doc is None:
            return
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Aller à la page")
        dialog.setLabelText(f"Numéro de la page (1 à {len(self.doc)}) :")
        dialog.setInputMode(QInputDialog.InputMode.IntInput)
        dialog.setIntRange(1, len(self.doc))
        dialog.setIntValue(self.current_page() + 1)
        dialog.setOkButtonText("Aller")
        dialog.setCancelButtonText("Annuler")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.go_to_page(dialog.intValue() - 1)

    def go_to_page(self, index):
        self.layout.activate()  # positions à jour même juste après un réaffichage
        self.scroll.verticalScrollBar().setValue(self.pages[index].y() - self.layout.spacing() // 2)
        self._update_page_label()

    def render_all(self):
        self.stack.setCurrentWidget(self.scroll)
        self.pending_image = None  # les pages sont recréées : un placement en cours est abandonné
        for widget in self.pages:
            widget.deleteLater()
        self.pages = []
        for i in range(len(self.doc)):
            widget = PageWidget(i)
            widget.span_edited.connect(self.edit_span)
            widget.font_info_requested.connect(self.show_font_info)
            widget.field_edited.connect(self.edit_field)
            widget.image_placed.connect(self.place_image)
            widget.placement_cancelled.connect(self.cancel_image)
            widget.rotate_requested.connect(self.rotate_page)
            widget.delete_requested.connect(self.delete_page)
            widget.set_edit_mode(self.edit_action.isChecked())
            self.layout.addWidget(widget)
            self.pages.append(widget)
            self.render_page(i)
        self.update_search()
        self._update_page_label()

    def set_edit_mode(self, enabled):
        for widget in self.pages:
            widget.set_edit_mode(enabled)
        if enabled:
            self.statusBar().showMessage("Mode édition : cliquez sur un texte pour le modifier.")
        else:
            self.statusBar().clearMessage()

    # --- Annulation ------------------------------------------------------

    def _snapshot(self, label):
        return label, self.doc.tobytes(), self.path, self.state_id, self.password

    def _restore(self, data, path, state_id, password):
        self.doc.close()
        self.doc = pymupdf.open("pdf", data)
        self.path = path
        self.state_id = state_id
        self.password = password
        self._update_title()
        self._update_actions()
        self.render_all()

    def push_undo(self, label):
        """Mémorise l'état du document avant une opération, pour pouvoir l'annuler."""
        self.undo_stack.append(self._snapshot(label))
        del self.undo_stack[:-MAX_UNDO]
        # Une nouvelle opération rend impossible de rétablir ce qui avait été annulé.
        self.redo_stack.clear()
        self._update_actions()

    def undo(self):
        if not self.undo_stack:
            return
        label, *state = self.undo_stack.pop()
        self.redo_stack.append(self._snapshot(label))
        self._restore(*state)
        self.statusBar().showMessage(f"Annulé : {label}.", 3000)

    def redo(self):
        if not self.redo_stack:
            return
        label, *state = self.redo_stack.pop()
        self.undo_stack.append(self._snapshot(label))
        self._restore(*state)
        self.statusBar().showMessage(f"Rétabli : {label}.", 3000)

    # --- Édition ---------------------------------------------------------

    def font_chain(self, span, text):
        """Polices candidates pour réécrire un texte, de la plus fidèle à la plus générale.

        1. la police d'origine : intégrée au PDF (souvent réduite aux seules lettres utilisées)
           ou installée sur le PC (ou son équivalent pour les polices standard du PDF) ; parmi
           ces versions, celle qui contient le plus de lettres du texte passe en premier ;
        2. la même famille dans une autre graisse intégrée au document, la plus proche d'abord
           (Work Sans Regular pour une lettre absente de Work Sans Medium) ;
        3. une police installée proche (Arial, Times New Roman ou Courier New, même style).
        Renvoie [(contenu de la police, provenance, police d'origine ?)].
        """
        target = normalize_font_name(span["font"])
        italic = bool(span["flags"] & pymupdf.TEXT_FONT_ITALIC) or "italic" in target
        embedded = {}  # xref -> nom de la police, pour tout le document
        for pno in range(len(self.doc)):
            for xref, ext, _type, basefont, *_ in self.doc.get_page_fonts(pno):
                if ext != "n/a":
                    embedded.setdefault(xref, basefont)

        def extract(xref):
            try:
                return self.doc.extract_font(xref)[3] or None
            except Exception:
                return None

        def read(path):
            with open(path, "rb") as f:
                return f.read()

        original = []
        for xref, basefont in embedded.items():
            if normalize_font_name(basefont) == target and (buffer := extract(xref)):
                original.append((buffer, "intégrée au PDF", True))

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            system_path, substitute = find_system_font(span)
            generic = generic_system_font(span["font"], italic)
        finally:
            QApplication.restoreOverrideCursor()
        if system_path:
            label = "installée sur le système"
            if substitute:
                label = f"équivalent installé : {pymupdf.Font(fontfile=system_path).name}"
            original.append((read(system_path), label, True))

        letters = {ch for ch in text if not ch.isspace()}

        def coverage(entry):
            font = pymupdf.Font(fontbuffer=entry[0])
            return sum(font.has_glyph(ord(ch)) > 0 for ch in letters)

        # Tri stable : à couverture égale, la version intégrée au PDF reste devant.
        chain = sorted(original, key=coverage, reverse=True)

        # Même famille, autre graisse : versions intégrées au document et polices installées
        # (une police variable installée, comme « Work Sans », ne s'affiche que dans sa graisse
        # par défaut : elle ne sert donc que pour les lettres absentes, pas pour tout le texte).
        family, weight = base_family(span["font"]), font_weight(span["font"])
        siblings = []
        for xref, name in embedded.items():
            key = normalize_font_name(name)
            if base_family(name) == family and key != target and ("italic" in key) == italic:
                siblings.append((abs(font_weight(name) - weight), 1, name.split("+", 1)[-1], ("pdf", xref)))
        for key, path in system_fonts()[0].items():
            if base_family(key) == family and key != target and ("italic" in key) == italic and path != system_path:
                siblings.append((abs(font_weight(key) - weight), 0, pymupdf.Font(fontfile=path).name, ("file", path)))
        # Graisse la plus proche d'abord ; à égalité, la police installée (complète) avant le sous-ensemble.
        for _distance, _rank, name, (kind, source) in sorted(siblings):
            buffer = extract(source) if kind == "pdf" else read(source)
            if buffer:
                where = "intégrée au PDF" if kind == "pdf" else "installée"
                chain.append((buffer, f"même police, autre graisse : {name} ({where})", False))

        if generic:
            chain.append((read(generic), f"police proche : {pymupdf.Font(fontfile=generic).name}", False))
        return chain

    def font_info(self, page_index, span):
        """Ce que le PDF dit de la police d'un texte : noms, éditeur, licence, intégration (voir FontInfoDialog)."""
        target = normalize_font_name(span["font"])
        info = {"pdf_name": span["font"].split("+", 1)[-1], "embedded": False, "letters": 0, "names": {},
                "subset": bool(re.match(r"^[A-Z]{6}\+", span["font"]))}
        for xref, ext, _type, basefont, *_ in self.doc.get_page_fonts(page_index):
            if normalize_font_name(basefont) != target:
                continue
            info["subset"] = info["subset"] or bool(re.match(r"^[A-Z]{6}\+", basefont))
            try:
                buffer = self.doc.extract_font(xref)[3] if ext != "n/a" else None
            except Exception:
                buffer = None
            if buffer:
                info["embedded"] = True
                info["names"] = font_names(buffer)
            break
        # Caractères écrits dans tout le document avec cette police : ceux qu'une police réduite contient
        # (son contenu ne le dit pas toujours : les polices Type0 réduites n'ont plus de table de caractères).
        used = set()
        for page in self.doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for other in line["spans"]:
                        if normalize_font_name(other["font"]) == target:
                            used.update(ch for ch in other["text"] if not ch.isspace())
        info["letters"] = "".join(sorted(used))
        family, style = readable_font_name(span["font"])
        names = info["names"]
        info["family"] = names.get(16) or names.get(1) or family
        info["style"] = names.get(17) or names.get(2) or style or "Regular"
        return info

    def show_font_info(self, page_index, span):
        """Fenêtre « Police d'origine » ; si l'utilisateur a installé la police, elle est prise en compte."""
        info = self.font_info(page_index, span)
        if FontInfoDialog(info, self).exec() != FontInfoDialog.INSTALLED:
            return
        refresh_system_fonts()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            path, _substitute = find_system_font(span)
        finally:
            QApplication.restoreOverrideCursor()
        if path:
            # La zone d'édition se rouvre dans la police installée, et le texte sera écrit avec elle.
            self.pages[page_index].open_editor(span)
            self.statusBar().showMessage(
                f"Police « {info['family']} {info['style']} » trouvée ({os.path.basename(path)}) : "
                "le texte sera écrit avec elle.", 10000)
        else:
            QMessageBox.information(
                self, "Police introuvable",
                f"La police « {info['family']} {info['style']} » n'apparaît pas encore parmi les polices "
                "installées.\n\nVérifiez que vous avez installé le bon style (gras, italique…) : le nom exact "
                f"attendu est « {info['names'].get(6) or info['pdf_name']} ».")

    def _font_resource_name(self, buffer):
        """Nom de ressource stable pour une police donnée (évite les doublons)."""
        return "EdF" + hashlib.md5(buffer).hexdigest()[:10]

    @staticmethod
    def split_runs(text, fonts):
        """Découpe le texte en morceaux écrits chacun avec la première police qui en a les lettres.

        fonts : [pymupdf.Font] par ordre de préférence. Renvoie [(indice de police, morceau)].
        """
        runs = []
        for ch in text:
            if ch.isspace() and runs:
                index = runs[-1][0]  # une espace reste dans la police du morceau en cours
            else:
                index = next((i for i, font in enumerate(fonts) if font.has_glyph(ord(ch))), 0)
            if runs and runs[-1][0] == index:
                runs[-1][1] += ch
            else:
                runs.append([index, ch])
        return runs

    def _write_text(self, page, span, text, chain):
        """Écrit le texte à la place du span, lettre par lettre dans la police la plus fidèle possible.

        Renvoie (police d'origine conservée pour tout le texte ?, message pour l'utilisateur).
        """
        size, color = span["size"], pymupdf.sRGB_to_pdf(span["color"])
        if not chain:  # dernier recours : police standard du PDF
            page.insert_text(span["origin"], text, fontsize=size, color=color,
                             fontname=base14_font(span["flags"]))
            return False, "police d'origine introuvable : police standard utilisée"

        fonts = [pymupdf.Font(fontbuffer=buffer) for buffer, _label, _original in chain]
        runs = self.split_runs(text, fonts)
        x, y = span["origin"]
        for index, run in runs:
            buffer = chain[index][0]
            fontname = self._font_resource_name(buffer)
            page.insert_font(fontname=fontname, fontbuffer=buffer)
            page.insert_text((x, y), run, fontsize=size, fontname=fontname, color=color)
            fix_space_mapping(self.doc, page, fontname)
            x += fonts[index].text_length(run, fontsize=size)

        main_label = chain[runs[0][0]][1] if runs else chain[0][1]
        borrowed = {}  # lettres prises dans une autre police que celle d'origine
        for index, run in runs:
            if not chain[index][2]:
                borrowed.setdefault(chain[index][1], []).extend(ch for ch in run if not ch.isspace())
        if not borrowed:
            return True, f"police d'origine conservée ({main_label})"
        details = " ; ".join(f"« {''.join(dict.fromkeys(chars))} » : {label}" for label, chars in borrowed.items())
        return False, f"police d'origine conservée ({main_label}), sauf lettres absentes de cette police — {details}"

    def replace_spans(self, page, edits):
        """Remplace le texte de plusieurs spans d'une page : edits = [(span, nouveau texte)].

        Renvoie, pour chaque texte écrit, (police d'origine conservée pour tout le texte ?, message).
        """
        # Les polices sont cherchées avant l'effacement, tant qu'elles sont encore utilisées.
        chains = [self.font_chain(span, text) if text else [] for span, text in edits]

        # Efface d'abord tous les anciens textes, puis écrit les nouveaux : un texte allongé
        # ne risque pas d'être effacé par la suppression d'un span voisin. Le rectangle est
        # légèrement réduit en hauteur pour ne pas toucher les lignes voisines ;
        # images et dessins sont conservés.
        for span, _ in edits:
            rect = pymupdf.Rect(span["bbox"])
            margin = rect.height * 0.15
            rect.y0 += margin
            rect.y1 -= margin
            page.add_redact_annot(rect, fill=False, cross_out=False)
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
        )

        results = []
        for (span, text), chain in zip(edits, chains):
            if text:
                results.append(self._write_text(page, span, text, chain))
        return results

    def edit_span(self, page_index, span, text, label="modification du texte"):
        self.push_undo(label)
        results = self.replace_spans(self.doc[page_index], [(span, text)])
        if results:
            exact, message = results[0]
            self.statusBar().showMessage(message[0].upper() + message[1:] + ".", 8000 if exact else 15000)
        self._set_modified(True)
        self.render_page(page_index)
        self.update_search()

    def edit_field(self, page_index, xref, value):
        """Enregistre la valeur d'un champ de formulaire (opération annulable)."""
        page = self.doc[page_index]
        widget = next((w for w in page.widgets() if w.xref == xref), None)
        if widget is None:
            return
        self.push_undo("remplissage du formulaire")
        try:
            widget.field_value = value
            widget.update()
        except Exception as exc:
            _label, *state = self.undo_stack.pop()
            self._restore(*state)
            QMessageBox.critical(self, "Erreur", f"Impossible de remplir ce champ :\n{exc}")
            return
        self._set_modified(True)
        self.render_page(page_index)

    # --- Images et signatures ----------------------------------------------

    def insert_image_dialog(self, signature=False):
        """Choisit une image (ou une signature) et la pose sur la page affichée, prête à être placée."""
        if self.doc is None:
            return
        what = "signature" if signature else "image"
        path, _ = QFileDialog.getOpenFileName(self, f"Insérer une {what}", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            # Signature scannée ou photographiée : le fond blanc devient transparent.
            pix, converted = load_image(path, transparent_white=signature)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire l'image :\n{path}\n\n{exc}")
            return
        for widget in self.pages:  # une seule image en cours de placement à la fois
            widget.end_placement(False)

        index = self.current_page()
        widget = self.pages[index]
        page_w, page_h = widget.width() / self.zoom, widget.height() / self.zoom
        # Taille naturelle à 150 ppp, limitée à la moitié de la page (un tiers de sa largeur pour une signature).
        w, h = pix.width * 72 / 150, pix.height * 72 / 150
        scale = min(1, page_w * (0.3 if signature else 0.5) / w, page_h * 0.5 / h)
        w, h = w * scale, h * scale
        # Centrée dans la partie visible de la page.
        top = self.scroll.verticalScrollBar().value() - widget.y()
        visible_top = max(0, top)
        visible_bottom = min(widget.height(), top + self.scroll.viewport().height())
        cx, cy = page_w / 2, (visible_top + visible_bottom) / 2 / self.zoom
        rect = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

        self.pending_image = {"path": path, "pixmap": pix if converted else None, "signature": signature}
        widget.start_placement(to_qimage(pix), rect)
        self.statusBar().showMessage(
            f"Faites glisser la {what} pour la déplacer et ses coins pour la redimensionner "
            "(Maj : sans garder les proportions), puis Entrée ou « Valider ». Échap pour annuler."
        )

    def place_image(self, page_index, view_rect):
        pending, self.pending_image = self.pending_image, None
        if pending is None:
            return
        page = self.doc[page_index]
        rect = pymupdf.Rect(view_rect) * page.derotation_matrix
        what = "signature" if pending["signature"] else "image"
        source = {"pixmap": pending["pixmap"]} if pending["pixmap"] is not None else {"filename": pending["path"]}
        self.push_undo(f"insertion d'une {what}")
        try:
            # rotate : l'image reste droite à l'écran sur une page pivotée.
            page.insert_image(rect, rotate=page.rotation, keep_proportion=False, **source)
        except Exception as exc:
            _label, *state = self.undo_stack.pop()
            self._restore(*state)
            QMessageBox.critical(self, "Erreur", f"Impossible d'insérer l'image :\n{exc}")
            return
        self._set_modified(True)
        self.render_page(page_index)
        self.update_search()
        self.statusBar().showMessage(f"{what.capitalize()} insérée (Ctrl+Z pour annuler).", 5000)

    def cancel_image(self, page_index):
        self.pending_image = None
        self.statusBar().showMessage("Insertion annulée.", 3000)

    # --- Recherche -------------------------------------------------------

    def _search_pattern(self):
        needle = self.search_bar.find_edit.text()
        if not needle:
            return None
        flags = 0 if self.search_bar.case_box.isChecked() else re.IGNORECASE
        return re.compile(re.escape(needle), flags)

    def show_search(self, replace=False):
        if self.doc is None:
            return
        self.search_bar.open(replace)
        self.update_search()

    def update_search(self, reset=False, scroll=False):
        """Recalcule les occurrences (après une saisie ou une modification du document).

        La recherche porte sur chaque fragment de texte : un mot coupé entre deux
        fragments (changement de police au milieu, par exemple) n'est pas trouvé.
        """
        pattern = None if self.search_bar.isHidden() else self._search_pattern()
        self.matches = []
        if pattern is not None and self.doc is not None:
            for page_index, widget in enumerate(self.pages):
                for span in widget.spans:
                    for m in pattern.finditer(span["text"]):
                        self.matches.append((page_index, span, m.start(), m.end()))
        if not self.matches:
            self.match_index = -1
        elif reset or self.match_index < 0:
            self.match_index = 0
        else:
            self.match_index = min(self.match_index, len(self.matches) - 1)
        self._show_matches(scroll)

    def _show_matches(self, scroll=False):
        rects = [[] for _ in self.pages]
        for page_index, span, start, end in self.matches:
            rects[page_index].append(text_rect(span, start, end))
        current = self.matches[self.match_index] if self.matches else None
        for page_index, widget in enumerate(self.pages):
            highlight = None
            if current is not None and current[0] == page_index:
                highlight = text_rect(*current[1:])
            widget.set_highlights(rects[page_index], highlight)
        self.search_bar.set_count(self.match_index, len(self.matches))
        if scroll and current is not None:
            widget = self.pages[current[0]]
            center = widget.to_widget(text_rect(*current[1:])).center().toPoint()
            self.layout.activate()  # positions à jour même juste après un réaffichage
            pos = widget.mapTo(self.container, center)
            self.scroll.ensureVisible(pos.x(), pos.y(), 100, 150)

    def find_step(self, step):
        if self.search_bar.isHidden():
            self.show_search()
        if not self.matches:
            return
        self.match_index = (self.match_index + step) % len(self.matches)
        self._show_matches(scroll=True)

    def replace_current(self):
        if not self.matches:
            return
        page_index, span, start, end = self.matches[self.match_index]
        replacement = self.search_bar.replace_edit.text()
        self.edit_span(page_index, span, span["text"][:start] + replacement + span["text"][end:], "remplacement")
        # L'occurrence remplacée disparaît : l'indice courant désigne déjà la suivante,
        # sauf si le texte de remplacement contient lui-même le texte cherché.
        if self.matches and self._search_pattern().search(replacement):
            self.match_index = (self.match_index + 1) % len(self.matches)
        self._show_matches(scroll=True)

    def replace_all(self):
        if not self.matches:
            return
        pattern = self._search_pattern()
        replacement = self.search_bar.replace_edit.text()
        count = len(self.matches)

        by_page = {}
        for page_index, span, _, _ in self.matches:
            spans = by_page.setdefault(page_index, [])
            if not any(s is span for s in spans):
                spans.append(span)

        self.push_undo("tout remplacer")
        results = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for page_index, spans in by_page.items():
                edits = [(span, pattern.sub(lambda _: replacement, span["text"])) for span in spans]
                results += self.replace_spans(self.doc[page_index], edits)
                self.render_page(page_index)
        finally:
            QApplication.restoreOverrideCursor()
        self._set_modified(True)
        self.update_search(reset=True)

        message = f"{count} occurrence(s) remplacée(s) (Ctrl+Z pour annuler)."
        if not all(exact for exact, _message in results):
            message += " Certaines lettres absentes de la police d'origine ont été prises dans une police proche."
        self.statusBar().showMessage(message, 6000)

    def reorder_dialog(self):
        if self.doc is None:
            return
        dialog = PageOrderDialog(self.doc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        pages = dialog.result_pages()
        if pages == [(i, 0) for i in range(len(self.doc))]:
            return
        self.push_undo("organisation des pages")
        self.doc.select([index for index, _ in pages])
        for page, (_, angle) in zip(self.doc, pages):
            if angle:
                page.set_rotation((page.rotation + angle) % 360)
        self._set_modified(True)
        self.render_all()
        self.statusBar().showMessage("Pages organisées.", 3000)

    def rotate_page(self, index, angle):
        self.push_undo("rotation de la page")
        page = self.doc[index]
        page.set_rotation((page.rotation + angle) % 360)
        self._set_modified(True)
        self.render_page(index)
        self.update_search()

    def delete_page(self, index):
        if len(self.doc) <= 1:
            QMessageBox.warning(self, "Suppression impossible", "Le document doit garder au moins une page.")
            return
        self.push_undo("suppression de la page")
        self.doc.delete_page(index)
        self._set_modified(True)
        self.render_all()
        self.statusBar().showMessage(f"Page {index + 1} supprimée (Ctrl+Z pour annuler).", 5000)

    # --- Fichiers --------------------------------------------------------

    # --- Impression ------------------------------------------------------

    def print_document(self):
        if self.doc is None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(os.path.basename(self.path) if self.path else "Sans titre")
        first = self.doc[0].rect
        printer.setPageOrientation(
            QPageLayout.Orientation.Landscape if first.width > first.height else QPageLayout.Orientation.Portrait
        )
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Imprimer")
        dialog.setMinMax(1, len(self.doc))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if printer.printRange() == QPrinter.PrintRange.PageRange:
            indices = range(printer.fromPage() - 1, min(printer.toPage(), len(self.doc)))
        else:
            indices = range(len(self.doc))
        if self.print_pages(printer, indices):
            self.statusBar().showMessage(f"{len(indices)} page(s) envoyée(s) à l'imprimante.", 5000)

    def print_pages(self, printer, indices):
        """Imprime les pages : chacune ajustée à la feuille sans déformation, centrée.

        Une page paysage sur une feuille portrait (ou l'inverse) est tournée d'un quart de tour
        pour occuper toute la feuille.
        """
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Erreur", "Impossible de démarrer l'impression.")
            return False
        dpi = min(printer.resolution(), PRINT_DPI)
        area = printer.pageRect(QPrinter.Unit.DevicePixel)
        area = QRectF(0, 0, area.width(), area.height())  # zone imprimable, origine du peintre
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for n, index in enumerate(indices):
                if n:
                    printer.newPage()
                self.statusBar().showMessage(f"Impression de la page {index + 1}…")
                QApplication.processEvents()
                pix = self.doc[index].get_pixmap(dpi=dpi, alpha=False)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                if (image.width() > image.height()) != (area.width() > area.height()):
                    image = image.transformed(QTransform().rotate(90))
                scale = min(area.width() / image.width(), area.height() / image.height())
                w, h = image.width() * scale, image.height() * scale
                target = QRectF(area.x() + (area.width() - w) / 2, area.y() + (area.height() - h) / 2, w, h)
                painter.drawImage(target, image)
        finally:
            painter.end()
            QApplication.restoreOverrideCursor()
        return True

    def maybe_save(self):
        """Propose d'enregistrer les modifications. Renvoie False si l'utilisateur annule."""
        if not self.modified:
            return True
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Modifications non enregistrées",
            "Le document a été modifié. Voulez-vous enregistrer les modifications ?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            self,
        )
        # Les traductions de Qt ne sont pas incluses dans l'exécutable : libellés en français ici.
        for button, text in ((QMessageBox.StandardButton.Save, "Enregistrer"),
                             (QMessageBox.StandardButton.Discard, "Ne pas enregistrer"),
                             (QMessageBox.StandardButton.Cancel, "Annuler")):
            box.button(button).setText(text)
        set_primary(box.button(QMessageBox.StandardButton.Save))
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        box.exec()
        answer = box.standardButton(box.clickedButton())
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def open_dialog(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un PDF", "", "Fichiers PDF (*.pdf)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        try:
            doc = pymupdf.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le PDF :\n{path}\n\n{exc}")
            return
        if not doc.is_pdf:
            doc.close()
            QMessageBox.critical(self, "Erreur", f"Ce fichier n'est pas un PDF :\n{path}")
            return
        password = None
        if doc.needs_pass:
            password = self.ask_password(doc, path)
            if password is None:
                doc.close()
                return
            doc = unlock(doc, password)
        if self.doc is not None:
            self.doc.close()
        self.doc = doc
        self.path = path
        self.password = password  # un PDF protégé le reste à l'enregistrement
        self.undo_stack = []
        self.redo_stack = []
        self._set_modified(False)
        self._update_actions()
        self.render_all()
        if doc.is_form_pdf:
            self.statusBar().showMessage("Ce document contient un formulaire : cliquez sur un champ pour le remplir.",
                                         10000)

    def close_document(self):
        """Ferme le PDF en cours (après avoir proposé d'enregistrer) et revient à l'écran d'accueil."""
        if self.doc is None or not self.maybe_save():
            return
        self.edit_action.setChecked(False)
        self.search_bar.hide()
        for widget in self.pages:
            widget.deleteLater()
        self.pages = []
        self.pending_image = None
        self.doc.close()
        self.doc = None
        self.path = None
        self.password = None
        self.undo_stack = []
        self.redo_stack = []
        self.stack.setCurrentWidget(self.welcome)
        self._set_modified(False)
        self._update_actions()
        self.update_search()
        self._update_page_label()
        self.statusBar().showMessage("Document fermé.", 3000)

    def ask_password(self, doc, path):
        """Demande le mot de passe d'un PDF protégé (et l'essaie). Renvoie None si l'utilisateur abandonne."""
        message = f"« {os.path.basename(path)} » est protégé par un mot de passe.\n\nMot de passe :"
        while True:
            dialog = QInputDialog(self)
            dialog.setWindowTitle("PDF protégé")
            dialog.setLabelText(message)
            dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
            dialog.setOkButtonText("Ouvrir")
            dialog.setCancelButtonText("Annuler")
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            password = dialog.textValue()
            if doc.authenticate(password):
                return password
            message = f"Mot de passe incorrect pour « {os.path.basename(path)} ». Réessayez.\n\nMot de passe :"

    def protect_dialog(self):
        if self.doc is None:
            return
        dialog = PasswordDialog(self.password is not None, self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            password, message = dialog.password(), "Protection par mot de passe ajoutée"
        elif result == PasswordDialog.REMOVE:
            password, message = None, "Protection par mot de passe retirée"
        else:
            return
        self.push_undo("protection par mot de passe")
        self.password = password
        self._set_modified(True)
        self.statusBar().showMessage(f"{message} : elle sera appliquée à l'enregistrement (Ctrl+S).", 8000)

    def merge_dialog(self):
        current_label = None
        if self.doc is not None:
            current_label = os.path.basename(self.path) if self.path else "Sans titre"
        dialog = MergeDialog(current_label, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        entries = dialog.entries()
        try:
            sources = self._open_sources([entry for entry in entries if entry is not MergeDialog.CURRENT])
        except RuntimeError as exc:
            QMessageBox.critical(self, "Erreur", f"La concaténation a échoué.\n\n{exc}")
            return

        merged = pymupdf.open()
        error = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            remaining = iter(sources)
            for entry in entries:
                # Document affiché : on reprend la version en mémoire, avec ses modifications.
                merged.insert_pdf(self.doc if entry is MergeDialog.CURRENT else next(remaining))
        except Exception as exc:
            error = exc
        finally:
            QApplication.restoreOverrideCursor()
            for source in sources:
                source.close()
        if error is not None:
            merged.close()
            QMessageBox.critical(self, "Erreur", f"La concaténation a échoué.\n\n{error}")
            return

        if not self.maybe_save():
            merged.close()
            return
        if self.doc is not None:
            self.push_undo("concaténation")
            self.doc.close()
        self.doc = merged
        self.path = None
        self.password = None  # nouveau document : non protégé
        self._set_modified(True)
        self._update_actions()
        self.render_all()
        self.statusBar().showMessage(
            f"{len(entries)} documents concaténés ({len(merged)} pages). "
            "Ctrl+R pour organiser les pages. Pensez à enregistrer.",
            8000,
        )

    def _open_sources(self, paths):
        """Ouvre les PDF à ajouter au document (mot de passe demandé si besoin).

        En cas de problème, referme tout et lève RuntimeError.
        """
        sources = []
        try:
            for path in paths:
                try:
                    source = pymupdf.open(path)
                except Exception as exc:
                    raise RuntimeError(f"Impossible d'ouvrir :\n{path}\n\n{exc}")
                if not source.is_pdf:
                    source.close()
                    raise RuntimeError(f"Ce fichier n'est pas un PDF :\n{path}")
                if source.needs_pass:
                    password = self.ask_password(source, path)
                    if password is None:
                        source.close()
                        raise RuntimeError(f"Mot de passe non fourni pour :\n{path}")
                    source = unlock(source, password)
                sources.append(source)
        except RuntimeError:
            for source in sources:
                source.close()
            raise
        return sources

    def append_files(self, paths):
        """Ajoute les PDF à la fin du document ouvert (opération annulable)."""
        try:
            sources = self._open_sources(paths)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Erreur", f"La concaténation a échoué.\n\n{exc}")
            return
        self.push_undo("ajout de documents")
        error = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for source in sources:
                self.doc.insert_pdf(source)
        except Exception as exc:
            error = exc
        finally:
            QApplication.restoreOverrideCursor()
            for source in sources:
                source.close()
        if error is not None:
            # Document peut-être à moitié complété : on revient à l'état d'avant l'ajout.
            _label, *state = self.undo_stack.pop()
            self._restore(*state)
            QMessageBox.critical(self, "Erreur", f"La concaténation a échoué.\n\n{error}")
            return
        self._set_modified(True)
        self.render_all()
        self.statusBar().showMessage(
            f"{len(sources)} document(s) ajouté(s) à la fin ({len(self.doc)} pages). "
            "Ctrl+R pour organiser les pages, Ctrl+Z pour annuler.",
            8000,
        )

    # --- Glisser-déposer de fichiers ---------------------------------------

    @staticmethod
    def _dropped_pdfs(event):
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        return [url.toLocalFile() for url in mime.urls()
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf")]

    def dragEnterEvent(self, event):
        if not self._dropped_pdfs(event):
            event.ignore()
            return
        # Copie (et non déplacement) : l'Explorateur ne doit jamais retirer le fichier d'origine.
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        self.statusBar().showMessage(
            "Déposez pour ajouter à la fin du document ouvert." if self.doc is not None else "Déposez pour ouvrir."
        )

    def dragMoveEvent(self, event):
        if self._dropped_pdfs(event):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.statusBar().clearMessage()

    def dropEvent(self, event):
        paths = self._dropped_pdfs(event)
        if not paths:
            event.ignore()
            return
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        self.statusBar().clearMessage()
        self.drop_files(paths)

    def drop_files(self, paths):
        """Sans document ouvert, ouvre le premier PDF ; les autres sont ajoutés à la fin du document."""
        if self.doc is None:
            self.open_file(paths[0])
            paths = paths[1:]
            if self.doc is None or not paths:
                return
        self.append_files(paths)

    def save(self):
        if self.doc is None:
            return False
        if self.path is None:
            return self.save_as()
        compression = self.ask_compression()
        if compression is None:
            return False
        return self._write(self.path, compression)

    def save_as(self):
        if self.doc is None:
            return False
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer sous", self.path or "document.pdf", "Fichiers PDF (*.pdf)"
        )
        if not path:
            return False
        compression = self.ask_compression(always=True)
        if compression is None:
            return False
        return self._write(path, compression)

    def ask_compression(self, always=False):
        """Propose de compresser le PDF. Renvoie le choix, ou None si l'utilisateur annule.

        Sans always, le choix gardé avec « Ne plus demander » est repris sans poser la question.
        """
        if self.remembered_compression is not None and not always:
            return self.remembered_compression
        dialog = CompressDialog(self.last_compression, self.remembered_compression is not None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        self.last_compression = dialog.choice()
        self.remembered_compression = self.last_compression if dialog.remember() else None
        return self.last_compression

    def _encryption(self):
        """Options d'enregistrement : chiffrement si le document est protégé par mot de passe."""
        if self.password is None:
            return {}  # sans protection demandée, le chiffrement éventuel du fichier d'origine est conservé
        return {"encryption": pymupdf.PDF_ENCRYPT_AES_256, "user_pw": self.password, "owner_pw": self.password}

    def _reopen(self, source):
        """Rouvre le fichier (ou le contenu) enregistré, déverrouillé avec le mot de passe du document."""
        doc = pymupdf.open(source) if isinstance(source, str) else pymupdf.open("pdf", source)
        return unlock(doc, self.password) if self.password is not None else doc

    def _save_file(self, path, compression):
        """Enregistre le document dans path, compressé ou non, chiffré s'il est protégé."""
        if compression == COMPRESS_NONE:
            self.doc.save(path, garbage=3, deflate=True, **self._encryption())
            return
        doc = self.doc
        if compression == COMPRESS_IMAGES:
            # Sur une copie : si l'enregistrement échoue, le document affiché garde ses images d'origine.
            doc = pymupdf.open("pdf", self.doc.tobytes())
            doc.rewrite_images(dpi_threshold=COMPRESS_DPI + 20, dpi_target=COMPRESS_DPI_TARGET,
                               quality=COMPRESS_JPEG_QUALITY)
        try:
            doc.save(path, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, use_objstms=1,
                     **self._encryption())
        finally:
            if doc is not self.doc:
                doc.close()

    def _write(self, path, compression=COMPRESS_NONE):
        # Document en mémoire (après une annulation ou une concaténation, doc.name n'est pas un fichier) :
        # réécriture complète.
        name = self.doc.name
        same_file = bool(name) and os.path.isfile(name) and os.path.exists(path) and os.path.samefile(path, name)
        tmp_path = path + ".tmp"
        before = None  # taille qu'aurait eue le fichier sans compression
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                # Ajout incrémental impossible pour chiffrer le fichier : réécriture complète.
                incremental = compression == COMPRESS_NONE and self.password is None
                if incremental and same_file and self.doc.can_save_incrementally():
                    self.doc.saveIncr()
                else:
                    if compression != COMPRESS_NONE:
                        before = len(self.doc.tobytes(garbage=3, deflate=True))
                    # Un fichier ouvert ne peut pas être réécrit directement :
                    # on passe par un fichier temporaire, puis on rouvre le résultat.
                    self._save_file(tmp_path, compression)
                    self.doc.close()
                    os.replace(tmp_path, path)
                    self.doc = self._reopen(path)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer :\n{exc}")
            if self.doc.is_closed:
                # Le remplacement a échoué : on recharge en mémoire la copie temporaire
                # pour ne perdre aucune modification.
                with open(tmp_path, "rb") as f:
                    self.doc = self._reopen(f.read())
                os.remove(tmp_path)
                self.render_all()
            return False
        self.path = path
        self._set_modified(False)
        if before is None:
            self.statusBar().showMessage("Document enregistré.", 3000)
        else:
            after = os.path.getsize(path)
            percent = round(100 * (before - after) / before)
            gain = f"−{percent} %" if percent >= 1 else "fichier déjà optimisé, aucun gain possible"
            self.statusBar().showMessage(
                f"Document enregistré et compressé : {format_size(before)} → {format_size(after)} ({gain}).", 8000
            )
        return True

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setWindowIcon(app_icon())
    editor = PdfEditor()
    editor.showMaximized()  # occupe tout l'écran, barre de titre et barre des tâches conservées
    if len(sys.argv) > 1:
        editor.open_file(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
