"""
Authored interrogation graphs for BRAND and TECHNISCHE HILFELEISTUNG.

Berlin's Alarm- und Ausrückeordnung is classified "Nur für den Dienstgebrauch" and the FPDS
determinant codes are licensed IAED material, so neither can be derived from public data. These
graphs are written for this tool: the shape and the vocabulary follow what the AAO is publicly
known to do — three disciplines, levels raised a step at a time — but every question, answer and
determinant here is invented and must be replaced with the real Ausrückeordnung before anyone
relies on it operationally.

An entry is either a question with answers below it,

    (label, aussage, frage, [answers])

or the end of the interrogation at a determinant,

    (label, aussage, code, stichwort, anlass)

and the two nest as deep as a protocol needs.
"""


def menschen(protokoll, nummer, anlass, ohne, gefaehrdet, rettung):
    """
    The question a fire is judged by, and the reason the tree runs deeper than the others: it is
    asked last, because the answer is what sets the Stichwort. The same fire is a different alarm
    with people still inside, so the situation only fixes the base level and this raises it.

    Returns the tail of an answer — question and children — to be spliced in with `*`.
    """
    return ("Sind Menschen in Gefahr?", [
        ("Niemand in Gefahr",
         "Menschen sind nach derzeitiger Kenntnis nicht in Gefahr.",
         f"{protokoll}C{nummer}", ohne, anlass),
        ("Personen im Gefahrenbereich",
         "Personen befinden sich im Gefahrenbereich.",
         f"{protokoll}D{nummer}", gefaehrdet, f"{anlass} - Personen im Gefahrenbereich"),
        ("Menschenleben in Gefahr, Rettung erforderlich",
         "Menschenleben sind in Gefahr, eine Menschenrettung ist erforderlich.",
         f"{protokoll}E{nummer}", rettung, f"{anlass} - Menschenrettung"),
        ("Unbekannt, ob Menschen betroffen sind",
         "Ob Menschen betroffen sind, ist nicht bekannt.",
         f"{protokoll}D{nummer}U", gefaehrdet, f"{anlass} - Betroffenheit unbekannt"),
    ])


def personen(protokoll, nummer, anlass, ohne, betroffen, rettung):
    """
    The same question for a technical call, where it turns on whether anyone has come to harm
    rather than on whether anyone is still inside.
    """
    return ("Sind Personen betroffen?", [
        ("Niemand betroffen",
         "Personen sind nicht betroffen.",
         f"{protokoll}A{nummer}", ohne, anlass),
        ("Personen betroffen, ansprechbar",
         "Personen sind betroffen und ansprechbar.",
         f"{protokoll}C{nummer}", betroffen, f"{anlass} - Personen betroffen"),
        ("Personen eingeschlossen oder nicht ansprechbar",
         "Personen sind eingeschlossen oder nicht ansprechbar.",
         f"{protokoll}E{nummer}", rettung, f"{anlass} - Personenrettung"),
        ("Unbekannt, ob Personen betroffen sind",
         "Ob Personen betroffen sind, ist nicht bekannt.",
         f"{protokoll}C{nummer}U", betroffen, f"{anlass} - Betroffenheit unbekannt"),
    ])


BRAND = [
    ("67", "Brand im Freien", "Was brennt im Freien?", [
        ("Mülltonne, Container", "Es handelt sich um einen Brand im Freien.",
         *menschen("67", "01", "Brand im Freien - Behälter", "BRAND K.", "BRAND M.", "BRAND 2")),
        ("Abfall, Sperrmüll im Freien", "Abfall im Freien brennt.",
         *menschen("67", "02", "Kleinbrand im Freien", "BRAND K.", "BRAND M.", "BRAND 2")),
        ("Gartenlaube, Schuppen", "Eine Laube oder ein Schuppen brennt.",
         *menschen("67", "03", "Brand einer Laube", "BRAND M.", "BRAND 1", "BRAND 2")),
        ("Hecke, Gebüsch, Grünfläche", "Eine Grünfläche brennt.", "Wie groß ist die Fläche?", [
            ("Unter 100 m²", "Die brennende Fläche ist kleiner als 100 m².",
             *menschen("67", "05", "Vegetationsbrand - Kleinfläche", "BRAND K.", "BRAND M.", "BRAND 2")),
            ("100 bis 1000 m²", "Die brennende Fläche beträgt 100 bis 1000 m².",
             *menschen("67", "06", "Vegetationsbrand - Mittlere Fläche", "BRAND 1", "BRAND 2", "BRAND 3")),
            ("Über 1000 m²", "Die brennende Fläche ist größer als 1000 m².",
             *menschen("67", "07", "Vegetationsbrand - Großfläche", "BRAND 3", "BRAND 4", "BRAND 6")),
        ]),
        ("Unklar, was brennt", "Was brennt, ist dem Anrufer nicht bekannt.",
         *menschen("67", "09", "Brand im Freien - Lage unklar", "BRAND K.", "BRAND M.", "BRAND 2")),
    ]),
    ("68", "Brand in Verkehrsanlagen", "Wo brennt es?", [
        ("U-Bahn-Tunnel oder -Bahnhof", "Der Brand liegt in einer U-Bahn-Anlage.",
         *menschen("68", "01", "Brand in U-Bahn-Anlage", "BRAND 8", "BRAND 8", "BRAND 10")),
        ("Eisenbahntunnel oder Bahnhof", "Der Brand liegt in einer Eisenbahnanlage.",
         *menschen("68", "02", "Brand in Bahnanlage", "BRAND 6", "BRAND 8", "BRAND 10")),
        ("Straßentunnel", "Der Brand liegt in einem Straßentunnel.",
         *menschen("68", "03", "Brand im Straßentunnel", "BRAND 6", "BRAND 8", "BRAND 10")),
        ("Parkhaus, Tiefgarage", "Der Brand liegt in einem Parkhaus oder einer Tiefgarage.",
         *menschen("68", "04", "Brand in Tiefgarage", "BRAND 3", "BRAND 4", "BRAND 6")),
    ]),
    ("69", "Gebäudebrand", "Welcher Gebäudeteil ist betroffen?", [
        ("Wohnung", "Es brennt in einer Wohnung.",
         *menschen("69", "01", "Wohnungsbrand", "BRAND 2", "BRAND 3", "BRAND 4")),
        ("Keller", "Es brennt im Keller.", "Ist der Treppenraum verraucht?", [
            ("Treppenraum frei", "Der Treppenraum ist frei.",
             *menschen("69", "02", "Kellerbrand", "BRAND 2", "BRAND 3", "BRAND 4")),
            ("Treppenraum verraucht", "Der Treppenraum ist verraucht.",
             *menschen("69", "03", "Kellerbrand mit Verrauchung", "BRAND 3", "BRAND 4", "BRAND 6")),
        ]),
        ("Dachstuhl", "Es brennt im Dachstuhl.", "Wie weit ist der Brand fortgeschritten?", [
            ("Kleiner Bereich", "Ein kleiner Bereich des Dachstuhls brennt.",
             *menschen("69", "04", "Dachstuhlbrand", "BRAND 2", "BRAND 3", "BRAND 4")),
            ("In voller Ausdehnung", "Der Dachstuhl brennt in voller Ausdehnung.",
             *menschen("69", "05", "Dachstuhlbrand in voller Ausdehnung", "BRAND 6", "BRAND 6", "BRAND 8")),
        ]),
        ("Treppenraum, Flur", "Es brennt im Treppenraum.",
         *menschen("69", "06", "Brand im Rettungsweg", "BRAND 3", "BRAND 4", "BRAND 6")),
        ("Gewerbeeinheit im Wohnhaus", "Es brennt in einer Gewerbeeinheit im Wohnhaus.",
         *menschen("69", "07", "Brand in Gewerbeeinheit", "BRAND 2", "BRAND 3", "BRAND 4")),
        ("Unklar, wo es brennt", "Wo es brennt, ist dem Anrufer nicht bekannt.",
         *menschen("69", "09", "Gebäudebrand - Lage unklar", "BRAND 2", "BRAND 3", "BRAND 4")),
    ]),
    ("70", "Brandmeldeanlage", "Was meldet die Anlage?", [
        ("Automatischer Melder ausgelöst", "Ein automatischer Melder hat ausgelöst.",
         "Was ist vor Ort erkennbar?", [
            ("Kein Brandereignis erkennbar", "Ein Brandereignis ist vor Ort nicht erkennbar.",
             "70A01", "BRAND K.", "Brandmeldeanlage - Auslösung"),
            ("Niemand vor Ort, der nachsehen kann", "Vor Ort ist niemand, der nachsehen kann.",
             "70B01", "BRAND 1", "Brandmeldeanlage - unbestätigt"),
            ("Rauch oder Feuer erkennbar", "Rauch oder Feuer ist erkennbar.",
             *menschen("70", "02", "Brandmeldeanlage mit Brandereignis", "BRAND 2", "BRAND 3", "BRAND 4")),
        ]),
        ("Handfeuermelder ausgelöst", "Ein Handfeuermelder wurde betätigt.",
         *menschen("70", "04", "Brandmeldeanlage - Handmelder", "BRAND 1", "BRAND 2", "BRAND 3")),
        ("Sprinkleranlage ausgelöst", "Eine Sprinkleranlage hat ausgelöst.",
         *menschen("70", "05", "Sprinkleranlage ausgelöst", "BRAND 2", "BRAND 3", "BRAND 4")),
        ("Anlage in einem Sonderbau", "Die Anlage steht in einem Sonderbau.",
         *menschen("70", "06", "Brandmeldeanlage - Sonderbau", "BRAND 2", "BRAND 4", "BRAND 6")),
    ]),
    ("71", "Fahrzeugbrand", "Welches Fahrzeug brennt?", [
        ("PKW", "Ein PKW brennt.", "Wo steht das Fahrzeug?", [
            ("Im Freien", "Das Fahrzeug steht im Freien.",
             *menschen("71", "01", "PKW-Brand", "BRAND K.", "BRAND M.", "BRAND 2")),
            ("In Tiefgarage oder Gebäude", "Das Fahrzeug steht in einer Tiefgarage oder einem Gebäude.",
             *menschen("71", "02", "Fahrzeugbrand in Tiefgarage", "BRAND 3", "BRAND 4", "BRAND 6")),
            ("Fahrzeug mit Hochvoltbatterie", "Es handelt sich um ein Fahrzeug mit Hochvoltbatterie.",
             *menschen("71", "03", "Fahrzeugbrand - Hochvoltbatterie", "BRAND M.", "BRAND 2", "BRAND 3")),
        ]),
        ("LKW, Bus", "Ein LKW oder Bus brennt.", "Wird Gefahrgut mitgeführt?", [
            ("Kein Gefahrgut", "Gefahrgut wird nicht mitgeführt.",
             *menschen("71", "04", "LKW-Brand", "BRAND 1", "BRAND 2", "BRAND 3")),
            ("Gefahrgut", "Das Fahrzeug führt Gefahrgut mit.",
             *menschen("71", "05", "LKW-Brand mit Gefahrgut", "BRAND 4", "BRAND 6", "BRAND 8")),
        ]),
        ("Schienenfahrzeug", "Ein Schienenfahrzeug brennt.", "Wo befindet es sich?", [
            ("Im Tunnel oder Bahnhof", "Das Fahrzeug befindet sich im Tunnel oder Bahnhof.",
             *menschen("71", "06", "Schienenfahrzeugbrand im Tunnel", "BRAND 8", "BRAND 8", "BRAND 10")),
            ("Auf freier Strecke", "Das Fahrzeug befindet sich auf freier Strecke.",
             *menschen("71", "07", "Schienenfahrzeugbrand", "BRAND 4", "BRAND 4", "BRAND 6")),
        ]),
        ("Boot, Schiff", "Ein Boot oder Schiff brennt.",
         *menschen("71", "08", "Bootsbrand", "BRAND 2", "BRAND 3", "BRAND 4")),
    ]),
    ("72", "Rauchentwicklung, Brandgeruch", "Was wird wahrgenommen?", [
        ("Brandgeruch im Gebäude", "Im Gebäude ist Brandgeruch wahrnehmbar.",
         *menschen("72", "01", "Brandgeruch - Ursache unklar", "BRAND K.", "BRAND M.", "BRAND 2")),
        ("Rauch aus einem Gebäude", "Aus dem Gebäude tritt Rauch aus.", "Wie stark ist der Rauch?", [
            ("Leichte Rauchentwicklung", "Es liegt eine leichte Rauchentwicklung vor.",
             *menschen("72", "02", "Rauchentwicklung aus Gebäude", "BRAND M.", "BRAND 2", "BRAND 3")),
            ("Starke Rauchentwicklung", "Es liegt eine starke Rauchentwicklung vor.",
             *menschen("72", "03", "Starke Rauchentwicklung aus Gebäude", "BRAND 3", "BRAND 4", "BRAND 6")),
        ]),
        ("Kohlenmonoxid-Warner", "Ein Kohlenmonoxid-Warner hat ausgelöst.",
         "Klagen Betroffene über Beschwerden?", [
            ("Ohne Beschwerden", "Beschwerden werden nicht angegeben.",
             "72B04", "BRAND M.", "CO-Warnmeldung"),
            ("Mit Beschwerden", "Betroffene klagen über Beschwerden.",
             "72D04", "BRAND 2", "CO-Warnmeldung mit Betroffenen"),
        ]),
        ("Rauch im Freien, Ursache unklar", "Im Freien ist Rauch sichtbar, die Ursache ist unklar.",
         *menschen("72", "05", "Rauch im Freien - Ursache unklar", "BRAND K.", "BRAND M.", "BRAND 2")),
    ]),
    ("73", "Industrie- und Gewerbebrand", "Welcher Bereich brennt?", [
        ("Produktions- oder Lagerhalle", "Eine Produktions- oder Lagerhalle brennt.",
         "Wie weit ist der Brand fortgeschritten?", [
            ("Entstehungsbrand", "Es handelt sich um einen Entstehungsbrand.",
             *menschen("73", "01", "Gewerbebrand - Entstehungsbrand", "BRAND 2", "BRAND 3", "BRAND 4")),
            ("Halle in voller Ausdehnung", "Die Halle brennt in voller Ausdehnung.",
             *menschen("73", "02", "Hallenbrand in voller Ausdehnung", "BRAND 10", "BRAND 10", "BRAND 10")),
        ]),
        ("Anlage mit Gefahrstoffen", "Eine Anlage mit Gefahrstoffen ist betroffen.",
         *menschen("73", "03", "Industriebrand mit Gefahrstoffen", "BRAND 8", "BRAND 8", "BRAND 10")),
        ("Lager mit Batterien oder Akkus", "Ein Lager mit Batterien oder Akkus brennt.",
         *menschen("73", "04", "Brand eines Batterielagers", "BRAND 4", "BRAND 6", "BRAND 8")),
    ]),
    ("74", "Brand in Sonderobjekt", "Um welches Objekt handelt es sich?", [
        ("Krankenhaus, Pflegeheim", "Betroffen ist ein Krankenhaus oder Pflegeheim.",
         *menschen("74", "01", "Brand in Pflegeeinrichtung", "BRAND 4", "BRAND 6", "BRAND 8")),
        ("Schule, Kindertagesstätte", "Betroffen ist eine Schule oder Kindertagesstätte.",
         *menschen("74", "02", "Brand in Schule oder Kita", "BRAND 3", "BRAND 4", "BRAND 6")),
        ("Versammlungsstätte, Diskothek", "Betroffen ist eine Versammlungsstätte.",
         *menschen("74", "03", "Brand in Versammlungsstätte", "BRAND 6", "BRAND 8", "BRAND 10")),
        ("Hochhaus", "Betroffen ist ein Hochhaus.",
         *menschen("74", "04", "Hochhausbrand", "BRAND 4", "BRAND 6", "BRAND 8")),
        ("Unterkunft, Wohnheim", "Betroffen ist eine Unterkunft oder ein Wohnheim.",
         *menschen("74", "05", "Brand in Unterkunft", "BRAND 3", "BRAND 4", "BRAND 6")),
    ]),
    ("75", "Explosion", "Was ist explodiert?", [
        ("Explosion in einem Gebäude", "In einem Gebäude hat es eine Explosion gegeben.",
         *menschen("75", "01", "Explosion in Gebäude", "BRAND 6", "BRAND 8", "BRAND 10")),
        ("Explosion im Freien", "Im Freien hat es eine Explosion gegeben.",
         *menschen("75", "02", "Explosion im Freien", "BRAND 3", "BRAND 4", "BRAND 6")),
        ("Verpuffung ohne Gebäudeschaden", "Es hat eine Verpuffung ohne Gebäudeschaden gegeben.",
         *menschen("75", "03", "Verpuffung", "BRAND M.", "BRAND 2", "BRAND 3")),
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
        ("LKW oder Bus beteiligt", "Ein LKW oder Bus ist beteiligt.", "Wird Gefahrgut mitgeführt?", [
            ("Kein Gefahrgut", "Gefahrgut wird nicht mitgeführt.", "29D13", "TH 2", "Verkehrsunfall mit LKW oder Bus"),
            ("Gefahrgut", "Das Fahrzeug führt Gefahrgut mit.", "29E13", "TH 3", "Verkehrsunfall mit Gefahrgut"),
        ]),
        ("Schienenfahrzeug beteiligt", "Ein Schienenfahrzeug ist beteiligt.", None, [
            ("Person im Gleisbereich", "Eine Person befindet sich im Gleisbereich.", "29E14", "TH 3", "Verkehrsunfall im Gleisbereich"),
            ("Niemand im Gleisbereich", "Im Gleisbereich befindet sich niemand.", "29D14", "TH 2", "Verkehrsunfall an Bahnanlage"),
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
            ("Kein Rauch wahrnehmbar", "Rauch ist nicht wahrnehmbar.", "50B01", "TH K.", "Türöffnung - Herd in Betrieb"),
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
        ("Rohrbruch im Gebäude", "Im Gebäude ist eine Leitung gebrochen.", "Wie weit reicht der Schaden?", [
            ("Einzelne Wohnung", "Betroffen ist eine einzelne Wohnung.",
             *personen("52", "01", "Wasserschaden - Wohnung", "TH K.", "TH K.", "TH 1")),
            ("Mehrere Geschosse", "Mehrere Geschosse sind betroffen.",
             *personen("52", "02", "Wasserschaden - mehrere Geschosse", "TH 1", "TH 1", "TH 2")),
            ("Elektroanlage betroffen", "Die Elektroanlage ist betroffen.",
             *personen("52", "03", "Wasserschaden an Elektroanlage", "TH M.", "TH 1", "TH 2")),
        ]),
        ("Starkregen, Überflutung", "Es liegt eine Überflutung nach Starkregen vor.", "Was steht unter Wasser?", [
            ("Keller", "Ein Keller steht unter Wasser.",
             *personen("52", "05", "Überflutung - Keller", "TH K.", "TH 1", "TH 2")),
            ("Tiefgarage oder Unterführung", "Eine Tiefgarage oder Unterführung steht unter Wasser.",
             *personen("52", "06", "Überflutung - Tiefgarage", "TH 1", "TH 2", "TH 3")),
        ]),
    ]),
    ("53", "Sturmschaden", "Was ist betroffen?", [
        ("Baum droht zu stürzen oder liegt", "Ein Baum liegt oder droht zu stürzen.", "Was ist versperrt?", [
            ("Nichts versperrt", "Es ist nichts versperrt.",
             *personen("53", "01", "Sturmschaden - Baum", "TH K.", "TH 1", "TH 2")),
            ("Straße oder Gleis blockiert", "Eine Straße oder ein Gleis ist blockiert.",
             *personen("53", "02", "Sturmschaden - Verkehrsweg blockiert", "TH K.", "TH 1", "TH 2")),
        ]),
        ("Bauteil droht herabzustürzen", "Ein Bauteil droht herabzustürzen.", None, [
            ("Über öffentlichem Verkehrsraum", "Der Bereich liegt über öffentlichem Verkehrsraum.", "53C03", "TH M.", "Absturzgefahr Bauteil"),
            ("Über nicht begangenem Bereich", "Der Bereich wird nicht begangen.", "53A03", "TH K.", "Absturzgefahr - kein Verkehrsraum"),
        ]),
        ("Dach abgedeckt", "Ein Dach ist abgedeckt.", None, [
            ("Gebäude bewohnt", "Das Gebäude ist bewohnt.", "53C04", "TH 1", "Sturmschaden - Dach abgedeckt"),
            ("Gebäude unbewohnt", "Das Gebäude ist unbewohnt.", "53A04", "TH K.", "Sturmschaden - Dach"),
        ]),
    ]),
    ("54", "Person in Notlage", "Wo befindet sich die Person?", [
        ("In der Höhe", "Die Person befindet sich in der Höhe.", None, [
            ("Auf einem Dach oder Kran", "Die Person befindet sich auf einem Dach oder Kran.", "54D01", "TH 2", "Höhenrettung"),
            ("Absturzgefahr", "Es besteht unmittelbare Absturzgefahr.", "54E01", "TH 3", "Höhenrettung mit Absturzgefahr"),
        ]),
        ("In der Tiefe", "Die Person befindet sich in der Tiefe.", None, [
            ("Schacht oder Grube", "Die Person befindet sich in einem Schacht oder einer Grube.", "54D02", "TH 2", "Rettung aus Tiefe"),
            ("Baugrube oder Silo", "Die Person befindet sich in einer Baugrube oder einem Silo.", "54E02", "TH 3", "Rettung aus Baugrube"),
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
            ("Austritt in ein Gewässer", "Betriebsmittel treten in ein Gewässer aus.", "55D01", "TH 2", "Gewässerverunreinigung"),
        ]),
        ("Gas", "Gas tritt aus.", "Wo tritt das Gas aus?", [
            ("Im Freien", "Im Freien ist Gasgeruch wahrnehmbar.",
             *personen("55", "02", "Gasgeruch im Freien", "TH M.", "TH 1", "TH 2")),
            ("Im Gebäude", "Im Gebäude ist Gasgeruch wahrnehmbar.",
             *personen("55", "03", "Gasaustritt im Gebäude", "TH 2", "TH 2", "TH 3")),
            ("Beschädigte Versorgungsleitung", "Eine Versorgungsleitung wurde beschädigt.",
             *personen("55", "04", "Beschädigte Gasleitung", "TH 2", "TH 3", "TH 3")),
        ]),
        ("Unbekannter Stoff", "Ein unbekannter Stoff ist ausgetreten.",
         *personen("55", "06", "Unbekannter Stoff", "TH M.", "TH 2", "TH 3")),
    ]),
    ("56", "Tierrettung", "Welches Tier und wo?", [
        ("Tier in Notlage", "Ein Tier befindet sich in einer Notlage.", None, [
            ("Katze auf Baum oder Dach", "Ein Tier befindet sich auf einem Baum oder Dach.", "56A01", "TH K.", "Tierrettung aus Höhe"),
            ("Tier in Schacht oder Kanal", "Ein Tier befindet sich in einem Schacht.", "56B01", "TH K.", "Tierrettung aus Tiefe"),
            ("Großtier verunfallt", "Ein Großtier ist verunfallt.", "56C01", "TH M.", "Großtierrettung"),
        ]),
    ]),
    ("57", "Einsturz, Gebäudeschaden", "Was ist eingestürzt?", [
        ("Gebäude oder Gebäudeteil", "Ein Gebäude oder Gebäudeteil ist eingestürzt.",
         *personen("57", "01", "Gebäudeeinsturz", "TH 2", "TH 3", "TH 3")),
        ("Decke, Balkon, Treppe", "Eine Decke, ein Balkon oder eine Treppe ist eingestürzt.",
         *personen("57", "02", "Teileinsturz im Gebäude", "TH 1", "TH 2", "TH 3")),
        ("Baugerüst, Kran", "Ein Baugerüst oder Kran ist eingestürzt.",
         *personen("57", "03", "Einsturz Baugerüst oder Kran", "TH 2", "TH 2", "TH 3")),
        ("Einsturz droht", "Ein Einsturz droht, ist aber nicht eingetreten.",
         *personen("57", "04", "Einsturzgefahr", "TH M.", "TH 1", "TH 2")),
    ]),
    ("58", "Unterstützung Rettungsdienst", "Worum wird gebeten?", [
        ("Tragehilfe", "Der Rettungsdienst bittet um Tragehilfe.", None, [
            ("Ohne besondere Umstände", "Besondere Umstände liegen nicht vor.", "58A01", "TH K.", "Tragehilfe"),
            ("Schwergewichtiger Patient", "Der Patient ist schwergewichtig.", "58C01", "TH M.", "Tragehilfe - schwergewichtiger Patient"),
            ("Rettung über Drehleiter nötig", "Eine Rettung über die Drehleiter ist erforderlich.", "58C02", "TH 1", "Tragehilfe über Drehleiter"),
        ]),
        ("Zugang schaffen", "Der Rettungsdienst bittet darum, Zugang zu schaffen.", None, [
            ("Tür verschlossen", "Die Tür ist verschlossen.", "58A03", "TH K.", "Zugang für Rettungsdienst"),
        ]),
        ("Absicherung der Einsatzstelle", "Die Einsatzstelle ist abzusichern.", None, [
            ("Im fließenden Verkehr", "Die Einsatzstelle liegt im fließenden Verkehr.", "58B04", "TH K.", "Absicherung im Verkehrsraum"),
            ("Auf der Autobahn", "Die Einsatzstelle liegt auf der Autobahn.", "58C04", "TH M.", "Absicherung auf der Autobahn"),
        ]),
    ]),
]
