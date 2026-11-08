"""Essai de la reconnaissance de texte (OCR), sans document personnel : des « scans » de synthèse sont fabriqués
(texte français connu, accents, guillemets, nombres, tableau ; image en niveaux de gris, bruitée, inclinée, JPEG),
lus, puis vérifiés : précision, recherche, sélection et copie, enregistrement, OCR refaite sans doublon, pages
pivotées ou tournées, ressources partagées, chemin accentué, langue absente, interface.

    python tests/essai_ocr.py                        logique et interface (sans écran), depuis le code source
    python tests/essai_ocr.py --exe "dist/PDF Toolkit 2.exe"
                                                     même lecture par l'exécutable construit (« --ocr »)

Vérifications explicites (if/raise) : l'exécutable est construit avec optimize=2, qui retire les assert.
Les PDF et captures produits vont dans build/essai-ocr/ (non suivi par git).
"""
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

import pymupdf  # noqa: E402

import main  # noqa: E402

SORTIE = os.path.join(RACINE, "build", "essai-ocr")
POLICES = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

PAGE_A = [
    ("Compte rendu du conseil d’école", 16),
    ("Réunion du jeudi 12 février 2026, à 18 h 30, salle des fêtes.", 12),
    ("Présents : Hélène Dupré, François Lefèvre, Noël Bénard, Zoé Mercier.", 12),
    ("La directrice ouvre la séance et rappelle l’ordre du jour.", 12),
    ("« Nous devons préserver la qualité de l’accueil », souligne-t-elle.", 12),
    ("Le cœur du débat porte sur la sortie de fin d’année à Évian.", 12),
    ("Le coût prévu s’élève à 1 245,50 € pour 48 élèves, soit 25,95 € chacun.", 12),
    ("Les parents pourront régler en trois fois ; la mairie verse 300 €.", 12),
]
TABLEAU_A = [
    ["Poste", "Quantité", "Prix unitaire", "Montant"],
    ["Cahiers", "120", "2,50 €", "300,00 €"],
    ["Crayons", "350", "0,80 €", "280,00 €"],
    ["Règles", "45", "1,20 €", "54,00 €"],
]
FIN_A = [("Prochaine réunion : mardi 7 avril 2026. Fin de séance à 20 h 15.", 12)]
PAGE_B = [
    ("Objet : déménagement de l’agence", 14),
    ("Madame, Monsieur,", 12),
    ("Nous avons le plaisir de vous annoncer que notre agence déménage le 3 mars 2026.", 12),
    ("Notre nouvelle adresse : 27, rue de l’Église, 69002 Lyon.", 12),
    ("Vos rendez-vous déjà fixés sont maintenus aux mêmes heures.", 12),
    ("Pour toute question, appelez le 04 78 12 34 56 ou écrivez-nous.", 12),
    ("Veuillez agréer, Madame, Monsieur, nos salutations distinguées.", 12),
    ("Le responsable, Jérôme Côté", 12),
]
PAGE_C = [
    ("Recette : la tarte aux pommes de grand-mère", 15),
    ("Préparation : 25 minutes. Cuisson : 40 minutes à 180 °C.", 12),
    ("Ingrédients pour 6 personnes : 1 pâte brisée, 4 pommes, 80 g de sucre,", 12),
    ("2 œufs, 20 cl de crème fraîche et une pincée de cannelle.", 12),
    ("Épluchez les pommes, coupez-les en lamelles et disposez-les en rosace.", 12),
    ("Battez les œufs avec le sucre et la crème, puis versez sur les fruits.", 12),
    ("« C’est meilleur tiède », disait-elle toujours.", 12),
]
PAGE_D = [
    ("Note de service n° 14", 15),
    ("À compter du lundi 2 mars, l’accueil ouvrira à 8 h 45 au lieu de 9 h.", 12),
    ("Les badges périmés seront échangés au secrétariat, bâtiment B, 2e étage.", 12),
    ("Merci de prévenir vos équipes ; la direction reste à votre écoute.", 12),
]
# Mots accentués à retrouver par la recherche, page par page.
RECHERCHES = {0: ["séance", "cœur", "élèves", "Prix unitaire"], 1: ["déménagement", "Église", "distinguées"],
              2: ["œufs", "crème fraîche", "pincée"], 3: ["périmés", "secrétariat", "écoute"]}

erreurs = []
bilan = []


def verifier(condition, message):
    if not condition:
        erreurs.append(message)
        print("  ÉCHEC :", message)


def texte_attendu(lignes, tableau=None, fin=()):
    out = [t for t, _ in lignes] + [" ".join(rang) for rang in (tableau or [])] + [t for t, _ in fin]
    return "\n".join(out)


def page_propre(doc, lignes, tableau=None, fin=(), police="arial.ttf"):
    page = doc.new_page(width=595, height=842)
    if not os.path.exists(os.path.join(POLICES, police)):  # machine de construction sans cette police
        police = "arial.ttf"
    page.insert_font(fontname="F0", fontfile=os.path.join(POLICES, police))
    y = 90
    for texte, taille in lignes:
        page.insert_text((60, y), texte, fontsize=taille, fontname="F0")
        y += taille * 2
    if tableau:
        y += 10
        colonnes = [60, 190, 300, 420, 535]
        for r, rang in enumerate(tableau):
            for c, cellule in enumerate(rang):
                page.insert_text((colonnes[c] + 8, y + r * 24 + 16), cellule, fontsize=11, fontname="F0")
        for r in range(len(tableau) + 1):
            page.draw_line((colonnes[0], y + r * 24), (colonnes[-1], y + r * 24), width=0.8)
        for x in colonnes:
            page.draw_line((x, y), (x, y + len(tableau) * 24), width=0.8)
        y += len(tableau) * 24 + 34
    for texte, taille in fin:
        page.insert_text((60, y), texte, fontsize=taille, fontname="F0")
        y += taille * 2


def scanner(propre, numero, inclinaison, quart=0, graine=1):
    """Rendu « scanné » d'une page propre : incliné de quelques dixièmes de degré, à 300 ppp, gris, bruité."""
    hasard = random.Random(graine)
    tmp = pymupdf.open()
    page = tmp.new_page(width=595, height=842)
    page.show_pdf_page(page.rect, propre, numero, rotate=inclinaison)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72).prerotate(quart), colorspace=pymupdf.csGRAY)
    tmp.close()
    teinte = bytes(min(238, 18 + round(v * 0.88)) for v in range(256))  # papier gris, encre un peu pâle
    data = bytearray(pix.samples.translate(teinte))
    n, largeur = len(data), pix.width
    for _ in range(int(n * 0.002)):  # piqûres
        data[hasard.randrange(n)] = hasard.randrange(0, 90) if hasard.random() < 0.5 else 255
    for _ in range(int(n * 0.002 / 40)):  # poussières
        i = hasard.randrange(n - 3 * largeur - 3)
        for dy in range(hasard.randrange(2, 4)):
            for dx in range(hasard.randrange(2, 4)):
                data[i + dy * largeur + dx] = hasard.randrange(20, 80)
    return pymupdf.Pixmap(pymupdf.csGRAY, pix.width, pix.height, bytes(data), False)


def page_image(doc, pix, largeur, hauteur, rotation=0):
    page = doc.new_page(width=largeur, height=hauteur)
    page.insert_image(page.rect, stream=pix.tobytes("jpeg", jpg_quality=70))
    if rotation:
        page.set_rotation(rotation)


def fabriquer_scans(chemin):
    """PDF d'essai et texte attendu de chaque page (None : page déjà textuelle)."""
    propre = pymupdf.open()
    page_propre(propre, PAGE_A, TABLEAU_A, FIN_A, "arial.ttf")
    page_propre(propre, PAGE_B, police="times.ttf")
    page_propre(propre, PAGE_C, police="georgia.ttf")
    page_propre(propre, PAGE_D, police="calibri.ttf")
    doc = pymupdf.open()
    page_image(doc, scanner(propre, 0, 0.6, graine=1), 595, 842)  # 1. droite
    page_image(doc, scanner(propre, 1, -0.5, -90, graine=2), 842, 595, rotation=90)  # 2. image de côté, /Rotate 90
    page_image(doc, scanner(propre, 2, 0.4, -90, graine=3), 842, 595)  # 3. quart de tour dans l'image
    page_image(doc, scanner(propre, 3, 0.3, 180, graine=4), 595, 842)  # 4. à l'envers
    doc.insert_pdf(propre, from_page=1, to_page=1)  # 5. vrai texte
    propre.close()
    doc.save(chemin, garbage=3, deflate=True)
    doc.close()
    return [texte_attendu(PAGE_A, TABLEAU_A, FIN_A), texte_attendu(PAGE_B), texte_attendu(PAGE_C),
            texte_attendu(PAGE_D), None]


def levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        courante = [i]
        for j, cb in enumerate(b, 1):
            courante.append(min(precedente[j] + 1, courante[j - 1] + 1, precedente[j - 1] + (ca != cb)))
        precedente = courante
    return precedente[-1]


def taux_erreur(attendu, lu):
    """Taux d'erreur par caractère, espaces et sauts de ligne ramenés à une espace."""
    a, b = re.sub(r"\s+", " ", attendu).strip(), re.sub(r"\s+", " ", lu).strip()
    return levenshtein(a, b) / max(1, len(a))


def encre(page, rect):
    """Part de pixels sombres dans un rectangle rendu par search_for (coordonnées de la page non pivotée) : le mot
    trouvé est-il sur l'encre du mot dans l'image ?"""
    affiche = pymupdf.Rect(rect) * page.rotation_matrix  # get_pixmap découpe dans la page affichée
    pix = page.get_pixmap(dpi=150, clip=affiche, colorspace=pymupdf.csGRAY, annots=False)
    sombres = sum(1 for v in pix.samples if v < 128)
    return sombres / max(1, len(pix.samples))


def empreinte(doc):
    """Ce qui compte d'un document : rotation, texte et calques de chaque page (tobytes() change à chaque appel)."""
    return [(page.rotation, page.get_text(), main.ocr_layers(doc, page)) for page in doc]


def verifier_document(doc, attendus, contexte):
    """Vérifications communes au code source et à l'exécutable, sur le document lu."""
    total_erreurs = total_car = 0
    for numero, attendu in enumerate(attendus):
        page = doc[numero]
        if attendu is None:
            verifier(not main.ocr_layers(doc, page), f"{contexte} : la page {numero + 1}, déjà textuelle, a reçu un calque")
            continue
        texte = page.get_text()
        cer = taux_erreur(attendu, texte)
        a = re.sub(r"\s+", " ", attendu).strip()
        total_erreurs += levenshtein(a, re.sub(r"\s+", " ", texte).strip())
        total_car += len(a)
        bilan.append(f"{contexte} — page {numero + 1} (rotation {page.rotation}°) : {cer:.1%} d'erreurs par caractère")
        verifier(cer < 0.06, f"{contexte} : page {numero + 1}, {cer:.1%} d'erreurs (6 % au plus attendus)")
        verifier(len(main.ocr_layers(doc, page)) == 1, f"{contexte} : page {numero + 1} sans calque OCR unique")
        for mot in RECHERCHES[numero]:
            trouves = page.search_for(mot)
            verifier(bool(trouves), f"{contexte} : « {mot} » introuvable page {numero + 1}")
            for rect in trouves[:1]:
                # Le mot trouvé est bien sur l'encre du mot dans l'image (coordonnées justes, même page pivotée).
                verifier(encre(page, rect) > 0.04, f"{contexte} : « {mot} » trouvé hors du texte de l'image, page {numero + 1}")
                # Sélection et copie : le texte du rectangle est bien le mot.
                copie = page.get_textbox(rect).strip()
                verifier(mot.lower() in copie.lower(), f"{contexte} : sélection de « {mot} » → « {copie} »")
    verifier(doc[1].rotation == 90, f"{contexte} : la page pivotée (2) a changé de rotation ({doc[1].rotation}°)")
    verifier(doc[2].rotation == 90, f"{contexte} : la page tournée d'un quart de tour (3) n'est pas redressée")
    verifier(doc[3].rotation == 180, f"{contexte} : la page à l'envers (4) n'est pas redressée")
    texte = doc[0].get_text()
    for signe in ("€", "«", "»", "œ", "é", "è", "ê", "à", "ç"):
        verifier(signe in texte or signe in doc[2].get_text() + doc[1].get_text(), f"{contexte} : « {signe} » jamais lu")
    return total_erreurs / max(1, total_car)


def essai_source(attendus, chemin):
    print("— Logique, depuis le code source")
    doc = pymupdf.open(chemin)
    taille_avant = os.path.getsize(chemin)
    resultat = {}
    changements = []
    debut = time.perf_counter()
    etapes = list(main.ocr_document(doc, list(range(len(doc))), "fra", True, True,
                                    lambda: changements.append(1), resultat))
    duree = time.perf_counter() - debut
    verifier(len(changements) == 1, "before_change doit être appelé une seule fois")
    verifier(resultat["done"] == [0, 1, 2, 3], f"pages lues : {resultat['done']}")
    verifier(resultat["skipped"] == [4], f"pages ignorées : {resultat['skipped']}")
    verifier(resultat["rotated"] == {2: 90, 3: 180}, f"pages redressées : {resultat['rotated']}")
    verifier(not resultat["failed"], f"échecs : {resultat['failed']}")
    verifier(all(0 <= f <= 1 for f, _m in etapes), "avancement hors de 0..1")
    cer = verifier_document(doc, attendus, "source")
    bilan.append(f"source — 4 pages scannées lues en {duree:.1f} s ({duree / 4:.2f} s par page, recherche du sens "
                 f"comprise pour 2 pages) ; erreurs par caractère sur l'ensemble : {cer:.2%}")

    # Temps d'une page droite seule.
    seule = pymupdf.open(chemin)
    debut = time.perf_counter()
    list(main.ocr_document(seule, [0], "fra"))
    bilan.append(f"source — page droite seule : {time.perf_counter() - debut:.2f} s")
    debut = time.perf_counter()
    list(main.ocr_document(pymupdf.open(chemin), [0], "fra+eng"))
    bilan.append(f"source — page droite seule, français et anglais : {time.perf_counter() - debut:.2f} s")
    seule.close()

    # Enregistrement : le calque est gardé ; augmentation de taille.
    enregistre = os.path.join(SORTIE, "scans-ocr.pdf")
    doc.save(enregistre, garbage=3, deflate=True)
    taille_apres = os.path.getsize(enregistre)
    bilan.append(f"source — taille : {taille_avant / 1024:.0f} Ko → {taille_apres / 1024:.0f} Ko "
                 f"(+{(taille_apres - taille_avant) / 1024:.1f} Ko pour 4 pages)")
    relu = pymupdf.open(enregistre)
    verifier(relu[0].get_text() == doc[0].get_text(), "le texte relu après enregistrement diffère")
    verifier_document(relu, attendus, "relu")

    # Refaire l'OCR, pages avec texte comprises : jamais de doublon.
    avant = [relu[i].get_text().count("séance") for i in range(1)]
    resultat2 = {}
    list(main.ocr_document(relu, list(range(4)), "fra", False, True, None, resultat2))
    verifier(resultat2["done"] == [0, 1, 2, 3], f"OCR refaite : pages lues {resultat2['done']}")
    verifier(not resultat2["rotated"], f"OCR refaite : pages redressées une deuxième fois {resultat2['rotated']}")
    for i in range(4):
        verifier(len(main.ocr_layers(relu, relu[i])) == 1, f"OCR refaite : page {i + 1} a plusieurs calques")
    apres = [relu[i].get_text().count("séance") for i in range(1)]
    verifier(avant == apres and apres[0] == 2, f"OCR refaite : « séance » {avant} → {apres} (texte en double ?)")
    # Ignorer les pages qui ont déjà du texte : rien ne bouge.
    resultat3 = {}
    avant = empreinte(relu)
    list(main.ocr_document(relu, list(range(5)), "fra", True, True, None, resultat3))
    verifier(resultat3["skipped"] == [0, 1, 2, 3, 4] and empreinte(relu) == avant, "pages déjà lues retouchées")
    relu.close()
    doc.close()


def essai_structures():
    """Ressources partagées ou héritées, page pivotée à MediaBox décalée, chemin accentué, langue absente."""
    print("— Structures de PDF et données de langue")
    source = pymupdf.open(os.path.join(SORTIE, "scans.pdf"))
    # Deux pages identiques qui partagent le même dictionnaire de ressources (objet indirect).
    doc = pymupdf.open()
    doc.insert_pdf(source, from_page=0, to_page=0)
    doc.insert_pdf(source, from_page=0, to_page=0)
    partage = doc.xref_get_key(doc[0].xref, "Resources")
    if partage[0] != "xref":
        partage = ("xref", f"{main.new_pdf_object(doc, partage[1])} 0 R")
    for page in doc:
        doc.xref_set_key(page.xref, "Resources", partage[1])
    image0 = doc[0].get_images()[0][0]
    list(main.ocr_document(doc, [0], "fra"))
    verifier(not main.ocr_layers(doc, doc[1]), "ressources partagées : le calque de la page 1 apparaît sur la page 2")
    list(main.ocr_document(doc, [1], "fra", skip_text=False))
    verifier(len(main.ocr_layers(doc, doc[0])) == 1 and len(main.ocr_layers(doc, doc[1])) == 1,
             "ressources partagées : un calque par page attendu")
    verifier(doc[0].get_images()[0][0] == image0, "ressources partagées : image de la page 1 perdue")
    doc.close()

    # Ressources héritées de l'arbre des pages, MediaBox décalée et /Rotate 270.
    doc = pymupdf.open()
    doc.insert_pdf(source, from_page=0, to_page=0)
    page = doc[0]
    ressources = doc.xref_get_key(page.xref, "Resources")
    racine = doc.xref_get_key(doc.pdf_catalog(), "Pages")[1].split()[0]
    doc.xref_set_key(int(racine), "Resources", ressources[1])
    doc.xref_set_key(page.xref, "Resources", "null")
    doc.xref_set_key(page.xref, "MediaBox", "[100 50 695 892]")
    contenu = page.get_contents()[0]
    doc.update_stream(contenu, b"q 1 0 0 1 100 50 cm\n" + doc.xref_stream(contenu) + b"\nQ")
    page.set_rotation(270)
    resultat = {}
    list(main.ocr_document(doc, [0], "fra", True, True, None, resultat))
    page = doc[0]
    verifier(resultat["done"] == [0], f"ressources héritées : page non lue ({resultat})")
    verifier(page.rotation == 0, f"page /Rotate 270 : redressement attendu à 0°, obtenu {page.rotation}°")
    trouves = page.search_for("séance")
    verifier(bool(trouves) and encre(page, trouves[0]) > 0.04, "MediaBox décalée : « séance » mal placé")
    doc.close()

    # Données de langue dans un dossier au chemin accentué (comme C:\Users\Hélène\…), puis absentes.
    base = tempfile.mkdtemp(prefix="essai-ocr-")
    accentue = os.path.join(base, "Données Hélène")
    shutil.copytree(os.path.join(RACINE, "tessdata"), os.path.join(accentue, "tessdata"))
    ancien = getattr(sys, "_MEIPASS", None)
    try:
        sys._MEIPASS = accentue
        doc = pymupdf.open(os.path.join(SORTIE, "scans.pdf"))
        resultat = {}
        list(main.ocr_document(doc, [0], "fra", True, True, None, resultat))
        verifier(resultat["done"] == [0], f"chemin accentué : lecture impossible ({resultat.get('failed')})")
        sys._MEIPASS = base  # aucun dossier tessdata
        try:
            list(main.ocr_document(doc, [1], "eng"))
            verifier(False, "langue absente : OcrError attendue")
        except main.OcrError as exc:
            verifier("de l'anglais" in str(exc) and "eng.traineddata" in str(exc), f"message de langue absente : {exc}")
            bilan.append(f"langue absente : « {exc} »")
        doc.close()
    finally:
        if ancien is None:
            del sys._MEIPASS
        else:
            sys._MEIPASS = ancien
        shutil.rmtree(base, ignore_errors=True)
    source.close()


def essai_interface(chemin):
    """La fenêtre OCR dans l'application, sans écran : bilan, recherche, mode édition, remplacement, annulation."""
    print("— Interface (sans écran)")
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(main.APP_STYLE)
    editeur = main.PdfEditor()
    editeur.resize(1280, 900)
    editeur.show()
    editeur.open_file(chemin)
    app.processEvents()
    fenetre = main.OcrDialog(editeur)
    fenetre.show()
    app.processEvents()
    fenetre.grab().save(os.path.join(SORTIE, "fenetre-ocr.png"))
    fenetre.start()
    capture = False
    while fenetre.job is not None:
        app.processEvents()
        if not capture and "Page 2" in fenetre.status.text():
            fenetre.grab().save(os.path.join(SORTIE, "fenetre-ocr-progression.png"))
            capture = True
        time.sleep(0.005)
    fenetre.grab().save(os.path.join(SORTIE, "fenetre-ocr-bilan.png"))
    verifier("Texte reconnu sur 4 pages" in fenetre.status.text(), f"bilan : {fenetre.status.text()}")
    verifier(fenetre.copy_button.isVisible() and fenetre.export_button.isVisible(), "boutons Copier / Enregistrer absents")
    fenetre.copy_text()
    copie = QApplication.clipboard().text()
    verifier(copie.startswith("— Page 1 —") and "séance" in copie and "œufs" in copie, "texte copié incomplet")
    verifier([label for label, *_ in editeur.undo_stack] == ["reconnaissance de texte (OCR)"], "une seule annulation attendue")

    # « Voir le résultat… » : texte reconnu page par page, recherche sans accents ni majuscules, puis le mot montré
    # dans le document.
    verifier(fenetre.view_button.isVisible(), "bouton « Voir le résultat… » absent")
    fenetre.show_result()
    app.processEvents()
    resultat = next(w for w in QApplication.topLevelWidgets() if isinstance(w, main.OcrResultDialog))
    verifier(resultat.isVisible() and not fenetre.isVisible(), "fenêtre du résultat non ouverte")
    verifier(resultat.view.toPlainText() == copie, "le résultat ne montre pas le texte reconnu")
    resultat.find_edit.setText("SEANCE")
    app.processEvents()
    verifier(len(resultat.matches) == 2, f"résultat, « SEANCE » : {len(resultat.matches)} occurrence(s)")
    verifier(resultat.count_label.text() == "1 sur 2 · page 1", f"compteur : {resultat.count_label.text()}")
    from PySide6.QtGui import QKeyEvent
    for modificateur, attendu in ((Qt.KeyboardModifier.NoModifier, 1), (Qt.KeyboardModifier.ShiftModifier, 0)):
        QApplication.sendEvent(resultat.find_edit, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, modificateur))
        verifier(resultat.current == attendu, f"Entrée / Maj+Entrée : occurrence {resultat.current}")
    resultat.find_edit.setText("page")
    verifier(not resultat.matches, "les titres « — Page N — » ne doivent pas compter")
    resultat.find_edit.setText("Lyon")
    page_lyon = resultat.page_of(resultat.matches[0][0]) if resultat.matches else -1
    verifier(page_lyon > 0, f"« Lyon » : page {page_lyon + 1}")
    resultat.find_edit.setText("seance")
    resultat.step(1)
    app.processEvents()
    resultat.grab().save(os.path.join(SORTIE, "fenetre-resultat.png"))
    resultat.show_in_document()
    app.processEvents()
    verifier(not editeur.search_bar.isHidden() and len(editeur.matches) == 2 and editeur.match_index == 1,
             f"« Montrer dans le document » : {len(editeur.matches)} occurrence(s), n° {editeur.match_index}")
    editeur.grab().save(os.path.join(SORTIE, "resultat-dans-document.png"))
    resultat.find_edit.setText("Lyon")
    resultat.show_in_document()
    verifier(editeur.matches and editeur.matches[editeur.match_index][0] == page_lyon, "« Lyon » : mauvaise page")
    resultat.close()
    app.processEvents()
    editeur.search_bar.close_bar()
    fenetre.close()

    editeur.show_search()
    editeur.search_bar.find_edit.setText("crème fraîche")
    editeur.update_search(reset=True, scroll=True)
    verifier(len(editeur.matches) == 1, f"recherche « crème fraîche » : {len(editeur.matches)} occurrence(s)")
    editeur.search_bar.find_edit.setText("séance")
    editeur.update_search(reset=True, scroll=True)
    verifier(len(editeur.matches) == 2, f"recherche « séance » : {len(editeur.matches)} occurrence(s)")
    app.processEvents()
    editeur.grab().save(os.path.join(SORTIE, "recherche.png"))
    editeur.search_bar.replace_edit.setText("réunion")
    avant = empreinte(editeur.doc)
    editeur.replace_all()
    verifier(empreinte(editeur.doc) == avant and len(editeur.undo_stack) == 1, "« Tout remplacer » a modifié le texte OCR")

    editeur.edit_action.setChecked(True)
    app.processEvents()
    page = editeur.pages[0]
    morceau = next(s for s in page.spans if s["ocr"])
    centre = page.to_widget(morceau["view"]).center()
    for type_, bouton in ((QEvent.Type.MouseMove, Qt.MouseButton.NoButton), (QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton)):
        evenement = QMouseEvent(type_, QPointF(centre), page.mapToGlobal(centre), bouton, bouton, Qt.KeyboardModifier.NoModifier)
        (page.mouseMoveEvent if type_ == QEvent.Type.MouseMove else page.mousePressEvent)(evenement)
    verifier(page.editor is None, "mode édition : une saisie s'est ouverte sur le texte OCR")
    verifier("OCR" in editeur.statusBar().currentMessage(), "mode édition : pas d'explication sur le texte OCR")
    editeur.scroll.verticalScrollBar().setValue(0)
    app.processEvents()
    editeur.grab().save(os.path.join(SORTIE, "mode-edition.png"))
    editeur.edit_action.setChecked(False)

    editeur.undo()
    verifier(not editeur.doc[0].get_text().strip() and [p.rotation for p in editeur.doc] == [0, 90, 0, 0, 0],
             "Ctrl+Z n'a pas tout annulé")
    editeur.redo()
    verifier("séance" in editeur.doc[0].get_text() and editeur.doc[3].rotation == 180, "Ctrl+Y n'a pas tout rétabli")

    # Annuler pendant la lecture : les pages lues gardent leur texte, les autres restent intactes ; relancer reprend.
    editeur.undo()
    editeur.undo_stack.clear()
    fenetre = main.OcrDialog(editeur)
    fenetre.start()
    while fenetre.job is not None and "Page 2" not in fenetre.status.text():
        app.processEvents()
    app.processEvents()  # la page 2 est lue au passage suivant
    fenetre.reject()  # bouton « Annuler » pendant la lecture
    verifier(fenetre.job is None and "interrompue" in fenetre.status.text(), f"annulation : {fenetre.status.text()}")
    lues = [i for i in range(5) if main.ocr_layers(editeur.doc, editeur.doc[i])]
    verifier(lues and lues == list(range(len(lues))) and len(lues) < 4, f"annulation : pages lues {lues}")
    verifier(len(editeur.undo_stack) == 1, "annulation : une seule étape d'annulation attendue")
    fenetre.start()  # « Relancer » : seules les pages restantes sont lues
    while fenetre.job is not None:
        app.processEvents()
    verifier(sorted(fenetre.result["skipped"]) == [*lues, 4] and len(fenetre.result["done"]) == 4 - len(lues),
             f"reprise : {fenetre.result['done']} lues, {fenetre.result['skipped']} ignorées")
    bilan.append(f"interface — annulation après {len(lues)} page(s) lue(s), puis reprise des {4 - len(lues)} autres")
    fenetre.close()
    editeur._set_modified(False)
    editeur.close()


def essai_executable(exe, attendus, chemin):
    print("— Exécutable construit :", exe)
    sortie = os.path.join(SORTIE, "scans-exe.pdf")
    if os.path.exists(sortie):
        os.remove(sortie)
    debut = time.perf_counter()
    code = subprocess.run([exe, "--ocr", chemin, sortie], timeout=600).returncode
    duree = time.perf_counter() - debut
    verifier(code == 0 and os.path.exists(sortie), f"exécutable : code de sortie {code}")
    if code == 0:
        doc = pymupdf.open(sortie)
        cer = verifier_document(doc, attendus, "exécutable")
        bilan.append(f"exécutable — 4 pages scannées en {duree:.1f} s (démarrage compris) ; erreurs : {cer:.2%}")
        doc.close()
    vide = os.path.join(SORTIE, "absent.pdf")
    code = subprocess.run([exe, "--ocr", os.path.join(SORTIE, "inexistant.pdf"), vide], timeout=120).returncode
    verifier(code == 1, f"exécutable : fichier absent, code {code} au lieu de 1")


def principal():
    os.makedirs(SORTIE, exist_ok=True)
    chemin = os.path.join(SORTIE, "scans.pdf")
    attendus = fabriquer_scans(chemin)
    if "--exe" in sys.argv:
        essai_executable(os.path.abspath(sys.argv[sys.argv.index("--exe") + 1]), attendus, chemin)
    else:
        essai_source(attendus, chemin)
        essai_structures()
        essai_interface(chemin)
    print()
    print("\n".join(bilan))
    print()
    if erreurs:
        print(f"{len(erreurs)} échec(s).")
        sys.exit(1)
    print("Tout est conforme. Fichiers et captures dans", SORTIE)


if __name__ == "__main__":
    principal()
