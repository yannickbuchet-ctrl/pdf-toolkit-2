import ast
import difflib
import glob
import hashlib
import html
import math
import os
import re
import struct
import sys
import threading
import time

import pymupdf
from PySide6.QtCore import (
    QByteArray, QEvent, QMimeData, QPoint, QPointF, QRectF, QSize, QSizeF, Qt, QTimer, QUrl, QUrlQuery, Signal,
)
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QDrag, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QLinearGradient,
    QPageLayout, QPageSize, QPainter, QPainterPath, QPen, QPixmap, QTransform,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "PDF Toolkit 2"
APP_VERSION = "1.4"
APP_DATE = "8 novembre 2026"
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
    "print": ("🖶", ACCENT),
    "form": ("☑", ACCENT),
    "lock": ("🔒", ACCENT),
    "image": ("🖼", ACCENT),
    "signature": ("✍", ACCENT),
    "id_photo": ("👤", ACCENT),
    "crop": ("✂", ACCENT),
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


def zoom_icon(plus):
    """Loupe aux couleurs de l'application, avec un signe + ou −, dessinée pour chaque taille d'affichage : le symbole
    reste net même en petit."""
    icon = QIcon()
    for size in (18, 22, 32, 44, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 64, size / 64)  # dessin sur une grille de 64 × 64
        center, radius = QPointF(27, 27), 23

        # Manche, sous le verre.
        painter.setPen(QPen(QColor("#4338ca"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(44, 44), QPointF(57, 57))

        # Verre : même dégradé que le bandeau de l'écran d'accueil.
        gradient = QLinearGradient(4, 4, 50, 50)
        gradient.setColorAt(0, QColor("#3b82f6"))
        gradient.setColorAt(1, QColor("#7c3aed"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)

        # Signe.
        painter.setPen(QPen(QColor("#ffffff"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(center.x() - 11, center.y()), QPointF(center.x() + 11, center.y()))
        if plus:
            painter.drawLine(QPointF(center.x(), center.y() - 11), QPointF(center.x(), center.y() + 11))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def compare_icon():
    """Deux pages côte à côte, aux couleurs de l'application, l'une avec un passage surligné : comparer deux PDF."""
    icon = QIcon()
    for size in (18, 22, 32, 44, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 64, size / 64)  # dessin sur une grille de 64 × 64
        for x, color in ((4, "#3b82f6"), (34, "#7c3aed")):
            painter.setPen(QPen(QColor(color), 4))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRoundedRect(QRectF(x, 8, 26, 48), 4, 4)
            painter.setPen(QPen(QColor(color), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for y in (20, 30, 40):
                painter.drawLine(QPointF(x + 7, y), QPointF(x + 19, y))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(234, 122, 0, 200))  # passage modifié, surligné
        painter.drawRoundedRect(QRectF(37, 25, 20, 10), 2, 2)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def ocr_icon():
    """Coins de cadrage d'un scanner autour d'un « T », aux couleurs de l'application : lire le texte d'une image."""
    icon = QIcon()
    for size in (18, 22, 32, 44, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 64, size / 64)  # dessin sur une grille de 64 × 64
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#3b82f6"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        for x, y, dx, dy in ((6, 6, 1, 1), (58, 6, -1, 1), (6, 58, 1, -1), (58, 58, -1, -1)):
            corner = QPainterPath(QPointF(x, y + 15 * dy))
            corner.lineTo(x, y)
            corner.lineTo(x + 15 * dx, y)
            painter.drawPath(corner)
        painter.setPen(QPen(QColor("#7c3aed"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(20, 21), QPointF(44, 21))
        painter.drawLine(QPointF(32, 21), QPointF(32, 45))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def make_icon(name):
    """Icône dessinée à partir d'un symbole Unicode (aucun fichier image nécessaire)."""
    if name in ("zoom_in", "zoom_out"):
        return zoom_icon(name == "zoom_in")
    if name == "compare":
        return compare_icon()
    if name == "ocr":
        return ocr_icon()
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


def is_ocr_span(span):
    """Texte invisible (mode de rendu 3, ou transparent) ou écrit dans la police des calques OCR : du texte reconnu
    sur une image et posé dessus pour la recherche et la copie, par cette application ou par une autre."""
    return span.get("alpha", 255) == 0 or "GlyphLessFont" in span["font"]


def page_spans(page):
    """Renvoie les fragments de texte (spans) non vides de la page.

    "bbox" et "origin" sont en coordonnées de page non pivotée (celles qu'attendent
    les fonctions d'édition) ; "view" est le rectangle tel qu'affiché, rotation comprise.
    "chars" donne la position de chaque caractère (pour surligner une partie du texte).
    "ocr" repère le texte invisible (calque OCR posé sur une image) : il ne se modifie pas.
    """
    data = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_TEXT)
    spans = []
    for block in data["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            merged = []
            for span in line["spans"]:
                span["text"] = "".join(ch["c"] for ch in span["chars"])
                span["ocr"] = is_ocr_span(span)
                # Un calque OCR étire chaque mot à sa largeur : PyMuPDF en fait autant de fragments (leur taille
                # apparente diffère). Ceux d'une même ligne sont réunis, pour que la recherche trouve aussi une suite
                # de mots.
                if span["ocr"] and merged and merged[-1]["ocr"]:
                    last = merged[-1]
                    last["chars"] = last["chars"] + span["chars"]
                    last["text"] += span["text"]
                    last["bbox"] = tuple(pymupdf.Rect(last["bbox"]) | pymupdf.Rect(span["bbox"]))
                else:
                    merged.append(span)
            spans += [span for span in merged if span["text"].strip()]
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


# Formats d'image : PyMuPDF lit JPEG, PNG, GIF, BMP, TIFF et JPEG 2000 ; le HEIC et le HEIF des iPhone sont lus par
# pillow-heif, le WebP par Pillow (ni Qt ni MuPDF ne les lisent dans l'application construite).
IMAGE_FILTER = ("Images (*.jpg *.jpeg *.png *.heic *.heif *.webp *.gif *.bmp *.tif *.tiff);;"
                "Tous les fichiers (*)")
IMAGE_FORMATS_TEXT = "JPEG, PNG, HEIC et HEIF (iPhone), WebP, GIF, BMP et TIFF"
HEIF_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"hevm", b"hevs", b"mif1", b"msf1"}
PHOTO_JPEG_QUALITY = 92  # photo HEIC ou WebP réencodée pour le PDF
# Orientation EXIF -> rotation à donner à insert_image (sens inverse des aiguilles d'une montre). Les orientations
# en miroir (2, 4, 5, 7) n'y sont pas : l'image est alors redressée pixel par pixel.
EXIF_INSERT_ROTATION = {1: 0, 3: 180, 6: 270, 8: 90}


def image_format(head):
    """Format d'une image d'après ses premiers octets (64 suffisent) : le nom du fichier peut être faux."""
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp":  # conteneur ISO : HEIF ou AVIF, d'après les marques de la boîte « ftyp »
        end = min(len(head), int.from_bytes(head[:4], "big"))
        brands = [head[8:12]] + [head[i:i + 4] for i in range(16, end - 3, 4)]
        if b"avif" in brands or b"avis" in brands:
            return "avif"
        if HEIF_BRANDS.intersection(brands):
            return "heif"
    return "autre"


def _pillow_pixmap(image):
    """Image Pillow -> pixmap RVB, avec transparence si elle en a."""
    alpha = image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if alpha else "RGB")
    return pymupdf.Pixmap(pymupdf.csRGB, image.width, image.height, image.tobytes(), alpha)


def read_image(source):
    """Image d'un fichier (chemin) ou d'octets : (pixmap RVB, avec ou sans transparence ; format ; orientation).

    orientation : celle de l'EXIF (1 à 8), que l'appelant doit appliquer ; une photo HEIC ou WebP arrive déjà
    redressée (orientation 1).
    """
    if isinstance(source, str):
        with open(source, "rb") as f:
            data = f.read()
    else:
        data = bytes(source)
    kind = image_format(data[:64])
    if kind == "avif":
        raise ValueError("le format AVIF n'est pas pris en charge : enregistrez la photo en JPEG ou en PNG.")
    if kind in ("heif", "webp"):
        import io
        try:
            if kind == "heif":
                # pillow-heif applique la rotation enregistrée dans la photo (photo d'iPhone prise en hauteur).
                import pillow_heif
                return _pillow_pixmap(pillow_heif.open_heif(io.BytesIO(data), convert_hdr_to_8bit=True).to_pillow()), kind, 1
            from PIL import ImageOps, WebPImagePlugin
            return _pillow_pixmap(ImageOps.exif_transpose(WebPImagePlugin.WebPImageFile(io.BytesIO(data)))), kind, 1
        except ImportError:  # lancé depuis les sources sans les modules : pip install pillow pillow-heif
            raise ValueError(f"le format {'HEIC' if kind == 'heif' else 'WebP'} demande les modules Pillow et "
                             "pillow-heif (pip install pillow pillow-heif).") from None
    try:
        pix = pymupdf.Pixmap(data)
    except Exception as exc:
        raise ValueError(f"format d'image non reconnu ({exc}). Formats acceptés : {IMAGE_FORMATS_TEXT}.") from None
    if pix.colorspace is not None and pix.colorspace.n != 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    return pix, kind, exif_orientation(data)


def qimage_to_pixmap(image):
    """QImage -> pixmap RVB de PyMuPDF, avec transparence si l'image en a."""
    alpha = image.hasAlphaChannel()
    image = image.convertToFormat(QImage.Format.Format_RGBA8888 if alpha else QImage.Format.Format_RGB888)
    width, height, line, n = image.width(), image.height(), image.bytesPerLine(), 4 if alpha else 3
    data = bytes(image.constBits())
    if line != width * n:  # lignes complétées à un multiple de 4 octets par Qt
        data = b"".join(data[y * line:y * line + width * n] for y in range(height))
    return pymupdf.Pixmap(pymupdf.csRGB, width, height, data, alpha)


def load_image(path, transparent_white=False):
    """Image à insérer : (aperçu QImage redressé, arguments de page.insert_image).

    Un fichier que MuPDF lit (JPEG, PNG…) est inséré tel quel : un JPEG reste compressé en JPEG, et la rotation
    demandée par son EXIF (photo prise en hauteur) est donnée à insert_image (« rotate »). Une photo HEIC ou WebP est
    réencodée en JPEG (en PNG si elle a des transparences). transparent_white (signature scannée ou photographiée) :
    le fond blanc devient transparent.
    """
    pix, kind, orientation = read_image(path)
    if transparent_white and not pix.alpha:
        gray = pymupdf.Pixmap(pymupdf.csGRAY, pix).samples
        with_alpha = pymupdf.Pixmap(pix, 1)
        with_alpha.set_alpha(gray.translate(WHITE_TO_ALPHA))
        pix = with_alpha
    preview = oriented_image(to_qimage(pix), orientation)
    if transparent_white:
        return preview, {"pixmap": pix if orientation == 1 else qimage_to_pixmap(preview)}
    if kind in ("heif", "webp"):
        return preview, {"pixmap": pix} if pix.alpha else {"stream": pix.tobytes("jpeg", jpg_quality=PHOTO_JPEG_QUALITY)}
    if orientation in EXIF_INSERT_ROTATION:
        return preview, {"filename": path, "rotate": EXIF_INSERT_ROTATION[orientation]}
    # Photo en miroir (orientation 2, 4, 5 ou 7, rare) : redressée pixel par pixel.
    fixed = qimage_to_pixmap(preview)
    return preview, {"pixmap": fixed} if fixed.alpha else {"stream": fixed.tobytes("jpeg", jpg_quality=PHOTO_JPEG_QUALITY)}


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
        # Une autre fenêtre (« Police d'origine », autre application) n'annule pas la saisie : on la
        # retrouve en revenant. Seul un clic ailleurs dans la fenêtre l'annule.
        if event.reason() not in (Qt.FocusReason.ActiveWindowFocusReason, Qt.FocusReason.PopupFocusReason):
            self.cancelled.emit()


class FontWarning(QLabel):
    """Bandeau « police non installée » : garde pour lui les clics, qui sinon passeraient à la page ; la page
    prendrait le focus et la zone de saisie se fermerait (en supprimant le bandeau avant la fin du clic)."""

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()


class PageWidget(QWidget):
    span_edited = Signal(int, object, str)
    font_info_requested = Signal(int, object)  # page, texte dont la police n'est pas installée
    field_edited = Signal(int, int, object)  # page, xref du champ de formulaire, nouvelle valeur
    image_placed = Signal(int, object)  # page, rectangle affiché (en points) de l'image placée
    placement_cancelled = Signal(int)
    rotate_requested = Signal(int, int)
    delete_requested = Signal(int)
    ocr_text_clicked = Signal(int)  # page : clic, en mode édition, sur un texte invisible (calque OCR)

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
            editable = QPen(QColor(0, 120, 215, 90), 1)
            recognized = QPen(QColor(100, 116, 139, 120), 1, Qt.PenStyle.DashLine)  # calque OCR : non modifiable
            for span in self.spans:
                painter.setPen(recognized if span.get("ocr") else editable)
                painter.drawRect(self._span_rect(span))
            if self.hovered is not None and self.hovered.get("ocr"):
                painter.fillRect(self._span_rect(self.hovered), QColor(100, 116, 139, 30))
            elif self.hovered is not None:
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
            self.setToolTip(OCR_EDIT_HINT if span is not None and span.get("ocr") else "")
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
            if span is not None and span.get("ocr"):
                self.ocr_text_clicked.emit(self.index)
            elif span is not None:
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
        warning = FontWarning(f"⚠ Police « <b>{name}</b> » non installée sur ce PC : la saisie s'affiche dans une autre "
                         "police, et le texte sera écrit avec la police intégrée au PDF si elle contient vos "
                         "lettres, sinon avec une police proche. <a href='infos'>Infos sur la police…</a> "
                         "pour la retrouver et l'installer.", self)
        warning.setTextFormat(Qt.TextFormat.RichText)
        # Un clic sur le bandeau ne doit pas retirer le focus à la zone de saisie : elle se fermerait et
        # supprimerait le bandeau avant la fin du clic sur le lien. Le focus du bandeau est donc confié à la zone
        # de saisie (sinon Qt le donnerait à la page, premier parent qui l'accepte).
        warning.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        warning.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        warning.setFocusProxy(self.editor)
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

    def childEvent(self, event):
        super().childEvent(event)
        if event.added():
            event.child().installEventFilter(self)
        elif event.removed():
            self.update()

    def eventFilter(self, watched, event):
        # L'ombre déborde de la page : quand celle-ci change de taille ou de place, Qt ne repeint que la zone de la page
        # et l'ancienne ombre resterait à l'écran. Le fond est donc repeint en entier.
        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self.update()
        return False

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


# --- Photos d'identité -------------------------------------------------------

# (libellé, largeur et hauteur de la photo en mm, hauteur de la tête en mm : minimum et maximum)
ID_PHOTO_FORMATS = [
    ("France, Union européenne (35 × 45 mm)", 35, 45, 32, 36),
    ("Royaume-Uni (35 × 45 mm)", 35, 45, 29, 34),
    ("États-Unis, Inde (51 × 51 mm)", 50.8, 50.8, 25, 35),
    ("Canada, passeport (50 × 70 mm)", 50, 70, 31, 36),
    ("Chine, visa (33 × 48 mm)", 33, 48, 28, 33),
    ("Japon, Australie (35 × 45 mm)", 35, 45, 32, 36),
    ("Personnalisé", None, None, None, None),
]

# (libellé, largeur et hauteur de la feuille en mm)
ID_PHOTO_PAPERS = [
    ("Photo 10 × 15 cm", 101.6, 152.4),  # le papier vendu sous ce nom mesure en réalité 4 × 6 pouces
    ("Photo 13 × 18 cm", 127, 178),
    ("A6 (10,5 × 14,8 cm)", 105, 148),
    ("A5 (14,8 × 21 cm)", 148, 210),
    ("A4 (21 × 29,7 cm)", 210, 297),
    ("Lettre US (21,6 × 27,9 cm)", 215.9, 279.4),
    ("Personnalisé", None, None),
]

ID_PHOTO_MIN_DPI, ID_PHOTO_MAX_DPI = 300, 600  # résolution de la photo dans le PDF
ID_PHOTO_LOW_DPI = 250  # en dessous, la photo paraîtra floue une fois imprimée
ID_PHOTO_JPEG_QUALITY = 95
ID_PHOTO_PREVIEW = 2400  # plus grand côté de l'image affichée pendant le recadrage, en pixels
ID_PHOTO_MAX_ANGLE = 15  # redressement maximal, en degrés
ID_PHOTO_HISTORY = 20  # opérations annulables dans la fenêtre
ID_PHOTO_MIN_MARGIN = 3  # mm : plus près du bord, la plupart des imprimantes couperaient les photos
ID_PHOTO_SOURCE_QUALITY = 92  # photo entière jointe au PDF pour pouvoir modifier la planche
ID_PHOTO_TITLE = "Photos d'identité"
# Fichiers joints au PDF : la photo entière (réencodée, donc sans ses métadonnées) et les réglages de la planche.
ID_PHOTO_SOURCE_FILE = "photo-identite-source.jpg"
ID_PHOTO_SETTINGS_FILE = "photo-identite-reglages.txt"
ID_PHOTO_MAX_OPS = 200  # opérations relues au plus dans un PDF
POINTS_PER_MM = 72 / 25.4


def mm_text(value):
    """Une dimension à la française : 50,8 ; 35."""
    return f"{value:g}".replace(".", ",")


def exif_orientation(source):
    """Orientation EXIF (1 à 8) d'une photo JPEG ou TIFF (chemin ou octets) ; 1 si elle n'en indique pas."""
    try:
        if isinstance(source, str):
            with open(source, "rb") as f:
                data = f.read(256 * 1024)
        else:
            data = bytes(source[:256 * 1024])
        tiff = data if data[:4] in (b"II*\0", b"MM\0*") else None
        if data[:2] == b"\xff\xd8":
            i = 2
            while tiff is None and i + 4 <= len(data) and data[i] == 0xFF and data[i + 1] not in (0xDA, 0xD9):
                length = int.from_bytes(data[i + 2:i + 4], "big")
                if data[i + 1] == 0xE1 and data[i + 4:i + 10] == b"Exif\0\0":
                    tiff = data[i + 10:i + 2 + length]
                i += 2 + length
        if tiff is None:
            return 1
        order = "little" if tiff[:2] == b"II" else "big"
        ifd = int.from_bytes(tiff[4:8], order)
        for k in range(int.from_bytes(tiff[ifd:ifd + 2], order)):
            entry = tiff[ifd + 2 + 12 * k:ifd + 14 + 12 * k]
            if int.from_bytes(entry[:2], order) == 0x0112:
                orientation = int.from_bytes(entry[8:10], order)
                return orientation if 1 <= orientation <= 8 else 1
    except (OSError, ValueError):
        pass
    return 1


def oriented_image(image, orientation):
    """L'image redressée d'après son orientation EXIF (1 à 8) : PyMuPDF ne l'applique pas."""
    transform = {
        2: QTransform().scale(-1, 1),
        3: QTransform().rotate(180),
        4: QTransform().scale(1, -1),
        5: QTransform(0, 1, 1, 0, 0, 0),
        6: QTransform().rotate(90),
        7: QTransform(0, -1, -1, 0, 0, 0),
        8: QTransform().rotate(270),
    }.get(orientation)
    return image if transform is None else image.transformed(transform)


def load_photo(path):
    """Photo à recadrer, redressée, sur fond blanc si elle est transparente. path : chemin du fichier, ou son
    contenu (bytes). Formats : ceux de read_image, photos HEIC des iPhone comprises. Renvoie un QImage RVB."""
    pix, _kind, orientation = read_image(path)
    image = to_qimage(pix)
    if pix.alpha:
        flat = QImage(image.size(), QImage.Format.Format_RGB32)
        flat.fill(Qt.GlobalColor.white)
        painter = QPainter(flat)
        painter.drawImage(0, 0, image)
        painter.end()
        image = flat.convertToFormat(QImage.Format.Format_RGB888)
    return oriented_image(image, orientation)


def adjust_image(image, brightness, contrast):
    """Luminosité et contraste (-50 à 50), appliqués à tous les pixels par une table de correspondance."""
    if not brightness and not contrast:
        return image
    factor = 1 + contrast / 100
    table = bytes(max(0, min(255, round((v - 128) * factor + 128 + brightness))) for v in range(256))
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    data = bytes(image.constBits()).translate(table)
    return QImage(data, image.width(), image.height(), image.bytesPerLine(), QImage.Format.Format_RGB888).copy()


def jpeg_bytes(image, quality=ID_PHOTO_JPEG_QUALITY):
    """QImage -> JPEG, encodé par PyMuPDF (le lecteur et l'encodeur JPEG de Qt ne sont pas inclus)."""
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = image.width(), image.height(), image.bytesPerLine()
    bits = image.constBits()
    # Qt complète chaque ligne à un multiple de 4 octets ; PyMuPDF attend des lignes sans remplissage.
    samples = b"".join(bytes(bits[y * stride:y * stride + width * 3]) for y in range(height))
    pix = pymupdf.Pixmap(pymupdf.csRGB, width, height, samples, False)
    return pix.tobytes("jpeg", jpg_quality=quality)


def id_photo_layout(paper, photo, margin, gap, orientation="auto", count=0):
    """Dispose les photos sur la feuille, le bloc étant centré (toutes les dimensions en mm).

    paper, photo : (largeur, hauteur). orientation : "auto" (celle qui contient le plus de photos), "portrait" ou
    "landscape". count : nombre de photos voulu, 0 pour remplir la feuille.
    Renvoie (largeur de la page, hauteur de la page, capacité, [(x, y) de chaque photo]).
    """
    def grid(page_w, page_h):
        # La tolérance évite de perdre une rangée à cause d'un arrondi quand tout tient au dixième de mm près.
        columns = int((page_w - 2 * margin + gap + 1e-6) // (photo[0] + gap))
        rows = int((page_h - 2 * margin + gap + 1e-6) // (photo[1] + gap))
        return max(columns, 0), max(rows, 0)

    portrait = min(paper), max(paper)
    landscape = max(paper), min(paper)
    if orientation == "portrait":
        page = portrait
    elif orientation == "landscape":
        page = landscape
    else:
        portrait_columns, portrait_rows = grid(*portrait)
        landscape_columns, landscape_rows = grid(*landscape)
        page = landscape if landscape_columns * landscape_rows > portrait_columns * portrait_rows else portrait
    columns, rows = grid(*page)
    capacity = columns * rows
    if not capacity:
        return page[0], page[1], 0, []
    left = (page[0] - columns * photo[0] - (columns - 1) * gap) / 2
    top = (page[1] - rows * photo[1] - (rows - 1) * gap) / 2
    positions = [(left + c * (photo[0] + gap), top + r * (photo[1] + gap)) for r in range(rows) for c in range(columns)]
    return page[0], page[1], capacity, positions[:count] if count else positions


def id_photo_pdf(image, page_size, photo, positions, cut_lines, source=None):
    """PDF d'une page portant la photo à chaque position (dimensions en mm).

    Le PDF demande à être imprimé sans mise à l'échelle (/PrintScaling /None) : les photos doivent sortir à leur
    taille exacte. Une même image est partagée par toutes les photos, le fichier reste léger.
    source : (JPEG de la photo entière, texte des réglages), joints au PDF pour pouvoir modifier la planche.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=page_size[0] * POINTS_PER_MM, height=page_size[1] * POINTS_PER_MM)
    jpeg = jpeg_bytes(image)
    xref = 0
    for x, y in positions:
        rect = pymupdf.Rect(x, y, x + photo[0], y + photo[1]) * POINTS_PER_MM
        if xref:
            page.insert_image(rect, xref=xref, keep_proportion=False)
        else:
            xref = page.insert_image(rect, stream=jpeg, keep_proportion=False)
        if cut_lines:
            page.draw_rect(rect, color=(0.6, 0.6, 0.6), width=0.25)
    doc.set_metadata({"title": ID_PHOTO_TITLE, "creator": APP_NAME, "producer": APP_NAME})
    doc.xref_set_key(doc.pdf_catalog(), "ViewerPreferences", "<</PrintScaling/None>>")
    if source is not None:
        doc.embfile_add(ID_PHOTO_SOURCE_FILE, source[0], filename=ID_PHOTO_SOURCE_FILE,
                        desc="Photo entière, pour modifier la planche dans " + APP_NAME)
        doc.embfile_add(ID_PHOTO_SETTINGS_FILE, source[1].encode("utf-8"), filename=ID_PHOTO_SETTINGS_FILE,
                        desc="Réglages de la planche pour " + APP_NAME)
    return doc


def sheet_photos(page):
    """Rectangles des photos d'une planche : toutes la même image, à la même taille. None si la page en diffère."""
    infos = page.get_image_info(xrefs=True)
    if not infos or len({info["xref"] for info in infos}) != 1:
        return None
    boxes = [info["bbox"] for info in infos]
    w, h = boxes[0][2] - boxes[0][0], boxes[0][3] - boxes[0][1]
    if any(abs(box[2] - box[0] - w) > 0.5 or abs(box[3] - box[1] - h) > 0.5 for box in boxes):
        return None
    return boxes


def is_id_photo_sheet(doc):
    """Ce PDF est-il une planche de photos d'identité créée par l'application ?"""
    try:
        if len(doc) == 0:
            return False
        names = doc.embfile_names()
        if ID_PHOTO_SOURCE_FILE in names and ID_PHOTO_SETTINGS_FILE in names:
            return True
        return ((doc.metadata or {}).get("title") == ID_PHOTO_TITLE and prints_actual_size(doc)
                and sheet_photos(doc[0]) is not None)
    except (RuntimeError, ValueError):
        return False


def page_sheet_settings(page):
    """Réglages déduits de la page, pour une planche sans réglages joints."""
    boxes = sheet_photos(page)
    photo = ((boxes[0][2] - boxes[0][0]) / POINTS_PER_MM, (boxes[0][3] - boxes[0][1]) / POINTS_PER_MM)
    page_w, page_h = page.rect.width / POINTS_PER_MM, page.rect.height / POINTS_PER_MM
    lefts = sorted({round(box[0] / POINTS_PER_MM, 2) for box in boxes})
    tops = sorted({round(box[1] / POINTS_PER_MM, 2) for box in boxes})
    if len(lefts) > 1:
        gap = lefts[1] - lefts[0] - photo[0]
    else:
        gap = tops[1] - tops[0] - photo[1] if len(tops) > 1 else 2
    margin = min(min(lefts), min(tops), page_w - max(lefts) - photo[0], page_h - max(tops) - photo[1])
    margin = max(margin, ID_PHOTO_MIN_MARGIN)
    orientation = "landscape" if page_w > page_h else "portrait"
    paper = (min(page_w, page_h), max(page_w, page_h))
    capacity = id_photo_layout(paper, photo, margin, gap, orientation)[2]
    return {"photo": photo, "paper": paper, "orientation": orientation, "margin": margin, "gap": gap,
            "count": 0 if len(boxes) >= capacity else len(boxes), "cut_lines": bool(page.get_drawings())}


def read_id_photo_sheet(doc):
    """Ce qu'il faut pour modifier une planche : (photo, réglages, complet).

    complet : False si le PDF ne contient que la photo déjà recadrée, sans ce qui était hors du cadre.
    """
    names = doc.embfile_names()
    if ID_PHOTO_SOURCE_FILE in names and ID_PHOTO_SETTINGS_FILE in names:
        try:
            settings = ast.literal_eval(doc.embfile_get(ID_PHOTO_SETTINGS_FILE).decode("utf-8"))
            if isinstance(settings, dict):
                return load_photo(doc.embfile_get(ID_PHOTO_SOURCE_FILE)), settings, True
        except Exception:  # pièces jointes abîmées : on se rabat sur la photo visible dans la page
            pass
    page = doc[0]
    xref = page.get_image_info(xrefs=True)[0]["xref"]
    return load_photo(doc.extract_image(xref)["image"]), page_sheet_settings(page), False


def finite_numbers(value, count):
    """Le tuple de count nombres finis lu dans un PDF, ou None : un fichier reçu peut contenir n'importe quoi."""
    if not isinstance(value, (tuple, list)) or len(value) != count:
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value):
        return None
    return tuple(value)


def quarter_turn_needed(w, h, paper_w, paper_h, tolerance):
    """Une page en taille réelle doit-elle être tournée pour tenir sur le papier ? (Seulement si c'est indispensable.)
    La tolérance couvre les arrondis des pilotes (A4 : 595 points au lieu de 595,28)."""
    room_w, room_h = paper_w + tolerance, paper_h + tolerance
    return (w > room_w or h > room_h) and h <= room_w and w <= room_h


def photos_outside_printable(page, paper, printable):
    """Des images de la page, imprimée en taille réelle et centrée sur le papier, sortent-elles de la zone que
    l'imprimante peut atteindre ? paper, printable : QRectF en points, printable étant relatif au coin du papier."""
    center = page.rect.width / 2, page.rect.height / 2
    boxes = [info["bbox"] for info in page.get_image_info()] or [tuple(page.rect)]
    reach_x = max(max(abs(box[0] - center[0]), abs(box[2] - center[0])) for box in boxes)
    reach_y = max(max(abs(box[1] - center[1]), abs(box[3] - center[1])) for box in boxes)
    if quarter_turn_needed(page.rect.width, page.rect.height, paper.width(), paper.height(), 2):
        reach_x, reach_y = reach_y, reach_x
    tolerance = 0.5  # points : arrondis des pilotes
    return (paper.width() / 2 - reach_x < printable.left() - tolerance
            or paper.width() / 2 + reach_x > printable.right() + tolerance
            or paper.height() / 2 - reach_y < printable.top() - tolerance
            or paper.height() / 2 + reach_y > printable.bottom() + tolerance)


def prints_actual_size(doc):
    """Le PDF demande-t-il à être imprimé sans mise à l'échelle (/PrintScaling /None) ?"""
    try:
        kind, value = doc.xref_get_key(doc.pdf_catalog(), "ViewerPreferences")
        if kind == "xref":
            value = doc.xref_object(int(value.split()[0]))
    except (RuntimeError, ValueError):
        return False
    return re.search(r"/PrintScaling\s*/None", value) is not None


class PhotoCropView(QWidget):
    """Photo et zone sélectionnée : le cadre se déplace et se redimensionne à la souris, ses proportions sont celles
    de la photo d'identité (libres en mode « tronquer »). Molette : zoom sous la souris ; clic droit : déplacer la vue.

    Les positions sont en pixels de l'image, avec pour origine son centre : une inclinaison tourne l'image autour de
    ce point sans déplacer le cadre.
    """

    changed = Signal()
    GRAB = 10  # distance de saisie d'un coin ou d'un bord du cadre, en pixels de l'écran

    def __init__(self, image):
        super().__init__()
        self.ratio = 35 / 45  # largeur / hauteur du cadre
        self.head = None  # hauteur de la tête rapportée à celle de la photo : (minimum, maximum), pour le guide
        self.show_guide = True
        self.free = False  # mode « tronquer » : proportions libres
        self.saved_selection = None
        self.brightness = 0
        self.contrast = 0
        self.zoom = 1.0
        self.center = QPointF()  # point de l'image au centre de la vue
        self.drag = None
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.set_state(image, 0.0, None)

    # --- État ---------------------------------------------------------------

    def state(self):
        return self.image, self.angle, QRectF(self.selection)

    def set_state(self, image, angle, selection):
        self.image = image
        self.angle = angle
        longest = max(image.width(), image.height())
        self.preview = image
        if longest > ID_PHOTO_PREVIEW:
            self.preview = image.scaled(ID_PHOTO_PREVIEW, ID_PHOTO_PREVIEW, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
        self.display = adjust_image(self.preview, self.brightness, self.contrast)
        self.zoom = 1.0
        self.center = QPointF()
        # Un cadre mémorisé repart aux proportions actuelles : le format a pu changer depuis.
        self._set_selection(selection if selection is not None else self.default_selection())

    def default_selection(self):
        """La plus grande zone aux bonnes proportions, centrée dans l'image."""
        w, h = self.image.width(), self.image.height()
        if self.ratio > w / h:
            h = w / self.ratio
        else:
            w = h * self.ratio
        return QRectF(-w / 2, -h / 2, w, h)

    def set_adjustments(self, brightness, contrast):
        self.brightness, self.contrast = brightness, contrast
        self.display = adjust_image(self.preview, brightness, contrast)
        self.update()
        self.changed.emit()

    def set_angle(self, angle):
        self.angle = angle
        self._set_selection(self.selection)
        self._clamp_center()
        self.update()

    def set_ratio(self, ratio):
        """Nouvelles proportions : le cadre garde son centre et, autant que possible, sa hauteur."""
        if abs(ratio - self.ratio) < 1e-9:
            return
        self.ratio = ratio
        if self.free:  # appliquées à la sortie du mode « tronquer »
            return
        center, h = self.selection.center(), self.selection.height()
        bounds = self.bounds()
        h = min(h, bounds.height(), bounds.width() / ratio)
        w = h * ratio
        self._set_selection(QRectF(center.x() - w / 2, center.y() - h / 2, w, h))

    def set_guide(self, head, visible):
        self.head, self.show_guide = head, visible
        self.update()

    def begin_free(self):
        """Mode « tronquer » : toute l'image est sélectionnée, aux proportions libres."""
        self.free = True
        self.saved_selection = QRectF(self.selection)
        self.selection = self.bounds()
        self.update()
        self.changed.emit()

    def end_free(self, apply):
        """Quitte le mode « tronquer » ; apply : l'image est réduite à la zone sélectionnée, redressement inclus."""
        self.free = False
        if apply:
            cropped = self.render(max(1, round(self.selection.width())), max(1, round(self.selection.height())),
                                  adjusted=False)
            self.set_state(cropped, 0.0, None)
        else:
            self._set_selection(self.saved_selection)

    # --- Géométrie ----------------------------------------------------------

    def bounds(self):
        """Rectangle contenant toute l'image inclinée : le cadre ne peut pas en sortir."""
        angle = math.radians(self.angle)
        cos, sin = abs(math.cos(angle)), abs(math.sin(angle))
        w, h = self.image.width(), self.image.height()
        half_w, half_h = (w * cos + h * sin) / 2, (w * sin + h * cos) / 2
        return QRectF(-half_w, -half_h, 2 * half_w, 2 * half_h)

    def covers_image(self):
        """Le cadre reste-t-il dans l'image ? (Une image inclinée laisse des coins vides, imprimés en blanc.)"""
        inverse = QTransform().rotate(-self.angle)
        half_w, half_h = self.image.width() / 2 + 0.5, self.image.height() / 2 + 0.5
        rect = self.selection
        for corner in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            point = inverse.map(corner)
            if abs(point.x()) > half_w or abs(point.y()) > half_h:
                return False
        return True

    def _set_selection(self, rect):
        """Applique un cadre, réduit si besoin puis ramené dans les limites de l'image."""
        bounds = self.bounds()
        w, h = rect.width(), rect.height()
        if self.free:
            w, h = min(w, bounds.width()), min(h, bounds.height())
        else:
            h = min(h, bounds.height(), bounds.width() / self.ratio)
            w = h * self.ratio
        x = max(bounds.left(), min(rect.center().x() - w / 2, bounds.right() - w))
        y = max(bounds.top(), min(rect.center().y() - h / 2, bounds.bottom() - h))
        self.selection = QRectF(x, y, w, h)
        self.update()
        self.changed.emit()

    def _scale(self):
        """Pixels de l'écran par pixel de l'image."""
        bounds = self.bounds()
        fit = min((self.width() - 24) / bounds.width(), (self.height() - 24) / bounds.height())
        return max(fit, 1e-4) * self.zoom

    def _to_view(self, point):
        return QPointF(self.width() / 2, self.height() / 2) + (point - self.center) * self._scale()

    def _to_photo(self, point):
        return self.center + (point - QPointF(self.width() / 2, self.height() / 2)) / self._scale()

    def _view_selection(self):
        return QRectF(self._to_view(self.selection.topLeft()), self._to_view(self.selection.bottomRight()))

    def _clamp_center(self):
        bounds, scale = self.bounds(), self._scale()
        half_w, half_h = self.width() / 2 / scale, self.height() / 2 / scale
        x = 0.0 if bounds.width() <= 2 * half_w else max(bounds.left() + half_w, min(self.center.x(),
                                                                                    bounds.right() - half_w))
        y = 0.0 if bounds.height() <= 2 * half_h else max(bounds.top() + half_h, min(self.center.y(),
                                                                                     bounds.bottom() - half_h))
        self.center = QPointF(x, y)

    def zoom_by(self, factor, anchor=None):
        """Zoome en gardant fixe le point de l'image sous anchor (centre de la vue par défaut)."""
        middle = QPointF(self.width() / 2, self.height() / 2)
        anchor = anchor if anchor is not None else middle
        point = self._to_photo(anchor)
        self.zoom = max(1.0, min(20.0, self.zoom * factor))
        self.center = point - (anchor - middle) / self._scale()
        self._clamp_center()
        self.update()

    def fit_view(self):
        self.zoom = 1.0
        self.center = QPointF()
        self.update()

    # --- Rendu --------------------------------------------------------------

    def render(self, width, height, adjusted=True, fast=False):
        """Contenu du cadre en image de width × height pixels, sur fond blanc.

        fast : d'après l'image d'affichage (aperçu) plutôt que d'après l'image complète.
        """
        source = self.display if fast else self.image
        output = QImage(width, height, QImage.Format.Format_RGB32)
        output.fill(Qt.GlobalColor.white)
        scale = width / self.selection.width()
        drawn_w, drawn_h = self.image.width() * scale, self.image.height() * scale
        if drawn_w < source.width() * 0.9:  # une forte réduction par le peintre seul crénelerait les détails
            source = source.scaled(max(1, round(drawn_w)), max(1, round(drawn_h)),
                                   Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter = QPainter(output)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(scale, scale)
        painter.translate(-self.selection.topLeft())
        painter.rotate(self.angle)
        painter.drawImage(QRectF(-self.image.width() / 2, -self.image.height() / 2,
                                 self.image.width(), self.image.height()), source)
        painter.end()
        if adjusted and not fast:
            return adjust_image(output, self.brightness, self.contrast)
        return output

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#1e293b"))

        scale = self._scale()
        painter.save()
        painter.translate(self._to_view(QPointF()))
        painter.scale(scale, scale)
        painter.rotate(self.angle)
        painter.drawImage(QRectF(-self.image.width() / 2, -self.image.height() / 2,
                                 self.image.width(), self.image.height()), self.display)
        painter.restore()

        # Assombrit ce qui sera coupé.
        frame = self._view_selection()
        outside = QPainterPath()
        outside.addRect(QRectF(self.rect()))
        inside = QPainterPath()
        inside.addRect(frame)
        painter.fillPath(outside.subtracted(inside), QColor(15, 23, 42, 170))

        color = QColor("#f59e0b") if self.free else QColor("#ffffff")
        if not self.free and self.show_guide and self.head is not None:
            # Ovale de la bonne hauteur (du menton au sommet du crâne) et axe du visage.
            h = frame.height() * sum(self.head) / 2
            w = h * 0.74
            center = QPointF(frame.center().x(), frame.top() + frame.height() * 0.48)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, w / 2, h / 2)
            painter.setPen(QPen(QColor(255, 255, 255, 110), 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(frame.center().x(), frame.top()), QPointF(frame.center().x(), frame.bottom()))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 2))
        painter.drawRect(frame)
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#1e293b"), 1))
        points = [frame.topLeft(), frame.topRight(), frame.bottomLeft(), frame.bottomRight()]
        if self.free:
            points += [QPointF(frame.center().x(), frame.top()), QPointF(frame.center().x(), frame.bottom()),
                       QPointF(frame.left(), frame.center().y()), QPointF(frame.right(), frame.center().y())]
        for point in points:
            painter.drawRect(QRectF(point.x() - 4.5, point.y() - 4.5, 9, 9))

    # --- Souris et clavier ----------------------------------------------------

    def _hit(self, position):
        """Partie du cadre sous la souris : (sx, sy) pour un coin ou un bord, "move" à l'intérieur, None en dehors."""
        frame = self._view_selection()
        near_left = abs(position.x() - frame.left()) <= self.GRAB
        near_right = abs(position.x() - frame.right()) <= self.GRAB
        near_top = abs(position.y() - frame.top()) <= self.GRAB
        near_bottom = abs(position.y() - frame.bottom()) <= self.GRAB
        sx = 1 if near_right else -1 if near_left else 0
        sy = 1 if near_bottom else -1 if near_top else 0
        if sx and sy:
            return sx, sy
        if self.free:
            if sx and frame.top() <= position.y() <= frame.bottom():
                return sx, 0
            if sy and frame.left() <= position.x() <= frame.right():
                return 0, sy
        return "move" if frame.contains(position) else None

    def _update_cursor(self, position):
        hit = self._hit(position)
        if hit == "move":
            shape = Qt.CursorShape.SizeAllCursor
        elif hit is None:
            shape = Qt.CursorShape.CrossCursor
        elif hit[0] == 0:
            shape = Qt.CursorShape.SizeVerCursor
        elif hit[1] == 0:
            shape = Qt.CursorShape.SizeHorCursor
        elif hit[0] == hit[1]:
            shape = Qt.CursorShape.SizeFDiagCursor
        else:
            shape = Qt.CursorShape.SizeBDiagCursor
        self.setCursor(shape)

    def mousePressEvent(self, event):
        position = event.position()
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self.drag = ("pan", position, QPointF(self.center))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            hit = self._hit(position)
            rect = self.selection
            if hit == "move":
                self.drag = ("move", self._to_photo(position) - rect.topLeft())
            elif hit is None:  # nouvelle zone, seulement si la souris bouge vraiment
                bounds = self.bounds()
                point = self._to_photo(position)
                anchor = QPointF(max(bounds.left(), min(point.x(), bounds.right())),
                                 max(bounds.top(), min(point.y(), bounds.bottom())))
                self.drag = ("draw", position, anchor)
            else:
                sx, sy = hit
                anchor = QPointF(rect.left() if sx >= 0 else rect.right(), rect.top() if sy >= 0 else rect.bottom())
                self.drag = ("resize", anchor, sx, sy)

    def mouseMoveEvent(self, event):
        position = event.position()
        if self.drag is None:
            self._update_cursor(position)
            return
        point = self._to_photo(position)
        kind = self.drag[0]
        if kind == "pan":
            self.center = self.drag[2] - (position - self.drag[1]) / self._scale()
            self._clamp_center()
            self.update()
        elif kind == "move":
            rect = QRectF(self.selection)
            rect.moveTopLeft(point - self.drag[1])
            self._set_selection(rect)
        elif kind == "resize":
            self._resize_selection(self.drag[1], point, self.drag[2], self.drag[3])
        elif (position - self.drag[1]).manhattanLength() >= 6:  # "draw"
            anchor = self.drag[2]
            sx = 1 if point.x() >= anchor.x() else -1
            sy = 1 if point.y() >= anchor.y() else -1
            self._resize_selection(anchor, point, sx, sy, new=True)

    def _resize_selection(self, anchor, point, sx, sy, new=False):
        """Étire le cadre depuis le point fixe anchor (coin ou bord opposé) ; sx, sy : sens de l'étirement."""
        bounds = self.bounds()
        minimum = max(24 / self._scale(), 2.0)
        if self.free:
            rect = QRectF(anchor, anchor) if new else QRectF(self.selection)
            if sx > 0:
                rect.setRight(max(min(point.x(), bounds.right()), anchor.x() + minimum))
            elif sx < 0:
                rect.setLeft(min(max(point.x(), bounds.left()), anchor.x() - minimum))
            if sy > 0:
                rect.setBottom(max(min(point.y(), bounds.bottom()), anchor.y() + minimum))
            elif sy < 0:
                rect.setTop(min(max(point.y(), bounds.top()), anchor.y() - minimum))
            self._set_selection(rect)
            return
        room_w = bounds.right() - anchor.x() if sx > 0 else anchor.x() - bounds.left()
        room_h = bounds.bottom() - anchor.y() if sy > 0 else anchor.y() - bounds.top()
        limit = min(room_h, room_w / self.ratio)
        wanted = max(abs(point.x() - anchor.x()) / self.ratio, abs(point.y() - anchor.y()))
        h = max(min(wanted, limit), min(minimum, limit))
        w = h * self.ratio
        self.selection = QRectF(anchor.x() if sx > 0 else anchor.x() - w, anchor.y() if sy > 0 else anchor.y() - h,
                                w, h)
        self.update()
        self.changed.emit()

    def mouseReleaseEvent(self, event):
        self.drag = None
        self._update_cursor(event.position())

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        if steps:
            self.zoom_by(1.15 ** steps, event.position())

    def keyPressEvent(self, event):
        """Les flèches déplacent le cadre d'un pixel de l'écran (dix avec Maj)."""
        moves = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if event.key() not in moves:
            super().keyPressEvent(event)
            return
        step = (10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1) / self._scale()
        dx, dy = moves[event.key()]
        self._set_selection(self.selection.translated(dx * step, dy * step))

    def resizeEvent(self, event):
        self._clamp_center()
        super().resizeEvent(event)


class SheetPreview(QWidget):
    """Aperçu de la feuille à imprimer, avec ses photos."""

    def __init__(self):
        super().__init__()
        self.page = None
        self.photo = None
        self.positions = []
        self.image = None
        self.cut_lines = False
        self.setMinimumSize(220, 200)

    def set_sheet(self, page, photo, positions, cut_lines):
        self.page, self.photo, self.positions, self.cut_lines = page, photo, positions, cut_lines
        self.update()

    def set_image(self, image):
        self.image = image
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#e5e9f0"))
        if self.page is None:
            return
        scale = min((self.width() - 20) / self.page[0], (self.height() - 20) / self.page[1])
        w, h = self.page[0] * scale, self.page[1] * scale
        left, top = (self.width() - w) / 2, (self.height() - h) / 2
        painter.fillRect(QRectF(left + 2, top + 3, w, h), QColor(15, 23, 42, 40))
        painter.fillRect(QRectF(left, top, w, h), QColor("#ffffff"))
        for x, y in self.positions:
            rect = QRectF(left + x * scale, top + y * scale, self.photo[0] * scale, self.photo[1] * scale)
            if self.image is not None:
                painter.drawImage(rect, self.image)
            if self.cut_lines:
                painter.setPen(QPen(QColor("#94a3b8"), 0))
                painter.drawRect(rect)


class IdPhotoDialog(QDialog):
    """Prépare une photo d'identité : recadrage et retouches à gauche, format et feuille à droite.

    settings : réglages d'une planche existante, à reprendre pour la modifier. limited : la photo reçue est déjà
    recadrée, ce qui était hors du cadre n'existe plus.
    """

    def __init__(self, image, name, parent=None, settings=None, limited=False):
        super().__init__(parent)
        self.setWindowTitle(f"{'Modifier la planche' if settings is not None else 'Photos d’identité'} — {name}")
        self.original = image
        self.history = []
        self.ops = []  # quarts de tour et découpes depuis la photo d'origine, gardés dans les réglages de la planche

        self.view = PhotoCropView(image)
        self.view.changed.connect(self._schedule_refresh)
        self.refresh_timer = QTimer(self)  # un glissement de souris envoie beaucoup d'événements
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(30)
        self.refresh_timer.timeout.connect(self._refresh_photo)

        layout = QHBoxLayout(self)
        layout.setSpacing(14)
        layout.addLayout(self._photo_column(), 1)
        layout.addWidget(self._settings_column())

        screen = self.screen().availableGeometry()
        self.resize(min(1180, screen.width() - 40), min(800, screen.height() - 60))
        self._update_sheet()
        if settings is not None:
            self.ok_button.setText("Mettre à jour la planche")
            self.limited_label.setVisible(limited)
            self.apply_settings(settings)

    # --- Construction de la fenêtre ---------------------------------------------

    @staticmethod
    def _tool_button(text, icon, tooltip, slot):
        button = QPushButton(make_icon(icon), text) if icon else QPushButton(text)
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        button.setAutoDefault(False)  # Entrée dans un champ ne doit pas déclencher un bouton
        button.clicked.connect(slot)
        return button

    def _photo_column(self):
        self.tools = QWidget()
        tools = QHBoxLayout(self.tools)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(6)
        tools.addWidget(self._tool_button("", "rotate_ccw", "Pivoter d'un quart de tour à gauche",
                                          lambda: self.rotate(270)))
        tools.addWidget(self._tool_button("", "rotate_cw", "Pivoter d'un quart de tour à droite",
                                          lambda: self.rotate(90)))
        tools.addSpacing(8)
        tools.addWidget(self._tool_button("", "zoom_out", "Zoom arrière (molette)", lambda: self.view.zoom_by(0.8)))
        tools.addWidget(self._tool_button("", "zoom_in", "Zoom avant (molette)", lambda: self.view.zoom_by(1.25)))
        tools.addWidget(self._tool_button("Ajuster", None, "Afficher toute la photo", self.view.fit_view))
        tools.addSpacing(8)
        tools.addWidget(self._tool_button("Tronquer…", "crop", "Couper définitivement les bords de la photo, "
                                          "aux proportions de votre choix", self.start_truncate))
        tools.addStretch()
        self.undo_button = self._tool_button("Annuler", "undo", "Annuler le dernier quart de tour ou la dernière "
                                             "découpe", self.undo)
        self.undo_button.setEnabled(False)
        tools.addWidget(self.undo_button)
        tools.addWidget(self._tool_button("Réinitialiser", "reset", "Revenir à la photo d'origine", self.reset))

        # Boutons du mode « tronquer », à la place des outils.
        self.truncate_bar = QWidget()
        bar = QHBoxLayout(self.truncate_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)
        hint = QLabel("Délimitez la partie à garder, puis appliquez (Entrée). Échap pour annuler.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        bar.addWidget(hint, 1)
        bar.addWidget(self._tool_button("Annuler", None, "Garder la photo telle quelle", self.cancel_truncate))
        apply_button = self._tool_button("Appliquer la découpe", "crop", "Couper tout ce qui est hors du cadre",
                                         self.apply_truncate)
        set_primary(apply_button)
        bar.addWidget(apply_button)
        self.truncate_bar.hide()

        self.angle_slider, self.angle_label = self._slider(-ID_PHOTO_MAX_ANGLE * 10, ID_PHOTO_MAX_ANGLE * 10)
        self.brightness_slider, self.brightness_label = self._slider(-50, 50)
        self.contrast_slider, self.contrast_label = self._slider(-50, 50)
        self.angle_slider.setToolTip("Corrige une photo légèrement penchée")
        self.brightness_slider.setToolTip("Reste discret : une photo d'identité ne doit pas être retouchée")
        self.contrast_slider.setToolTip("Reste discret : une photo d'identité ne doit pas être retouchée")
        self.angle_slider.valueChanged.connect(self._angle_changed)
        self.brightness_slider.valueChanged.connect(self._adjustments_changed)
        self.contrast_slider.valueChanged.connect(self._adjustments_changed)

        sliders = QGridLayout()
        sliders.setHorizontalSpacing(8)
        sliders.setVerticalSpacing(2)
        for column, (title, slider, label) in enumerate((
                ("Redresser", self.angle_slider, self.angle_label),
                ("Luminosité", self.brightness_slider, self.brightness_label),
                ("Contraste", self.contrast_slider, self.contrast_label))):
            sliders.addWidget(QLabel(title), 0, column * 2)
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            label.setObjectName("hint")
            sliders.addWidget(label, 0, column * 2 + 1)
            sliders.addWidget(slider, 1, column * 2, 1, 2)
        self.angle_label.setText("0°")

        hint = QLabel("Déplacez le cadre et tirez ses coins, ou tracez une nouvelle zone. Molette : zoom. "
                      "Clic droit : déplacer la vue. Flèches : réglage fin.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        self.limited_label = QLabel("Cette planche ne contient que la photo déjà recadrée : vous pouvez la recadrer "
                                    "davantage, mais pas retrouver ce qui était hors du cadre. Repartez de la photo "
                                    "d'origine pour cela (bouton « Identité »).")
        self.limited_label.setWordWrap(True)
        self.limited_label.setStyleSheet("color: #b45309;")
        self.limited_label.hide()

        column = QVBoxLayout()
        column.setSpacing(8)
        column.addWidget(self.tools)
        column.addWidget(self.truncate_bar)
        column.addWidget(self.limited_label)
        column.addWidget(self.view, 1)
        column.addWidget(hint)
        column.addLayout(sliders)
        return column

    @staticmethod
    def _slider(minimum, maximum):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(0)
        return slider, QLabel("0")

    @staticmethod
    def _spin(value, minimum, maximum, slot):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(1)
        spin.setSingleStep(1)
        spin.setSuffix(" mm")
        spin.setValue(value)
        spin.valueChanged.connect(slot)
        return spin

    def _settings_column(self):
        self.format_combo = QComboBox()
        for label, *_size in ID_PHOTO_FORMATS:
            self.format_combo.addItem(label)
        self.format_combo.currentIndexChanged.connect(self._update_sheet)
        self.photo_w = self._spin(35, 10, 200, self._update_sheet)
        self.photo_h = self._spin(45, 10, 200, self._update_sheet)
        self.guide_box = QCheckBox("Afficher l'ovale du visage")
        self.guide_box.setChecked(True)
        self.guide_box.setToolTip("Le haut du crâne et le menton doivent toucher l'ovale")
        self.guide_box.toggled.connect(self._update_sheet)

        self.paper_combo = QComboBox()
        for label, *_size in ID_PHOTO_PAPERS:
            self.paper_combo.addItem(label)
        self.paper_combo.currentIndexChanged.connect(self._update_sheet)
        self.paper_w = self._spin(100, 40, 500, self._update_sheet)
        self.paper_h = self._spin(150, 40, 500, self._update_sheet)

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Automatique", "auto")
        self.orientation_combo.addItem("Portrait", "portrait")
        self.orientation_combo.addItem("Paysage", "landscape")
        self.orientation_combo.currentIndexChanged.connect(self._update_sheet)
        self.margin_spin = self._spin(5, ID_PHOTO_MIN_MARGIN, 50, self._update_sheet)
        self.margin_spin.setToolTip("Blanc autour des photos. Leur taille ne change pas, seulement leur nombre. "
                                    f"Minimum {ID_PHOTO_MIN_MARGIN} mm : plus près du bord, l'imprimante les couperait")
        self.gap_spin = self._spin(2, 0, 30, self._update_sheet)
        self.gap_spin.setToolTip("Blanc entre les photos. Leur taille ne change pas, seulement leur nombre")
        self.wanted_count = 0  # nombre demandé, rétabli quand la feuille peut de nouveau le contenir
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 1)
        self.count_spin.setSpecialValueText("Feuille entière")
        self.count_spin.valueChanged.connect(self._count_changed)
        self.cut_box = QCheckBox("Traits de coupe autour des photos")
        self.cut_box.setChecked(True)
        self.cut_box.toggled.connect(self._update_sheet)
        self.keep_box = QCheckBox("Garder la photo pour modifier la planche plus tard")
        self.keep_box.setChecked(True)
        self.keep_box.setToolTip("La photo entière, y compris ce qui est hors du cadre, est jointe au PDF (quelques Mo, "
                                 "sans ses métadonnées). Décochez si vous transmettez ce PDF à quelqu'un d'autre")

        self.custom_photo_rows = []
        self.custom_paper_rows = []
        grid = QGridLayout()
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        row = 0

        def add(label, widget, rows=None):
            nonlocal row
            caption = QLabel(label)
            grid.addWidget(caption, row, 0)
            grid.addWidget(widget, row, 1)
            if rows is not None:
                rows.extend((caption, widget))
            row += 1

        def heading(text):
            nonlocal row
            title = QLabel(text)
            title.setStyleSheet("font-weight: 600;")
            grid.addWidget(title, row, 0, 1, 2)
            row += 1

        heading("Format de la photo")
        grid.addWidget(self.format_combo, row, 0, 1, 2)
        row += 1
        add("Largeur", self.photo_w, self.custom_photo_rows)
        add("Hauteur", self.photo_h, self.custom_photo_rows)
        grid.addWidget(self.guide_box, row, 0, 1, 2)
        row += 1
        heading("Papier de l'imprimante")
        grid.addWidget(self.paper_combo, row, 0, 1, 2)
        row += 1
        add("Largeur", self.paper_w, self.custom_paper_rows)
        add("Hauteur", self.paper_h, self.custom_paper_rows)
        add("Orientation", self.orientation_combo)
        add("Marge", self.margin_spin)
        add("Espacement", self.gap_spin)
        add("Nombre", self.count_spin)
        grid.addWidget(self.cut_box, row, 0, 1, 2)
        grid.addWidget(self.keep_box, row + 1, 0, 1, 2)

        self.sheet_preview = SheetPreview()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-weight: 600;")
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet(f"color: {RED};")
        self.warning.hide()
        note = QLabel("La marge et l'espacement ne changent que le nombre de photos, jamais leur taille. Imprimez sur le "
                      "papier choisi ici, vérifiez à la règle une photo, et les exigences de l'organisme qui la demande.")
        note.setObjectName("hint")
        note.setWordWrap(True)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Générer le PDF")
        self.ok_button.setIcon(make_icon("id_photo"))
        set_primary(self.ok_button)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setText("Annuler")
        for button in (self.ok_button, cancel):  # aucun bouton par défaut : Entrée sert à valider les champs
            button.setAutoDefault(False)
            button.setDefault(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        panel = QVBoxLayout()
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setSpacing(8)
        panel.addLayout(grid)
        panel.addWidget(self.sheet_preview, 1)
        panel.addWidget(self.summary)
        panel.addWidget(self.warning)
        panel.addWidget(note)
        panel.addWidget(self.buttons)
        widget = QWidget()
        widget.setFixedWidth(340)
        widget.setLayout(panel)
        return widget

    # --- Réglages de la feuille ---------------------------------------------------

    def photo_size(self):
        """(largeur, hauteur) de la photo en mm."""
        _label, w, h, _head_min, _head_max = ID_PHOTO_FORMATS[self.format_combo.currentIndex()]
        return (self.photo_w.value(), self.photo_h.value()) if w is None else (w, h)

    def paper_size(self):
        """(largeur, hauteur) de la feuille en mm."""
        _label, w, h = ID_PHOTO_PAPERS[self.paper_combo.currentIndex()]
        return (self.paper_w.value(), self.paper_h.value()) if w is None else (w, h)

    def _layout(self):
        return id_photo_layout(self.paper_size(), self.photo_size(), self.margin_spin.value(), self.gap_spin.value(),
                               self.orientation_combo.currentData(), self.count_spin.value())

    def _count_changed(self, value):
        self.wanted_count = value
        self._update_sheet()

    def _update_sheet(self):
        """Applique le format et la feuille choisis au cadre, à l'aperçu et au résumé."""
        _label, custom, _h, head_min, head_max = ID_PHOTO_FORMATS[self.format_combo.currentIndex()]
        for widget in self.custom_photo_rows:
            widget.setVisible(custom is None)
        for widget in self.custom_paper_rows:
            widget.setVisible(ID_PHOTO_PAPERS[self.paper_combo.currentIndex()][1] is None)

        photo = self.photo_size()
        head = None if custom is None else (head_min / photo[1], head_max / photo[1])
        self.guide_box.setVisible(head is not None)  # format sur mesure : hauteur de tête inconnue
        self.view.set_guide(head, self.guide_box.isChecked())
        self.view.set_ratio(photo[0] / photo[1])

        page_w, page_h, capacity, positions = self._layout()
        # Moins de place : moins de photos que demandé, jamais des photos plus petites.
        self.count_spin.blockSignals(True)
        self.count_spin.setMaximum(max(capacity, 1))
        self.count_spin.setValue(self.wanted_count)
        self.count_spin.blockSignals(False)
        page_w, page_h, capacity, positions = self._layout()
        self.positions = positions
        self.page_size = (page_w, page_h)
        self.sheet_preview.set_sheet((page_w, page_h), photo, positions, self.cut_box.isChecked())
        if positions:
            self.summary.setText(f"{len(positions)} photo{'s' if len(positions) > 1 else ''} de {mm_text(photo[0])} × "
                                 f"{mm_text(photo[1])} mm sur une feuille de {mm_text(round(page_w, 1))} × "
                                 f"{mm_text(round(page_h, 1))} mm")
        else:
            self.summary.setText("La photo ne tient pas sur cette feuille : réduisez la marge ou changez de papier.")
        self._refresh_photo()

    # --- Photo ---------------------------------------------------------------------

    def _schedule_refresh(self):
        self.refresh_timer.start()

    def output_dpi(self):
        """Résolution réelle de la zone sélectionnée une fois imprimée, en pixels par pouce."""
        return self.view.selection.width() / (self.photo_size()[0] / 25.4)

    def _refresh_photo(self):
        """Met à jour la vignette, les avertissements et l'état du bouton de génération."""
        self.refresh_timer.stop()
        if self.view.free:
            self.ok_button.setEnabled(False)
            return
        photo = self.photo_size()
        self.sheet_preview.set_image(self.view.render(240, max(1, round(240 * photo[1] / photo[0])), fast=True))
        messages = []
        dpi = self.output_dpi()
        if dpi < ID_PHOTO_LOW_DPI:
            messages.append(f"Zone peu détaillée ({round(dpi)} ppp) : la photo risque d'être floue une fois imprimée. "
                            "Il en faudrait au moins 300.")
        if not self.view.covers_image():
            messages.append("Le cadre dépasse de la photo : les parties vides seront imprimées en blanc.")
        self.warning.setText("\n".join(messages))
        self.warning.setVisible(bool(messages))
        self.ok_button.setEnabled(bool(self.positions))

    def _remember(self):
        self.history.append(self.view.state())
        del self.history[:-ID_PHOTO_HISTORY]
        self.undo_button.setEnabled(True)

    def _set_angle_slider(self, angle):
        self.angle_slider.blockSignals(True)
        self.angle_slider.setValue(round(angle * 10))
        self.angle_slider.blockSignals(False)
        self.angle_label.setText(f"{mm_text(angle)}°")

    def _angle_changed(self, value):
        angle = value / 10
        self.angle_label.setText(f"{mm_text(angle)}°")
        self.view.set_angle(angle)

    def _adjustments_changed(self):
        brightness, contrast = self.brightness_slider.value(), self.contrast_slider.value()
        self.brightness_label.setText(str(brightness))
        self.contrast_label.setText(str(contrast))
        self.view.set_adjustments(brightness, contrast)

    def rotate(self, degrees):
        """Quart de tour : l'inclinaison fine est conservée, le cadre repart de la zone par défaut."""
        self._remember()
        self.ops.append(("rotate", degrees))
        self.view.set_state(self.view.image.transformed(QTransform().rotate(degrees)), self.view.angle, None)

    def undo(self):
        if not self.history:
            return
        image, angle, selection = self.history.pop()
        self.ops.pop()
        self.view.set_state(image, angle, selection)
        self._set_angle_slider(angle)
        self.undo_button.setEnabled(bool(self.history))

    def reset(self):
        self.history.clear()
        self.ops.clear()
        self.undo_button.setEnabled(False)
        self._set_angle_slider(0)
        for slider in (self.brightness_slider, self.contrast_slider):
            slider.blockSignals(True)
            slider.setValue(0)
            slider.blockSignals(False)
        self.brightness_label.setText("0")
        self.contrast_label.setText("0")
        self.view.brightness = self.view.contrast = 0
        self.view.set_state(self.original, 0.0, None)

    # --- Mode « tronquer » ------------------------------------------------------------

    def _set_truncating(self, active):
        self.tools.setVisible(not active)
        self.truncate_bar.setVisible(active)

    def start_truncate(self):
        self.view.begin_free()
        self._set_truncating(True)
        self.view.setFocus()

    def apply_truncate(self):
        self._remember()
        # Le souvenir garde le cadre d'avant le mode « tronquer » : c'est lui qui revient à l'annulation.
        image, angle, selection = self.history[-1]
        self.history[-1] = (image, angle, QRectF(self.view.saved_selection))
        self.ops.append(("crop", angle, selection.x(), selection.y(), selection.width(), selection.height()))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.view.end_free(True)
        finally:
            QApplication.restoreOverrideCursor()
        self._set_angle_slider(0)
        self._set_truncating(False)

    def cancel_truncate(self):
        self.view.end_free(False)
        self._set_truncating(False)

    def keyPressEvent(self, event):
        """Entrée applique la découpe ou active le bouton sélectionné, mais ne génère jamais le PDF depuis un champ
        (la barre de boutons se redonne un bouton par défaut à l'affichage)."""
        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            super().keyPressEvent(event)
        elif self.view.free:
            self.apply_truncate()
        elif isinstance(self.focusWidget(), QPushButton):
            self.focusWidget().click()

    def reject(self):
        """Échap quitte d'abord le mode « tronquer »."""
        if self.view.free:
            self.cancel_truncate()
        else:
            super().reject()

    # --- Réglages d'une planche ----------------------------------------------------------

    def settings(self):
        """Tout ce qu'il faut, avec la photo d'origine, pour reprendre cette planche plus tard."""
        rect = self.view.selection
        return {
            "version": 1,
            "format": self.format_combo.currentText(),
            "photo": self.photo_size(),
            "paper_name": self.paper_combo.currentText(),
            "paper": self.paper_size(),
            "orientation": self.orientation_combo.currentData(),
            "margin": self.margin_spin.value(),
            "gap": self.gap_spin.value(),
            "count": self.wanted_count,
            "cut_lines": self.cut_box.isChecked(),
            "guide": self.guide_box.isChecked(),
            "ops": list(self.ops),
            "angle": self.view.angle,
            "selection": (rect.x(), rect.y(), rect.width(), rect.height()),
            "brightness": self.brightness_slider.value(),
            "contrast": self.contrast_slider.value(),
        }

    @staticmethod
    def _choose_size(combo, table, name, size, spin_w, spin_h):
        """Sélectionne la ligne du tableau de ce nom et de cette taille, sinon de cette taille, sinon « Personnalisé »."""
        def same(row):
            return row[1] is not None and abs(row[1] - size[0]) < 0.06 and abs(row[2] - size[1]) < 0.06

        rows = list(enumerate(table))
        match = next((i for i, row in rows if row[0] == name and same(row)), None)
        if match is None:
            match = next((i for i, row in rows if same(row)), None)
        if match is None:
            spin_w.setValue(size[0])
            spin_h.setValue(size[1])
            match = next(i for i, row in rows if row[1] is None)
        combo.setCurrentIndex(match)

    def apply_settings(self, settings):
        """Reprend les réglages d'une planche. Ils viennent d'un fichier : toute valeur invalide est ignorée."""
        photo = finite_numbers(settings.get("photo"), 2)
        if photo is not None:
            self._choose_size(self.format_combo, ID_PHOTO_FORMATS, settings.get("format"), photo,
                              self.photo_w, self.photo_h)
        paper = finite_numbers(settings.get("paper"), 2)
        if paper is not None:
            self._choose_size(self.paper_combo, ID_PHOTO_PAPERS, settings.get("paper_name"), paper,
                              self.paper_w, self.paper_h)
        index = self.orientation_combo.findData(settings.get("orientation"))
        if index >= 0:
            self.orientation_combo.setCurrentIndex(index)
        for key, spin in (("margin", self.margin_spin), ("gap", self.gap_spin)):
            value = finite_numbers((settings.get(key),), 1)
            if value is not None:
                spin.setValue(value[0])
        self.cut_box.setChecked(settings.get("cut_lines", True) is not False)
        self.guide_box.setChecked(settings.get("guide", True) is not False)
        count = finite_numbers((settings.get("count"),), 1)
        if count is not None:
            self.wanted_count = max(0, int(min(count[0], 10000)))

        ops = settings.get("ops")
        for op in ops[:ID_PHOTO_MAX_OPS] if isinstance(ops, (list, tuple)) else ():
            if not isinstance(op, (list, tuple)) or not op:
                continue
            if op[0] == "rotate" and len(op) == 2 and op[1] in (90, 270):
                self.rotate(op[1])
            elif op[0] == "crop":
                crop = finite_numbers(op[1:], 5)
                if crop is not None and crop[3] >= 1 and crop[4] >= 1 and abs(crop[0]) <= ID_PHOTO_MAX_ANGLE:
                    self._set_angle_slider(crop[0])
                    self.view.set_angle(crop[0])
                    self.start_truncate()
                    self.view._set_selection(QRectF(*crop[1:]))
                    self.apply_truncate()

        angle = finite_numbers((settings.get("angle"),), 1)
        if angle is not None and abs(angle[0]) <= ID_PHOTO_MAX_ANGLE:
            self._set_angle_slider(angle[0])
            self.view.set_angle(angle[0])
        self._update_sheet()
        selection = finite_numbers(settings.get("selection"), 4)
        if selection is not None and selection[2] >= 1 and selection[3] >= 1:
            self.view._set_selection(QRectF(*selection))
        for key, slider in (("brightness", self.brightness_slider), ("contrast", self.contrast_slider)):
            value = finite_numbers((settings.get(key),), 1)
            if value is not None:
                slider.setValue(round(max(slider.minimum(), min(value[0], slider.maximum()))))
        self._refresh_photo()

    # --- Résultat ---------------------------------------------------------------------

    def sheet(self):
        """Le PDF de la feuille de photos, à la résolution que permet la zone sélectionnée."""
        photo = self.photo_size()
        dpi = max(ID_PHOTO_MIN_DPI, min(self.output_dpi(), ID_PHOTO_MAX_DPI))
        width = max(1, round(photo[0] / 25.4 * dpi))
        height = max(1, round(photo[1] / 25.4 * dpi))
        source = None
        if self.keep_box.isChecked():
            source = jpeg_bytes(self.original, ID_PHOTO_SOURCE_QUALITY), repr(self.settings())
        return id_photo_pdf(self.view.render(width, height), self.page_size, photo, self.positions,
                            self.cut_box.isChecked(), source)


# --- Comparaison de deux PDF ---------------------------------------------------------

# Types de différences : (couleur, libellé, libellé au pluriel en minuscules)
COMPARE_KINDS = {
    "ajout": (GREEN, "Ajout", "ajouts"),
    "suppression": (RED, "Suppression", "suppressions"),
    "modification": ("#ea7a00", "Modification", "modifications"),
    "visuel": ("#7c3aed", "Changement visuel", "changements visuels"),
    "page_ajoutee": (GREEN, "Page ajoutée", "pages ajoutées"),
    "page_supprimee": (RED, "Page supprimée", "pages supprimées"),
    "mise_en_page": ("#0891b2", "Mise en page", "changements de mise en page"),
}
COMPARE_TEXT_KINDS = ("ajout", "suppression", "modification")
COMPARE_PAGE_KINDS = ("page_ajoutee", "page_supprimee", "mise_en_page")
COMPARE_MODES = [("both", "Texte et visuel"), ("text", "Texte seul"), ("visual", "Visuel seul")]
COMPARE_DPI = 72  # résolution du rendu comparé pixel par pixel
COMPARE_CELL = 4  # pixels : grain des zones de différence visuelle (4 px à 72 ppp ≈ 1,4 mm)
COMPARE_GAP = 2  # cellules : deux différences plus proches que cela forment une seule zone
COMPARE_GAP_FINE = 1  # réglage « plan technique » : seules les cellules qui se touchent forment une zone (un via et
# la piste voisine restent deux différences)
COMPARE_DPI_FINE = 144  # réglage « plan technique » : cellules de 0,7 mm au lieu de 1,4 mm
COMPARE_MAX_ZONES_FINE = 150
COMPARE_PRESETS = [("document", "Document", 10), ("plan", "Plan technique (circuit, dessin)", 5)]
COMPARE_REPORT_DETAILS = 150  # différences au plus montrées en gros plan dans le rapport
# Nom d'une couche de circuit imprimé (KiCad, Altium, Eagle, Gerber) ou d'un plan de perçage, lu dans le texte de la page.
LAYER_NAME = re.compile(
    r"(?<![\w.])(?:[FB][._](?:Cu|SilkS|Silkscreen|Mask|Paste|Fab|CrtYd|Courtyard|Adhes|Adhesive)|In\d{1,2}[._]Cu"
    r"|Edge[._]Cuts|User[._]\w+|Dwgs[._]User|Cmts[._]User|Margin"
    r"|(?:Top|Bottom) (?:Layer|Overlay|Solder|Paste|Silkscreen|Copper)|Mid-?Layer ?\d+|Inner ?Layer ?\d+"
    r"|Drill (?:Drawing|Guide|Map)|Plan de perçage|Perçages)(?![\w])", re.IGNORECASE)
COMPARE_LINE_JOIN = 3  # lignes identiques au plus entre deux blocs modifiés comparés ensemble, mot à mot
COMPARE_MAX_ZONES = 25  # au-delà, les zones d'une page sont réunies en une seule
COMPARE_TEXT_SIMILARITY = 0.25  # part des mots retrouvés à l'identique pour apparier deux pages
COMPARE_IMAGE_SIMILARITY = 0.6  # ressemblance des vignettes pour apparier deux pages sans texte
COMPARE_PAGE_BAND = 30  # écart (en pages) cherché autour de la diagonale pour apparier les pages
COMPARE_THUMB = (24, 34)  # vignette en niveaux de gris des pages sans texte
COMPARE_NEW_PAGE_SHARE = 0.9  # part de mots nouveaux au-delà de laquelle une page sans équivalent est « ajoutée »
COMPARE_TICK = 0.04  # secondes de calcul entre deux passages dans la boucle d'événements
COMPARE_EXCERPT = 80  # caractères au plus pour citer un texte
COMPARE_HEADER = 26  # pixels : bandeau au-dessus de chaque page dans la vue comparée
PUNCTUATION = re.compile(r"[\W_]+")


def word_key(text, ignore_case, ignore_punctuation):
    """Forme d'un mot utilisée pour la comparaison (vide : mot ignoré)."""
    if ignore_punctuation:
        text = PUNCTUATION.sub("", text)
    else:
        text = "".join(text.split())  # espaces insécables ou fines restées dans un mot
    return text.casefold() if ignore_case else text


def page_words(page, ignore_case=False, ignore_punctuation=False):
    """Mots de la page dans l'ordre du contenu du fichier : (rectangle affiché, texte, clé de comparaison, ligne).

    Cet ordre est le plus stable d'une version à l'autre (un tri par position mélangerait les colonnes) ; un texte
    réécrit ailleurs dans le contenu est rapproché ensuite par sa position (reconcile_rewritten). MuPDF donne les
    coordonnées de la page non pivotée : elles sont ramenées à la page affichée."""
    matrix = page.rotation_matrix
    words = []
    extracted = page.get_text("words", flags=pymupdf.TEXT_MEDIABOX_CLIP)
    for x0, y0, x1, y1, text, block, line, _ in extracted:
        key = word_key(text, ignore_case, ignore_punctuation)
        if key:
            words.append((pymupdf.Rect(x0, y0, x1, y1) * matrix, text, key, (block, line)))
    return words


def unmoved_words(words, others, tolerance=0.5):
    """Les mots de words présents tels quels au même endroit dans others (à tolerance points près) : ils n'ont ni
    changé ni bougé, et visual_differences les compare donc à l'image."""
    places = {}
    for rect, text, *_ in others:
        places.setdefault(text, []).append(rect)
    return [word for word in words if any(
        abs(word[0].x0 - r.x0) <= tolerance and abs(word[0].y0 - r.y0) <= tolerance
        and abs(word[0].x1 - r.x1) <= tolerance and abs(word[0].y1 - r.y1) <= tolerance
        for r in places.get(word[1], ()))]


def page_name(page, words=None):
    """Nom d'une page pour la comparaison : son étiquette dans le PDF si elle n'est pas un simple numéro, sinon le
    nom de couche de circuit imprimé trouvé dans son texte (« F.Cu », « Top Layer », « Perçages »…), sinon ""."""
    try:
        label = page.get_label().strip()
    except Exception:
        label = ""
    if label and not label.isdigit():
        return label[:40]
    text = " ".join(w[1] for w in words) if words is not None else page.get_text()
    found = LAYER_NAME.search(text)
    return found.group(0) if found else ""


def overlay_pixmap(page_a, page_b, matrix, clip=None):
    """Superposition des deux pages en une image RVB : ce qui n'est que dans A en rouge, que dans B en vert, ce qui est
    commun en noir (chaque page est rendue en niveaux de gris : la couleur d'origine ne compte pas)."""
    pix_a = page_a.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY, alpha=False, clip=clip)
    pix_b = page_b.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY, alpha=False, clip=clip)
    if pix_b.irect != pix_a.irect:  # pages de formats différents : B est ramenée au cadre de A, fond blanc
        fond = pymupdf.Pixmap(pymupdf.csGRAY, pix_a.irect, False)
        fond.clear_with(255)
        commun = pix_a.irect & pix_b.irect
        if not commun.is_empty:
            fond.copy(pix_b, commun)
        pix_b = fond
    gray_a, gray_b = pix_a.samples, pix_b.samples
    rgb = bytearray(3 * len(gray_a))
    rgb[0::3] = gray_b  # rouge : clair là où B est blanc (le noir de A seul devient rouge)
    rgb[1::3] = gray_a  # vert : clair là où A est blanc (le noir de B seul devient vert)
    rgb[2::3] = bytes(map(min, gray_a, gray_b))
    return pymupdf.Pixmap(pymupdf.csRGB, pix_a.width, pix_a.height, bytes(rgb), False)


def page_thumbnail(page):
    """Vignette en niveaux de gris de taille fixe, pour apparier des pages sans texte."""
    width, height = COMPARE_THUMB
    rect = page.rect
    pix = page.get_pixmap(matrix=pymupdf.Matrix(width / max(1, rect.width), height / max(1, rect.height)),
                          colorspace=pymupdf.csGRAY, alpha=False)
    data, out = pix.samples, bytearray(b"\xff" * (width * height))
    w = min(width, pix.width)
    for y in range(min(height, pix.height)):
        out[y * width:y * width + w] = data[y * pix.stride:y * pix.stride + w]
    return bytes(out)


def thumbnail_similarity(a, b):
    """Ressemblance de deux vignettes, de 0 à 1, rapportée à l'encre présente (une page presque blanche ne
    ressemble pas à toutes les autres)."""
    ink = (255 * len(a) - sum(a)) + (255 * len(b) - sum(b))
    if ink == 0:
        return 1.0
    return max(0.0, 1 - sum(abs(x - y) for x, y in zip(a, b)) / ink)


def align_pages(n, m, similarity):
    """Apparie les pages des deux versions, à la manière d'un diff : une page insérée ou supprimée ne décale pas
    les suivantes. Générateur (une ligne du tableau par étape) qui renvoie la liste ordonnée des couples
    (i, j), i ou j valant None pour une page sans équivalent.

    Les pages restées seules entre deux couples sont ensuite associées dans l'ordre (page modifiée en profondeur
    plutôt que supprimée puis ajoutée) ; le surplus seul est déclaré ajouté ou supprimé."""
    band = COMPARE_PAGE_BAND + abs(n - m)
    previous = [0.0] * (m + 1)
    moves = []  # 0 : couple, 1 : page de A seule, 2 : page de B seule
    for i in range(1, n + 1):
        center = (i - 1) * m / max(1, n)
        low, high = max(1, int(center - band)), min(m, int(center + band) + 1)
        row, move = [0.0] * (m + 1), bytearray(m + 1)
        for j in range(1, m + 1):
            best, choice = previous[j], 1
            if row[j - 1] > best:
                best, choice = row[j - 1], 2
            if low <= j <= high:
                score, threshold = similarity(i - 1, j - 1)
                if score >= threshold and previous[j - 1] + score >= best:
                    best, choice = previous[j - 1] + score, 0
            row[j], move[j] = best, choice
        moves.append(move)
        previous = row
        yield i / max(1, n)

    path, i, j = [], n, m
    while i > 0 or j > 0:
        choice = moves[i - 1][j] if i > 0 and j > 0 else (1 if i > 0 else 2)
        if choice == 0:
            path.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif choice == 1:
            path.append((i - 1, None))
            i -= 1
        else:
            path.append((None, j - 1))
            j -= 1
    path.reverse()

    pairs, lone_a, lone_b = [], [], []

    def flush():
        for a, b in zip(lone_a, lone_b):
            pairs.append((a, b))
        pairs.extend((a, None) for a in lone_a[len(lone_b):])
        pairs.extend((None, b) for b in lone_b[len(lone_a):])
        lone_a.clear()
        lone_b.clear()

    for a, b in path:
        if a is None:
            lone_b.append(b)
        elif b is None:
            lone_a.append(a)
        else:
            flush()
            pairs.append((a, b))
    flush()
    return pairs


def merge_word_rects(words):
    """Rectangles (page, Rect) de mots consécutifs, réunis ligne par ligne."""
    marks = []
    last = None
    for page, rect, _text, _key, line in words:
        if last is not None and last == (page, line):
            marks[-1] = (page, marks[-1][1] | rect)
        else:
            marks.append((page, pymupdf.Rect(rect)))
        last = (page, line)
    return marks


TEXT_CHANGES = {"replace": "modification", "delete": "suppression", "insert": "ajout"}


def text_item(kind, old, new):
    """Différence de texte entre les mots old (version A) et new (version B), donnés comme dans text_differences.
    Les mots eux-mêmes sont gardés (raw_a, raw_b) jusqu'à la fin du calcul."""
    return {"kind": kind, "marks_a": merge_word_rects(old), "marks_b": merge_word_rects(new),
            "old": excerpt(w[2] for w in old), "new": excerpt(w[2] for w in new), "raw_a": old, "raw_b": new}


def word_changes(old, new):
    """Différences mot à mot entre deux suites de mots (les mots identiques sont ignorés)."""
    matcher = difflib.SequenceMatcher(None, [w[3] for w in old], [w[3] for w in new], autojunk=False)
    return [text_item(TEXT_CHANGES[tag], old[a1:a2], new[b1:b2])
            for tag, a1, a2, b1, b2 in matcher.get_opcodes() if tag != "equal"]


def excerpt(texts):
    """Citation abrégée d'une suite de mots."""
    text = " ".join(texts)
    return text if len(text) <= COMPARE_EXCERPT else text[:COMPARE_EXCERPT - 1].rstrip() + "…"


def in_background(function, progress):
    """Exécute function (du Python pur, jamais MuPDF) dans un fil d'exécution à part. Générateur qui produit
    progress tant que le calcul dure (l'interface reste fluide), puis renvoie son résultat."""
    outcome = []

    def work():
        try:
            outcome.append((True, function()))
        except Exception as exc:
            outcome.append((False, exc))

    worker = threading.Thread(target=work, daemon=True)  # abandonné sans attendre si l'on annule
    worker.start()
    while worker.is_alive():
        worker.join(0.01)
        yield progress
    succeeded, value = outcome[0]
    if not succeeded:
        raise value
    return value


def text_differences(pages_a, pages_b):
    """Différences de texte entre deux documents, donnés par les mots de chaque page (voir page_words).

    Les lignes sont comparées d'abord (rapide, et insensible au décalage d'un paragraphe inséré), puis les mots
    des seuls blocs de lignes qui diffèrent. Générateur : produit l'avancement (0 à 1) ; renvoie (différences,
    mots identiques par couple de pages {(page de A, page de B): nombre}), qui sert à apparier les pages."""
    def lines(words):
        result, start = [], 0
        for index in range(1, len(words) + 1):
            if index == len(words) or (words[index][0], words[index][4]) != (words[start][0], words[start][4]):
                result.append((start, index))
                start = index
        return result

    def prepare():
        # Suite des mots (page, rect, texte, clé, ligne) de tout le document, et ses lignes.
        words = [[(page, rect, text, key, line) for page, list_ in enumerate(pages) for rect, text, key, line in list_]
                 for pages in (pages_a, pages_b)]
        spans = [lines(sequence) for sequence in words]
        keys = [[" ".join(w[3] for w in sequence[s:e]) for s, e in list_] for sequence, list_ in zip(words, spans)]
        opcodes = difflib.SequenceMatcher(None, *keys, autojunk=False).get_opcodes()
        return words, spans, opcodes

    (words_a, words_b), (lines_a, lines_b), opcodes = yield from in_background(prepare, 0.0)

    # Blocs de lignes qui diffèrent. Deux blocs séparés par quelques lignes identiques sont comparés ensemble : un
    # paragraphe dont un mot change est souvent recoupé, et une ligne identique peut s'y glisser par hasard.
    segments = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            segments.append(["equal", i1, i2, j1, j2])
        elif (len(segments) >= 2 and segments[-2][0] == "block"
              and segments[-1][2] - segments[-1][1] <= COMPARE_LINE_JOIN):
            segments.pop()
            segments[-1][2], segments[-1][4] = i2, j2
        else:
            segments.append(["block", i1, i2, j1, j2])

    shared, items = {}, []
    blocks = sum(1 for segment in segments if segment[0] == "block")
    done = 0
    for kind, i1, i2, j1, j2 in segments:
        if kind == "equal":
            for k in range(i2 - i1):
                start_a, end_a = lines_a[i1 + k]
                key = (words_a[start_a][0], words_b[lines_b[j1 + k][0]][0])
                shared[key] = shared.get(key, 0) + end_a - start_a
            continue
        part_a = words_a[lines_a[i1][0]:lines_a[i2 - 1][1]] if i2 > i1 else []
        part_b = words_b[lines_b[j1][0]:lines_b[j2 - 1][1]] if j2 > j1 else []
        done += 1

        def compare_block(part_a=part_a, part_b=part_b):
            # Tout en arrière-plan, y compris la mise en forme : un très gros bloc (deux documents sans rapport)
            # figerait sinon l'interface plusieurs secondes. Rien ici n'appelle MuPDF (Rect est du Python pur).
            sequences = [w[3] for w in part_a], [w[3] for w in part_b]
            found, common = [], {}
            for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, *sequences, autojunk=False).get_opcodes():
                if tag == "equal":
                    for wa, wb in zip(part_a[a1:a2], part_b[b1:b2]):
                        common[(wa[0], wb[0])] = common.get((wa[0], wb[0]), 0) + 1
                    continue
                found.append(text_item(TEXT_CHANGES[tag], part_a[a1:a2], part_b[b1:b2]))
            return found, common

        found, common = yield from in_background(compare_block, done / blocks)
        items.extend(found)
        for key, count in common.items():
            shared[key] = shared.get(key, 0) + count
        yield done / blocks
    return items, shared


def marks_overlap(marks_a, marks_b):
    """Deux suites de rectangles se superposent-elles (même ligne, au moins en partie) ?"""
    for rect_a in marks_a:
        for rect_b in marks_b:
            height = min(rect_a.height, rect_b.height)
            vertical = min(rect_a.y1, rect_b.y1) - max(rect_a.y0, rect_b.y0)
            if height > 0 and vertical >= height / 2 and min(rect_a.x1, rect_b.x1) > max(rect_a.x0, rect_b.x0):
                return True
    return False


def reconcile_rewritten(items, pairs):
    """Rapproche une suppression et les ajouts écrits au même endroit d'une page appariée.

    Un éditeur de PDF qui modifie un mot l'efface et réécrit la ligne à la fin du contenu de la page : dans l'ordre
    du fichier, cela ressemble à une suppression et à un ajout éloignés. Superposés, ils sont comparés mot à mot
    entre eux : seuls les mots changés restent (aucun si le texte n'a été que déplacé dans le fichier)."""
    paired = {(a, b) for a, b in pairs if a is not None and b is not None}
    additions = [item for item in items if item["kind"] == "ajout"]
    dropped, replaced = set(), {}
    for deletion in [item for item in items if item["kind"] == "suppression"]:
        pages = {page for page, _ in deletion["marks_a"]}
        if len(pages) != 1:
            continue
        page_a = pages.pop()
        rects_a = [rect for _, rect in deletion["marks_a"]]
        group = [addition for addition in additions if id(addition) not in dropped
                 and all((page_a, page) in paired for page, _ in addition["marks_b"])
                 and marks_overlap(rects_a, [rect for _, rect in addition["marks_b"]])]
        if not group:
            continue
        dropped.update(id(addition) for addition in group)
        replaced[id(deletion)] = word_changes(deletion["raw_a"], [w for addition in group for w in addition["raw_b"]])
    return [change for item in items if id(item) not in dropped for change in replaced.get(id(item), [item])]


def visual_differences(page_a, page_b, tolerance, mask_rects=(), gap=COMPARE_GAP, dpi=COMPARE_DPI,
                       max_zones=COMPARE_MAX_ZONES):
    """Les zones qui diffèrent, d'un seul tenant (voir visual_differences_steps)."""
    steps = visual_differences_steps(page_a, page_b, tolerance, mask_rects, gap, dpi, max_zones)
    while True:
        try:
            next(steps)
        except StopIteration as stop:
            return stop.value


def visual_differences_steps(page_a, page_b, tolerance, mask_rects=(), gap=COMPARE_GAP, dpi=COMPARE_DPI,
                             max_zones=COMPARE_MAX_ZONES, progress=None):
    """Zones (Rect, en points de la page affichée) où le rendu des deux pages diffère.

    Les pages sont rendues en couleurs par MuPDF puis comparées par cellules de COMPARE_CELL pixels : une cellule
    diffère si l'écart d'une composante (rouge, vert ou bleu) d'un de ses pixels dépasse la tolérance (0 à 1). Le
    gris ne suffirait pas : un bleu et un rouge de même luminosité y sont identiques. Les cellules couvertes par
    mask_rects (le texte, déjà comparé mot à mot) sont ignorées. Les cellules proches sont réunies en zones."""
    scale = dpi / 72
    matrix = pymupdf.Matrix(scale, scale)
    pix_a = page_a.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
    pix_b = page_b.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
    width, height = min(pix_a.width, pix_b.width), min(pix_a.height, pix_b.height)
    row_bytes, cell_bytes = width * 3, COMPARE_CELL * 3
    data_a, data_b, stride_a, stride_b = pix_a.samples, pix_b.samples, pix_a.stride, pix_b.stride
    limit = round(max(0.0, min(1.0, tolerance)) * 255)
    cell = COMPARE_CELL
    columns = (width + cell - 1) // cell

    masked = set()
    for rect in mask_rects:
        for cy in range(max(0, int(rect.y0 * scale) // cell - 1), int(rect.y1 * scale) // cell + 2):
            for cx in range(max(0, int(rect.x0 * scale) // cell - 1), int(rect.x1 * scale) // cell + 2):
                masked.add((cx, cy))

    marked = set()
    group = 16 * cell_bytes  # les cellules sont d'abord comparées par groupes de 16 : la plupart sont identiques
    for y in range(height):
        if y % 32 == 0:
            yield progress  # générateur : l'interface reprend la main entre deux bandes de la page
        row_a = data_a[y * stride_a:y * stride_a + row_bytes]
        row_b = data_b[y * stride_b:y * stride_b + row_bytes]
        if row_a == row_b:
            continue
        cy = y // cell
        for start in range(0, row_bytes, group):
            if row_a[start:start + group] == row_b[start:start + group]:
                continue
            for x0 in range(start, min(start + group, row_bytes), cell_bytes):
                cx = x0 // cell_bytes
                if (cx, cy) in marked or (cx, cy) in masked:
                    continue
                chunk_a, chunk_b = row_a[x0:x0 + cell_bytes], row_b[x0:x0 + cell_bytes]
                if chunk_a != chunk_b and max(abs(p - q) for p, q in zip(chunk_a, chunk_b)) > limit:
                    marked.add((cx, cy))

    zones = []
    while marked:
        stack = [marked.pop()]
        x0 = x1 = stack[0][0]
        y0 = y1 = stack[0][1]
        while stack:
            cx, cy = stack.pop()
            x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
            for dy in range(-gap, gap + 1):
                for dx in range(-gap, gap + 1):
                    neighbour = (cx + dx, cy + dy)
                    if neighbour in marked:
                        marked.remove(neighbour)
                        stack.append(neighbour)
        zones.append(pymupdf.Rect(x0 * cell / scale, y0 * cell / scale,
                                  min(width, (x1 + 1) * cell) / scale, min(height, (y1 + 1) * cell) / scale))
    if len(zones) > max_zones:
        union = zones[0]
        for zone in zones[1:]:
            union |= zone
        zones = [union]
    zones.sort(key=lambda r: (r.y0, r.x0))
    return zones


def compare_documents(doc_a, doc_b, options):
    """Compare deux documents ouverts. Générateur : produit (avancement de 0 à 1, message) après chaque étape, ce
    qui laisse l'interface répondre et permet d'annuler ; renvoie le résultat (StopIteration.value).

    Tout le travail de MuPDF a lieu dans le fil qui appelle (MuPDF ne se partage pas entre fils d'exécution).
    options : mode (« both », « text » ou « visual »), ignore_case, ignore_punctuation, tolerance (0 à 1)."""
    mode = options.get("mode", "both")
    ignore_case = options.get("ignore_case", False)
    ignore_punctuation = options.get("ignore_punctuation", False)
    n, m = len(doc_a), len(doc_b)
    total = max(1, n + m)
    notes = []

    # 1. Lecture des mots de chaque page (30 %).
    infos = ([], [])
    for side, doc in enumerate((doc_a, doc_b)):
        for index, page in enumerate(doc):
            words = page_words(page, ignore_case, ignore_punctuation)
            infos[side].append({"words": words, "thumb": None, "rect": pymupdf.Rect(page.rect),
                                "name": page_name(page, words)})
            done = index + 1 + (n if side else 0)
            yield 0.3 * done / total, f"Lecture de la version {'AB'[side]} : page {index + 1} / {len(doc)}"
    infos_a, infos_b = infos
    text_a = any(info["words"] for info in infos_a)
    text_b = any(info["words"] for info in infos_b)
    use_text = text_a and text_b
    for name, has_text in (("A", text_a), ("B", text_b)):
        if not has_text and (n if name == "A" else m):
            notes.append(f"La version {name} ne contient pas de texte (PDF scanné ou image) : seule la comparaison "
                         "visuelle est possible.")
    text_mode = mode in ("both", "text") and use_text
    visual_mode = mode in ("both", "visual") or (mode == "text" and not use_text)
    if mode == "text" and not use_text:
        notes.append("Comparaison du texte impossible : la comparaison visuelle a été faite à la place.")

    # 2. Texte, mot à mot, sur l'ensemble du document : un paragraphe qui passe à la page suivante n'est pas
    # signalé comme supprimé puis ajouté (25 %). Fait aussi en mode visuel seul : il sert à apparier les pages.
    items, shared = [], {}
    if use_text:
        differ = text_differences([info["words"] for info in infos_a], [info["words"] for info in infos_b])
        while True:
            try:
                fraction = next(differ)
            except StopIteration as stop:
                items, shared = stop.value
                break
            yield 0.3 + 0.25 * fraction, "Comparaison du texte…"
        if not text_mode:
            items = []

    # Vignettes des pages sans texte, pour les apparier (5 %).
    need = [(side, index) for side, list_ in enumerate(infos) for index, info in enumerate(list_)
            if not use_text or not info["words"]]
    for count, (side, index) in enumerate(need):
        infos[side][index]["thumb"] = page_thumbnail((doc_a, doc_b)[side][index])
        yield 0.55 + 0.05 * (count + 1) / len(need), "Préparation des pages sans texte…"

    # 3. Appariement des pages, d'après les mots retrouvés à l'identique, ou l'aspect des pages sans texte (5 %).
    def similarity(i, j):
        """(ressemblance de 0 à 1, seuil d'appariement) de la page i de A et de la page j de B."""
        a, b = infos_a[i], infos_b[j]
        if use_text and (a["words"] or b["words"]):
            if not (a["words"] and b["words"]):
                return 0.0, 1.0  # une page avec du texte et une sans : pas apparentées
            return shared.get((i, j), 0) / max(len(a["words"]), len(b["words"])), COMPARE_TEXT_SIMILARITY
        return thumbnail_similarity(a["thumb"], b["thumb"]), COMPARE_IMAGE_SIMILARITY

    aligner = align_pages(n, m, similarity)
    while True:
        try:
            fraction = next(aligner)
        except StopIteration as stop:
            pairs = stop.value
            break
        yield 0.6 + 0.05 * fraction, "Appariement des pages…"
    pair_of_a = {a: k for k, (a, b) in enumerate(pairs) if a is not None}
    pair_of_b = {b: k for k, (a, b) in enumerate(pairs) if b is not None}

    items = reconcile_rewritten(items, pairs)

    # Pages sans équivalent : ajoutées ou supprimées si leur texte est surtout nouveau (ou absent), sinon simple
    # décalage de la mise en page (texte venu de pages voisines).
    changed_a, changed_b = {}, {}
    for item in items:
        for page, *_ in item.get("raw_a", ()):
            changed_a[page] = changed_a.get(page, 0) + 1
        for page, *_ in item.get("raw_b", ()):
            changed_b[page] = changed_b.get(page, 0) + 1
    whole_a, whole_b, page_items = set(), set(), []
    for k, (a, b) in enumerate(pairs):
        if a is not None and b is not None:
            continue
        side, index = ("a", a) if b is None else ("b", b)
        info = (infos_a if side == "a" else infos_b)[index]
        changed = (changed_a if side == "a" else changed_b).get(index, 0)
        words = len(info["words"])
        if not text_mode or words == 0 or changed >= COMPARE_NEW_PAGE_SHARE * words:
            (whole_a if side == "a" else whole_b).add(index)
            kind = "page_supprimee" if side == "a" else "page_ajoutee"
            detail = (f"Page {index + 1} de A, absente de B" if side == "a"
                      else f"Page {index + 1} de B, absente de A")
        else:
            kind = "mise_en_page"
            detail = (f"Page {index + 1} de {'A' if side == 'a' else 'B'} sans équivalent dans "
                      f"{'B' if side == 'a' else 'A'} : texte décalé d'une page à l'autre (contenu ajouté ou "
                      "retiré plus haut)")
        rect = info["rect"]
        page_items.append({"kind": kind, "marks_a": [(index, pymupdf.Rect(rect))] if side == "a" else [],
                           "marks_b": [(index, pymupdf.Rect(rect))] if side == "b" else [],
                           "old": "", "new": "", "detail": detail, "page_level": True})
    if whole_a or whole_b:  # le texte d'une page ajoutée ou supprimée n'est pas énuméré mot par mot
        kept = []
        for item in items:
            item["marks_a"] = [mark for mark in item["marks_a"] if mark[0] not in whole_a]
            item["marks_b"] = [mark for mark in item["marks_b"] if mark[0] not in whole_b]
            if item["marks_a"] or item["marks_b"]:
                kept.append(item)
        items = kept
    items.extend(page_items)

    # 4. Comparaison visuelle des pages appariées (35 %).
    if visual_mode:
        compared = [(k, a, b) for k, (a, b) in enumerate(pairs) if a is not None and b is not None]
        for count, (k, a, b) in enumerate(compared):
            page_a, page_b = doc_a[a], doc_b[b]
            ra, rb = page_a.rect, page_b.rect
            if abs(ra.width - rb.width) > 1 or abs(ra.height - rb.height) > 1:
                items.append({"kind": "mise_en_page", "marks_a": [(a, pymupdf.Rect(ra))],
                              "marks_b": [(b, pymupdf.Rect(rb))], "old": "", "new": "", "page_level": True,
                              "detail": f"Format de page différent : {ra.width:.0f} × {ra.height:.0f} pt "
                                        f"→ {rb.width:.0f} × {rb.height:.0f} pt"})
            mask = []
            if text_mode:
                # Les mots changés ou déplacés sont déjà comparés mot à mot : ils sont masqués. Un mot identique resté
                # exactement à sa place, lui, reste comparé à l'image : un changement de couleur, de police, un
                # surlignage ou un tampon posé dessus doivent apparaître.
                words_a, words_b = infos_a[a]["words"], infos_b[b]["words"]
                kept_a = {id(w) for w in unmoved_words(words_a, words_b)}
                kept_b = {id(w) for w in unmoved_words(words_b, words_a)}
                mask = ([w[0] for w in words_a if id(w) not in kept_a]
                        + [w[0] for w in words_b if id(w) not in kept_b])
            fine = options.get("preset") == "plan"
            zones = yield from visual_differences_steps(
                page_a, page_b, options.get("tolerance", 0.1), mask, COMPARE_GAP_FINE if fine else COMPARE_GAP,
                COMPARE_DPI_FINE if fine else COMPARE_DPI, COMPARE_MAX_ZONES_FINE if fine else COMPARE_MAX_ZONES,
                (0.65 + 0.35 * count / max(1, len(compared)), f"Comparaison visuelle : page {count + 1} / {len(compared)}"))
            for zone in zones:
                items.append({"kind": "visuel", "marks_a": [(a, zone & ra)], "marks_b": [(b, zone & rb)],
                              "old": "", "new": "", "detail": visual_detail(zone)})
            yield 0.65 + 0.35 * (count + 1) / max(1, len(compared)), \
                f"Comparaison visuelle : page {count + 1} / {len(compared)}"

    # Ordre de lecture : par couple de pages, puis de haut en bas.
    for item in items:
        item.pop("raw_a", None)
        item.pop("raw_b", None)
        item["page_a"] = item["marks_a"][0][0] if item["marks_a"] else None
        item["page_b"] = item["marks_b"][0][0] if item["marks_b"] else None
        item["pair"] = pair_of_b[item["page_b"]] if item["page_b"] is not None else pair_of_a[item["page_a"]]
        first = (item["marks_b"] or item["marks_a"])[0][1]
        item["order"] = (item["pair"], not item.get("page_level"), first.y0, first.x0)
    items.sort(key=lambda item: item["order"])
    yield 1.0, "Terminé."
    return {"pairs": pairs, "items": items, "notes": notes, "pages_a": n, "pages_b": m,
            "names": ([info["name"] for info in infos_a], [info["name"] for info in infos_b]),
            "text_used": text_mode, "visual_used": visual_mode, "options": dict(options)}


def millimetres(points):
    """Points PDF en millimètres, à la française : 12,3."""
    return f"{points * 25.4 / 72:.1f}".replace(".", ",")


def visual_detail(zone):
    """Description d'un changement visuel : sa taille et sa position, en mm depuis le coin haut gauche de la page."""
    return (f"zone de {millimetres(zone.width)} × {millimetres(zone.height)} mm à x {millimetres(zone.x0)} mm, "
            f"y {millimetres(zone.y0)} mm (image, dessin, couleur ou mise en page)")


def compare_counts(items):
    """Nombre de différences par type, dans l'ordre de COMPARE_KINDS."""
    counts = {}
    for item in items:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {kind: counts[kind] for kind in COMPARE_KINDS if kind in counts}


def compare_summary_text(items):
    """« 3 modifications, 1 ajout… » (vide s'il n'y a aucune différence)."""
    parts = []
    for kind, count in compare_counts(items).items():
        label = COMPARE_KINDS[kind][2] if count > 1 else COMPARE_KINDS[kind][1].lower()
        parts.append(f"{count} {label}")
    return ", ".join(parts)


def compare_description(item):
    """Description d'une différence en une ligne."""
    kind = item["kind"]
    if kind == "modification":
        return f"« {item['old']} » → « {item['new']} »"
    if kind == "ajout":
        return f"« {item['new']} »"
    if kind == "suppression":
        return f"« {item['old']} »"
    return item.get("detail", "")


def pair_title(pair, names=None):
    """Titre d'un couple de pages, précédé du nom de la couche quand il est connu (« B.Cu — page 2 de A ↔ … »)."""
    a, b = pair
    name_a = names[0][a] if names and a is not None and a < len(names[0]) else ""
    name_b = names[1][b] if names and b is not None and b < len(names[1]) else ""
    name = name_a if name_a == name_b or not name_b else name_b if not name_a else f"{name_a} / {name_b}"
    prefix = f"{name} — " if name else ""
    if a is None:
        return f"{prefix}Page {b + 1} de B (sans équivalent dans A)"
    if b is None:
        return f"{prefix}Page {a + 1} de A (sans équivalent dans B)"
    return f"{prefix}Page {a + 1} de A ↔ page {b + 1} de B"


def hex_rgb(color):
    """« #16a34a » → (r, g, b) de 0 à 1, pour PyMuPDF."""
    color = QColor(color)
    return color.redF(), color.greenF(), color.blueF()


FRENCH_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
                 "octobre", "novembre", "décembre")


def report_fonts():
    """Polices du rapport (normale, grasse) : Arial de Windows pour les accents et les symboles, sinon la police
    standard des PDF (Helvetica, limitée aux caractères latins)."""
    for directory in SYSTEM_FONT_DIRS:
        regular, bold = os.path.join(directory, "arial.ttf"), os.path.join(directory, "arialbd.ttf")
        if os.path.isfile(regular) and os.path.isfile(bold):
            return regular, bold
    return None, None


class ReportWriter:
    """Écriture ligne à ligne des pages de synthèse du rapport, avec passage automatique à la page suivante."""

    WIDTH, HEIGHT, MARGIN = 595, 842, 48

    def __init__(self, doc):
        self.doc = doc
        self.regular_file, self.bold_file = report_fonts()
        self.fonts = {False: pymupdf.Font(fontfile=self.regular_file) if self.regular_file else pymupdf.Font("helv"),
                      True: pymupdf.Font(fontfile=self.bold_file) if self.bold_file else pymupdf.Font("hebo")}
        self.page = None
        self.y = 0
        self.inserted = set()  # (page, police) déjà intégrées
        self.new_page()

    def new_page(self):
        self.page = self.doc.new_page(width=self.WIDTH, height=self.HEIGHT)
        self.y = self.MARGIN

    def text(self, page, point, text, size=10, bold=False, color=(0.12, 0.16, 0.23)):
        if self.regular_file:
            name, fontfile = ("rapportg", self.bold_file) if bold else ("rapport", self.regular_file)
            if (page.xref, name) not in self.inserted:
                page.insert_font(fontname=name, fontfile=fontfile)
                self.inserted.add((page.xref, name))
        else:
            name = "hebo" if bold else "helv"
            text = text.replace("→", "->").replace("↔", "<->").encode("cp1252", "replace").decode("cp1252")
        page.insert_text(point, text, fontsize=size, fontname=name, color=color)

    def fit(self, text, width, size=10, bold=False):
        """Texte raccourci (…) pour tenir dans la largeur donnée."""
        font = self.fonts[bold]
        if font.text_length(text, size) <= width:
            return text
        while text and font.text_length(text + "…", size) > width:
            text = text[:-1]
        return text.rstrip() + "…"

    def line(self, text="", size=10, bold=False, color=(0.12, 0.16, 0.23), indent=0, gap=4, swatch=None):
        """Une ligne de texte ; swatch : couleur d'un petit carré dessiné devant."""
        if self.y + size + gap > self.HEIGHT - self.MARGIN:
            self.new_page()
        self.y += size
        x = self.MARGIN + indent
        if swatch is not None:
            self.page.draw_rect(pymupdf.Rect(x, self.y - size * 0.8, x + size * 0.8, self.y), color=None,
                                fill=swatch)
            x += size * 1.3
        if text:
            self.text(self.page, (x, self.y), self.fit(text, self.WIDTH - self.MARGIN - x, size, bold), size, bold,
                      color)
        self.y += gap

    def columns(self, values, positions, size=9, bold=False, color=(0.12, 0.16, 0.23), swatch=None):
        """Une ligne de tableau : values[k] écrit à partir de positions[k] (en points depuis la marge)."""
        if self.y + size + 4 > self.HEIGHT - self.MARGIN:
            self.new_page()
        self.y += size
        limits = list(positions[1:]) + [self.WIDTH - 2 * self.MARGIN]
        for k, (value, x, end) in enumerate(zip(values, positions, limits)):
            if swatch is not None and k == 2:
                self.page.draw_rect(pymupdf.Rect(self.MARGIN + x, self.y - size * 0.8,
                                                 self.MARGIN + x + size * 0.8, self.y), color=None, fill=swatch)
                x += size * 1.2
            self.text(self.page, (self.MARGIN + x, self.y), self.fit(str(value), end - x - 6, size, bold), size,
                      bold, color)
        self.y += 4

    def rule(self):
        self.y += 2
        self.page.draw_line((self.MARGIN, self.y), (self.WIDTH - self.MARGIN, self.y), color=(0.89, 0.91, 0.94),
                            width=0.8)
        self.y += 6


def comparison_report(result, doc_a, doc_b, name_a, name_b):
    """Rapport PDF : synthèse et liste numérotée des différences, puis, pour chaque couple de pages qui diffère,
    la version A à gauche et la version B à droite, surlignées par des annotations (numérotées comme la liste,
    avec la description de la différence)."""
    report = pymupdf.open()
    writer = ReportWriter(report)
    items, pairs, options = result["items"], result["pairs"], result["options"]
    names = result.get("names")
    slate = hex_rgb(SLATE)

    writer.line("Comparaison de deux PDF", size=20, bold=True, gap=8)
    now = time.localtime()
    writer.line(f"Rapport établi le {now.tm_mday} {FRENCH_MONTHS[now.tm_mon - 1]} {now.tm_year} à "
                f"{now.tm_hour} h {now.tm_min:02d} par {APP_NAME}", size=9, color=slate, gap=12)
    writer.line(f"Version A : {name_a} ({result['pages_a']} page{'s' if result['pages_a'] > 1 else ''})", bold=True)
    writer.line(f"Version B : {name_b} ({result['pages_b']} page{'s' if result['pages_b'] > 1 else ''})", bold=True)
    mode = dict(COMPARE_MODES)[options.get("mode", "both")]
    details = [f"comparaison : {mode.lower()}"]
    if options.get("ignore_case"):
        details.append("casse ignorée")
    if options.get("ignore_punctuation"):
        details.append("ponctuation et espaces ignorés")
    if result["visual_used"]:
        details.append(f"tolérance visuelle {round(options.get('tolerance', 0.1) * 100)} %")
        if options.get("preset") == "plan":
            details.append("réglage plan technique (zones fines)")
    writer.line("Options : " + ", ".join(details), size=9, color=slate, gap=6)
    for note in result["notes"]:
        writer.line(note, size=9, color=hex_rgb("#b45309"))
    writer.rule()

    writer.line("Résumé", size=13, bold=True, gap=6)
    if not items:
        writer.line("Aucune différence trouvée : les deux versions sont identiques selon les options choisies.")
    else:
        writer.line(f"{len(items)} différence{'s' if len(items) > 1 else ''} au total", bold=True, gap=6)
        for kind, count in compare_counts(items).items():
            color, label, plural = COMPARE_KINDS[kind]
            writer.line(f"{label if count == 1 else plural.capitalize()} : {count}", indent=8,
                        swatch=hex_rgb(color))
        writer.y += 6
        writer.line("Différences par page", size=13, bold=True, gap=6)
        positions = (0, 210, 262, 314, 366, 418)
        writer.columns(("Pages", "Ajouts", "Suppr.", "Modif.", "Visuel", "Autres"), positions, bold=True,
                       color=slate)
        by_pair = {}
        for item in items:
            by_pair.setdefault(item["pair"], []).append(item)
        for k in sorted(by_pair):
            counts = compare_counts(by_pair[k])
            others = sum(counts.get(kind, 0) for kind in COMPARE_PAGE_KINDS)
            writer.columns([pair_title(pairs[k], names)] + [counts.get(kind, "") or "" for kind in
                                                     ("ajout", "suppression", "modification", "visuel")]
                           + [others or ""], positions)
        writer.y += 6
        writer.line("Liste des différences", size=13, bold=True, gap=4)
        writer.line("Les numéros renvoient aux annotations des pages suivantes (version A à gauche, version B à "
                    "droite), puis aux gros plans de la fin du rapport.", size=9, color=slate, gap=6)
        positions = (0, 26, 96, 200)
        writer.columns(("N°", "Pages", "Type", "Détail"), positions, bold=True, color=slate)
        for number, item in enumerate(items, 1):
            pages = " · ".join(f"{side} {page + 1}" for side, page in (("A", item["page_a"]), ("B", item["page_b"]))
                               if page is not None)
            color, label, _ = COMPARE_KINDS[item["kind"]]
            writer.columns((number, pages, label, compare_description(item)), positions, swatch=hex_rgb(color))

    # Pages annotées : un feuillet par couple de pages qui diffère.
    marks = {}  # (côté, page) -> [(numéro, différence, rect)]
    for number, item in enumerate(items, 1):
        for side in ("a", "b"):
            for page, rect in item["marks_" + side]:
                marks.setdefault((side, page), []).append((number, item, rect))
    margin, header, gap = 24, 46, 24
    for k, (a, b) in enumerate(pairs):
        if (a is None or ("a", a) not in marks) and (b is None or ("b", b) not in marks):
            continue
        rect_a = doc_a[a].rect if a is not None else doc_b[b].rect
        rect_b = doc_b[b].rect if b is not None else doc_a[a].rect
        width = margin * 2 + gap + rect_a.width + rect_b.width
        height = header + margin + max(rect_a.height, rect_b.height)
        sheet = report.new_page(width=width, height=height)
        title = pair_title((a, b), names)
        count = len({id(entry[1]) for side, page in (("a", a), ("b", b)) if page is not None
                     for entry in marks.get((side, page), [])})
        writer.text(sheet, (margin, 22), f"{title} — {count} différence{'s' if count > 1 else ''}", 12, True)
        for side, index, doc, origin, rect, name in (
                ("a", a, doc_a, margin, rect_a, name_a),
                ("b", b, doc_b, margin + rect_a.width + gap, rect_b, name_b)):
            place = pymupdf.Rect(origin, header, origin + rect.width, header + rect.height)
            writer.text(sheet, (origin, header - 8),
                        writer.fit(f"Version {side.upper()} — {name}", rect.width, 9), 9, False, slate)
            if index is None:
                sheet.draw_rect(place, color=(0.8, 0.83, 0.87), fill=(0.97, 0.98, 0.99), dashes="[4] 0", width=1)
                writer.text(sheet, (place.x0 + 16, place.y0 + 30), "Pas de page correspondante", 11, False, slate)
                continue
            sheet.show_pdf_page(place, doc, index)
            sheet.draw_rect(place, color=(0.8, 0.83, 0.87), width=0.6)
            numbered = set()
            for number, item, mark in marks.get((side, index), []):
                target = pymupdf.Rect(mark.x0 + place.x0, mark.y0 + place.y0, mark.x1 + place.x0,
                                      mark.y1 + place.y0)
                color = hex_rgb(COMPARE_KINDS[item["kind"]][0])
                label = COMPARE_KINDS[item["kind"]][1]
                if item["kind"] in COMPARE_TEXT_KINDS:
                    annot = sheet.add_highlight_annot(target)
                    annot.set_colors(stroke=color)
                    opacity = 0.45
                else:
                    annot = sheet.add_rect_annot(target)
                    annot.set_colors(stroke=color)
                    annot.set_border(width=2.5 if item.get("page_level") else 1.5)
                    opacity = 1
                annot.set_info(title=APP_NAME, subject=label,
                               content=f"{number}. {label} : {compare_description(item)}")
                annot.update(opacity=opacity)
                if number not in numbered:
                    numbered.add(number)
                    writer.text(sheet, (target.x0, max(header + 7, target.y0 - 1.5)), str(number), 7, True, color)
    report_details(report, writer, result, doc_a, doc_b)
    if report_fonts()[0]:
        report.subset_fonts()
        fix_space_unicode(report)
    return report


def fix_space_unicode(doc):
    """Arial dessine l'espace et l'espace insécable avec le même glyphe, et MuPDF déclare l'insécable dans la table
    ToUnicode : le texte copié ou cherché dans le rapport aurait des espaces insécables (« Gros plans » introuvable).
    La table des polices du document est corrigée pour annoncer de vraies espaces."""
    for xref in range(1, doc.xref_length()):
        kind, value = doc.xref_get_key(xref, "ToUnicode")
        if kind != "xref":
            continue
        target = int(value.split()[0])
        stream = doc.xref_stream(target)
        if stream and (b"<00A0>" in stream or b"<00a0>" in stream):
            doc.update_stream(target, stream.replace(b"<00A0>", b"<0020>").replace(b"<00a0>", b"<0020>"))


def detail_clip(rect, page_rect):
    """Cadre carré d'un gros plan autour d'une zone : la zone et ses abords (au moins 12 mm de côté), dans la page."""
    side = max(rect.width, rect.height) * 1.5 + 18
    side = min(max(side, 34), max(page_rect.width, page_rect.height))
    center = rect.tl + (rect.br - rect.tl) * 0.5
    clip = pymupdf.Rect(center.x - side / 2, center.y - side / 2, center.x + side / 2, center.y + side / 2)
    # Ramené dans la page sans le réduire, tant qu'il y tient.
    dx = max(page_rect.x0 - clip.x0, 0) - max(clip.x1 - page_rect.x1, 0)
    dy = max(page_rect.y0 - clip.y0, 0) - max(clip.y1 - page_rect.y1, 0)
    return (clip + (dx, dy, dx, dy)) & page_rect


def report_details(report, writer, result, doc_a, doc_b):
    """Gros plans à la fin du rapport : pour chaque différence, la zone et ses abords dans A, dans B et superposés
    (rouge : seulement dans A, vert : seulement dans B), avec sa position en millimètres depuis le coin de la page."""
    items, pairs, names = result["items"], result["pairs"], result.get("names")
    shown = [(number, item) for number, item in enumerate(items, 1) if not item.get("page_level")]
    if not shown:
        return
    slate = hex_rgb(SLATE)
    width, height, margin = writer.WIDTH, writer.HEIGHT, 36
    gap, caption = 10, 30
    panel = (width - 2 * margin - 2 * gap) / 3
    row = caption + panel + 18
    rows_per_page = int((height - 2 * margin - 30) // row)
    sheet, y = None, 0
    for count, (number, item) in enumerate(shown):
        if count == COMPARE_REPORT_DETAILS:
            writer.text(sheet, (margin, min(y + 12, height - margin)),
                        f"Les {len(shown) - count} différences suivantes ne sont pas montrées en gros plan.", 9, False,
                        slate)
            break
        if sheet is None or count % rows_per_page == 0:
            sheet = report.new_page(width=width, height=height)
            writer.text(sheet, (margin, margin), "Gros plans des différences", 14, True)
            writer.text(sheet, (margin, margin + 14), "A : ancienne version · B : nouvelle version · superposition : "
                        "rouge = seulement dans A, vert = seulement dans B, noir = identique", 8, False, slate)
            y = margin + 30
        page_a, page_b = item["page_a"], item["page_b"]
        pair = pairs[item["pair"]]
        page_a = pair[0] if page_a is None else page_a
        page_b = pair[1] if page_b is None else page_b
        marks = item["marks_b"] or item["marks_a"]
        zone = pymupdf.Rect(marks[0][1])
        for _, rect in marks[1:]:
            zone |= rect
        reference = doc_b[page_b] if page_b is not None else doc_a[page_a]
        clip = detail_clip(zone, reference.rect)
        color, label, _ = COMPARE_KINDS[item["kind"]]
        title = pair_title(pair, names).split(" — ")[0] if names and " — " in pair_title(pair, names) else ""
        head = f"{number}. {label}" + (f" · {title}" if title else "") + f" : {compare_description(item)}"
        writer.text(sheet, (margin, y + 10), writer.fit(head, width - 2 * margin, 9.5, True), 9.5, True, hex_rgb(color))
        writer.text(sheet, (margin, y + 22), f"Zone : x {millimetres(zone.x0)} à {millimetres(zone.x1)} mm, "
                    f"y {millimetres(zone.y0)} à {millimetres(zone.y1)} mm, depuis le coin haut gauche de la page (A page "
                    f"{'—' if page_a is None else page_a + 1}, B page {'—' if page_b is None else page_b + 1})", 8,
                    False, slate)
        top = y + caption
        for k, (title_panel, doc, index) in enumerate((("A", doc_a, page_a), ("B", doc_b, page_b),
                                                       ("Superposition", None, None))):
            place = pymupdf.Rect(margin + k * (panel + gap), top, margin + k * (panel + gap) + panel, top + panel)
            writer.text(sheet, (place.x0, place.y1 + 11), title_panel, 8, True, slate)
            scale = min(place.width / clip.width, place.height / clip.height)
            shown_rect = pymupdf.Rect(0, 0, clip.width * scale, clip.height * scale)
            shown_rect += (place.x0 + (place.width - shown_rect.width) / 2, place.y0 + (place.height - shown_rect.height) / 2) * 2
            if doc is None:
                if page_a is None or page_b is None:
                    writer.text(sheet, (place.x0 + 8, place.y0 + 20), "Une seule version", 9, False, slate)
                    continue
                zoom = min(8.0, 2 * place.width / clip.width)
                pix = overlay_pixmap(doc_a[page_a], doc_b[page_b], pymupdf.Matrix(zoom, zoom), clip)
                sheet.insert_image(shown_rect, pixmap=pix)
            elif index is None:
                writer.text(sheet, (place.x0 + 8, place.y0 + 20), "Pas de page correspondante", 9, False, slate)
                continue
            else:
                source = doc[index]
                sheet.show_pdf_page(shown_rect, doc, index, clip=clip * source.derotation_matrix
                                    if source.rotation else clip)
            frame = pymupdf.Rect(shown_rect.x0 + (zone.x0 - clip.x0) * scale, shown_rect.y0 + (zone.y0 - clip.y0) * scale,
                                 shown_rect.x0 + (zone.x1 - clip.x0) * scale, shown_rect.y0 + (zone.y1 - clip.y0) * scale)
            sheet.draw_rect(frame + (-2, -2, 2, 2), color=hex_rgb(color), width=1.2, dashes="[3] 0")
        for k in range(3):  # cadres dessinés en dernier : l'image ou la page ne les recouvre pas
            sheet.draw_rect(pymupdf.Rect(margin + k * (panel + gap), top, margin + k * (panel + gap) + panel, top + panel),
                            color=(0.8, 0.83, 0.87), width=0.6)
        y += row


class ComparePageWidget(QWidget):
    """Une page dans la vue comparée : bandeau (numéro, état), rendu de la page et surlignage des différences."""

    def __init__(self, view, index):
        super().__init__()
        self.view = view
        self.index = index

    def paintEvent(self, event):
        view = self.view
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        state = view.page_states.get(self.index)
        label, color = f"Page {self.index + 1}", QColor(SLATE)
        if view.names.get(self.index):
            label += f"  ·  {view.names[self.index]}"
        if self.index in view.partners and view.partners[self.index] != self.index:
            label += f"  ↔  page {view.partners[self.index] + 1} de {'B' if view.side == 'a' else 'A'}"
        if view.overlay is not None:
            partner = view.overlay_partner(self.index)
            label += (f"  —  superposée à la page {partner + 1} de B" if partner is not None
                      else "  —  sans page correspondante dans B")
        if state is not None:
            label += f"  —  {COMPARE_KINDS[state][1].lower()}"
            color = QColor(COMPARE_KINDS[state][0])
        font = painter.font()
        font.setPointSizeF(9)
        font.setBold(state is not None)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(QRectF(2, 0, self.width() - 4, COMPARE_HEADER - 4),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        top = COMPARE_HEADER
        pixmap = view.page_pixmap(self.index)
        target = QRectF(0, top, self.width(), self.height() - top)
        if pixmap is not None:
            painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        else:
            painter.fillRect(target, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(target.adjusted(0, 0, -1, -1))

        zoom = view.zoom
        for rect, kind, number in view.page_marks(self.index):
            selected = number == view.selected
            color = QColor(COMPARE_KINDS[kind][0])
            area = QRectF(rect.x0 * zoom, top + rect.y0 * zoom, rect.width * zoom, rect.height * zoom)
            if kind in COMPARE_PAGE_KINDS:
                fill = QColor(color)
                fill.setAlpha(28)
                painter.fillRect(area, fill)
                painter.setPen(QPen(color, 5 if selected else 3))
                painter.drawRect(area.adjusted(1.5, 1.5, -1.5, -1.5))
                continue
            area = area.adjusted(-1.5, -1.5, 1.5, 1.5)
            fill = QColor(color)
            fill.setAlpha((150 if selected else 90) if kind in COMPARE_TEXT_KINDS else (45 if selected else 18))
            # Teinte « multipliée » : le texte surligné reste noir et lisible, comme avec un surligneur.
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(area, 2, 2)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, 2 if selected else 1))
            painter.drawRoundedRect(area, 2, 2)
            if selected:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(ACCENT), 1.5, Qt.PenStyle.DashLine))
                painter.drawRoundedRect(area.adjusted(-4, -4, 4, 4), 4, 4)
        painter.end()


class CompareView(QScrollArea):
    """Une des deux versions, pages les unes sous les autres, rendues à la demande (un gros document ne remplit
    pas la mémoire) et surlignées selon les différences trouvées."""

    scrolled = Signal()
    wheel_zoom = Signal(float)

    CACHE = 24  # pages rendues gardées en mémoire

    def __init__(self, side, parent=None):
        super().__init__(parent)
        self.side = side
        self.setObjectName("viewer")
        self.setWidgetResizable(True)
        self.doc = None
        self.zoom = 1.0
        self.widgets = []
        self.cache = {}
        self.marks = {}  # page -> [(Rect, type, numéro de la différence)]
        self.page_states = {}  # page -> type de différence propre à la page entière
        self.partners = {}  # page -> page appariée de l'autre version
        self.names = {}  # page -> nom de la couche (« B.Cu »…), connu après la comparaison
        self.overlay = None  # vue de l'autre version, quand les pages sont superposées
        self.selected = None
        self.container = QWidget()
        self.container.setObjectName("viewer")
        self.layout_ = QVBoxLayout(self.container)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.layout_.setContentsMargins(16, 12, 16, 16)
        self.layout_.setSpacing(16)
        self.setWidget(self.container)
        self.verticalScrollBar().valueChanged.connect(self.scrolled)
        self.horizontalScrollBar().valueChanged.connect(self.scrolled)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if (watched is self.viewport() and event.type() == QEvent.Type.Wheel
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            steps = event.angleDelta().y() / 120
            if steps:
                self.wheel_zoom.emit(1.15 ** steps)
            return True
        return super().eventFilter(watched, event)

    def set_document(self, doc):
        for widget in self.widgets:
            self.layout_.removeWidget(widget)  # retirée tout de suite, sans attendre sa destruction
            widget.hide()
            widget.deleteLater()
        self.widgets, self.cache = [], {}
        self.marks, self.page_states, self.partners, self.selected = {}, {}, {}, None
        self.names = {}
        self.doc = doc
        if doc is not None:
            for index in range(len(doc)):
                widget = ComparePageWidget(self, index)
                self.layout_.addWidget(widget)
                self.widgets.append(widget)
            self._resize_pages()

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.cache = {}
        self._resize_pages()

    def _resize_pages(self):
        if self.doc is None:
            return
        for widget in self.widgets:
            rect = self.doc[widget.index].rect
            widget.setFixedSize(max(1, round(rect.width * self.zoom)),
                                max(1, round(rect.height * self.zoom)) + COMPARE_HEADER)
        self.layout_.activate()
        self.container.resize(self.container.sizeHint().expandedTo(self.viewport().size()))
        self.layout_.activate()

    def set_overlay(self, other):
        """Superpose les pages de l'autre vue (version B) à celles-ci, ou revient aux pages seules (None)."""
        self.overlay = other
        self.cache = {}
        self.refresh()

    def overlay_partner(self, index):
        """Page de B superposée à la page index : celle qui lui est appariée, ou la même avant toute comparaison."""
        other = self.overlay
        if other is None or other.doc is None:
            return None
        if self.partners:
            return self.partners.get(index)
        return index if index < len(other.doc) else None

    def page_marks(self, index):
        """Les différences dessinées sur la page ; superposée, celles de la page de B aussi (texte ajouté…)."""
        marks = list(self.marks.get(index, []))
        partner = self.overlay_partner(index)
        if partner is not None:
            seen = {number for _, _, number in marks}
            marks += [mark for mark in self.overlay.marks.get(partner, []) if mark[2] not in seen]
        return marks

    def page_pixmap(self, index):
        if index in self.cache:
            return self.cache[index]
        if self.doc is None:
            return None
        ratio = self.devicePixelRatioF()
        scale = self.zoom * ratio
        try:
            partner = self.overlay_partner(index)
            if partner is not None:
                pix = overlay_pixmap(self.doc[index], self.overlay.doc[partner], pymupdf.Matrix(scale, scale))
            else:
                pix = self.doc[index].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        except Exception:
            return None
        pixmap = QPixmap.fromImage(to_qimage(pix))
        pixmap.setDevicePixelRatio(ratio)
        if len(self.cache) >= self.CACHE:
            self.cache.pop(next(iter(self.cache)))
        self.cache[index] = pixmap
        return pixmap

    def max_page_width(self):
        return max((self.doc[i].rect.width for i in range(len(self.doc))), default=0) if self.doc else 0

    def position(self):
        """(page en haut de la zone visible, fraction de sa hauteur déjà passée)."""
        if not self.widgets:
            return 0, 0.0
        top = self.verticalScrollBar().value()
        low, high = 0, len(self.widgets) - 1
        while low < high:  # pages de hauteur fixe, rangées dans l'ordre : recherche par dichotomie
            middle = (low + high + 1) // 2
            if self.widgets[middle].y() <= top:
                low = middle
            else:
                high = middle - 1
        widget = self.widgets[low]
        return low, max(0.0, min(1.0, (top - widget.y()) / max(1, widget.height())))

    def scroll_to(self, index, fraction):
        if 0 <= index < len(self.widgets):
            widget = self.widgets[index]
            self.verticalScrollBar().setValue(round(widget.y() + fraction * widget.height()))

    def show_rect(self, index, rect):
        """Fait défiler jusqu'au rectangle (points) de la page, placé au tiers supérieur de la zone visible."""
        if not 0 <= index < len(self.widgets):
            return
        widget = self.widgets[index]
        y = widget.y() + COMPARE_HEADER + rect.y0 * self.zoom
        self.verticalScrollBar().setValue(round(y - self.viewport().height() / 3))
        x0, x1 = widget.x() + rect.x0 * self.zoom, widget.x() + rect.x1 * self.zoom
        bar = self.horizontalScrollBar()
        if x0 < bar.value() or x1 > bar.value() + self.viewport().width():
            bar.setValue(round(x0 - 24))

    def refresh(self):
        for widget in self.widgets:
            widget.update()


class CompareDialog(QDialog):
    """Comparer deux PDF : texte mot à mot, rendu des pages, pages ajoutées ou supprimées ; les deux versions
    côte à côte avec défilement et zoom synchronisés, la liste des différences et l'export d'un rapport PDF.

    current : (contenu PDF, nom) du document ouvert dans l'éditeur, proposé comme version A.
    ask_password(doc, chemin) : demande le mot de passe d'un PDF protégé (None si l'utilisateur abandonne)."""

    def __init__(self, current=None, ask_password=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparer deux PDF")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.ask_password = ask_password
        self.docs = {"a": None, "b": None}
        self.names = {"a": "", "b": ""}
        self.paths = {"a": None, "b": None}
        self.result = None
        self.job = None
        self.order = []  # numéros des différences, dans l'ordre de la liste
        self._syncing = False
        self.fitted = False
        self.timer = QTimer(self)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._step)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addLayout(self._files_row())
        layout.addLayout(self._options_row())
        layout.addWidget(self._progress_row())
        self.notes_label = QLabel()
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet("color: #b45309;")
        self.notes_label.hide()
        layout.addWidget(self.notes_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._differences_panel())
        splitter.addWidget(self._views_panel())
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 1000])
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self.export_button = QPushButton(make_icon("save"), "Exporter le rapport PDF…")
        self.export_button.setIconSize(QSize(18, 18))
        self.export_button.setToolTip("Enregistrer un PDF : synthèse, liste des différences et pages annotées")
        self.export_button.setAutoDefault(False)
        self.export_button.clicked.connect(self.export_report)
        self.export_button.setEnabled(False)
        close_button = QPushButton("Fermer")
        close_button.setAutoDefault(False)
        close_button.clicked.connect(self.reject)
        bottom.addWidget(self.export_button)
        bottom.addStretch()
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

        for key, slot in (("F3", lambda: self.step_difference(1)), ("Shift+F3", lambda: self.step_difference(-1))):
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(slot)
            self.addAction(action)

        screen = self.screen().availableGeometry()
        self.resize(min(1500, screen.width() - 40), min(940, screen.height() - 60))
        if current is not None:
            data, name = current
            self.set_document("a", pymupdf.open("pdf", data), f"{name} (document ouvert)", None)
        self._update_buttons()

    # --- Construction de la fenêtre ---------------------------------------------

    def _files_row(self):
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        self.file_edits = {}
        self.browse_buttons = {}
        for row, (side, label) in enumerate((("a", "Version A (ancienne) :"), ("b", "Version B (nouvelle) :"))):
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setPlaceholderText("Choisissez un PDF…")
            button = QPushButton(make_icon("open"), "Parcourir…")
            button.setIconSize(QSize(18, 18))
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, s=side: self.browse(s))
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(button, row, 2)
            self.file_edits[side] = edit
            self.browse_buttons[side] = button
        self.swap_button = QPushButton(make_icon("replace"), "Inverser")
        self.swap_button.setIconSize(QSize(18, 18))
        self.swap_button.setToolTip("Échanger les versions A et B")
        self.swap_button.setAutoDefault(False)
        self.swap_button.clicked.connect(self.swap)
        grid.addWidget(self.swap_button, 0, 3, 2, 1)
        grid.setColumnStretch(1, 1)
        return grid

    def _options_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel("Réglage :"))
        self.preset_combo = QComboBox()
        for key, label, _ in COMPARE_PRESETS:
            self.preset_combo.addItem(label, key)
        self.preset_combo.setToolTip("Plan technique : tolérance de 5 %, rendu deux fois plus fin et zones plus "
                                     "petites, pour les circuits imprimés et les dessins (un via et la piste voisine "
                                     "restent deux différences). Un peu plus lent.")
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        row.addWidget(self.preset_combo)
        row.addSpacing(6)
        row.addWidget(QLabel("Comparer :"))
        self.mode_combo = QComboBox()
        for key, label in COMPARE_MODES:
            self.mode_combo.addItem(label, key)
        self.mode_combo.setToolTip("Texte : mots ajoutés, supprimés ou modifiés. Visuel : images, dessins, mise en "
                                   "page (et tout le contenu des PDF scannés).")
        self.mode_combo.currentIndexChanged.connect(self._update_buttons)
        row.addWidget(self.mode_combo)
        self.case_box = QCheckBox("Ignorer la casse")
        self.case_box.setToolTip("« Paris » et « PARIS » sont considérés comme identiques")
        self.punctuation_box = QCheckBox("Ignorer la ponctuation et les espaces")
        self.punctuation_box.setToolTip("Seuls les lettres et les chiffres des mots sont comparés. Les écarts "
                                        "d'espacement entre les mots sont toujours ignorés.")
        row.addWidget(self.case_box)
        row.addWidget(self.punctuation_box)
        row.addSpacing(10)
        self.tolerance_label = QLabel("Tolérance visuelle :")
        row.addWidget(self.tolerance_label)
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 60)
        self.tolerance_spin.setValue(10)
        self.tolerance_spin.setSuffix(" %")
        self.tolerance_spin.setToolTip("Écart de teinte toléré entre deux pixels avant de signaler une différence. "
                                       "Augmentez-la pour des PDF scannés (grain, compression).")
        row.addWidget(self.tolerance_spin)
        row.addStretch()
        self.compare_button = QPushButton(make_icon("compare"), "Comparer")
        self.compare_button.setIconSize(QSize(18, 18))
        self.compare_button.setDefault(True)
        set_primary(self.compare_button)
        self.compare_button.clicked.connect(self.start_comparison)
        row.addWidget(self.compare_button)
        return row

    def _progress_row(self):
        self.progress_widget = QWidget()
        row = QHBoxLayout(self.progress_widget)
        row.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("hint")
        self.progress_label.setMinimumWidth(320)
        cancel = QPushButton(make_icon("close"), "Annuler")
        cancel.setIconSize(QSize(16, 16))
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.cancel_comparison)
        row.addWidget(self.progress, 1)
        row.addWidget(self.progress_label)
        row.addWidget(cancel)
        self.progress_widget.hide()
        return self.progress_widget

    def _differences_panel(self):
        panel = QWidget()
        column = QVBoxLayout(panel)
        column.setContentsMargins(0, 0, 6, 0)
        title = QLabel("Différences")
        title.setStyleSheet("font-size: 11pt; font-weight: 600;")
        column.addWidget(title)
        self.summary_label = QLabel("Choisissez les deux versions, puis cliquez sur « Comparer ».")
        self.summary_label.setObjectName("hint")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.summary_label)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.currentItemChanged.connect(self._list_changed)
        column.addWidget(self.list, 1)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton(make_icon("previous"), "Précédente")
        self.previous_button.setToolTip("Différence précédente (Maj+F3)")
        self.previous_button.clicked.connect(lambda: self.step_difference(-1))
        self.next_button = QPushButton(make_icon("next"), "Suivante")
        self.next_button.setToolTip("Différence suivante (F3)")
        self.next_button.clicked.connect(lambda: self.step_difference(1))
        for button in (self.previous_button, self.next_button):
            button.setIconSize(QSize(16, 16))
            button.setAutoDefault(False)
            navigation.addWidget(button)
        column.addLayout(navigation)
        panel.setMinimumWidth(260)
        return panel

    def _views_panel(self):
        panel = QWidget()
        column = QVBoxLayout(panel)
        column.setContentsMargins(6, 0, 0, 0)
        tools = QHBoxLayout()
        for icon, tooltip, slot in (("zoom_out", "Zoom arrière (Ctrl + molette)", lambda: self.zoom_by(0.8)),
                                    ("zoom_in", "Zoom avant (Ctrl + molette)", lambda: self.zoom_by(1.25))):
            button = QPushButton(make_icon(icon), "")
            button.setIconSize(QSize(18, 18))
            button.setToolTip(tooltip)
            button.setAutoDefault(False)
            button.clicked.connect(slot)
            tools.addWidget(button)
            if icon == "zoom_out":
                self.zoom_label = QLabel()
                self.zoom_label.setObjectName("hint")
                self.zoom_label.setMinimumWidth(48)
                self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tools.addWidget(self.zoom_label)
        fit = QPushButton("Ajuster")
        fit.setToolTip("Adapter le zoom à la largeur des pages")
        fit.setAutoDefault(False)
        fit.clicked.connect(self.fit_width)
        tools.addWidget(fit)
        tools.addSpacing(12)
        tools.addWidget(QLabel("Affichage :"))
        self.display_combo = QComboBox()
        self.display_combo.addItem("Côte à côte", "side")
        self.display_combo.addItem("Superposées", "overlay")
        self.display_combo.setToolTip("Superposées : les deux versions en une seule page, ce qui n'est que dans A en "
                                      "rouge, ce qui n'est que dans B en vert, ce qui est commun en noir. Idéal pour "
                                      "les plans et les circuits imprimés.")
        self.display_combo.currentIndexChanged.connect(self._display_changed)
        tools.addWidget(self.display_combo)
        tools.addSpacing(12)
        self.sync_box = QCheckBox("Défilement synchronisé")
        self.sync_box.setChecked(True)
        self.sync_box.setToolTip("Les deux versions défilent ensemble, page appariée en face de page appariée")
        tools.addWidget(self.sync_box)
        tools.addStretch()
        self.legend_side = "  ".join(
            f"<span style='color:{COMPARE_KINDS[kind][0]}; font-size: 12pt;'>■</span> {COMPARE_KINDS[kind][1]}"
            for kind in ("ajout", "suppression", "modification", "visuel"))
        self.legend_overlay = ("<span style='color:#ff0000; font-size: 12pt;'>■</span> seulement dans A  "
                               "<span style='color:#00c000; font-size: 12pt;'>■</span> seulement dans B  "
                               "<span style='color:#000000; font-size: 12pt;'>■</span> identique")
        self.legend = QLabel(self.legend_side)
        self.legend.setObjectName("hint")
        tools.addWidget(self.legend)
        column.addLayout(tools)

        views = QHBoxLayout()
        views.setSpacing(8)
        self.views, self.view_titles, self.view_boxes = {}, {}, {}
        for side in ("a", "b"):
            holder = QWidget()
            box = QVBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(4)
            title = QLabel()
            title.setStyleSheet("font-weight: 600;")
            title.setTextFormat(Qt.TextFormat.PlainText)
            view = CompareView(side)
            view.scrolled.connect(lambda s=side: self._view_scrolled(s))
            view.wheel_zoom.connect(self.zoom_by)
            box.addWidget(title)
            box.addWidget(view, 1)
            views.addWidget(holder, 1)
            self.views[side], self.view_titles[side], self.view_boxes[side] = view, title, holder
        column.addLayout(views, 1)
        self.zoom = 1.0
        self._update_zoom_label()
        return panel

    # --- Documents ----------------------------------------------------------------

    def browse(self, side):
        path, _ = QFileDialog.getOpenFileName(self, f"Choisir la version {side.upper()}", "", "Fichiers PDF (*.pdf)")
        if path:
            self.open_path(side, path)

    def open_path(self, side, path):
        """Ouvre un PDF comme version A ou B (mot de passe demandé s'il est protégé). Renvoie True si c'est fait."""
        try:
            doc = pymupdf.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le PDF :\n{path}\n\n{exc}")
            return False
        if not doc.is_pdf:
            doc.close()
            QMessageBox.critical(self, "Erreur", f"Ce fichier n'est pas un PDF :\n{path}")
            return False
        if doc.needs_pass:
            password = self.ask_password(doc, path) if self.ask_password else None
            if password is None:
                doc.close()
                return False
            doc = unlock(doc, password)
        self.set_document(side, doc, os.path.basename(path), path)
        return True

    def set_document(self, side, doc, name, path):
        self.cancel_comparison()
        if self.docs[side] is not None:
            self.docs[side].close()
        self.docs[side], self.names[side], self.paths[side] = doc, name, path
        self.file_edits[side].setText(path or name)
        self.file_edits[side].setToolTip(path or "Document ouvert dans l'éditeur, avec ses modifications")
        self.views[side].zoom = self.zoom
        self.views[side].set_document(doc)
        self.views["a"].set_overlay(self.views["b"] if self.overlaid() else None)
        self._clear_result()
        self._update_titles()
        self._update_buttons()

    def swap(self):
        self.cancel_comparison()
        for store in (self.docs, self.names, self.paths):
            store["a"], store["b"] = store["b"], store["a"]
        for side in ("a", "b"):
            self.file_edits[side].setText(self.paths[side] or self.names[side])
            self.views[side].zoom = self.zoom
            self.views[side].set_document(self.docs[side])
        self.views["a"].set_overlay(self.views["b"] if self.overlaid() else None)
        self._clear_result()
        self._update_titles()
        self._update_buttons()

    def overlaid(self):
        return self.display_combo.currentData() == "overlay"

    def _display_changed(self):
        """Côte à côte ou superposées. L'endroit regardé est gardé : même page, même hauteur dans la page et même
        point en largeur (centre de la zone visible), et la version B est remise en face au retour au côte à côte."""
        overlay = self.overlaid()
        view_a = self.views["a"]
        anchor = None
        if view_a.doc is not None:
            bar = view_a.horizontalScrollBar()
            anchor = (*view_a.position(), (bar.value() + view_a.viewport().width() / 2) / max(1, view_a.widget().width()))
        self.view_boxes["b"].setVisible(not overlay)
        self.sync_box.setEnabled(not overlay)
        self.legend.setText(self.legend_overlay if overlay else self.legend_side)
        view_a.set_overlay(self.views["b"] if overlay else None)
        self._update_titles()
        if anchor is not None:
            # Après la nouvelle mise en page (largeur des vues changée), pas avant.
            QTimer.singleShot(0, lambda: self._restore_position(anchor))

    def _restore_position(self, anchor):
        index, fraction, center = anchor
        view_a, view_b = self.views["a"], self.views["b"]
        self._syncing = True
        try:
            view_a.scroll_to(index, fraction)
            bar = view_a.horizontalScrollBar()
            bar.setValue(round(center * view_a.widget().width() - view_a.viewport().width() / 2))
            if not self.overlaid() and view_b.doc is not None:
                partner = self._partner_page("a", index)
                if partner is not None:
                    view_b.scroll_to(partner, fraction)
                other = view_b.horizontalScrollBar()
                other.setValue(round(center * view_b.widget().width() - view_b.viewport().width() / 2))
        finally:
            self._syncing = False

    def _update_titles(self):
        for side in ("a", "b"):
            doc = self.docs[side]
            text = f"Version {side.upper()}"
            if doc is not None:
                text += f" — {self.names[side]} ({len(doc)} page{'s' if len(doc) > 1 else ''})"
            if side == "a" and self.overlaid() and self.docs["b"] is not None:
                text = f"Superposition : A — {self.names['a']}  et  B — {self.names['b']}"
            self.view_titles[side].setText(text)
            self.view_titles[side].setToolTip(self.paths[side] or "")
        if not self.fitted and all(doc is not None for doc in self.docs.values()):
            self.fitted = True  # zoom adapté une fois, à l'arrivée des deux versions ; ensuite celui de l'utilisateur
            QTimer.singleShot(0, self.fit_width)

    def _update_buttons(self):
        running = self.job is not None
        ready = all(doc is not None for doc in self.docs.values())
        self.compare_button.setEnabled(ready and not running)
        for button in (*self.browse_buttons.values(), self.swap_button):
            button.setEnabled(not running)
        visual = self.mode_combo.currentData() != "text"
        self.tolerance_spin.setEnabled(visual)
        self.tolerance_label.setEnabled(visual)
        has_result = self.result is not None and not running
        self.export_button.setEnabled(has_result)
        navigable = has_result and bool(self.order)
        self.previous_button.setEnabled(navigable)
        self.next_button.setEnabled(navigable)

    # --- Calcul -------------------------------------------------------------------

    def _preset_changed(self):
        tolerance = {key: value for key, _, value in COMPARE_PRESETS}[self.preset_combo.currentData()]
        self.tolerance_spin.setValue(tolerance)

    def options(self):
        return {"mode": self.mode_combo.currentData(), "ignore_case": self.case_box.isChecked(),
                "ignore_punctuation": self.punctuation_box.isChecked(),
                "tolerance": self.tolerance_spin.value() / 100, "preset": self.preset_combo.currentData()}

    def start_comparison(self):
        if not all(doc is not None for doc in self.docs.values()) or self.job is not None:
            return
        self._clear_result()
        self.job = compare_documents(self.docs["a"], self.docs["b"], self.options())
        self.progress.setValue(0)
        self.progress_label.setText("Comparaison en cours…")
        self.progress_widget.show()
        self.summary_label.setText("Comparaison en cours…")
        self._update_buttons()
        self.timer.start()

    def _step(self):
        """Avance la comparaison pendant COMPARE_TICK secondes, puis rend la main à l'interface."""
        deadline = time.perf_counter() + COMPARE_TICK
        fraction, message = None, None
        try:
            while time.perf_counter() < deadline:
                fraction, message = next(self.job)
        except StopIteration as stop:
            self.timer.stop()
            self.job = None
            self.progress_widget.hide()
            self.show_result(stop.value)
            return
        except Exception as exc:
            self.timer.stop()
            self.job = None
            self.progress_widget.hide()
            self.summary_label.setText("La comparaison a échoué.")
            self._update_buttons()
            QMessageBox.critical(self, "Erreur", f"La comparaison a échoué.\n\n{exc}")
            return
        if fraction is not None:
            self.progress.setValue(round(fraction * 1000))
            self.progress_label.setText(message)

    def cancel_comparison(self):
        if self.job is None:
            return
        self.timer.stop()
        self.job.close()
        self.job = None
        self.progress_widget.hide()
        self.summary_label.setText("Comparaison annulée.")
        self._update_buttons()

    def _clear_result(self):
        self.result = None
        self.order = []
        self.list.clear()
        self.notes_label.hide()
        for view in self.views.values():
            view.marks, view.page_states, view.partners, view.selected = {}, {}, {}, None
            view.names = {}
            view.cache = {}  # superposition : les pages appariées peuvent changer
            view.refresh()
        self.summary_label.setText("Choisissez les deux versions, puis cliquez sur « Comparer »."
                                   if not all(doc is not None for doc in self.docs.values()) else "Cliquez sur « Comparer ».")
        self._update_buttons()

    def show_result(self, result):
        """Affiche les différences : surlignage des deux versions, liste groupée par page et résumé."""
        self.result = result
        items, pairs = result["items"], result["pairs"]
        names = result.get("names")
        for side in ("a", "b"):
            view = self.views[side]
            view.marks, view.page_states, view.partners = {}, {}, {}
            view.names = dict(enumerate(names[0 if side == "a" else 1])) if names else {}
            view.cache = {}
            for a, b in pairs:
                if a is not None and b is not None:
                    view.partners[a if side == "a" else b] = b if side == "a" else a
        for number, item in enumerate(items):
            for side in ("a", "b"):
                for page, rect in item["marks_" + side]:
                    self.views[side].marks.setdefault(page, []).append((rect, item["kind"], number))
                    if item.get("page_level") and item["kind"] != "mise_en_page":
                        self.views[side].page_states[page] = item["kind"]

        self.list.clear()
        self.order = []
        by_pair = {}
        for number, item in enumerate(items):
            by_pair.setdefault(item["pair"], []).append(number)
        for k in sorted(by_pair):
            numbers = by_pair[k]
            header = QListWidgetItem(f"{pair_title(pairs[k], names)}\n"
                                     f"{compare_summary_text([items[n] for n in numbers])}")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            header.setForeground(QColor("#1e293b"))
            header.setBackground(QColor("#f1f5f9"))
            self.list.addItem(header)
            for number in numbers:
                item = items[number]
                color, label, _ = COMPARE_KINDS[item["kind"]]
                entry = QListWidgetItem(self._swatch(color), f"{label} : {compare_description(item)}")
                pages = " · ".join(f"page {page + 1} de {side}" for side, page
                                   in (("A", item["page_a"]), ("B", item["page_b"])) if page is not None)
                entry.setToolTip(f"Différence n° {number + 1} — {pages}")
                entry.setData(Qt.ItemDataRole.UserRole, number)
                self.list.addItem(entry)
                self.order.append(number)

        if items:
            parts = [f"<span style='color:{COMPARE_KINDS[kind][0]};'>■</span>&nbsp;{count}&nbsp;"
                     f"{html.escape(COMPARE_KINDS[kind][2] if count > 1 else COMPARE_KINDS[kind][1].lower())}"
                     for kind, count in compare_counts(items).items()]
            self.summary_label.setText(f"<b style='color:#1e293b;'>{len(items)} différence{'s' if len(items) > 1 else ''}"
                                       f"</b> sur {len(by_pair)} page{'s' if len(by_pair) > 1 else ''} :<br>"
                                       + " · ".join(parts))
        else:
            self.summary_label.setText("<b style='color:#16a34a;'>Aucune différence</b> : les deux versions sont "
                                       "identiques selon les options choisies.")
        self.notes_label.setText("\n".join(result["notes"]))
        self.notes_label.setVisible(bool(result["notes"]))
        for view in self.views.values():
            view.refresh()
        self._update_buttons()
        if self.order:
            self.select(self.order[0])

    @staticmethod
    def _swatch(color):
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(1, 1, 12, 12), 3, 3)
        painter.end()
        return QIcon(pixmap)

    # --- Navigation ---------------------------------------------------------------

    def _list_changed(self, current, _previous):
        if (self.result is not None and current is not None
                and current.data(Qt.ItemDataRole.UserRole) is not None):
            self.select(current.data(Qt.ItemDataRole.UserRole))

    def step_difference(self, step):
        if not self.order:
            return
        current = self.views["a"].selected
        position = self.order.index(current) + step if current in self.order else (0 if step > 0 else -1)
        self.select(self.order[position % len(self.order)])

    def select(self, number):
        """Met en avant une différence et la montre dans les deux versions."""
        item = self.result["items"][number]
        for side in ("a", "b"):
            self.views[side].selected = number
            self.views[side].refresh()
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole) == number:
                if self.list.currentRow() != row:
                    self.list.blockSignals(True)
                    self.list.setCurrentRow(row)
                    self.list.blockSignals(False)
                self.list.scrollToItem(self.list.item(row))
                break
        self._syncing = True
        try:
            for side, other in (("a", "b"), ("b", "a")):
                marks = item["marks_" + side]
                if marks:
                    self.views[side].show_rect(*marks[0])
                elif item["marks_" + other]:
                    # Rien de ce côté (texte ajouté, page supprimée…) : même endroit de la page appariée.
                    page, rect = item["marks_" + other][0]
                    partner = self._partner_page(other, page)
                    if partner is not None:
                        self.views[side].show_rect(partner, rect)
        finally:
            self._syncing = False

    def _partner_page(self, side, index):
        """Page de l'autre version en face de la page index (la plus proche appariée si elle n'a pas d'équivalent)."""
        other = "b" if side == "a" else "a"
        count = len(self.docs[other]) if self.docs[other] is not None else 0
        if not count:
            return None
        if self.result is None:
            return min(index, count - 1)
        partners = self.views[side].partners
        if index in partners:
            return partners[index]
        for distance in range(1, len(self.docs[side]) + 1):
            for candidate in (index - distance, index + distance):
                if candidate in partners:
                    return partners[candidate]
        return min(index, count - 1)

    def _view_scrolled(self, side):
        if self._syncing or not self.sync_box.isChecked():
            return
        other = "b" if side == "a" else "a"
        source, target = self.views[side], self.views[other]
        if source.doc is None or target.doc is None:
            return
        self._syncing = True
        try:
            index, fraction = source.position()
            partner = self._partner_page(side, index)
            if partner is not None:
                target.scroll_to(partner, fraction)
            bar, other_bar = source.horizontalScrollBar(), target.horizontalScrollBar()
            if bar.maximum() > 0 and other_bar.maximum() > 0:
                other_bar.setValue(round(bar.value() / bar.maximum() * other_bar.maximum()))
        finally:
            self._syncing = False

    # --- Zoom ---------------------------------------------------------------------

    def set_zoom(self, zoom):
        zoom = max(0.2, min(5.0, zoom))
        anchor = self.views["a"].position() if self.docs["a"] is not None else None
        self.zoom = zoom
        self._syncing = True
        try:
            for view in self.views.values():
                if view.doc is not None:
                    view.set_zoom(zoom)
            if anchor is not None:
                self.views["a"].scroll_to(*anchor)
        finally:
            self._syncing = False
        if anchor is not None:
            self._view_scrolled("a")
        self._update_zoom_label()

    def zoom_by(self, factor):
        self.set_zoom(self.zoom * factor)

    def fit_width(self):
        shown = [view for side, view in self.views.items() if not (side == "b" and self.overlaid())]
        widths = [view.max_page_width() for view in shown if view.doc is not None]
        if not widths:
            return
        available = min(view.viewport().width() for view in shown) - 40
        self.set_zoom(max(0.2, available / max(widths)))

    def _update_zoom_label(self):
        # Rendu à 72 points par pouce × zoom, sur un écran à 96 pixels par pouce.
        self.zoom_label.setText(f"{round(self.zoom * 72 / 96 * 100)} %")

    # --- Rapport ------------------------------------------------------------------

    def export_report(self):
        if self.result is None:
            return
        stem_a = os.path.splitext(self.names["a"].replace(" (document ouvert)", ""))[0]
        stem_b = os.path.splitext(self.names["b"].replace(" (document ouvert)", ""))[0]
        folder = os.path.dirname(self.paths["b"] or self.paths["a"] or "")
        suggested = os.path.join(folder, f"Comparaison {stem_a} - {stem_b}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le rapport de comparaison", suggested,
                                              "Fichiers PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        if any(p and os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(path))
               for p in self.paths.values()):
            QMessageBox.warning(self, "Exporter le rapport", "Choisissez un autre nom : ce fichier est l'une des "
                                "deux versions comparées.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            report = comparison_report(self.result, self.docs["a"], self.docs["b"], self.names["a"], self.names["b"])
            report.save(path, garbage=3, deflate=True)
            report.close()
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le rapport :\n{path}\n\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        box = QMessageBox(QMessageBox.Icon.Information, "Rapport enregistré",
                          f"Le rapport de comparaison a été enregistré :\n{path}",
                          QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close, self)
        box.button(QMessageBox.StandardButton.Open).setText("Ouvrir le rapport")
        box.button(QMessageBox.StandardButton.Close).setText("Fermer")
        box.exec()
        if box.standardButton(box.clickedButton()) == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # --- Fermeture ----------------------------------------------------------------

    def done(self, result):
        self.cancel_comparison()
        for side in ("a", "b"):
            self.views[side].set_document(None)
            if self.docs[side] is not None:
                self.docs[side].close()
                self.docs[side] = None
        super().done(result)


# --- Reconnaissance de caractères (OCR) ---------------------------------------------------------------------------
#
# Le Tesseract intégré à PyMuPDF lit chaque page rendue en image ; le texte reconnu est posé sur la page en calque
# invisible (mode de rendu 3), mot par mot, à la place de chaque mot de l'image : la page devient cherchable,
# sélectionnable et copiable sans changer d'aspect. Tout se fait sur l'ordinateur, avec les données de langue livrées
# dans le dossier tessdata (modèles « best_int » de Tesseract, licence Apache 2.0).

OCR_DPI = 300  # résolution des pages lues : un texte de 8 points y reste net
OCR_ORIENTATION_DPI = 150  # rendu réduit, pour essayer vite les quatre sens d'une page qui se lit mal
OCR_MAX_PIXELS = 36_000_000  # au-delà (affiche, plan A1…), la résolution baisse pour ménager la mémoire
OCR_MIN_DPI = 100
OCR_LANGUAGES = (("fra", "Français"), ("eng", "Anglais"), ("fra+eng", "Français et anglais"))
OCR_LANGUAGE_NAMES = {"fra": "du français", "eng": "de l'anglais"}  # « les données du français »
# Mise en page automatique (3) : sans elle, Tesseract lit la page comme un seul bloc de texte et saute les tableaux.
OCR_TESSERACT_OPTIONS = "tessedit_pageseg_mode=3"
OCR_FONT = "GlyphLessFont"  # nom usuel de la police des calques OCR (Tesseract, MuPDF, OCRmyPDF…)
OCR_MARKER = "PDFToolkitOCR"  # clé du formulaire (XObject) qui porte le calque : refaire l'OCR le remplace
OCR_XOBJECT = "PTOcr"  # préfixe de son nom dans les ressources de la page
OCR_UPRIGHT_WORDS = 3  # mots courants à partir desquels une page est tenue pour lue à l'endroit…
OCR_UPRIGHT_SHARE = 0.2  # … s'ils font au moins 20 % des mots (voir ocr_common_words)
OCR_EDIT_HINT = ("Texte reconnu par l'OCR : invisible, posé sur l'image du scan pour la recherche et la copie. "
                 "Il ne se modifie pas : le texte réécrit s'afficherait par-dessus l'image.")

# Police sans aucun dessin de Tesseract (572 octets, Apache 2.0, telle que MuPDF l'écrit) : chaque caractère y est un
# blanc d'un demi-cadratin. Avec le codage Identity-H, le code d'un caractère est son numéro Unicode, et la table
# ToUnicode le rend tel quel : toutes les lettres sont couvertes (é è ê à ç œ « » ’ €…), pour la recherche comme
# pour le copier-coller.
OCR_GLYPHLESS_TTF = bytes.fromhex(
    "00010000000a0080000300204f532f3256dec8940000012800000060636d6170000a0034000001900000001e676c796615224124000001b8"
    "00000018686561640b78f165000000ac00000036686865610c020402000000e400000024686d74780400000000000188000000086c6f6361"
    "000c0000000001b0000000066d6178700004000500000108000000206e616d65f2eb16da000001d00000004b706f7374000100010000021c"
    "000000200001000000010000b09471105f0f3cf50407080000000000cf9afc6e00000000d4c3a7f200000000040008000000001000020000"
    "00000000000100000800ffff0000040000000000040000010000000000000000000000000000000200010000000200040001000000000001"
    "0000000000000000000000000000000000030000019000050000000000000000000000000000000000000000000000000500010001000000"
    "000000000000000000000000000000000000474f4f470040000000000001ffff000000010001800000000000000000000000000000010000"
    "000000000400000000000002000100000000001400030000000000140006000a000000000000000000000000000c00000001000000000400"
    "080000030000312111210400fc00080000000003002a0000000300000005001600000001000000000005000b001600030001040900050016"
    "000000560065007200730069006f006e00200031002e003056657273696f6e20312e30000001000000000000000000000000000100000000"
    "000000000000000000000000"
)
OCR_TO_UNICODE = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /Adobe-Identity-UCS def
/CMapType 2 def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
1 beginbfrange
<0000> <FFFF> <0000>
endbfrange
endcmap
CMapName currentdict /CMap defineresource pop
end
end
"""

# Mots courants du français et de l'anglais : une page lue à l'endroit en contient beaucoup, une page lue à l'envers
# ou de travers presque aucun (Tesseract y voit « sadinbo SOA » ou des lettres isolées).
OCR_COMMON_WORDS = frozenset("""
le la les de des du un une et en au aux ce ces cet cette il ils elle elles on nous vous je tu ne pas plus que qui
dont où est sont été être avoir ont fait par pour sur sous dans avec sans chez entre après avant mais ou donc car si
comme tout tous toute toutes son sa ses leur leurs notre nos votre vos mon ma mes se lui moins très bien aussi
the and of to in is it that for on with as was are be by this at from or an not but have has had they we you he she
his her their our your will would can there which who what when all any if no do into than then also more about
""".split())

# Ce que MuPDF écrit pour chaque mot du calque de son PDF « pdfocr » : taille de la ligne (Tf), étirement (Tz),
# déplacement (Td) et mot en Unicode sur 4 chiffres hexadécimaux par caractère (Tj).
OCR_STREAM_TOKENS = re.compile(rb"/F0\s+(-?[\d.]+)\s+Tf|(-?[\d.]+)\s+Tz|(-?[\d.]+)\s+(-?[\d.]+)\s+Td|<([0-9A-Fa-f]*)>\s*Tj")


class OcrError(Exception):
    """Échec de la reconnaissance de texte, avec un message pour l'utilisateur."""


def tessdata_location():
    """(dossier, nom du sous-dossier) des données de langue de Tesseract, livrées avec le programme : à côté de main.py,
    ou dans le dossier où l'exécutable s'extrait (sys._MEIPASS)."""
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__)), "tessdata"


def missing_ocr_languages(language):
    """Langues de « fra+eng » dont le fichier de données manque."""
    base, folder = tessdata_location()
    return [code for code in language.split("+")
            if not os.path.isfile(os.path.join(base, folder, code + ".traineddata"))]


def missing_language_message(codes):
    names = " et ".join(OCR_LANGUAGE_NAMES.get(code, f"de la langue « {code} »") for code in codes)
    base, folder = tessdata_location()
    return (f"Les données de reconnaissance {names} sont introuvables (fichier "
            f"{', '.join(code + '.traineddata' for code in codes)} absent de {os.path.join(base, folder)}). "
            "Réinstallez l'application, ou choisissez une autre langue.")


def parse_pdfocr(content, height):
    """Mots du calque de texte écrit par MuPDF (voir ocr_pixmap) : [(x0, y0, x1, y1, texte, ligne)], en points, y vers
    le bas. Les mots d'une même ligne ont la même ligne de base et la même taille ; ligne les numérote, dans l'ordre de
    lecture de Tesseract (une colonne après l'autre). Le texte vertical, que MuPDF écrit caractère par caractère en
    remontant (déplacement purement vertical vers le haut), est écarté : il ne vient que d'une page lue de travers."""
    words = []
    size = scale = x = y = 0.0
    rising = False
    line, key = -1, None
    for token in OCR_STREAM_TOKENS.finditer(content):
        if token.group(1) is not None:
            size = float(token.group(1))
        elif token.group(2) is not None:
            scale = float(token.group(2))
        elif token.group(3) is not None:
            dx, dy = float(token.group(3)), float(token.group(4))
            x, y = x + dx, y + dy
            rising = dx == 0 and dy > 0
        else:
            codes = token.group(5)
            if (rising and len(codes) == 4) or size <= 0 or scale <= 0 or not codes or len(codes) % 4:
                continue
            text = bytes.fromhex(codes.decode("ascii")).decode("utf-16-be", "replace")
            if (round(y, 2), round(size, 2)) != key:
                key, line = (round(y, 2), round(size, 2)), line + 1
            width = scale * size * (len(codes) // 4) / 200  # un caractère : un demi-cadratin, étiré de scale %
            words.append((x, height - y - size, x + width, height - y, text, line))
    return words


def ocr_pixmap(pix, language):
    """Lit le texte d'une image (Pixmap RVB dont la résolution est fixée) avec le Tesseract intégré à MuPDF.

    MuPDF écrit un PDF de l'image avec son calque de texte (« pdfocr »), dont on relit les mots : renvoie ceux de
    parse_pdfocr, en points de l'image (pixels × 72 / résolution). Une image en niveaux de gris ne convient pas :
    MuPDF 1.28 n'en lit que la première ligne.

    Les données de langue sont désignées par un chemin relatif au dossier courant, le temps de la lecture : Tesseract
    les ouvre avec fopen, qui ne sait pas lire un chemin accentué sous Windows (C:\\Users\\Hélène\\…)."""
    mu = pymupdf.mupdf
    options = mu.FzPdfocrOptions()
    options.compress = 0
    options.language_set2(language)
    base, folder = tessdata_location()
    options.datadir_set2(folder)
    variables = mu.FzOptions(OCR_TESSERACT_OPTIONS)  # à garder jusqu'à la fin : options n'en garde que l'adresse
    options.options = variables.m_internal
    buffer = mu.FzBuffer(pix.stride * pix.height + 65536)
    out = mu.FzOutput(buffer)
    previous = os.getcwd()
    os.chdir(base)
    try:
        mu.fz_write_pixmap_as_pdfocr(out, pix.this, options)
    except Exception as exc:
        if "language" in str(exc).lower():
            raise OcrError(missing_language_message(language.split("+"))) from exc
        raise
    finally:
        os.chdir(previous)
        try:
            out.fz_close_output()
        except Exception:
            pass
    ocr = pymupdf.open("pdf", buffer.fz_buffer_extract())
    try:
        page = ocr[0]
        return parse_pdfocr(page.read_contents(), page.rect.height)
    finally:
        ocr.close()


def ocr_render(page, dpi, rotation=0):
    """Image RVB de la page telle qu'affichée (annotations exclues), tournée en plus de rotation degrés, à environ dpi
    points par pouce (moins pour une très grande page). Renvoie (pixmap, facteur des points de l'image lue par
    ocr_pixmap vers les points de la page)."""
    rect = page.rect
    zoom = dpi / 72
    pixels = rect.width * rect.height * zoom * zoom
    if pixels > OCR_MAX_PIXELS:
        zoom = max(OCR_MIN_DPI / 72, zoom * math.sqrt(OCR_MAX_PIXELS / pixels))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom).prerotate(rotation), alpha=False, annots=False)
    resolution = max(1, round(zoom * 72))
    pix.set_dpi(resolution, resolution)
    return pix, resolution / 72 / zoom


def ocr_lines(words, factor=1.0):
    """Regroupe les mots lus en lignes, dans l'ordre de lecture, et écarte le bruit : traits de tableau lus « | »,
    lignes sans lettre ni chiffre (taches lues « . » ou « - »). Renvoie [(hauteur, ligne de base, [(x0, x1, texte)])],
    en points de la page (factor : voir ocr_render). La ligne de base est le bas de la ligne : le texte du calque
    couvre exactement la ligne de l'image, jambages compris."""
    grouped = {}
    for x0, y0, x1, y1, text, line in words:
        text = text.strip("|¦")
        if text.strip():
            grouped.setdefault(line, []).append((x0 * factor, y0 * factor, x1 * factor, y1 * factor, text))
    lines = []
    for line in grouped.values():
        if not any(ch.isalnum() for word in line for ch in word[4]):
            continue
        line.sort(key=lambda word: word[0])
        top, bottom = min(word[1] for word in line), max(word[3] for word in line)
        lines.append((bottom - top, bottom, [(word[0], word[2], word[4]) for word in line]))
    # Un trait de tableau collé à un mot étire parfois la ligne entière (95 points au lieu de 17) : une ligne plus de
    # deux fois plus haute que la ligne type de la page reprend sa hauteur, sous le même bas de ligne.
    if len(lines) >= 3:
        usual = sorted(height for height, _base, _words in lines)[len(lines) // 2]
        lines = [(usual if height > 2 * usual else height, base, words) for height, base, words in lines]
    return lines


def ocr_common_words(lines):
    """(nombre de mots courants, leur part parmi les mots d'au moins deux lettres) : mots courants du français ou de
    l'anglais. Sur les pages d'essai, une page lue à l'endroit en compte de 25 à 40 % ; lue à l'envers ou de
    travers, quelques-uns par hasard (« ne », « son »), 14 % au plus."""
    count = words_count = 0
    for _height, _base, words in lines:
        for _x0, _x1, text in words:
            for part in re.split(r"[’'\-]", text.lower()):
                part = part.strip(".,;:!?«»“”\"()[]")
                if sum(ch.isalpha() for ch in part) >= 2:
                    words_count += 1
                    count += part in OCR_COMMON_WORDS
    return count, count / max(1, words_count)


def ocr_reads_well(score):
    return score[0] >= OCR_UPRIGHT_WORDS and score[1] >= OCR_UPRIGHT_SHARE


def ocr_page_lines(page, language, rotation=0, dpi=OCR_DPI):
    """Lignes lues sur la page affichée, tournée en plus de rotation degrés, dans les coordonnées de la page ainsi
    tournée (voir ocr_lines)."""
    pix, factor = ocr_render(page, dpi, rotation)
    try:
        words = ocr_pixmap(pix, language)
    finally:
        pix = None
    return ocr_lines(words, factor)


def ocr_text(lines):
    """Le texte lu, ligne par ligne, dans l'ordre de lecture."""
    return "\n".join(" ".join(word[2] for word in words) for _height, _base, words in lines)


def display_to_pdf(page):
    """Matrice des coordonnées de la page affichée (points, origine en haut à gauche, rotation du fichier comprise)
    vers l'espace du PDF : celle de MuPDF, juste même pour une page pivotée dont la MediaBox ne part pas de zéro."""
    mu = pymupdf.mupdf
    ctm = mu.FzMatrix()
    mu.pdf_page_transform(mu.pdf_page_from_fz_page(page.this), mu.FzRect(), ctm)
    return ~pymupdf.Matrix(ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f)


def ocr_number(value):
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def ocr_layer_stream(lines, matrix):
    """Contenu du calque : texte invisible (3 Tr) en police /F0 (ocr_font), ligne par ligne. Chaque mot est posé à sa
    place et étiré (Tz) à sa largeur sur l'image, pour que la sélection tombe juste ; une espace, étirée elle aussi,
    comble l'écart jusqu'au mot suivant, pour que le copier-coller sépare les mots dans toutes les visionneuses.
    Coordonnées des lignes : celles de la page affichée ; matrix les ramène à l'espace du PDF."""
    out = [" ".join(ocr_number(v) for v in matrix) + " cm", "BT", "3 Tr"]
    for height, base, words in lines:
        if height <= 0:
            continue
        out.append(f"/F0 {ocr_number(height)} Tf")
        for k, (x0, x1, text) in enumerate(words):
            units = "".join(ch if ord(ch) < 0x10000 else "\ufffd" for ch in text).encode("utf-16-be")
            count = len(units) // 2
            if not count:
                continue
            scale = max(1.0, 100 * (x1 - x0) / (count * 0.5 * height))
            # Repère de la page affichée (y vers le bas) : la matrice de texte retourne l'axe y.
            out.append(f"{ocr_number(scale)} Tz 1 0 0 -1 {ocr_number(x0)} {ocr_number(base)} Tm "
                       f"<{units.hex().upper()}> Tj")
            if k + 1 < len(words):
                gap = words[k + 1][0] - x1
                out.append(f"{ocr_number(max(1.0, 100 * gap / (0.5 * height)))} Tz <0020> Tj")
    out.append("ET")
    return ("\n".join(out) + "\n").encode("ascii")


def new_pdf_object(doc, source, stream=None):
    xref = doc.get_new_xref()
    doc.update_object(xref, source)
    if stream is not None:
        doc.update_stream(xref, stream)
    return xref


def ocr_font(doc):
    """Ajoute au document la police des calques OCR (Type 0, Identity-H, GlyphLessFont intégrée) ; renvoie son xref."""
    font_file = new_pdf_object(doc, f"<</Length1 {len(OCR_GLYPHLESS_TTF)}>>", OCR_GLYPHLESS_TTF)
    descriptor = new_pdf_object(
        doc, f"<</Type/FontDescriptor/FontName/{OCR_FONT}/Flags 5/FontBBox[0 0 500 1000]/ItalicAngle 0/Ascent 1000"
             f"/Descent -1/CapHeight 1000/StemV 80/FontFile2 {font_file} 0 R>>")
    cid_to_gid = new_pdf_object(doc, "<<>>", b"\x00\x01" * 65536)  # tous les caractères : le glyphe blanc n° 1
    to_unicode = new_pdf_object(doc, "<<>>", OCR_TO_UNICODE)
    descendant = new_pdf_object(
        doc, f"<</Type/Font/Subtype/CIDFontType2/BaseFont/{OCR_FONT}/CIDSystemInfo<</Registry(Adobe)"
             f"/Ordering(Identity)/Supplement 0>>/FontDescriptor {descriptor} 0 R/DW 500"
             f"/CIDToGIDMap {cid_to_gid} 0 R>>")
    return new_pdf_object(doc, f"<</Type/Font/Subtype/Type0/BaseFont/{OCR_FONT}/Encoding/Identity-H"
                               f"/DescendantFonts[{descendant} 0 R]/ToUnicode {to_unicode} 0 R>>")


def ocr_layers(doc, page):
    """Les calques OCR posés par cette application sur la page : [(nom de la ressource, xref)]."""
    return [(name, xref) for xref, name, invoker, _bbox in page.get_xobjects()
            if invoker == 0 and doc.xref_get_key(xref, OCR_MARKER)[0] != "null"]


def inherited_resources(doc, page):
    """Le dictionnaire de ressources que la page hérite de l'arbre des pages (sa source PDF), ou None."""
    node = page.xref
    for _depth in range(32):
        kind, value = doc.xref_get_key(node, "Parent")
        if kind != "xref":
            return None
        node = int(value.split()[0])
        kind, value = doc.xref_get_key(node, "Resources")
        if kind == "xref":
            return doc.xref_object(int(value.split()[0]), compressed=True)
        if kind == "dict":
            return value
    return None


def own_resources(doc, page):
    """Donne à la page un dictionnaire de ressources à elle, copie de celui qu'elle a, partage avec d'autres pages ou
    hérite, avec un dictionnaire XObject direct ; renvoie son xref. Ajouter le calque d'une page ne touche ainsi
    jamais aux ressources d'une autre."""
    kind, value = doc.xref_get_key(page.xref, "Resources")
    if kind == "xref":
        source = doc.xref_object(int(value.split()[0]), compressed=True)
    elif kind == "dict":
        source = value
    else:
        source = inherited_resources(doc, page) or "<<>>"
    resources = new_pdf_object(doc, source)
    kind, value = doc.xref_get_key(resources, "XObject")
    if kind == "xref":
        doc.xref_set_key(resources, "XObject", doc.xref_object(int(value.split()[0]), compressed=True))
    elif kind != "dict":
        doc.xref_set_key(resources, "XObject", "<<>>")
    doc.xref_set_key(page.xref, "Resources", f"{resources} 0 R")
    return resources


def add_ocr_layer(doc, page, xref):
    """Ajoute le formulaire xref aux ressources de la page, sous un nom libre, et le dessine par-dessus tout le contenu
    (dans des flux ajoutés : le contenu existant est isolé entre q et Q)."""
    used = {name for _xref, name, *_rest in page.get_xobjects()}
    number = 1
    while f"{OCR_XOBJECT}{number}" in used:
        number += 1
    name = f"{OCR_XOBJECT}{number}"
    doc.xref_set_key(own_resources(doc, page), f"XObject/{name}", f"{xref} 0 R")
    begin = new_pdf_object(doc, "<<>>", b"q\n")
    end = new_pdf_object(doc, "<<>>", f"Q\nq /{name} Do Q\n".encode("ascii"))
    streams = [begin, *page.get_contents(), end]
    doc.xref_set_key(page.xref, "Contents", "[" + " ".join(f"{x} 0 R" for x in streams) + "]")


def set_ocr_layer(doc, page, lines, font_xref):
    """Pose le calque OCR de la page : un formulaire (XObject) marqué OCR_MARKER, dessiné en dernier. Sur une page déjà
    passée à l'OCR, le calque existant est réécrit : le texte n'est jamais ajouté en double."""
    matrix = display_to_pdf(page)
    box = page.rect * matrix  # la page affichée, dans l'espace du PDF
    source = (f"<</Type/XObject/Subtype/Form/BBox[{ocr_number(box.x0 - 1)} {ocr_number(box.y0 - 1)} "
              f"{ocr_number(box.x1 + 1)} {ocr_number(box.y1 + 1)}]/Resources<</Font<</F0 {font_xref} 0 R>>>>"
              f"/{OCR_MARKER} 1>>")
    stream = ocr_layer_stream(lines, matrix)
    layers = ocr_layers(doc, page)
    if layers:
        _name, xref = layers[0]
        doc.update_object(xref, source)
        doc.update_stream(xref, stream)
        for _other_name, other in layers[1:]:
            doc.update_stream(other, b"")  # calques en trop d'un ancien passage : vidés
    else:
        add_ocr_layer(doc, page, new_pdf_object(doc, source, stream))


def page_has_text(page):
    """La page contient-elle déjà du texte, visible ou non (calque OCR compris) ?"""
    return bool(page.get_text("text").strip())


def ocr_document(doc, pages, language, skip_text=True, straighten=True, before_change=None, result=None):
    """Reconnaît le texte des pages (indices) et le pose en calque invisible sur chacune.

    Générateur : produit (avancement de 0 à 1, message) avant chaque lecture d'image, qui garde la main environ une
    seconde, puis renvoie le bilan result : {"done": pages lues, "skipped": pages qui avaient déjà du texte,
    "empty": pages sans texte reconnu, "rotated": {page: angle}, "failed": {page: raison}, "text": {page: texte}}.
    Il est rempli au fur et à mesure : interrompu (close()), le document reste cohérent, car chaque page n'est modifiée
    qu'à la fin de sa lecture, d'un seul coup ; les pages déjà lues gardent leur texte.

    before_change() est appelé juste avant la première modification du document (push_undo). skip_text : les pages
    qui ont déjà du texte sont laissées telles quelles ; sinon, un calque OCR existant est remplacé. straighten : une
    page qui se lit mal est essayée dans les quatre sens, et redressée (/Rotate) si elle se lit mieux autrement.
    Lève OcrError si les données de langue manquent."""
    if result is None:
        result = {}
    for key in ("done", "skipped", "empty"):
        result.setdefault(key, [])
    for key in ("rotated", "failed", "text"):
        result.setdefault(key, {})
    missing = missing_ocr_languages(language)
    if missing:
        raise OcrError(missing_language_message(missing))
    font = None
    total = max(1, len(pages))
    for k, index in enumerate(pages):
        page = doc[index]
        label = f"Page {index + 1} ({k + 1} sur {len(pages)})"
        if skip_text and page_has_text(page):
            result["skipped"].append(index)
            continue
        yield k / total, f"{label} : lecture du texte…"
        rotation = 0
        try:
            lines = ocr_page_lines(page, language)
            if straighten and not ocr_reads_well(ocr_common_words(lines)):
                # Page qui se lit mal : essayée dans les quatre sens, à plus basse résolution. Un autre sens ne
                # l'emporte que s'il se lit bien, et nettement mieux.
                scores = {}
                for turn in (0, 90, 180, 270):
                    yield (k + 0.4 + turn / 900) / total, f"{label} : recherche du sens de lecture…"
                    scores[turn] = ocr_common_words(ocr_page_lines(page, language, turn, OCR_ORIENTATION_DPI))
                best = max(scores, key=lambda turn: scores[turn][0])
                if best and ocr_reads_well(scores[best]) and scores[best][0] >= 2 * scores[0][0] + 1:
                    yield (k + 0.8) / total, f"{label} : lecture dans le bon sens…"
                    lines = ocr_page_lines(page, language, best)
                    rotation = best
        except OcrError:
            raise
        except MemoryError:
            result["failed"][index] = "mémoire insuffisante"
            continue
        except Exception as exc:
            result["failed"][index] = f"page illisible ({exc})"
            continue
        if not lines:
            result["empty"].append(index)
            continue
        if font is None:
            if before_change is not None:
                before_change()
            font = ocr_font(doc)
        previous_rotation = page.rotation
        try:
            if rotation:
                page.set_rotation((previous_rotation + rotation) % 360)
            set_ocr_layer(doc, page, lines, font)
        except Exception as exc:
            if rotation:
                page.set_rotation(previous_rotation)
            result["failed"][index] = f"calque impossible à écrire ({exc})"
            continue
        if rotation:
            result["rotated"][index] = rotation
        result["done"].append(index)
        result["text"][index] = ocr_text(lines)
    return result


def parse_page_ranges(text, count):
    """« 1-3, 7 » -> [0, 1, 2, 6] (pages de 1 à count). Lève ValueError, avec un message, si la saisie est invalide."""
    pages = set()
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        bounds = re.fullmatch(r"(\d+)\s*(?:[-–]\s*(\d+))?", part)
        if not bounds:
            raise ValueError(f"« {part} » n'est pas un numéro de page ni une plage (exemple : 1-3, 7).")
        first = int(bounds.group(1))
        last = int(bounds.group(2) or first)
        if first > last:
            first, last = last, first
        if first < 1 or last > count:
            raise ValueError(f"Le document a {count} page{'s' if count > 1 else ''} : « {part} » en sort.")
        pages.update(range(first - 1, last))
    if not pages:
        raise ValueError("Indiquez les pages à lire (exemple : 1-3, 7).")
    return sorted(pages)


def ocr_export_text(result):
    """Le texte reconnu, page par page, pour le presse-papiers ou un fichier .txt."""
    return "\n\n".join(f"— Page {index + 1} —\n{result['text'][index]}" for index in sorted(result["text"]))


def ocr_summary(result, cancelled=False):
    """Bilan d'une reconnaissance, en une phrase ou deux."""
    def pages(indices):
        return ", ".join(str(i + 1) for i in sorted(indices))

    done = len(result["done"])
    parts = [f"Texte reconnu sur {done} page{'s' if done > 1 else ''}" if done else "Aucun texte ajouté"]
    if result["rotated"]:
        parts.append(f"redressée{'s' if len(result['rotated']) > 1 else ''} : page{'s' if len(result['rotated']) > 1 else ''} "
                     f"{pages(result['rotated'])}")
    if result["skipped"]:
        parts.append(f"déjà du texte, laissée{'s' if len(result['skipped']) > 1 else ''} telle{'s' if len(result['skipped']) > 1 else ''} : "
                     f"page{'s' if len(result['skipped']) > 1 else ''} {pages(result['skipped'])}")
    if result["empty"]:
        parts.append(f"aucun texte trouvé : page{'s' if len(result['empty']) > 1 else ''} {pages(result['empty'])}")
    message = parts[0] + (" (" + " ; ".join(parts[1:]) + ")" if len(parts) > 1 else "") + "."
    for index, reason in sorted(result["failed"].items()):
        message += f" Page {index + 1} : {reason}."
    if cancelled:
        message = "Reconnaissance interrompue : les pages déjà lues gardent leur texte. " + message
    return message


class OcrDialog(QDialog):
    """Reconnaissance de texte (OCR) du document ouvert : pages, langue et options, puis lecture page par page, avec
    progression et bouton Annuler. Chaque lecture d'image garde la main environ une seconde (PyMuPDF ne rend pas la
    main pendant le calcul) : la fenêtre se met à jour et l'annulation est prise en compte entre deux lectures.

    Le document n'est modifié que par pages entières ; un premier changement appelle editor.push_undo, si bien que
    Ctrl+Z annule toute l'opération d'un coup. Annuler en cours de route garde les pages déjà lues : relancer
    l'OCR, en laissant « Ignorer les pages qui contiennent déjà du texte » coché, reprend où elle s'était arrêtée."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setWindowTitle("Reconnaissance de texte (OCR)")
        self.job = None
        self.result = None
        self.changed = False  # le document a été modifié (au moins une page lue)
        self.timer = QTimer(self)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._step)
        count = len(editor.doc)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        intro = QLabel("Le texte des pages scannées est lu sur l'image, puis posé dessus en calque invisible : le "
                       "document devient cherchable, et son texte sélectionnable et copiable, sans changer d'aspect. "
                       "Tout se fait sur cet ordinateur.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Pages :"), 0, 0)
        self.all_pages = QRadioButton(f"Toutes les pages ({count})")
        self.some_pages = QRadioButton("Seulement les pages :")
        self.pages_edit = QLineEdit(str(editor.current_page() + 1))
        self.pages_edit.setPlaceholderText("exemple : 1-3, 7")
        self.pages_edit.setToolTip("Numéros de pages et plages, séparés par des virgules : 1-3, 7")
        self.pages_edit.textEdited.connect(lambda _text: self.some_pages.setChecked(True))
        (self.all_pages if count > 1 else self.some_pages).setChecked(True)
        some = QHBoxLayout()
        some.addWidget(self.some_pages)
        some.addWidget(self.pages_edit, 1)
        grid.addWidget(self.all_pages, 0, 1)
        grid.addLayout(some, 1, 1)
        grid.addWidget(QLabel("Langue :"), 2, 0)
        self.language_combo = QComboBox()
        for code, label in OCR_LANGUAGES:
            self.language_combo.addItem(label, code)
        self.language_combo.setToolTip("Langue du texte à lire. « Français et anglais » convient à un document "
                                       "mêlant les deux, mais lit un peu moins bien chacune et deux fois moins vite.")
        grid.addWidget(self.language_combo, 2, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.skip_box = QCheckBox("Ignorer les pages qui contiennent déjà du texte")
        self.skip_box.setChecked(True)
        self.skip_box.setToolTip("Décochez pour refaire l'OCR d'une page : le texte reconnu la première fois est "
                                 "remplacé, jamais ajouté en double.")
        self.straighten_box = QCheckBox("Redresser les pages scannées à l'envers ou d'un quart de tour")
        self.straighten_box.setChecked(True)
        self.straighten_box.setToolTip("Une page qui se lit mal est essayée dans les quatre sens, puis pivotée "
                                       "pour s'afficher à l'endroit si elle se lit mieux autrement.")
        layout.addWidget(self.skip_box)
        hint = QLabel("Décochée, une page déjà passée à l'OCR est relue : son ancien texte reconnu est remplacé, "
                      "jamais ajouté en double.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hint.setContentsMargins(24, 0, 0, 0)
        layout.addWidget(hint)
        layout.addWidget(self.straighten_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copier le texte")
        self.copy_button.setToolTip("Copier dans le presse-papiers le texte reconnu, page par page")
        self.copy_button.clicked.connect(self.copy_text)
        self.export_button = QPushButton(make_icon("save"), "Enregistrer en .txt…")
        self.export_button.setIconSize(QSize(18, 18))
        self.export_button.clicked.connect(self.export_text)
        for button in (self.copy_button, self.export_button):
            button.setAutoDefault(False)
            button.hide()
            buttons.addWidget(button)
        buttons.addStretch()
        self.close_button = QPushButton("Fermer")
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.reject)
        self.start_button = QPushButton("Lancer")
        self.start_button.setDefault(True)
        set_primary(self.start_button)
        self.start_button.clicked.connect(self.start)
        buttons.addWidget(self.close_button)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)
        self.setMinimumWidth(560)

    # --- Calcul -------------------------------------------------------------------

    def chosen_pages(self):
        if self.all_pages.isChecked():
            return list(range(len(self.editor.doc)))
        return parse_page_ranges(self.pages_edit.text(), len(self.editor.doc))

    def start(self):
        try:
            pages = self.chosen_pages()
        except ValueError as exc:
            self.status.setText(str(exc))
            self.pages_edit.setFocus()
            return
        language = self.language_combo.currentData()
        missing = missing_ocr_languages(language)
        if missing:
            QMessageBox.critical(self, "Données de langue absentes", missing_language_message(missing))
            return
        self.result = {}
        self.changed = False
        self.job = ocr_document(self.editor.doc, pages, language, self.skip_box.isChecked(),
                                self.straighten_box.isChecked(), self._before_change, self.result)
        for widget in (self.all_pages, self.some_pages, self.pages_edit, self.language_combo, self.skip_box,
                       self.straighten_box, self.start_button, self.copy_button, self.export_button):
            widget.setEnabled(False)
        self.copy_button.hide()
        self.export_button.hide()
        self.close_button.setText("Annuler")
        self.progress.setValue(0)
        self.progress.show()
        self.status.setText("Préparation…")
        QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
        self.timer.start()

    def _before_change(self):
        self.editor.push_undo("reconnaissance de texte (OCR)")
        self.changed = True

    def _step(self):
        """Avance la reconnaissance d'une lecture d'image au plus (environ une seconde), puis rend la main."""
        deadline = time.perf_counter() + COMPARE_TICK
        try:
            while time.perf_counter() < deadline:
                fraction, message = next(self.job)
                self.progress.setValue(round(fraction * 1000))
                self.status.setText(message)
        except StopIteration:
            self._finish(cancelled=False)
        except OcrError as exc:
            self._finish(cancelled=True)
            QMessageBox.critical(self, "Reconnaissance impossible", str(exc))
        except MemoryError:
            self._finish(cancelled=True)
            QMessageBox.critical(self, "Mémoire insuffisante", "La mémoire manque pour lire ces pages. Fermez "
                                 "d'autres applications, ou lisez moins de pages à la fois.")
        except Exception as exc:
            self._finish(cancelled=True)
            QMessageBox.critical(self, "Reconnaissance impossible", f"La reconnaissance de texte a échoué.\n\n{exc}")

    def cancel(self):
        if self.job is None:
            return
        self.job.close()  # entre deux lectures : aucune page n'est à moitié modifiée
        self._finish(cancelled=True)

    def _finish(self, cancelled):
        self.timer.stop()
        self.job = None
        QApplication.restoreOverrideCursor()
        self.progress.hide()
        for widget in (self.all_pages, self.some_pages, self.pages_edit, self.language_combo, self.skip_box,
                       self.straighten_box, self.start_button, self.copy_button, self.export_button):
            widget.setEnabled(True)
        self.close_button.setText("Fermer")
        self.start_button.setText("Relancer")
        has_text = bool(self.result and self.result.get("text"))
        self.copy_button.setVisible(has_text)
        self.export_button.setVisible(has_text)
        if self.result is not None and "done" in self.result:
            summary = ocr_summary(self.result, cancelled)
            if self.changed:
                summary += " Ctrl+Z dans la fenêtre principale annule toute l'opération."
            self.status.setText(summary)
        if self.changed:
            self.editor.ocr_applied(self.result)

    def reject(self):
        if self.job is not None:
            self.cancel()  # « Annuler » pendant la lecture : arrêt, la fenêtre reste ouverte avec le bilan
            return
        super().reject()

    def closeEvent(self, event):
        if self.job is not None:
            self.cancel()
        super().closeEvent(event)

    # --- Texte reconnu ------------------------------------------------------------

    def copy_text(self):
        QApplication.clipboard().setText(ocr_export_text(self.result))
        self.status.setText("Texte reconnu copié dans le presse-papiers.")

    def export_text(self):
        base = os.path.splitext(os.path.basename(self.editor.path))[0] if self.editor.path else "document"
        folder = os.path.dirname(self.editor.path) if self.editor.path else ""
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le texte reconnu",
                                              os.path.join(folder, f"{base} (texte).txt"), "Fichiers texte (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\r\n") as file:
                file.write(ocr_export_text(self.result) + "\n")
        except OSError as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le texte :\n{exc}")
            return
        self.status.setText(f"Texte enregistré dans « {os.path.basename(path)} ».")


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
    ("id_photo", "Photos d'identité",
     "Sélectionnez la zone d'une photo, zoomez, tronquez, redressez, puis obtenez un PDF de photos au bon format, "
     "disposées selon le papier de votre imprimante et imprimées à leur taille exacte. "
     "Une planche enregistrée reste modifiable.",
     "Ctrl+Maj+P · Ctrl+Maj+M"),
    ("compare", "Comparer deux PDF",
     "Voyez côte à côte ce qui a changé entre deux versions d'un document : mots ajoutés, supprimés ou modifiés, "
     "images, pages en plus ou en moins. Exportez un rapport PDF des différences.",
     "Ctrl+Maj+C"),
    ("ocr", "Reconnaissance de texte (OCR)",
     "Rendez un PDF scanné cherchable, et son texte sélectionnable et copiable : le texte lu sur l'image est posé, "
     "invisible, sur chaque page. Tout se fait sur cet ordinateur.",
     "Ctrl+Maj+O"),
]


class WelcomeWidget(QWidget):
    """Écran d'accueil affiché tant qu'aucun document n'est ouvert."""

    def __init__(self, open_callback, merge_callback, id_photo_callback, parent=None):
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
        id_photo_button = QPushButton(make_icon("id_photo"), "Photos d'identité…")
        id_photo_button.clicked.connect(id_photo_callback)
        for button in (merge_button, id_photo_button):
            button.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.15); color: white;"
                " border: 1px solid rgba(255,255,255,0.6); font-weight: 600; }"
                "QPushButton:hover { background: rgba(255,255,255,0.28); }"
            )
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        for button in (open_button, merge_button, id_photo_button):
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
        # Ctrl + molette : zoom autour du point sous la souris. Les crans rapprochés sont cumulés et appliqués
        # d'un coup (chaque zoom redessine toutes les pages).
        self.scroll.viewport().installEventFilter(self)
        self.wheel_zoom = 1.0
        self.wheel_anchor = None
        self.wheel_timer = QTimer(self)
        self.wheel_timer.setSingleShot(True)
        self.wheel_timer.setInterval(80)
        self.wheel_timer.timeout.connect(self._apply_wheel_zoom)

        # Accueil tant qu'aucun document n'est ouvert, puis affichage des pages.
        self.welcome = WelcomeWidget(self.open_dialog, self.merge_dialog, self.id_photo_dialog)
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

        self.id_photo_action = QAction(make_icon("id_photo"), "Photos d'i&dentité…", self)
        self.id_photo_action.setShortcut("Ctrl+Shift+P")
        self.id_photo_action.triggered.connect(self.id_photo_dialog)
        file_menu.addAction(self.id_photo_action)

        self.modify_sheet_action = QAction(make_icon("crop"), "Modifier la planche de p&hotos…", self)
        self.modify_sheet_action.setShortcut("Ctrl+Shift+M")
        self.modify_sheet_action.triggered.connect(self.modify_id_photo_sheet)
        file_menu.addAction(self.modify_sheet_action)

        self.compare_action = QAction(make_icon("compare"), "Co&mparer deux PDF…", self)
        self.compare_action.setShortcut("Ctrl+Shift+C")
        self.compare_action.triggered.connect(self.compare_dialog)
        file_menu.addAction(self.compare_action)

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

        self.ocr_action = QAction(make_icon("ocr"), "Reconnaissance de te&xte (OCR)…", self)
        self.ocr_action.setShortcut("Ctrl+Shift+O")
        self.ocr_action.triggered.connect(self.ocr_dialog)
        edit_menu.addAction(self.ocr_action)

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
            "et suppression des pages, recherche et remplacement, annulation et rétablissement, impression, "
            "photos d'identité, comparaison de deux PDF, reconnaissance de texte (OCR).</p>"
            f"<p style='color:{SLATE};'>Reconnaissance de texte : Tesseract (licence Apache 2.0), intégré à PyMuPDF, "
            "avec ses données de langue française et anglaise.</p>"
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
            [(self.open_action, "Ouvrir"), (self.merge_action, "Concaténer"), (self.id_photo_action, "Identité"),
             (self.modify_sheet_action, "Modifier planche"),  # visible seulement sur une planche
             (self.compare_action, "Comparer"),
             (self.save_action, "Enregistrer"), (self.print_action, "Imprimer"), (self.close_action, "Fermer")],
            [(self.undo_action, "Annuler"), (self.redo_action, "Rétablir")],
            [(self.edit_action, "Éditer le texte"), (self.reorder_action, "Pages"),
             (self.find_action, "Rechercher"), (self.replace_action, "Remplacer"), (self.ocr_action, "OCR")],
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
        self.zoom_in_action.setToolTip("Zoom avant (Ctrl++ ou Ctrl + molette)")
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
        self.modify_sheet_action.setVisible(has_doc and is_id_photo_sheet(self.doc))
        for action in (self.find_action, self.replace_action, self.find_next_action, self.find_previous_action,
                       self.zoom_in_action, self.zoom_out_action, self.goto_action,
                       self.insert_image_action, self.insert_signature_action, self.ocr_action):
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

    def _zoom(self, factor, anchor=None):
        """Change le zoom ; anchor (point de la zone de lecture, Ctrl + molette) : le point du document qui s'y
        trouve y reste après le zoom."""
        if self.doc is None:
            return
        old = self.zoom
        self.zoom = max(0.25, min(6.0, self.zoom * factor))
        if self.zoom == old:
            return
        target = None
        if anchor is not None:  # page sous la souris, et position relative dans cette page
            point = QPoint(self.scroll.horizontalScrollBar().value() + anchor.x(),
                           self.scroll.verticalScrollBar().value() + anchor.y())
            for i, widget in enumerate(self.pages):
                geometry = widget.geometry()
                if point.y() <= geometry.bottom() + self.layout.spacing() or i == len(self.pages) - 1:
                    target = (i, (point.x() - geometry.x()) / max(1, geometry.width()),
                              (point.y() - geometry.y()) / max(1, geometry.height()))
                    break
        for i in range(len(self.pages)):
            self.render_page(i)
        self._update_zoom_label()
        if target is not None:
            self._scroll_to_anchor(target, anchor)

    def _scroll_to_anchor(self, target, anchor):
        index, fx, fy = target
        # Mise en page immédiate à la nouvelle taille (sinon elle n'a lieu qu'au prochain passage de la boucle
        # d'événements, et le défilement resterait limité à l'ancienne longueur).
        self.layout.activate()
        self.container.resize(self.container.sizeHint().expandedTo(self.scroll.viewport().size()))
        self.layout.activate()
        geometry = self.pages[index].geometry()
        self.scroll.horizontalScrollBar().setValue(round(geometry.x() + fx * geometry.width() - anchor.x()))
        self.scroll.verticalScrollBar().setValue(round(geometry.y() + fy * geometry.height() - anchor.y()))

    def eventFilter(self, watched, event):
        if (watched is self.scroll.viewport() and event.type() == QEvent.Type.Wheel
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            steps = event.angleDelta().y() / 120  # un cran = 120 ; un pavé tactile envoie des fractions
            if steps and self.doc is not None:
                self.wheel_zoom *= 1.15 ** steps
                self.wheel_anchor = event.position().toPoint()
                self.wheel_timer.start()
            return True  # Ctrl + molette ne fait jamais défiler
        return super().eventFilter(watched, event)

    def _apply_wheel_zoom(self):
        factor, self.wheel_zoom = self.wheel_zoom, 1.0
        self._zoom(factor, self.wheel_anchor)

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
            widget.ocr_text_clicked.connect(self.explain_ocr_text)
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
        path, _ = QFileDialog.getOpenFileName(self, f"Insérer une {what}", "", IMAGE_FILTER)
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Signature scannée ou photographiée : le fond blanc devient transparent.
            preview, source = load_image(path, transparent_white=signature)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire l'image :\n{path}\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        for widget in self.pages:  # une seule image en cours de placement à la fois
            widget.end_placement(False)

        index = self.current_page()
        widget = self.pages[index]
        page_w, page_h = widget.width() / self.zoom, widget.height() / self.zoom
        # Taille naturelle à 150 ppp, limitée à la moitié de la page (un tiers de sa largeur pour une signature).
        w, h = preview.width() * 72 / 150, preview.height() * 72 / 150
        scale = min(1, page_w * (0.3 if signature else 0.5) / w, page_h * 0.5 / h)
        w, h = w * scale, h * scale
        # Centrée dans la partie visible de la page.
        top = self.scroll.verticalScrollBar().value() - widget.y()
        visible_top = max(0, top)
        visible_bottom = min(widget.height(), top + self.scroll.viewport().height())
        cx, cy = page_w / 2, (visible_top + visible_bottom) / 2 / self.zoom
        rect = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

        self.pending_image = {"source": source, "signature": signature}
        widget.start_placement(preview, rect)
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
        source = dict(pending["source"])
        # rotate : l'image reste droite à l'écran sur une page pivotée, et une photo JPEG prise en hauteur est
        # redressée d'après son EXIF.
        rotate = (page.rotation + source.pop("rotate", 0)) % 360
        self.push_undo(f"insertion d'une {what}")
        try:
            page.insert_image(rect, rotate=rotate, keep_proportion=False, **source)
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
        if span.get("ocr"):
            self.statusBar().showMessage("Cette occurrence fait partie du texte reconnu par l'OCR, invisible sur l'image "
                                         "du scan : elle ne peut pas être remplacée (F3 : occurrence suivante).", 10000)
            return
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
        recognized = sum(1 for _page, span, _start, _end in self.matches if span.get("ocr"))
        count = len(self.matches) - recognized
        if not count:
            self.statusBar().showMessage("Ces occurrences font toutes partie du texte reconnu par l'OCR, invisible sur "
                                         "l'image du scan : elles ne peuvent pas être remplacées.", 10000)
            return

        by_page = {}
        for page_index, span, _, _ in self.matches:
            if span.get("ocr"):
                continue
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
        if recognized:
            message += f" {recognized} occurrence(s) du texte reconnu par l'OCR laissée(s) telle(s) quelle(s)."
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
        actual_size = prints_actual_size(self.doc)
        if actual_size and not self._explain_actual_size():
            return
        if actual_size:  # feuille de photos d'identité : le papier du PDF est proposé d'emblée
            printer.setPageSize(QPageSize(QSizeF(min(first.width, first.height), max(first.width, first.height)),
                                          QPageSize.Unit.Point))
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
        if actual_size:
            if not self._photos_fit(printer, self.doc[indices[0]]):
                return
            # Aucune marge ajoutée à l'impression. Après le contrôle : en pleine page, pageRect() ne donne plus la zone
            # que l'imprimante peut atteindre.
            printer.setFullPage(True)
        if self.print_pages(printer, indices, actual_size):
            scale = " à la taille réelle" if actual_size else ""
            self.statusBar().showMessage(f"{len(indices)} page(s) envoyée(s) à l'imprimante{scale}.", 5000)

    def _explain_actual_size(self):
        """Précise, avant d'imprimer une feuille de photos, comment garder leur taille exacte. False : abandon."""
        box = QMessageBox(
            QMessageBox.Icon.Information,
            "Imprimer les photos d'identité",
            "Les photos seront imprimées à leur taille exacte : aucune marge ajoutée à l'impression, aucune mise à "
            "l'échelle.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            self,
        )
        box.setInformativeText(
            "Dans les propriétés de l'imprimante, choisissez le papier de cette feuille et désactivez tout "
            "agrandissement ou réduction.\n\n"
            "Laissez l'option « Sans marges » (« Borderless ») décochée : elle agrandit l'image et les photos sortiraient "
            "trop grandes. Attention, les préréglages « Photo » de certaines imprimantes la cochent d'eux-mêmes."
        )
        box.button(QMessageBox.StandardButton.Ok).setText("Continuer")
        box.button(QMessageBox.StandardButton.Cancel).setText("Annuler")
        set_primary(box.button(QMessageBox.StandardButton.Ok))
        box.setDefaultButton(QMessageBox.StandardButton.Ok)
        box.exec()
        return box.standardButton(box.clickedButton()) == QMessageBox.StandardButton.Ok

    def _photos_fit(self, printer, page):
        """Les photos d'une page imprimée en taille réelle seront-elles entières ? Sinon, demande quoi faire."""
        paper = printer.paperRect(QPrinter.Unit.Point)
        if not photos_outside_printable(page, paper, printer.pageRect(QPrinter.Unit.Point)):
            return True
        box = QMessageBox(
            QMessageBox.Icon.Warning,
            "Photos coupées à l'impression",
            f"Le papier choisi dans l'imprimante mesure {mm_text(round(paper.width() / POINTS_PER_MM))} × "
            f"{mm_text(round(paper.height() / POINTS_PER_MM))} mm : à leur taille réelle, des photos sortiraient de la "
            "zone qu'elle peut imprimer et seraient coupées.\n\n"
            "Choisissez un papier plus grand, ou refaites la feuille avec une marge plus grande. Imprimer quand même ?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            self,
        )
        box.button(QMessageBox.StandardButton.Ok).setText("Imprimer quand même")
        box.button(QMessageBox.StandardButton.Cancel).setText("Annuler")
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        return box.standardButton(box.clickedButton()) == QMessageBox.StandardButton.Ok

    def print_pages(self, printer, indices, actual_size=False):
        """Imprime les pages : chacune ajustée à la feuille sans déformation, centrée.

        Une page paysage sur une feuille portrait (ou l'inverse) est tournée d'un quart de tour
        pour occuper toute la feuille.

        actual_size : les pages gardent leur taille exacte et sont centrées sur le papier (photos d'identité) ;
        elles ne sont tournées que si elles ne tiennent pas autrement.
        """
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Erreur", "Impossible de démarrer l'impression.")
            return False
        dpi = min(printer.resolution(), PRINT_DPI)
        area = printer.pageRect(QPrinter.Unit.DevicePixel)
        printable_left, printable_top = area.x(), area.y()  # position de la zone imprimable sur le papier
        area = QRectF(0, 0, area.width(), area.height())  # zone imprimable, origine du peintre
        paper = printer.paperRect(QPrinter.Unit.DevicePixel)
        device_per_point = printer.resolution() / 72
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for n, index in enumerate(indices):
                if n:
                    printer.newPage()
                self.statusBar().showMessage(f"Impression de la page {index + 1}…")
                QApplication.processEvents()
                pix = self.doc[index].get_pixmap(dpi=dpi, alpha=False)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                if actual_size:
                    rect = self.doc[index].rect
                    w, h = rect.width * device_per_point, rect.height * device_per_point
                    if quarter_turn_needed(w, h, paper.width(), paper.height(), 2 * device_per_point):
                        image = image.transformed(QTransform().rotate(90))
                        w, h = h, w
                    target = QRectF((paper.width() - w) / 2 - printable_left,
                                    (paper.height() - h) / 2 - printable_top, w, h)
                else:
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
        elif self.modify_sheet_action.isVisible():
            self.statusBar().showMessage("Planche de photos d'identité : « Modifier la planche » (Ctrl+Maj+M) pour "
                                         "changer le recadrage, le format ou la disposition.", 10000)

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

    def id_photo_dialog(self):
        """Prépare une photo d'identité et ouvre la feuille de photos générée comme un nouveau document."""
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une photo", "", IMAGE_FILTER)
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            image = load_photo(path)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire l'image :\n{path}\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        dialog = IdPhotoDialog(image, os.path.basename(path), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sheet = dialog.sheet()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"La génération du PDF a échoué.\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        if not self.maybe_save():
            sheet.close()
            return
        if self.doc is not None:
            self.push_undo("photos d'identité")
            self.doc.close()
        self.doc = sheet
        self.path = None
        self.password = None  # nouveau document : non protégé
        self._set_modified(True)
        self._update_actions()
        self.render_all()
        self.statusBar().showMessage(
            f"Feuille de {len(dialog.positions)} photo(s) générée. Ctrl+P pour l'imprimer à la taille réelle, "
            "Ctrl+S pour l'enregistrer.",
            10000,
        )

    def modify_id_photo_sheet(self):
        """Rouvre la planche ouverte dans la fenêtre des photos d'identité, et la remplace par le résultat.

        L'opération s'annule (Ctrl+Z) ; le document garde son fichier et son mot de passe."""
        if self.doc is None or not is_id_photo_sheet(self.doc):
            return
        if len(self.doc) > 1:
            box = QMessageBox(
                QMessageBox.Icon.Warning,
                "Modifier la planche",
                f"Ce document a {len(self.doc)} pages. La planche mise à jour le remplacera entièrement : les autres "
                "pages seront retirées (Ctrl+Z pour les retrouver).",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                self,
            )
            box.button(QMessageBox.StandardButton.Ok).setText("Continuer")
            box.button(QMessageBox.StandardButton.Cancel).setText("Annuler")
            box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.standardButton(box.clickedButton()) != QMessageBox.StandardButton.Ok:
                return
        name = os.path.basename(self.path) if self.path else "Sans titre"
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            image, settings, complete = read_id_photo_sheet(self.doc)
            dialog = IdPhotoDialog(image, name, self, settings=settings, limited=not complete)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de relire cette planche.\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sheet = dialog.sheet()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"La génération du PDF a échoué.\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.push_undo("modification de la planche")
        self.doc.close()
        self.doc = sheet
        self._set_modified(True)
        self._update_actions()
        self.render_all()
        self.statusBar().showMessage(
            f"Planche mise à jour : {len(dialog.positions)} photo(s). Ctrl+Z pour annuler, Ctrl+S pour enregistrer.",
            10000,
        )

    def ocr_dialog(self):
        """Reconnaissance de texte (OCR) : rend le texte des pages scannées cherchable, sélectionnable et copiable."""
        if self.doc is None:
            return
        for widget in self.pages:  # saisie ou placement d'image en cours : abandonnés
            widget.close_editor()
            widget.end_placement(False)
        OcrDialog(self).exec()

    def ocr_applied(self, result):
        """Après une reconnaissance (terminée ou interrompue) qui a modifié le document : les pages sont redessinées
        (certaines ont pu être redressées) et la recherche en cours tient compte du texte reconnu."""
        self._set_modified(True)
        self._update_actions()
        self.render_all()
        done = len(result["done"])
        self.statusBar().showMessage(f"Texte reconnu sur {done} page{'s' if done > 1 else ''} : il se cherche (Ctrl+F) "
                                     "et se copie. Ctrl+Z pour annuler.", 10000)

    def explain_ocr_text(self, _page_index):
        self.statusBar().showMessage(OCR_EDIT_HINT + " Pour le corriger, refaites l'OCR de la page (Ctrl+Maj+O), "
                                     "« Ignorer les pages qui contiennent déjà du texte » décoché.", 15000)

    def compare_dialog(self):
        """Compare deux PDF ; le document ouvert, avec ses modifications, est proposé comme version A."""
        current = None
        if self.doc is not None:
            current = (self.doc.tobytes(), os.path.basename(self.path) if self.path else "Sans titre")
        dialog = CompareDialog(current, self.ask_password, self)
        dialog.exec()

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


def ocr_command_line(arguments):
    """« --ocr entrée.pdf sortie.pdf [fra|eng|fra+eng] » : reconnaissance du texte de toutes les pages, sans fenêtre,
    avec les réglages par défaut (pages qui ont déjà du texte ignorées, pages tournées redressées). Sert aux essais de
    l'exécutable construit et au traitement par lots. Renvoie le code de sortie : 0 si tout va bien."""
    if len(arguments) not in (2, 3):
        return 2
    source, target = arguments[0], arguments[1]
    language = arguments[2] if len(arguments) == 3 else "fra"
    try:
        doc = pymupdf.open(source)
        for _progress in ocr_document(doc, list(range(len(doc))), language):
            pass
        doc.save(target, garbage=3, deflate=True)
        doc.close()
    except Exception as exc:
        if sys.stderr is not None:  # aucune console pour l'exécutable fenêtré
            sys.stderr.write(f"OCR impossible : {exc}\n")
        return 1
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--ocr":
        sys.exit(ocr_command_line(sys.argv[2:]))
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
