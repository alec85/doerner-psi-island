# Artefakte des Originals: Wirkung der Schalter (Issue #29, ADR 0015)

Stand 2026-11-10. Gepaarter Vergleich je Seed gegen die Vergleichsbasis (Referenzmodus), Seeds 1001 bis 1020, je ein volles Leben mit `MaxLife` 5.000.000. Differenz = Variante − Basis, 95-%-Bootstrap-Intervall, Vorzeichen-Permutationstest, Holm-korrigiert über P1 bis P6. Einzelheiten je Schalter in den Unterordnern (`vergleich.md`, `vergleich.json`); erzeugt mit `scripts/baseline.py` und `scripts/compare_variants.py`.

Das ist die Vorauswahl nach Nachtrag 2 zum Analyseplan. Ein Schalter ohne signifikanten Effekt ist damit nicht als wirkungslos belegt; dafür folgt die Bestätigung mit 100 Seeds.

| Schalter | n | Signifikant nach Holm (p < 0,05) |
|---|---:|---|
| alle sechs zusammen | 20 | P1 −2,88 Exitus/1.000 Zyklen [−3,89; −1,84]; P4 +0,021 [0,011; 0,031]; P5 −0,076 [−0,085; −0,066]; P6 −8,5 Prozentpunkte [−11,0; −5,7] |
| `background_goals_as_described` | 19 | P1 −2,64 [−3,87; −1,41]; P4 +0,020 [0,009; 0,031]; P5 −0,065 [−0,074; −0,056]; P6 −7,2 [−10,0; −4,5] |
| `goal_in_current_situation` | 20 | P2 +1,33 Nukleotide/100 Zyklen [0,50; 2,15]; P4 +0,011 [0,005; 0,019]; P5 −0,029 [−0,037; −0,021] |
| `clean_direction_names` | 20 | P2 −1,27 [−2,12; −0,44] (p = 0,050); P3 +3,3 Orte [1,1; 5,7] (p = 0,050); P5 +0,012 [0,005; 0,019]; dazu +104 Zyklen pro Leben [56; 151] |
| `no_display_side_effects` | 20 | keiner |
| `aversion_check_in_aversions` | 20 | keiner |
| `real_umlaut_bitmaps` | 19 | keiner |

Lesart:

- Den größten Teil der Wirkung aller Schalter zusammen trägt die Annahmeregel für Hintergrundziele. Mit der Regel aus dem Buch stirbt Psi seltener, erleidet weniger Schaden und greift seltener auf Versuch und Irrtum zurück. Die Richtung passt zu Dörners Beschreibung: Bei starkem aktuellem Motiv konzentriert sich Psi; im Programm war es umgekehrt.
- Die Suche nach dem Ziel in der richtigen Situation (`goal_in_current_situation`) macht Pläne nützlicher: mehr Nukleotide, weniger Versuch und Irrtum.
- Die Speicherreste in `DirArtWert` wirken nicht neutral. Mit sauberen Richtungen erkundet Psi mehr Orte, sammelt aber weniger Nukleotide pro Zyklus. Warum das Leben dabei mehr Zyklen hat, ist offen.
- Zwei Leben brachen ab (`background_goals_as_described` Seed 1019 in Zyklus 46, `real_umlaut_bitmaps` Seed 1007 in Zyklus 697), beide in `ActivateAuto` an einer Protokollkette, die vor dem Ziel endet. Im Original wäre das eine Zugriffsverletzung. Die Stelle liegt also auch im Referenzmodus bereit; in den bisher gerechneten Seeds der Basis kam sie nicht vor. Der Schalter `guard_nil_dereferences` fängt sie ab und gehört zum modernen Modus. Die beiden Leben sind aus dem Vergleich genommen.
- Der Lauf „alle“ wurde vor Einführung von `guard_nil_dereferences` gerechnet; keins seiner 20 Leben brach ab, die Ergebnisse gelten damit auch für die Variante einschließlich dieses Schalters.

## Bestätigung: alle Schalter zusammen, 100 Seeds (2026-11-11)

Seeds 1001 bis 1100 (`all-100/`). Die Seeds 1021 bis 1100 liefen mit allen sieben Schaltern einschließlich `guard_nil_dereferences`, das dort zweimal griff. Kein Leben der Variante brach ab. Aus der Basis fallen drei abgebrochene Leben heraus, gepaart bleiben 97 Seeds.

| Kennzahl | Differenz (Variante − Basis) | 95-%-KI | p (Holm) |
|---|---:|---|---:|
| P1 Exitus pro 1.000 Zyklen | −2,61 | [−3,06; −2,15] | 0,0006 |
| P2 Nukleotide pro 100 Zyklen | −0,16 | [−0,54; 0,21] | 0,40 |
| P3 entdeckte Orte | +1,62 | [0,64; 2,61] | 0,005 |
| P4 Erfolgsquote Manipulationen | +0,020 | [0,013; 0,027] | 0,0006 |
| P5 Anteil Versuch und Irrtum | −0,068 | [−0,076; −0,061] | 0,0006 |
| P6 mittlere Bedürfnisstärke Schaden | −8,5 | [−9,5; −7,4] | 0,0006 |

Die Effekte auf Überleben, Schaden, Erfolgsquote und Versuch und Irrtum aus der Vorauswahl bestätigen sich in Größe und Richtung. Der Zuwachs an Nukleotiden aus der Vorauswahl (+0,76, nicht signifikant nach Holm) bestätigt sich nicht. Neu signifikant ist ein kleiner Zuwachs an entdeckten Orten. Die Zahl der Zyklen pro Leben ändert sich nicht.

Offen: Bestätigung der einzelnen Schalter mit 100 Seeds.
