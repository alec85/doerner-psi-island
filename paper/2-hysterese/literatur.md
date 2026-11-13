# Literaturrecherche Paper 2: Hysterese im Global Workspace

Stand 2026-11-12 (Issue #40). Legende wie in `../1-portierung/literatur.md`. PSI-Grundlagen (Dörner 1999, 2002; Dörner und Güss 2013; Bach 2009) und Paper 1 werden von dort übernommen.

## Global-Workspace-Theorie

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `baars1988cognitive` | Baars (1988), *A Cognitive Theory of Consciousness*, Cambridge University Press | ungeprüft (Standardwerk) | Ursprung der GWT |
| `dehaene1998neuronal` | Dehaene, Kerszberg und Changeux (1998), PNAS 95(24), 14529–14534 | ungeprüft | neuronales Workspace-Modell; Zündung, Selbsterhaltung von Aktivität |
| `mashour2020conscious` | Mashour, Roelfsema, Changeux und Dehaene (2020), *Conscious processing and the global neuronal workspace hypothesis*, Neuron 105(5), 776–798 | Titel, Autoren, Zeitschrift bestätigt (PubMed 32135090); Band und Seiten ungeprüft | aktueller Stand, nichtlineare Zündung, Stabilität |
| `vanrullen2021deep` | VanRullen und Kanai (2021), *Deep learning and the Global Workspace Theory*, Trends in Neurosciences 44(9), 692–704 | Titel, Autoren, Zeitschrift bestätigt (arXiv 2012.10390); Heft und Seiten ungeprüft | GWT in Maschinenlernen |
| `goyal2022coordination` | Goyal, Didolkar, Lamb, Badola, Ke, Rahaman, Binas, Blundell, Mozer und Bengio (2022), ICLR | geprüft (mlanthology) | Module konkurrieren um einen Kanal begrenzter Bandbreite |
| `dossa2024design` | Dossa, Arulkumaran, Juliani, Sasai und Kanai (2024), *Design and evaluation of a global workspace agent embodied in a realistic multimodal environment*, Frontiers in Computational Neuroscience 18, 1352685, doi:10.3389/fncom.2024.1352685 | Titel, Autoren, Zeitschrift, DOI bestätigt (Suche); Band ungeprüft | verkörperter Workspace-Agent |
| `franklin2014lida` | Franklin, Madl, D'Mello und Snaider (2014), *LIDA: A systems-level architecture for cognition, emotion, and learning*, IEEE Transactions on Autonomous Mental Development 6(1), 19–41 | Titel, Autoren, Zeitschrift bestätigt (dblp-Treffer); Seiten ungeprüft | GWT-Architektur mit Aufmerksamkeitskodelets |
| `shanahan2006cognitive` | Shanahan (2006), *A cognitive architecture that combines internal simulation with a global workspace*, Consciousness and Cognition 15(2), 433–449 | Titel und Autor geprüft (Seite des Autors); Band und Seiten ungeprüft | Workspace mit innerer Simulation |
| `butlin2023consciousness` | Butlin, Long et al. (2023), arXiv:2308.08708 | Autorenliste und GWT-1 bis GWT-4 wörtlich geprüft (arXiv) | Indikatoren: GWT-2 „limited capacity workspace, entailing a bottleneck in information flow and a selective attention mechanism“, GWT-3 „global broadcast“, GWT-4 „state-dependent attention“; unser Agent setzt GWT-2 und GWT-3 um, GWT-4 teilweise (Kapazität hängt vom Zustand ab) |

## Stabilität und Flexibilität, Volition

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `goschke2014emotional` | Goschke und Bolte (2014), Neuropsychologia 62, 403–423, doi:10.1016/j.neuropsychologia.2014.07.015 | geprüft (TU Dresden) | Stabilitäts-Flexibilitäts-Dilemma; Affekt verschiebt die Balance |
| `dreisbach2004positive` | Dreisbach und Goschke (2004), JEP: Learning, Memory, and Cognition 30(2), 343–353, doi:10.1037/0278-7393.30.2.343 | geprüft (PDF Universität Regensburg) | weniger Perseveration, mehr Ablenkbarkeit; Effekt an Valenz, nicht an Arousal gebunden (relevant für H3) |
| `musslick2021rationalizing` | Musslick und Cohen (2021), Trends in Cognitive Sciences 25(9), 757–775, doi:10.1016/j.tics.2021.06.001 | geprüft (Princeton) | Kapazitätsgrenzen als rationale Folge des Stabilitäts-Flexibilitäts-Zielkonflikts |
| `hommel2015between` | Hommel (2015), *Between persistence and flexibility: The Yin and Yang of action control*, Advances in Motivation Science 2, 33–67 | Titel und Reihe bestätigt; Band und Seiten ungeprüft | Persistenz gegen Flexibilität |
| `kuhl1985volitional` | Kuhl (1985), *Volitional mediators of cognition-behavior consistency*, in Kuhl und Beckmann (Hg.), *Action Control*, Springer, 101–128 | Buch bestätigt; Seiten ungeprüft | Abschirmung von Absichten |
| `heckhausen1987thought` | Heckhausen und Gollwitzer (1987), Motivation and Emotion 11(2), 101–120 | ungeprüft | Rubikon: nach der Entscheidung Abschirmung der Absicht |
| `oreilly2006making` | O'Reilly und Frank (2006), Neural Computation 18(2), 283–328 | Titel und Zeitschrift bestätigt (PubMed 16378516); Seiten ungeprüft | Gating: Arbeitsgedächtnis zwischen Halten und Aktualisieren |

## Arousal und Aufmerksamkeit

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `easterbrook1959effect` | Easterbrook (1959), Psychological Review 66(3), 183–201 | Titel und Zeitschrift bestätigt (PubMed 13658305); Heft und Seiten ungeprüft | Arousal verengt die genutzten Hinweise; Gegenstück zu Dörners Auflösungsgrad |
| `astonjones2005integrative` | Aston-Jones und Cohen (2005), Annual Review of Neuroscience 28, 403–450, doi:10.1146/annurev.neuro.28.061604.135709 | geprüft (Princeton) | adaptive Verstärkung, Ausbeutung gegen Erkundung |

## Hysterese und dynamische Systeme

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `hock1993bistability` | Hock, Kelso und Schöner (1993), JEP: Human Perception and Performance 19(1), 63–80 | geprüft (BISp) | Hysterese in der Wahrnehmung als Kennzeichen eines dynamischen Systems |
| `edmonds2003replication` | Edmonds und Hales (2003), JASSS 6(4), 11 | geprüft | Auflösung von Gleichständen ändert Ergebnisse; Bezug zu ADR 0018 |

## Vorarbeiten zu Selektionsschwelle, Hysterese und Workspace (Überarbeitung 2026-11-12)

| Quelle | Befund | Stand |
|---|---|---|
| Bach (2009), Abschnitte 4.6.2, 6.2.3, Abbildung 8.2 | Selektionsschwelle als Bias auf das aktuelle Motiv; in MicroPsi erhält die gewählte Absicht einen Bonus „which corresponds to a selection threshold, and which adds a hysteresis that keeps the active intention more stable“; Architektur enthält „Access Memory (Workspace)“ | gelesen im OUP-Entwurf vom Januar 2008 (Projekt-PDF); Wortlaut und Seiten vor Einreichung gegen die gedruckte Fassung prüfen |
| Cai, Goertzel und Geisweiller (2011), OpenPsi | Selektionsschwelle skaliert den kurzfristigen Aufmerksamkeitswert, der an die im Vorzyklus wertvollsten Ziel-Atome geht | Autorenfassung gelesen |
| Dossa et al. (2024), Abschnitt 2.4, Abbildung 1C | Voriger Workspace als Query der Aufmerksamkeit und als versteckter Zustand der zentralen GRU; Broadcast über die GRUs der Modalitäten; kein expliziter Bonus für den bisherigen Inhalt | Volltext (Frontiers) gelesen |
| Dörner (2002), S. 241–248 (Abschnitt von Frank Detje) | Simulationen mit Selektionsschwelle 0,1, 0,4 und 0,8 (je 30 Psis): höhere Schwelle, mehr Nukleotide und Orte, aber mehr Zusammenbrüche | im Projekt-PDF gelesen |

Folge für das Paper: Neuheit nur für die eine explizite additive Regel über alle Inhaltsarten, ihre kontrollierte Variation und den Test im rekonstruierten Original. Keine Erstbehauptung von Hysterese oder Workspace-Persistenz.

## Was die Recherche für die Rahmung ergibt

- Der Stabilitäts-Flexibilitäts-Zielkonflikt (Goschke, Dreisbach, Musslick, Hommel) ist der natürliche theoretische Ort von Paper 2. Dörners Selektionsschwelle ist eine frühe, rechnerisch umgesetzte Antwort darauf; die Hysterese im Workspace verallgemeinert sie.
- Dreisbach und Goschke (2004) finden die Verschiebung zur Flexibilität bei positiver Valenz, nicht bei Arousal. Das passt zu unserem Null-Ergebnis zu H3 und gibt der Diskussion eine empirische Stütze.
- GWT-Agenten der letzten Jahre (Goyal et al. 2022; Dossa et al. 2024) behandeln den Wettbewerb um den Workspace als Aufmerksamkeit über Module, ohne Gedächtnis für den vorigen Inhalt. Ein Amtsinhaber-Bonus kommt dort nach unserer Recherche nicht vor; das ist vor der Einreichung gezielt zu prüfen.

## Stand nach der zweiten Review-Runde (2026-11-13)

Die Prüfnotizen sind aus `referenzen.bib` entfernt und stehen nur noch hier. Offen vor der Einreichung:

- Bach (2009): Zitat, Abschnitte und Abbildung stammen aus dem Manuskript vom Januar 2008 (Projekt-PDF); das Manuskript sagt das in einer Fußnote. Gegen die gedruckte Ausgabe prüfen und dann die Fußnote anpassen. Der Review nennt zusätzlich einen öffentlichen Entwurf vom März 2007 mit derselben Passage zum Bonus der Intentionsauswahl.
- Seiten oder Hefte ungeprüft: `dehaene1998neuronal`, `mashour2020conscious`, `vanrullen2021deep`, `franklin2014lida`, `shanahan2006cognitive`, `hommel2015between`, `kuhl1985volitional`, `heckhausen1987thought`, `oreilly2006making`, `easterbrook1959effect`; Vornamen und Band bei `dossa2024design`.

**Geprüft von Alec am 2026-11-13:** Alec hat die Literatur nach eigener Angabe geprüft. Die Liste oben bleibt als Protokoll dessen stehen, was offen war.
