"""Essai du mode édition sur un PDF dont chaque mot est écrit à part, sans caractère d'espace (comme certaines pages
web imprimées en PDF) : une seule zone par ligne, espaces rétablies, colonnes et styles séparés, modification d'un
coup. Le PDF est fabriqué ici, sans aucun document personnel.

    python tests/essai_mots_separes.py

Vérifications explicites (if/raise), comme les autres essais.
"""
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

import pymupdf  # noqa: E402

import main  # noqa: E402

SORTIE = os.path.join(RACINE, "build", "essai-mots")


def verifier(condition, message):
    if not condition:
        raise SystemExit(f"ÉCHEC : {message}")


def mot_par_mot(page, mots, x, y, taille, police="helv"):
    font = pymupdf.Font(police)
    for mot in mots:
        page.insert_text((x, y), mot, fontname=police, fontsize=taille)
        x += font.text_length(mot, taille) + (0 if mot == "fi" else 0.28 * taille)
    return x


def fabriquer():
    doc = pymupdf.open()
    page = doc.new_page()
    mot_par_mot(page, ["Date", "de", "fi", "n", "du", "contrat", ":", "10/12/2024"], 60, 100, 11)
    mot_par_mot(page, ["Nom", "et", "prénom"], 60, 140, 11)
    mot_par_mot(page, ["Date", "de", "naissance"], 360, 140, 11)
    x = mot_par_mot(page, ["Total", ":"], 60, 180, 11)
    mot_par_mot(page, ["450", "EUR"], x, 180, 11, "hebo")
    page.insert_text((60, 220), "Une ligne écrite d'un seul tenant.", fontname="helv", fontsize=11)
    return doc


def textes(page):
    return [s["text"].strip() for s in main.page_spans(page)]


def main_essai():
    os.makedirs(SORTIE, exist_ok=True)
    doc = fabriquer()
    trouves = textes(doc[0])
    attendus = ["Date de fin du contrat : 10/12/2024", "Nom et prénom", "Date de naissance", "Total :", "450 EUR",
                "Une ligne écrite d'un seul tenant."]
    verifier(trouves == attendus, f"zones : {trouves}")
    for span in main.page_spans(doc[0]):
        verifier(len(span["chars"]) == len(span["text"]), f"positions des caractères : {span['text']}")
    print("zones : " + " | ".join(trouves))

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(main.APP_STYLE)
    chemin = os.path.join(SORTIE, "mots-separes.pdf")
    doc.save(chemin)
    editeur = main.PdfEditor()
    editeur.resize(1000, 700)
    editeur.show()
    editeur.open_file(chemin)
    editeur.edit_action.setChecked(True)
    app.processEvents()
    editeur.grab().save(os.path.join(SORTIE, "mode-edition.png"))
    span = next(s for s in editeur.pages[0].spans if s["text"].startswith("Date de fin"))
    editeur.edit_span(0, span, "Date de fin du contrat : 31/12/2025")
    app.processEvents()
    apres = textes(editeur.doc[0])
    verifier("Date de fin du contrat : 31/12/2025" in apres, f"après modification : {apres}")
    verifier(sum(t.startswith("Date de fin") for t in apres) == 1, f"ancien texte restant : {apres}")
    verifier("10/12/2024" not in editeur.doc[0].get_text(), "l'ancienne date est encore là")
    verifier("Date de naissance" in apres and "450 EUR" in apres, f"voisins abîmés : {apres}")
    editeur.grab().save(os.path.join(SORTIE, "apres-modification.png"))
    editeur.search_bar.find_edit.setText("fin du contrat")
    editeur.show_search()
    verifier(len(editeur.matches) == 1, f"recherche « fin du contrat » : {len(editeur.matches)}")
    editeur._set_modified(False)
    editeur.close()
    print(f"Tout est conforme. Captures dans {SORTIE}")


if __name__ == "__main__":
    main_essai()
