# PDF Toolkit 2

Un éditeur de PDF simple et en français pour Windows : modifier le texte, assembler et organiser les pages,
remplir les formulaires, signer, protéger par mot de passe et compresser vos documents.

![PDF Toolkit 2 : recherche et remplacement dans un document](captures/fenetre.png)

## Fonctionnalités

- **Ouvrir, enregistrer, imprimer** : ouverture par le menu ou par glisser-déposer d'un PDF dans la fenêtre.
- **Modifier le texte** : cliquez sur un texte pour le réécrire ; la police d'origine est conservée quand c'est
  possible (police intégrée au PDF ou installée sur l'ordinateur).
- **Rechercher et remplacer** : toutes les occurrences sont surlignées, remplacement une par une ou en une fois.
- **Concaténer des PDF** : assemblez plusieurs fichiers dans l'ordre de votre choix ; un PDF glissé sur le document
  ouvert est ajouté à la fin.
- **Organiser les pages** : sélection au clic gauche, déplacement par glisser au clic droit, rotation et suppression.
- **Remplir les formulaires** : champs texte, cases à cocher et listes de choix.
- **Images et signatures** : insérez une image ou une signature (PNG, JPG), placez-la et redimensionnez-la à la
  souris ; le fond blanc d'une signature scannée devient transparent.
- **Mots de passe** : ouverture des PDF protégés, protection par mot de passe (chiffrement AES 256 bits).
- **Compression à l'enregistrement** : sans perte, ou forte (images réduites) pour l'envoi par e-mail.
- **Annuler et rétablir** chaque opération, zoom, aller à une page (Ctrl+G).

![Écran d'accueil de PDF Toolkit 2](captures/accueil.png)

## Utiliser l'application

Téléchargez `PDF Toolkit 2.exe` depuis la page **Releases** de ce dépôt et lancez-le : rien à installer.

> Windows peut afficher « Windows a protégé votre ordinateur », car l'exécutable n'est pas signé numériquement.
> Cliquez sur **Informations complémentaires**, puis sur **Exécuter quand même**.

## Lancer depuis le code source

Développé et testé sous Windows avec Python 3.15, PySide6 6.12 et PyMuPDF 1.28.

```
pip install PySide6 pymupdf
python main.py
```

Un PDF peut aussi être passé en argument : `python main.py document.pdf`.

## Construire l'exécutable

```
pip install pyinstaller
python -m PyInstaller --clean "PDF Toolkit 2.spec"
```

Le résultat est `dist\PDF Toolkit 2.exe`, un seul fichier sans console. Il n'est pas compressé avec UPX : sur
d'autres PC, les antivirus bloquaient les DLL compressées et l'application ne démarrait pas
(« No module named 'PySide6.QtCore' »).

L'icône `PDF Toolkit 2.ico` est générée par `python make_icon.py` (à relancer seulement si son dessin change).
Le nom et la version de l'exécutable (Propriétés → Détails) sont lus dans `main.py` (`APP_NAME`, `APP_VERSION`).

### Installateur

L'installateur (Inno Setup 6) installe la version « en dossier » de l'application, qui n'extrait rien au
lancement : c'est la version recommandée, la moins souvent bloquée par les antivirus.

```
$env:CONSTRUCTION = "dossier"
python -m PyInstaller --clean --noconfirm "PDF Toolkit 2.spec"
ISCC "installer\PDF Toolkit 2.iss"
```

Le résultat est `dist\PDF-Toolkit-2-Installation-1.0.exe` : installation sans droits d'administrateur,
raccourcis dans le menu Démarrer (et sur le Bureau au choix), option « Ouvrir avec » pour les fichiers PDF (sans
changer le lecteur par défaut), désinstallation par Paramètres → Applications.

Les exécutables publiés sont construits par GitHub Actions (`.github/workflows/build.yml`) à partir du code de ce
dépôt, avec les versions de `requirements-build.txt` : il suffit de pousser une étiquette `v1.1`, `v1.2`… pour
construire, signer et publier une nouvelle Release.

## Politique de signature du code

Signature de code gratuite fournie par [SignPath.io](https://about.signpath.io/), certificat par
[SignPath Foundation](https://signpath.org/).
*(Free code signing provided by SignPath.io, certificate by SignPath Foundation.)*

- **Contributeurs et relecteurs** : [Yannick Buchet](https://github.com/yannickbuchet-ctrl)
- **Approbateur des signatures** : [Yannick Buchet](https://github.com/yannickbuchet-ctrl)

Seuls les exécutables construits par GitHub Actions à partir du code public de ce dépôt sont signés.

**Confidentialité** : ce programme ne transmet aucune information à d'autres systèmes en réseau, sauf demande
expresse de l'utilisateur. *(This program will not transfer any information to other networked systems unless
specifically requested by the user or the person installing or operating it.)*

## Fichiers

| Fichier | Rôle |
|---|---|
| `main.py` | l'application |
| `make_icon.py` | génère l'icône de l'exécutable |
| `PDF Toolkit 2.spec` | recette de construction de l'exécutable (PyInstaller) |
| `installer/PDF Toolkit 2.iss` | script de l'installateur (Inno Setup) |
| `requirements-build.txt` | versions des outils de construction |
| `.github/workflows/build.yml` | construction, signature et publication automatiques |
| `PDF Toolkit 2.ico` | icône |
| `captures/` | captures d'écran de ce README |

## Licence

PDF Toolkit 2 est distribué sous la licence **GNU AGPL v3** (voir [LICENSE](LICENSE)).
Ce choix est imposé par [PyMuPDF](https://pymupdf.readthedocs.io/), qui lit et écrit les PDF et est lui-même
sous licence AGPL : toute personne qui distribue ce logiciel, modifié ou non, doit aussi en publier le code source.

## Crédits

- Application écrite par **Claude Code** (Claude Opus 5.5) sous la direction de **Yannick Buchet**.
- [PyMuPDF](https://pymupdf.readthedocs.io/) (AGPL) pour le traitement des PDF,
  [PySide6 / Qt](https://doc.qt.io/qtforpython/) (LGPL) pour l'interface.
