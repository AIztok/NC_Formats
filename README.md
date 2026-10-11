# ABS- und NC-Formate

Lokale Streamlit-App mit deutscher Oberfläche. **ABS · Bewehrung** liest und bearbeitet BVBS-Dateien; **Stahlbau · DSTV / NC / NC1** liest Stahlbau-Bleche und gerade I-/H-Profile.

## Einrichtung und Start (Windows / PowerShell)

Im Projektordner mit dem bereits installierten uv:

```powershell
uv sync
uv run streamlit run app.py
```

Die App öffnet sich gewöhnlich unter http://localhost:8501. Mit `Strg+C` im Terminal stoppen. Eine manuelle Aktivierung ist nicht erforderlich. Python ab 3.11; uv verwaltet `.venv`, `pyproject.toml` und `uv.lock`. `.venv` bleibt lokal und wird nicht versioniert.

```powershell
uv run pytest
```

## Bedienung

1. Links eine `.abs`-Datei hochladen oder **Beispieldatei laden** wählen. Automatisch wird UTF-8 (einschließlich BOM) erkannt; andernfalls wird strikt Windows-1252 verwendet. Das Import-Encoding lässt sich ausdrücklich wählen.
2. Positionen filtern und auswählen. Datensatznummern unterscheiden auch identische Positionsnummern. Bei Mehrfachauswahl bestimmt **Aktive Position** den Einzelpositionseditor; jede Form erhält eine eigene Ansicht.
3. In Position 2 der Beispieldatei im Geometrieblock `Gl400@` zu `Gl500@` ändern. Nach dem von Streamlit übernommenen Änderungsereignis, etwa beim Verlassen des Felds, aktualisiert sich die Vorschau. **Übernehmen und prüfen** löst dieselbe Verarbeitung aus. Nicht jeder Tastendruck wird an Python gesendet. Sichtbare Zeilenumbrüche im Textfeld sind nur Anzeigeumbrüche. Ein kopierter Zeilenabschluss vor oder nach einem einzelnen Datensatz wird toleriert; echte Umbrüche innerhalb eines Datensatzes werden weiterhin gemeldet. Einzelpositionen und Gesamtdatei verwenden getrennte Editorzustände.
4. `w90@` zu `w-90@` ändern: Die Biegerichtung wechselt. Optional die Originalform grau gestrichelt einblenden. Headerfelder wie `d12` und `n10` verändern Eigenschaften; Header-`l` und Geometrie-`l` werden getrennt interpretiert.
5. Bei ungültiger Eingabe bleibt der Text erhalten; die letzte eindeutig zuordenbare gültige Grafik wird als veraltet gekennzeichnet. Auswahl-, Seiten- und Moduswechsel setzen den Entwurf nicht zurück. Ein Einzelpositionsentwurf mit Zeilenumbrüchen bleibt pro Editorziel erhalten und ist im Entwurfsdownload enthalten; zum strukturellen Bearbeiten **Gesamte Datei** verwenden.
6. **Prüfsumme aktualisieren** schreibt die Prüfsumme nur ausdrücklich um. Nicht-ASCII-Inhalte werden hierbei nicht mit einer vermuteten Formel korrigiert.

## Original, Entwurf und Export

- **Original herunterladen** liefert die unveränderten Uploadbytes.
- **Entwurf herunterladen (ungeprüft)** sichert Änderungen auch bei Fehlern und bewahrt unveränderte Datensätze, Zusatzdaten, Encoding/BOM und Zeilenenden. Nicht kodierbare Texte erzeugen einen Fehler, keine Ersatzzeichen.
- **Geprüften ABS-Export herunterladen** ist auf gerade BF2D-Stäbe ohne Zusatzblöcke beschränkt. Länge und nominales Einzelgewicht werden geprüft, Prüfsummen für den finalen Text neu berechnet. Der angezeigte Prüfumfang ist eingeschränkt; keine Maschinenfreigabe oder Zertifizierung.

Bei gebogenen Formen bleiben Headerlänge und Gewicht erhalten und gelten als fachlich ungeklärt bzw. möglicherweise veraltet. Auch manuelles Bestätigen hebt diese Einschränkung nicht auf. Der DSTV-Umfang ist im Abschnitt Stahlbau unten beschrieben.

Nach einem Gesamteditor-Eingriff bleibt der Originalvergleich nur aktiv, wenn Anzahl, Reihenfolge und eindeutige Plan-/Index-/Positionsidentitäten übereinstimmen. Bei Einfügen, Löschen, Umordnen oder uneindeutigen doppelten Identitäten wird er deaktiviert. **Änderungen zurücksetzen** stellt den Uploadzustand wieder her; dazu ist die Checkbox zu setzen. Neue Uploads ersetzen einen geänderten Entwurf erst nach ausdrücklichem Laden.

## Unterstützter Umfang und Beispiele

Gewöhnliche ebene BF2D-Formen mit positiven Schenkellängen und vorzeichenbehafteten Biegewinkeln werden schematisch dargestellt. Radien, Sonderlängen, Staffelungen, Muffen, Abstandhalter, BF3D, Wendeln, Matten und unbekannte Typen bleiben im Text erhalten und bekommen keine irreführende normale Polygonlinie. Private Zusatzdaten bleiben verlustarm erhalten und sperren den geprüften Export.

Die Grafik ist **keine exakte Stabachse** und berechnet keine Zuschnittlänge oder Biegeabzüge. Die Vorschau nutzt die übernommenen Außenmaße. **Biegeradien anzeigen (schematisch)** ist standardmäßig aktiviert: Ecken erhalten orange Kreisbögen mit dem Mittellinienradius `(s+d)/2`, beschriftet mit dem Innenradius `s/2`. Die Radiuswerte stehen zusätzlich in einer Tabelle. Das dünne gepunktete Maßpolygon bleibt als Bezug sichtbar. Ein geändertes `s` oder `d` aktualisiert die Rundung. Bei fehlendem Rollendurchmesser, zu kurzen Schenkeln oder 180°-Haken bleibt das Polygon mit einem Hinweis erhalten; Radien werden niemals stillschweigend verkleinert. Die Rundung ersetzt keine vollständige Umrechnung der BVBS-Außenmaße. Gewicht im Header bezeichnet die einzelne Biegeform, nicht das Gesamtgewicht der Stückzahl.

`examples/` enthält einen geraden Stab, L-/U-Form, eine Mehrpositionsdatei und das offizielle BF2D-Beispiel 1. `generate_examples.py` erzeugt diese Dateien reproduzierbar. `Example_Files/` bleibt unverändert.

Die reale Beispieldatei enthält 74 darstellbare Positionen in Windows-1252. Der ausgelassene Planindex `i` wird beim Import mit Warnung toleriert; Nicht-ASCII-Prüfsummen bleiben unbestätigt. Ein geprüfter Export dieser Datei ist gesperrt.

## Prüfung und Projektaufbau

37 Tests bestanden: unabhängige offizielle Prüfsummenwerte, Geometrie, Winkelvorzeichen, doppelte Positionen, verlustarme Einzeländerungen, BOM/Encoding/Zeilenenden, Sonderformen, Wiederimport, Exportsperren, veraltete Vorschau und Import der realen Datei. Streamlit-AppTest prüft Auswahl → Editoränderung → Grafikzustand → Downloadangebote und Moduswechsel. Da AppTest den Datei-Uploader nicht direkt befüllen kann, initialisiert der Test mit derselben `Document.load`-Funktion wie der Upload. Das native Uploadfenster, Plotly-Mausgesten und ein tatsächlicher Browserdownload sind nicht automatisiert getestet.

- `app.py`: mehrseitiger Einstieg mit `st.navigation`.
- `bvbs/`: Streamlit-unabhängige Modelle, Tokenizer, Parser, Geometrie, Prüfung und Serialisierung.
- `ui/`: Sitzungszustand, Plotly und beide Seiten; `dstv/`: separate NC-Fachlogik.
- `tests/`, `examples/`, `docs/bvbs_support.md`: Tests, Daten und fachlicher Prüfumfang.

Verarbeitung im Speicher der jeweiligen Sitzung, ohne externe Dienste oder KI-API. Bei lokalem Start bleibt die Verarbeitung auf diesem Rechner; eine spätere Serverbereitstellung würde die Uploads auf dem Server verarbeiten.


## Stahlbau – DSTV / NC / NC1

Die zweite Seite ist jetzt ein integrierter DSTV-Viewer und Texteditor. Links eine oder mehrere `.nc`-/`.nc1`-Dateien laden, ein aktives Einzelteil wählen und dessen gesamten Text bearbeiten. Die Endung allein genügt nicht: G-Code wird als anderer, nicht unterstützter NC-Dialekt erkannt. Mehrere Dateien bleiben getrennte Bauteile, auch bei gleichen Namen. ABS- und NC-Entwürfe sowie die Auswahl bleiben beim Seitenwechsel erhalten.

**Beide Projektbeispiele laden** öffnet den HEA300-Träger `B001_HEA300.nc1` und die separate Steife `S001_Stiffener.nc1`. Eine Position der Steife am Träger wird nicht aus einem Kommentar erfunden. Außerdem stehen drei zusätzliche Lehrbeispiele zur Auswahl: Blech mit Bohrungen/Innenausschnitt, Träger mit Bearbeitungen auf allen vier Flächen und eine Datei mit nicht unterstütztem Block.

Beispieländerung: Im Träger die BO-Zeile `o 500.00u 75.00 22.00 0.00` zu `o 700.00u 75.00 26.00 0.00` ändern. Beim übernommenen Änderungsereignis verschiebt sich die Bohrung auf der o-Fläche um 200 mm längs des Trägers; ihr Durchmesser steigt auf 26 mm. **Übernehmen und prüfen** löst dieselbe Verarbeitung aus. Sichtbarer Zeilenumbruch im Textfeld bleibt eine reine Anzeige. Änderungen werden nicht bei jedem Tastendruck versprochen.

Tabs zeigen v/h (Steg) und o/u (Flansche) getrennt, mit Ursprung, Achsen, Blickrichtung und schematischem Querschnitt. Für Bleche ist v unterstützt. Kreise sind maßstäblich; Ankörnungen sind Kreuze, Innenausschnitte helle Öffnungen. Die Standardskizzen sind zur besseren Lesbarkeit gedreht: x+ immer rechts, q+ bei v/u oben und bei h/o unten. Originalkonturen können grau gestrichelt eingeblendet werden. Eine Zeile in der Bearbeitungstabelle anklicken oder das Element im Auswahlfeld wählen, um es orange hervorzuheben.

Der Träger enthält einen PU-Markierungsblock. Bekannte Stegbohrungen und der Ausschnitt werden als **unvollständige Fläche** gezeigt; die Markierung wird nicht als Schnitt oder Schweißnaht umgedeutet. Andere sicher unterstützte Flächen bleiben sichtbar. Der geprüfte Export dieser Datei bleibt gesperrt.

**Original herunterladen** liefert die Uploadbytes; **Entwurf herunterladen** sichert auch fehlerhafte Eingaben. **Export nach unterstützten Prüfungen** ist für vollständige unterstützte B-/I-Dateien mit ST/EN, normalen BO-Bearbeitungen und geradlinigen AK/IK-Konturen verfügbar. Er prüft den endgültigen Text erneut und ergänzt keine Prüfsumme. Nicht unterstützte Blöcke, Konturradien, Sonderbohrungen oder unklare Profiländerungen sperren ihn. Keine Tragfähigkeits-, Mindestabstands- oder Maschinenfreigabe. Bei Fehlern bleibt der letzte gültige Stand mit deutlicher Kennzeichnung sichtbar; seine Eigenschaften stammen ebenfalls aus dieser alten Revision.

Konturen und Lochkoordinaten werden bei Headeränderungen niemals automatisch skaliert. Headermaße haben Vorrang vor dem Profilnamen; keine erfundenen Nennprofilmaße. Die HEA300-Beispiele sind mit einer Herstellerprofiltabelle abgeglichen. Profilname/-maßänderungen lassen abhängige Kennwerte ungeklärt. Ausführliche Flächenregeln, Quellen und Grenzen: [docs/dstv_support.md](docs/dstv_support.md).

Der aktuelle Gesamtstand hat **71 bestandene Tests**, einschließlich sämtlicher BVBS-Regressionen und integrierter Tests für Datei-/Seitenwechsel. AppTest verwendet für die Importtests dieselbe Ladefunktion wie der Upload; das native Uploadfenster, Browserdownloads, direkte Tabellen-Mausselektion und Plotly-Mausgesten sind nicht automatisiert getestet.

Die bisherigen uv-Befehle gelten unverändert; Shapely für die Konturprüfung ist in `pyproject.toml` und `uv.lock` ergänzt:

```powershell
uv sync
uv run streamlit run app.py
uv run pytest
```

## Bereitstellung auf Streamlit Community Cloud

Den Projektquellcode einschließlich `app.py`, `bvbs/`, `dstv/`, `ui/` und `examples/` ins GitHub-Repository übernehmen. Die lokale `.venv` und temporäre Dateien bleiben durch `.gitignore` ausgeschlossen.

In Streamlit Community Cloud das Repository und den Branch auswählen, als Einstiegspunkt **`app.py`** angeben und unter den erweiterten Einstellungen **Python 3.12** wählen, entsprechend der lokal getesteten Umgebung.

`requirements.txt` enthält ausschließlich die direkten Laufzeitabhängigkeiten in den getesteten Versionen. Testabhängigkeiten wie pytest sind dort nicht erforderlich. Die lokale Projektverwaltung erfolgt weiterhin mit uv.

Laut [Streamlit-Dokumentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) hat `uv.lock` Vorrang vor `requirements.txt`, wenn beide neben `app.py` liegen. Dieses Repository kann daher direkt über die vorhandene uv-Lockdatei bereitgestellt werden; die requirements-Datei ist zusätzlich als Alternative verfügbar. Keine zusätzliche Betriebssystem-Paketdatei ist für die hier verwendeten Laufzeitfunktionen erforderlich.

Bei einer gehosteten App werden hochgeladene ABS-/NC-Dateien auf dem Streamlit-Server in der jeweiligen Sitzung verarbeitet.
