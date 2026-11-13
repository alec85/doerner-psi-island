# Vorauswahl der Workspace-Experimente (nicht bestätigend)

Seeds 1001 bis 1020, Bedingungen B bis E (`scripts/workspace_runs.sh 1001-1020 2`), A aus `runs/ws-A`. Code: Stand nach Nachtrag 3 (Commit c0194b6), danach bis zur Bestätigung unverändert.

Zweck laut Analyseplan: Fehler finden, Effektgrößen schätzen. Die Tests in `tests.md` sind keine Bestätigung.

Fehlerprüfung: Kein Leben brach ab, kein nil-Zugriff wurde abgefangen. Alle fünf Inhaltsarten kamen in jedem Leben jeder Workspace-Bedingung vor.

Beobachtungen für die Planung der Bestätigung, ohne Änderung an Hypothesen oder Kriterien:

- Die Effekte auf W2b (H1), W1 der Nicht-Motive (H4) und W6 (H6) sind schon mit 20 Seeds groß.
- H3 (Arousal-Kopplung gegen festen Bonus) zeigt in der Vorauswahl keinen Unterschied. Die Selektionsschwelle schwankt in A wenig (Mittel 0,0646, Standardabweichung 0,0091), der feste Bonus von D liegt mitten darin. Bleibt das in der Bestätigung so, ist die Kernaussage nach dem Kriterium des Analyseplans nicht gestützt, und es gilt die vorab festgelegte Formulierung: Die Kopplung ans Arousal bringt gegenüber einem festen Bonus keinen messbaren Vorteil.
- H2 und H5 zeigen in der Vorauswahl keinen Unterschied.
- Motivwechsel kommen in B bis E selten vor (0,02 bis 0,06 je 100 Zyklen), in A nie.
- Ein Leben (E, Seed 1016) lief mit 1.376 Zyklen deutlich länger als die übrigen; kein Fehler erkennbar.
