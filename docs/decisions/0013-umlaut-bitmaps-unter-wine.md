# ADR 0013: Objektbilder mit Umlaut im Namen unter Wine

- Status: angenommen (Claude Code, 2026-11-10, im Rahmen von Alecs Auftrag vom 2026-11-10 14:31)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: ADR 0008 (exakte Ganzlauf-Vergleiche), ADR 0010 (Referenzmodus), ADR 0012 (Weltmodell)

## Kontext

Im vollen Leben mit Seed 16 nahm das Original in Zyklus 602 die Situation „Exit“ anders wahr als die Portierung. Das Original sah dort neun „Bergdurchhämmern1“-Objekte in einer Reihe, die Portierung eines. Ursache: Die Bitmapdateien `Bergdurchhämmern1.bmp` bis `…4.bmp` liegen mit Dateinamen in Codepage 437 vor (Byte 0x84 für „ä“). Das Original sucht unter Wine den Namen in Codepage 1252; Wine wandelt ihn nach UTF-8 und findet die Datei nicht. `Tbm.Create` (`UBitmaps.pas`) ruft dann `BuildBitmap` auf: weiße 50 × 50-Fläche mit schwarzem Rahmen (`Rectangle`) und dem Objektnamen als Text (`TextOut(5, 5, Name)`). Die neun Objekte sind der Rahmen und Buchstabenteile.

Geprüft: `scripts/wine_build_bitmap.c` baut `BuildBitmap` mit GDI nach (8-Bit-DIB, Standardschrift von Delphis `TFont`, „MS Sans Serif“ 8 pt, unter Wine durch Liberation Sans ersetzt, 96 dpi) und läuft im Wine-Präfix der Referenzläufe. Alle neun Positionen aus dem Protokoll des Originals (`[49,109]`, `[55,116]`, `[81,116]`, `[62,118]`, …) treffen schwarze Pixel dieses Bildes an den erwarteten Stellen.

Betroffen sind nur die vier Bergdurchhämmern-Bilder; drei davon kommen in der Insel vor. Situationsnamen mit Umlaut haben keine Bilder.

## Entscheidung

Der Referenzmodus bildet den Lauf unter Wine nach. Für Objektnamen mit Umlaut nimmt `BitmapStore` die unter Wine erzeugten Bilder aus `src/psi_gw/body/island/data/wine_text_bitmaps.txt` statt der Dateien. Mit `BitmapStore(wine_names=False)` werden die Dateien benutzt, wie es das Original unter Windows mit passender Codepage getan hätte.

## Betrachtete Alternativen

- **Dateien umbenennen.** Verworfen: `reference/` bleibt unverändert, und der Golden Master ist der Wine-Lauf.
- **Text in Python rendern.** Verworfen: Schriftbild und Rasterung von Wine und FreeType lassen sich nicht ohne neue Abhängigkeiten pixelgenau nachbauen. Die vier Bilder sind fest und klein; sie als Daten mitzuliefern ist einfacher und prüfbar.

## Konsequenzen

- Die Bilder hängen von der Schriftausstattung des Wine-Präfixes ab. Ein anderes Präfix kann ein anderes Original-Verhalten ergeben; `run_original.py` und `setup_wine.sh` legen das Präfix fest.
- Für Läufe im modernen Modus (ADR 0010, Stufe 2) ist `wine_names=False` die natürliche Wahl.
