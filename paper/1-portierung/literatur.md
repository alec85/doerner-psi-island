# Literaturrecherche Paper 1: Portierung

Stand 2026-11-12 (Issue #40). Recherche über Websuche und Verlags- bzw. Repositoriumsseiten. „Geprüft“ heißt: Autoren, Jahr, Titel, Ort der Veröffentlichung und, wo angegeben, Band und Seiten stimmen mit der genannten Quelle überein. „Ungeprüft“ heißt: aus dem Gedächtnis des Agenten, vor der Einreichung nachsehen. Schlüssel wie in `referenzen.bib`.

## PSI-Theorie und ihre Umsetzungen

| Schlüssel | Angabe | Stand | Wofür im Paper |
|---|---|---|---|
| `doerner1999bauplan` | Dörner (1999), *Bauplan für eine Seele*, Rowohlt | Titel und Verlag über Händlerseite bestätigt | Theorie, Einführung |
| `doerner2002mechanik` | Dörner (2002), *Die Mechanik des Seelenwagens. Eine neuronale Theorie der Handlungsregulation*, Huber, ISBN 978-3-456-83814-4 | geprüft (FIS Universität Bamberg) | Grundlage der Implementierung; das Buch beschreibt das Programm, das wir portieren; Seitenangaben zu Hintergrundzielen (S. 99) aus dem Projektdokument |
| `doerner2013psi` | Dörner und Güss (2013), *Review of General Psychology* 17(3), 297–317, doi:10.1037/a0032947 | geprüft (UNF Digital Commons) | englischsprachige Übersicht, Kernreferenz für Leser ohne Deutsch |
| `doerner2004emotions` | Dörner und Starker (2004), *Should successful agents have emotions? The role of emotions in problem solving*, ICCM 2004 | Titel, Autoren und Inhalt geprüft (Abstract auf der ICCM-Seite); Seiten offen | Vorbefund am Inselprogramm: 20 Menschen gegen 20 Psi-Agenten, acht Verhaltensmaße, kanonische Korrelation .88; Psi mit Emotion gegen Psi mit festen Modulatoren. Zeigt, dass das Inselprogramm wissenschaftlich als Vergleichsmodell genutzt wurde |
| `doerner2002sozionik` | Dörner, Levi, Detje, Becht und Lippold (um 2001/2002), *Der agentenorientierte, sozionische Ansatz mit PSI*, Projektbericht Sozionik | Autoren und Inhalt geprüft (Universität Hamburg, Sozionik-Journal 2); Jahr nicht angegeben | Inselwelt als Testumgebung, Nukleotide als Ziel |
| `bach2009principles` | Bach (2009), *Principles of Synthetic Intelligence. PSI: An Architecture of Motivated Cognition*, Oxford University Press, ISBN 978-0-19-537067-6 | geprüft (Händlerseite; Entwurf liegt im Projekt) | ausführliche englische Rekonstruktion; Kapitel „Dörner's Psi agent implementation“ |
| `bach2012micropsi2` | Bach (2012), *MicroPsi 2: The next generation of the MicroPsi framework*, AGI 2012, LNCS 7716, doi:10.1007/978-3-642-35506-6_2 | geprüft (Springer) | spätere Umsetzung, keine Portierung des Originals |
| `bach2005studying` | Bach (2005), *Studying emotion and interaction between autonomous cognitive agents in simulated and robotic environments*, Proc. CogSci 27 | geprüft (eScholarship) | MicroPsi, Abgrenzung |
| `cai2011openpsi` | Cai, Goertzel und Geisweiller (2011), *OpenPsi: Realizing Dörner's „Psi“ cognitive model in the OpenCog integrative AGI architecture*, AGI 2011, LNCS 6830, 212–221, doi:10.1007/978-3-642-22887-2_22 | geprüft (researchr; Autorenfassung goertzel.org gelesen; DOI aus dem Review und doi.org-Treffer) | Neuimplementierung von Motivation und Modulation in OpenCog, keine Portierung; Selektionsschwelle skaliert Aufmerksamkeitswert der Ziele des Vorzyklus (auch für Paper 2) |
| `lim2012npcs` | Lim, Dias, Aylett und Paiva (2012), *Creating adaptive affective autonomous NPCs*, Autonomous Agents and Multi-Agent Systems 24(2), 287–311, doi:10.1007/s10458-010-9161-2 | geprüft (Forschungsportal Heriot-Watt) | PSI-Antriebe mit FAtiMA für Spielfiguren |

Lücke, die das Paper füllt: Keine der Umsetzungen (MicroPsi, MicroPsi 2, OpenPsi, Spielfiguren) ist eine Portierung des Delphi-Programms; sie rekonstruieren die Theorie. Eine Suche nach Portierungen oder Neuimplementierungen des Inselprogramms ergab nichts (2026-11-12; ein GitHub-Projekt „AdversarialGroupPSISimulation“ konnte wegen einer Zugriffsbegrenzung nicht gelesen werden und ist vor der Einreichung zu prüfen).

## Kognitive Architekturen

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `kotseruba2020forty` | Kotseruba und Tsotsos (2020), *40 years of cognitive architectures: core cognitive abilities and practical applications*, Artificial Intelligence Review 53, 17–94, doi:10.1007/s10462-018-9646-y | Titel, Zeitschrift, DOI über Suche bestätigt; Band und Seiten ungeprüft | Einordnung |
| `laird2017standard` | Laird, Lebiere und Rosenbloom (2017), *A standard model of the mind*, AI Magazine 38(4), 13–26 | Titel und Zeitschrift bestätigt; Seiten ungeprüft | Einordnung: PSI fehlt im „Standard Model“, Motivation und Emotion dort randständig |

## Replikation und Reproduzierbarkeit von Rechenmodellen

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `axtell1996aligning` | Axtell, Axelrod, Epstein und Cohen (1996), *Aligning simulation models: a case study and results*, Computational and Mathematical Organization Theory 1, 123–141 | geprüft (Bibliothek J. M. Vidal) | Begriff „docking“, Stufen der Gleichheit (numerische Identität, distributionale Gleichheit, relationale Gleichheit) |
| `edmonds2003replication` | Edmonds und Hales (2003), *Replication, replication and replication: some hard lessons from model alignment*, JASSS 6(4), 11 | geprüft (JASSS) | kleine, nicht beschriebene Details (etwa Auflösung von Gleichständen) ändern Ergebnisse; Vergleich statistisch über viele Läufe |
| `wilensky2007making` | Wilensky und Rand (2007), *Making models match: replicating an agent-based model*, JASSS 10(4), 2 | geprüft (JASSS) | Replikationsstandards, Kriterien für Gleichheit |
| `rougier2017rescience` | Rougier, Hinsen et al. (2017), *Sustainable computational science: the ReScience initiative*, PeerJ Computer Science 3, e142, doi:10.7717/peerj-cs.142 | Autoren und DOI geprüft (arXiv); Artikelnummer aus DOI | Rahmen für Reproduktionen; mögliche Zielzeitschrift ReScience C |
| `perkel2020challenge` | Perkel (2020), Nature 584, 656–658 (Ten Years Reproducibility Challenge) | Autor, Band, Seiten geprüft (Nature-PDF); Titel im PDF „The digital archaeologists“, online als „Challenge to scientists: does your ten-year-old code still run?“ | veraltete Software und fehlende Dokumentation als Haupthindernisse |
| `collberg2016repeatability` | Collberg und Proebsting (2016), *Repeatability in computer systems research*, Communications of the ACM 59(3), 62–69 | geprüft (researchr) | wie selten Code überhaupt baubar ist |
| `sandve2013ten` | Sandve, Nekrutenko, Taylor und Hovig (2013), *Ten simple rules for reproducible computational research*, PLoS Computational Biology 9(10), e1003285 | Titel, Autoren, Zeitschrift, DOI 10.1371/journal.pcbi.1003285 bestätigt | Seeds, Versionsstand, Rohdaten |
| `hutson2018artificial` | Hutson (2018), *Artificial intelligence faces reproducibility crisis*, Science 359(6377), 725–726 | Titel, Band, Seite 725 bestätigt (ADS) | Kontext |

## Gleitkomma und Altcode

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `monniaux2008pitfalls` | Monniaux (2008), *The pitfalls of verifying floating-point computations*, ACM TOPLAS 30(3), Art. 12, doi:10.1145/1353445.1353446 | geprüft (arXiv) | x87, 80-Bit-Zwischenergebnisse, doppelte Rundung |
| `feathers2004working` | Feathers (2004), *Working Effectively with Legacy Code*, Prentice Hall | ungeprüft | Charakterisierungstests (Golden Master) |

## Ergänzt bei der Überarbeitung (2026-11-12)

| Schlüssel | Angabe | Stand | Wofür |
|---|---|---|---|
| `lakens2017equivalence` | Lakens (2017), *Equivalence tests*, Social Psychological and Personality Science 8(4), 355–362, doi:10.1177/1948550617697177 | DOI aus dem Review; Band und Seiten ungeprüft | Nichtsignifikanz ist keine Äquivalenz |

Suchumfang für die Aussage, es gebe keine Rekonstruktion des Programms (Abschnitt 1 des Manuskripts): Websuche im November 2026 nach Portierungen und Neuimplementierungen des Inselagenten sowie die in der zitierten Literatur genannten Umsetzungen. Ein GitHub-Projekt (`AdversarialGroupPSISimulation`) konnte wegen einer Zugriffsbegrenzung nicht gelesen werden und ist vor der Einreichung zu prüfen.

## Lücken der Recherche

- Weitere Vergleiche Psi gegen Menschen (Detje, BioLab, Dörner und Mitarbeiter) sind in den Bamberger Memoranden zu suchen; dort ist auch die Versionsgeschichte des Inselprogramms zu vermuten.
- Rechteinhaber am Delphi-Quelltext und an den Laufzeitdateien vor der Einreichung klären (betrifft die Beschreibung des Ausgangsmaterials, nicht das öffentliche Repository, das ohne `reference/` entsteht).

## Stand nach der zweiten Review-Runde (2026-11-13)

Die Prüfnotizen sind aus `referenzen.bib` entfernt (sie erschienen im Literaturverzeichnis) und stehen nur noch hier. Vor der Einreichung gegen Verlagsseite oder DOI zu prüfen, weil Verlags- und Katalogseiten aus dieser Umgebung gesperrt waren:

- `kotseruba2020forty`: Band 53, Seiten 17–94 (Titel, Zeitschrift, DOI bestätigt)
- `laird2017standard`: Heft 38(4), Seiten 13–26 (Titel, Zeitschrift bestätigt)
- `lakens2017equivalence`: Band 8(4), Seiten 355–362 (Titel, Zeitschrift, DOI bestätigt)
- `doerner2004emotions`: Seitenzahlen im ICCM-Band
- `doerner2002sozionik`: Jahr
- `feathers2004working`: Verlag und Ort

**Geprüft von Alec am 2026-11-13:** Alec hat die Literatur nach eigener Angabe geprüft. Die Liste oben bleibt als Protokoll dessen stehen, was offen war.
