# Prüfung: Bedingung A gleich moderner Grundlinie

Stand 2026-11-11. Bedingung A (Workspace aus, nur Protokoll) neu gerechnet für Seeds 1001 bis 1020 (`runs/ws-A`, `python scripts/baseline.py --seeds 1001-1020 --runs runs/ws-A --jobs 2 --variant all`) und mit der Grundlinie des modernen Modus (`runs/variant-all`) verglichen.

- In allen 20 Leben sind `actu*.Prt`, `seed*.Prt`, `Activities(1).Txt`, `eAch`, `Inpro` und `Consum` bytegleich, ebenso Zyklen, Alter und P1 bis P6. Kein Leben brach ab, kein nil-Zugriff wurde abgefangen.
- Der Workspace verändert in Bedingung A also nichts. Für die Seeds 1021 bis 1100 nimmt die Auswertung die Läufe aus `runs/variant-all` als A.

Selektionsschwelle in A über alle 18.095 Zyklen der 20 Leben: Mittel 0,064642, Standardabweichung 0,009059, Minimum 0,0341, Maximum 0,0900 (Mittel der Seed-Mittel 0,064618). Daraus der feste Bonus für D, Nachtrag 2 zum Analyseplan.
