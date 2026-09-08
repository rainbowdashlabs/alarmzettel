"""
Authored interrogation trees for BRAND and TECHNISCHE HILFELEISTUNG.

Berlin's Alarm- und Ausrückeordnung is classified "Nur für den Dienstgebrauch" and the FPDS
determinant codes are licensed IAED material, so neither can be derived from public data. These
trees are written for this tool: the shape and the vocabulary follow what the AAO is publicly
known to do — three disciplines, levels raised a step at a time — but every question, answer and
determinant here is invented and must be replaced with the real Ausrückeordnung before anyone
relies on it operationally.
"""

BRAND = [
    ("67", "Brand im Freien", "Was brennt im Freien?", [
        ("Mülltonne, Container", "Es handelt sich um einen Brand im Freien.", "Wie groß ist der Brand?", [
            ("Ein KLEINER Bereich brennt", "Ein KLEINER Bereich brennt.", "67B03", "BRAND K.", "Brand im Freien - Kleiner Bereich"),
            ("Mehrere Behälter brennen", "Mehrere Behälter brennen.", "67C02", "BRAND M.", "Brand im Freien - Mehrere Behälter"),
            ("Ausbreitung auf Gebäude droht", "Eine Ausbreitung auf ein Gebäude droht.", "67D01", "BRAND 1", "Brand im Freien - Ausbreitungsgefahr"),
            ("Unbekannte Situation", "Die Situation ist dem Anrufer nicht bekannt.", "67B01", "BRAND K.", "Brand im Freien - Unbekannte Situation"),
        ]),
        ("Hecke, Gebüsch, Grünfläche", "Eine Grünfläche brennt.", "Wie groß ist die Fläche?", [
            ("Unter 100 m²", "Die brennende Fläche ist kleiner als 100 m².", "67B05", "BRAND K.", "Vegetationsbrand - Kleinfläche"),
            ("100 bis 1000 m²", "Die brennende Fläche beträgt 100 bis 1000 m².", "67C05", "BRAND 1", "Vegetationsbrand - Mittlere Fläche"),
            ("Über 1000 m²", "Die brennende Fläche ist größer als 1000 m².", "67D05", "BRAND 3", "Vegetationsbrand - Großfläche"),
        ]),
        ("Abfall, Sperrmüll im Freien", "Abfall im Freien brennt.", None, [
            ("Ohne Ausbreitungsgefahr", "Eine Ausbreitung ist nicht zu erwarten.", "67A01", "BRAND K.", "Kleinbrand im Freien"),
            ("Mit Ausbreitungsgefahr", "Eine Ausbreitung ist zu erwarten.", "67C01", "BRAND M.", "Brand im Freien - Ausbreitungsgefahr"),
        ]),
    ]),
    ("69", "Gebäudebrand", "Welcher Gebäudeteil ist betroffen?", [
        ("Wohnung", "Es brennt in einer Wohnung.", "Sind Personen betroffen?", [
            ("Keine Personen gemeldet", "Personen sind nach derzeitiger Kenntnis nicht betroffen.", "69C01", "BRAND 2", "Wohnungsbrand"),
            ("Personen in Gefahr", "Personen befinden sich in unmittelbarer Gefahr.", "69D01", "BRAND 3", "Wohnungsbrand mit Menschenleben in Gefahr"),
            ("Menschenrettung über Leiter nötig", "Eine Menschenrettung über tragbare Leitern oder Drehleiter ist erforderlich.", "69E01", "BRAND 4", "Wohnungsbrand - Menschenrettung"),
        ]),
        ("Keller", "Es brennt im Keller.", None, [
            ("Verrauchung im Treppenraum", "Der Treppenraum ist verraucht.", "69D02", "BRAND 3", "Kellerbrand mit Verrauchung"),
            ("Keine Verrauchung gemeldet", "Eine Verrauchung ist nicht gemeldet.", "69C02", "BRAND 2", "Kellerbrand"),
        ]),
        ("Dachstuhl", "Es brennt im Dachstuhl.", None, [
            ("Kleiner Bereich", "Ein kleiner Bereich des Dachstuhls brennt.", "69C03", "BRAND 2", "Dachstuhlbrand"),
            ("Dachstuhl in voller Ausdehnung", "Der Dachstuhl brennt in voller Ausdehnung.", "69E03", "BRAND 6", "Dachstuhlbrand in voller Ausdehnung"),
        ]),
        ("Treppenraum, Flur", "Es brennt im Treppenraum.", None, [
            ("Rettungsweg betroffen", "Der bauliche Rettungsweg ist betroffen.", "69D04", "BRAND 4", "Brand im Rettungsweg"),
        ]),
    ]),
    ("70", "Brandmeldeanlage", "Was meldet die Anlage?", [
        ("Automatischer Melder ausgelöst", "Ein automatischer Melder hat ausgelöst.", None, [
            ("Kein Brandereignis erkennbar", "Ein Brandereignis ist vor Ort nicht erkennbar.", "70A01", "BRAND K.", "Brandmeldeanlage - Auslösung"),
            ("Objekt mit erhöhtem Risiko", "Das Objekt ist als Sonderbau eingestuft.", "70C01", "BRAND 2", "Brandmeldeanlage - Sonderbau"),
        ]),
        ("Handfeuermelder ausgelöst", "Ein Handfeuermelder wurde betätigt.", None, [
            ("Ohne weitere Angaben", "Weitere Angaben liegen nicht vor.", "70B02", "BRAND 1", "Brandmeldeanlage - Handmelder"),
        ]),
    ]),
    ("71", "Fahrzeugbrand", "Welches Fahrzeug brennt?", [
        ("PKW", "Ein PKW brennt.", None, [
            ("Im Freien, keine Ausbreitung", "Das Fahrzeug steht im Freien, eine Ausbreitung ist nicht zu erwarten.", "71B01", "BRAND K.", "PKW-Brand"),
            ("In Tiefgarage oder Gebäude", "Das Fahrzeug steht in einer Tiefgarage oder einem Gebäude.", "71D01", "BRAND 3", "Fahrzeugbrand in Tiefgarage"),
            ("Elektrofahrzeug", "Es handelt sich um ein Fahrzeug mit Hochvoltbatterie.", "71C01", "BRAND M.", "Fahrzeugbrand - Hochvoltbatterie"),
        ]),
        ("LKW, Bus", "Ein LKW oder Bus brennt.", None, [
            ("Ohne Gefahrgut", "Gefahrgut wird nicht mitgeführt.", "71C02", "BRAND 1", "LKW-Brand"),
            ("Mit Gefahrgut", "Das Fahrzeug führt Gefahrgut mit.", "71E02", "BRAND 4", "LKW-Brand mit Gefahrgut"),
        ]),
        ("Schienenfahrzeug", "Ein Schienenfahrzeug brennt.", None, [
            ("Im Tunnel oder Bahnhof", "Das Fahrzeug befindet sich im Tunnel oder Bahnhof.", "71E03", "BRAND 8", "Schienenfahrzeugbrand im Tunnel"),
            ("Auf freier Strecke", "Das Fahrzeug befindet sich auf freier Strecke.", "71D03", "BRAND 4", "Schienenfahrzeugbrand"),
        ]),
    ]),
    ("72", "Rauchentwicklung, Brandgeruch", "Was wird wahrgenommen?", [
        ("Brandgeruch im Gebäude", "Im Gebäude ist Brandgeruch wahrnehmbar.", None, [
            ("Ursache unklar", "Die Ursache ist unklar.", "72A01", "BRAND K.", "Brandgeruch - Ursache unklar"),
        ]),
        ("Rauch aus einem Gebäude", "Aus dem Gebäude tritt Rauch aus.", None, [
            ("Leichte Rauchentwicklung", "Es liegt eine leichte Rauchentwicklung vor.", "72B02", "BRAND M.", "Rauchentwicklung aus Gebäude"),
            ("Starke Rauchentwicklung", "Es liegt eine starke Rauchentwicklung vor.", "72D02", "BRAND 3", "Starke Rauchentwicklung aus Gebäude"),
        ]),
        ("Kohlenmonoxid-Warner", "Ein Kohlenmonoxid-Warner hat ausgelöst.", None, [
            ("Ohne Beschwerden", "Beschwerden werden nicht angegeben.", "72B03", "BRAND M.", "CO-Warnmeldung"),
            ("Mit Beschwerden", "Betroffene klagen über Beschwerden.", "72D03", "BRAND 2", "CO-Warnmeldung mit Betroffenen"),
        ]),
    ]),
    ("73", "Industrie- und Gewerbebrand", "Welcher Bereich brennt?", [
        ("Produktions- oder Lagerhalle", "Eine Produktions- oder Lagerhalle brennt.", None, [
            ("Entstehungsbrand", "Es handelt sich um einen Entstehungsbrand.", "73C01", "BRAND 2", "Gewerbebrand - Entstehungsbrand"),
            ("Halle in voller Ausdehnung", "Die Halle brennt in voller Ausdehnung.", "73E01", "BRAND 10", "Hallenbrand in voller Ausdehnung"),
        ]),
        ("Anlage mit Gefahrstoffen", "Eine Anlage mit Gefahrstoffen ist betroffen.", None, [
            ("Freisetzung möglich", "Eine Freisetzung von Gefahrstoffen ist möglich.", "73E02", "BRAND 8", "Industriebrand mit Gefahrstoffen"),
        ]),
    ]),
]

TH = [
    ("29", "Verkehrsunfall", "Sind Personen eingeklemmt?", [
        ("Keine Person eingeklemmt", "Es ist niemand eingeklemmt.", "Wie viele Fahrzeuge sind beteiligt?", [
            ("Ein Fahrzeug", "Ein Fahrzeug ist beteiligt.", "29B10", "TH K.", "Verkehrsunfall ohne eingeklemmte Person"),
            ("Zwei oder mehr Fahrzeuge", "Zwei oder mehr Fahrzeuge sind beteiligt.", "29C10", "TH M.", "Verkehrsunfall - mehrere Fahrzeuge"),
        ]),
        ("Person eingeklemmt", "Mindestens eine Person ist eingeklemmt.", "Wie viele Personen?", [
            ("Eine Person", "Eine Person ist eingeklemmt.", "29D11", "TH 1", "Verkehrsunfall mit eingeklemmter Person"),
            ("Mehrere Personen", "Mehrere Personen sind eingeklemmt.", "29D12", "TH 2", "Verkehrsunfall mit mehreren eingeklemmten Personen"),
        ]),
        ("LKW oder Bus beteiligt", "Ein LKW oder Bus ist beteiligt.", None, [
            ("Ohne Gefahrgut", "Gefahrgut wird nicht mitgeführt.", "29D13", "TH 2", "Verkehrsunfall mit LKW oder Bus"),
            ("Mit Gefahrgut", "Das Fahrzeug führt Gefahrgut mit.", "29E13", "TH 3", "Verkehrsunfall mit Gefahrgut"),
        ]),
        ("Schienenfahrzeug beteiligt", "Ein Schienenfahrzeug ist beteiligt.", None, [
            ("Person im Gleisbereich", "Eine Person befindet sich im Gleisbereich.", "29E14", "TH 3", "Verkehrsunfall im Gleisbereich"),
        ]),
    ]),
    ("50", "Türöffnung", "Warum wird geöffnet?", [
        ("Hilflose Person vermutet", "Hinter der Tür wird eine hilflose Person vermutet.", None, [
            ("Person reagiert nicht", "Die Person reagiert nicht auf Ansprache.", "50C01", "TH K.", "Türöffnung - hilflose Person"),
            ("Rettungsdienst vor Ort", "Der Rettungsdienst ist bereits vor Ort.", "50C02", "TH K.", "Türöffnung für Rettungsdienst"),
        ]),
        ("Kein Hinweis auf Gefahr", "Ein Hinweis auf eine Gefahr liegt nicht vor.", None, [
            ("Nachbarschaftshilfe", "Es besteht kein Zeitdruck.", "50A01", "TH K.", "Türöffnung ohne Gefahr im Verzug"),
        ]),
        ("Herd oder Wasser läuft", "Ein Herd oder Wasserhahn ist unbeaufsichtigt in Betrieb.", None, [
            ("Rauch wahrnehmbar", "Rauch ist wahrnehmbar.", "50D01", "TH M.", "Türöffnung mit Rauchentwicklung"),
        ]),
    ]),
    ("51", "Aufzugnotbefreiung", "Wer ist eingeschlossen?", [
        ("Person ohne Beschwerden", "Die eingeschlossene Person ist ansprechbar und ohne Beschwerden.", None, [
            ("Aufzugsfirma nicht verfügbar", "Der Aufzugsnotdienst ist nicht kurzfristig verfügbar.", "51A01", "TH K.", "Aufzugnotbefreiung"),
        ]),
        ("Person mit Beschwerden", "Die eingeschlossene Person klagt über Beschwerden.", None, [
            ("Medizinischer Notfall", "Es liegt zusätzlich ein medizinischer Notfall vor.", "51C01", "TH M.", "Aufzugnotbefreiung mit Notfall"),
        ]),
        ("Kind allein eingeschlossen", "Ein Kind ist allein eingeschlossen.", None, [
            ("Ohne weitere Angaben", "Weitere Angaben liegen nicht vor.", "51B01", "TH K.", "Aufzugnotbefreiung - Kind"),
        ]),
    ]),
    ("52", "Wasserschaden", "Woher kommt das Wasser?", [
        ("Rohrbruch im Gebäude", "Im Gebäude ist eine Leitung gebrochen.", None, [
            ("Einzelne Wohnung", "Betroffen ist eine einzelne Wohnung.", "52A01", "TH K.", "Wasserschaden - Wohnung"),
            ("Mehrere Geschosse", "Mehrere Geschosse sind betroffen.", "52C01", "TH 1", "Wasserschaden - mehrere Geschosse"),
            ("Elektroanlage betroffen", "Die Elektroanlage ist betroffen.", "52C02", "TH M.", "Wasserschaden an Elektroanlage"),
        ]),
        ("Starkregen, Überflutung", "Es liegt eine Überflutung nach Starkregen vor.", None, [
            ("Keller unter Wasser", "Ein Keller steht unter Wasser.", "52B02", "TH K.", "Überflutung - Keller"),
            ("Personen in Gefahr", "Personen sind durch das Wasser gefährdet.", "52D02", "TH 2", "Überflutung mit Personengefährdung"),
        ]),
    ]),
    ("53", "Sturmschaden", "Was ist betroffen?", [
        ("Baum droht zu stürzen oder liegt", "Ein Baum liegt oder droht zu stürzen.", None, [
            ("Keine Gefahr für Personen", "Personen sind nicht gefährdet.", "53A01", "TH K.", "Sturmschaden - Baum"),
            ("Straße blockiert", "Eine Straße ist blockiert.", "53B01", "TH K.", "Sturmschaden - Straße blockiert"),
            ("Person getroffen oder eingeschlossen", "Eine Person ist getroffen oder eingeschlossen.", "53D01", "TH 2", "Sturmschaden mit Personenschaden"),
        ]),
        ("Bauteil droht herabzustürzen", "Ein Bauteil droht herabzustürzen.", None, [
            ("Über öffentlichem Verkehrsraum", "Der Bereich liegt über öffentlichem Verkehrsraum.", "53C02", "TH M.", "Absturzgefahr Bauteil"),
        ]),
    ]),
    ("54", "Person in Notlage", "Wo befindet sich die Person?", [
        ("In der Höhe", "Die Person befindet sich in der Höhe.", None, [
            ("Auf einem Dach oder Kran", "Die Person befindet sich auf einem Dach oder Kran.", "54D01", "TH 2", "Höhenrettung"),
            ("Absturzgefahr", "Es besteht unmittelbare Absturzgefahr.", "54E01", "TH 3", "Höhenrettung mit Absturzgefahr"),
        ]),
        ("In der Tiefe", "Die Person befindet sich in der Tiefe.", None, [
            ("Schacht oder Grube", "Die Person befindet sich in einem Schacht oder einer Grube.", "54D02", "TH 2", "Rettung aus Tiefe"),
        ]),
        ("Im Wasser", "Die Person befindet sich im Wasser.", None, [
            ("Person treibt oder ruft um Hilfe", "Die Person treibt im Wasser oder ruft um Hilfe.", "54E03", "TH 3", "Wasserrettung"),
            ("Person auf Eisfläche eingebrochen", "Die Person ist in eine Eisfläche eingebrochen.", "54E04", "TH 3", "Eisrettung"),
        ]),
        ("Verschüttet oder eingeschlossen", "Die Person ist verschüttet oder eingeschlossen.", None, [
            ("Nach Einsturz", "Ein Einsturz ist vorausgegangen.", "54E05", "TH 3", "Rettung nach Einsturz"),
        ]),
    ]),
    ("55", "Gefahrstoffe", "Welcher Stoff tritt aus?", [
        ("Betriebsmittel, Öl, Kraftstoff", "Betriebsmittel sind ausgetreten.", None, [
            ("Ölspur auf der Fahrbahn", "Auf der Fahrbahn befindet sich eine Ölspur.", "55A01", "TH K.", "Ölspur"),
            ("Austritt aus einem Fahrzeug", "Betriebsmittel treten aus einem Fahrzeug aus.", "55B01", "TH K.", "Betriebsmittelaustritt"),
        ]),
        ("Gas", "Gas tritt aus.", None, [
            ("Gasgeruch im Freien", "Im Freien ist Gasgeruch wahrnehmbar.", "55C02", "TH M.", "Gasgeruch im Freien"),
            ("Gasgeruch im Gebäude", "Im Gebäude ist Gasgeruch wahrnehmbar.", "55D02", "TH 2", "Gasaustritt im Gebäude"),
            ("Beschädigte Versorgungsleitung", "Eine Versorgungsleitung wurde beschädigt.", "55D03", "TH 3", "Beschädigte Gasleitung"),
        ]),
        ("Unbekannter Stoff", "Ein unbekannter Stoff ist ausgetreten.", None, [
            ("Ohne Betroffene", "Betroffene gibt es nicht.", "55C04", "TH M.", "Unbekannter Stoff"),
            ("Mit Betroffenen", "Es gibt Betroffene.", "55E04", "TH 3", "Unbekannter Stoff mit Betroffenen"),
        ]),
    ]),
    ("56", "Tierrettung", "Welches Tier und wo?", [
        ("Tier in Notlage", "Ein Tier befindet sich in einer Notlage.", None, [
            ("Katze auf Baum oder Dach", "Ein Tier befindet sich auf einem Baum oder Dach.", "56A01", "TH K.", "Tierrettung aus Höhe"),
            ("Tier in Schacht oder Kanal", "Ein Tier befindet sich in einem Schacht.", "56B01", "TH K.", "Tierrettung aus Tiefe"),
            ("Großtier verunfallt", "Ein Großtier ist verunfallt.", "56C01", "TH M.", "Großtierrettung"),
        ]),
    ]),
]
