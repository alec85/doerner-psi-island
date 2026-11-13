# Preprint und Einreichung

Stand 2026-11-13 (Issue #55). Entscheidungen von Alec am selben Tag: Beide Paper erscheinen zuerst als Preprint auf PsyArXiv. Paper 1 geht an *Cognitive Systems Research* (Elsevier), Paper 2 an *Adaptive Behavior* (SAGE). Affiliation ist die DHBW Ravensburg. Die Literatur prüft Alec selbst. Code und Daten kommen in ein öffentliches Repository.

## Format der Manuskripte

| | Paper 1: Cognitive Systems Research | Paper 2: Adaptive Behavior |
|---|---|---|
| Vorlage | `elsarticle` (Option `preprint`, Rand 2,5 cm), Paket `texlive-publishers` | `article`, Literatur mit `apacite` (Paket `texlive-bibtex-extra`); SAGE bevorzugt Word, eine LaTeX-Vorlage gibt es nur über das Author Gateway |
| Literatur | Autor-Jahr, `elsarticle-harv` | APA, `apacite` |
| Abstract | 249 Wörter | 250 Wörter, unstrukturiert |
| Keywords | 6 | 6 (erlaubt 2 bis 6) |
| Highlights | `highlights.txt`, 5 Punkte, je höchstens 85 Zeichen (bei Elsevier eigene Datei) | nicht verlangt |
| Erklärungen am Ende | generative KI im Schreibprozess, konkurrierende Interessen, Finanzierung, CRediT, Datenverfügbarkeit | „Statements and declarations“ mit allen Pflichtpunkten (Ethik, Einwilligungen, Interessenkonflikt, Finanzierung, Daten, generative KI) |
| KI im Forschungsprozess | Absatz „Use of AI tools“ im Abschnitt zur Verfügbarkeit | ebenso |
| Umfang | 13 Seiten | rund 5.900 Wörter mit Beschriftungen und Erklärungen; SAGE nennt 6.000 bis 12.000 als üblich |

Die Bauanleitung bleibt `latexmk -pdf manuskript.tex` im jeweiligen Ordner. In einer frischen Umgebung vorher `apt-get install texlive-publishers texlive-bibtex-extra`.

## Preprint auf PsyArXiv

1. Konto bei OSF anlegen, ORCID verknüpfen.
2. Paper 1 hochladen: PDF, Titel und Abstract genau wie im Manuskript, Autoren in derselben Reihenfolge. PsyArXiv verlangt eine Kontaktadresse auf der Titelseite (Platzhalter `TODO-e-mail` bzw. „e-mail address“). Lizenz: CC BY 4.0; Elsevier schreibt für Preprints keine Lizenz vor, und die Richtlinien von Adaptive Behavior nennen keine Einschränkung. Fachgebiet etwa „Cognitive Psychology“ und „Computational Modeling“.
3. Die Moderation braucht in der Regel 24 bis 72 Stunden. Danach hat der Preprint eine DOI.
4. In `paper/2-hysterese/referenzen.bib` beim Eintrag `paper1` die DOI eintragen, Paper 2 neu bauen und hochladen.
5. Bei der Einreichung die Preprint-DOI angeben. SAGE verlangt, den Preprint während der Begutachtung nicht zu aktualisieren. Nach der Annahme den Preprint mit der veröffentlichten Fassung verlinken (beide Verlage).

PsyArXiv erlaubt KI-Nutzung, wenn wesentliche Nutzung im Manuskript offengelegt ist. Das ist in beiden Manuskripten geschehen.

## KI-Richtlinien der Zeitschriften: was das für die Einreichung heißt

Beide Manuskripte legen offen, dass Code, Analysen und der Text von Claude Code geschrieben und von Codex begutachtet wurden. Für den Preprint reicht das. Für die Zeitschriften gibt es eine Hürde, die Alec kennen sollte:

- **Elsevier** erlaubt generative KI im Schreibprozess laut seinem Leitfaden nur zur Verbesserung von Lesbarkeit und Sprache, unter menschlicher Aufsicht. Ein von KI entworfener Text geht darüber hinaus. Die Erklärung im Manuskript ist ehrlich formuliert und kann so bleiben; vor der Einreichung bei Cognitive Systems Research sollte Alec den Text aber selbst substanziell überarbeiten, damit Erklärung und Richtlinie zusammenpassen.
- **SAGE** erlaubt generative KI mit Offenlegung bei der Einreichung und im Methodenteil oder in den Danksagungen. Ausdrücklich untersagt ist unter anderem, eine Einreichung „using a series of prompts“ zu erzeugen. Auch hier ist Alecs eigene Überarbeitung der sicherste Weg.

Die Stilnotiz (`schreibstil.md`) nähert den Text an Alecs Stil an. Sie ersetzt diese Überarbeitung nicht.

## Öffentliches Repository

Empfehlung: **ein** öffentliches Repository für beide Paper, mit je einem archivierten Stand pro Paper.

- Paper 2 baut auf dem Code von Paper 1 auf. Zwei Repositories würden das Paket doppelt führen, und Fehlerkorrekturen müssten an zwei Stellen landen.
- Jedes Paper bekommt trotzdem seinen eigenen, zitierbaren Stand: Für jedes Paper ein Release im öffentlichen Repository anlegen; die Zenodo-Anbindung an GitHub erzeugt daraus je eine DOI. Diese DOI kommt in das jeweilige Manuskript (Platzhalter „DOI“).
- Releases und Tags kann der Agent in dieser Umgebung nicht anlegen; das macht Alec in der GitHub-Oberfläche.

Der Inhalt entsteht mit `scripts/public_export.sh <zielordner>` aus dem aktuellen Commit, ohne Git-Historie (die private Historie enthält `reference/`). Das Skript lässt `reference/` weg, nimmt die Protokolle der Originalläufe mit (abschaltbar mit `--without-original-traces`), bricht ab, wenn eine Datei des Exports byteweise einer Datei aus `reference/` gleicht, und sucht nach E-Mail-Adressen.

Geprüft am 2026-11-13 (Commit `9fea25c`): Export mit 1.361 Dateien, 63 MB. In einer frischen Umgebung (`pip install -e ".[dev,paper]"`) reproduziert `scripts/reproduce_revision.sh` alle Werte beider Paper und alle Tabellen identisch (Laufzeit rund 2,5 Minuten). Ohne `reference/` und ohne die Originalspuren schlagen 64 Tests fehl und 16 lassen sich nicht aufsetzen; 910 laufen durch.

Offen und von Alec zu entscheiden:

1. Name des öffentlichen Repositories.
2. Lizenz für den eigenen Code (zum Beispiel MIT, Apache-2.0, GPL-3.0) und für die Daten (zum Beispiel CC BY 4.0).
3. Entschieden am 2026-11-13: Die Protokolle der Läufe des Originals werden mit veröffentlicht. Dazu sind die Rohprotokolle der sieben Stichprobenleben (1001 bis 1081), die bisher nur lokal lagen, jetzt unter `traces/original-runs/2026-11-11-stichprobe/` archiviert. Das Exportskript nimmt `traces/original-runs/` standardmäßig mit.
4. Zeitpunkt: spätestens zusammen mit dem ersten Preprint, weil beide Manuskripte auf das Repository verweisen.

Vorschlag für den nächsten technischen Schritt: Tests, die `reference/` brauchen, im öffentlichen Repository mit einer klaren Meldung überspringen statt fehlschlagen lassen.

## Was vor dem Hochladen noch fehlt

- [x] E-Mail-Adresse auf beiden Titelseiten (Pflicht bei PsyArXiv): alec.sproten@aol.be.
- [x] Literatur prüfen (laut Alec am 2026-11-13 erledigt) (Liste in `1-portierung/literatur.md` und `2-hysterese/literatur.md`, dazu Bach 2009 gegen die gedruckte Ausgabe). Die KI-Erklärung von Paper 2 sagt, dass der Autor die Literatur geprüft hat; der Satz stimmt erst danach.
- [x] Modellversion von OpenAI Codex in beiden KI-Erklärungen: GPT 6.1 Sol.
- [ ] CRediT-Rollen in Paper 1 prüfen. Eingetragen sind nur Rollen, die Alec selbst ausgefüllt hat; „Software“, „Formal analysis“ und „Writing – original draft“ fehlen bewusst, weil diese Arbeit der Agent gemacht hat.
- [ ] Öffentliches Repository anlegen, URL, Lizenz und DOI in beiden Manuskripten eintragen.
- [ ] Nach der DOI von Paper 1 den Eintrag `paper1` in Paper 2 ergänzen.

## Öffentliches Repository: Stand und Ablauf

Entschieden am 2026-11-13: Name `alec85/doerner-psi-island`, Code unter MIT (`LICENSE`), Daten und Dokumente unter CC BY 4.0 (`LICENSE-DATA.md`). Die englische README des öffentlichen Repositories liegt unter `public/README.md`; das Exportskript setzt sie als `README.md` ein. URL und Lizenzen stehen in beiden Manuskripten.

Der Agent kann das Repository nicht selbst anlegen: Die Session ist an freigegebene Repositories gebunden, `POST /user/repos` liefert 403. Ablauf:

1. PR #57 nach `main` mergen (Alec), damit der Export von einem Commit auf `main` stammt.
2. Alec legt auf GitHub das leere öffentliche Repository `doerner-psi-island` an, ohne README, Lizenz oder `.gitignore`.
3. Alec gibt es für Claude frei (GitHub-App bzw. Session-Freigabe), damit der Agent es mit Schreibrechten anbinden kann.
4. Der Agent erzeugt den Export (`scripts/public_export.sh`), prüft ihn (Tests, `reproduce_revision.sh`) und pusht ihn als ersten Commit.
5. Alec verbindet das Repository bei Zenodo (GitHub-Integration), bevor er das erste Release anlegt; erst dann erzeugt Zenodo eine DOI.
6. Release `paper1-v1` anlegen, DOI in Paper 1 eintragen; nach dem Preprint von Paper 1 dasselbe für Paper 2 (`paper2-v1`).

