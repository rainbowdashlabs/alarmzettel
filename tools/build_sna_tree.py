"""
Builds the interrogation tree the SNA dialog walks.

The Notfallrettung branch is derived from the Berliner Feuerwehr open data workbook. Spreadsheets
are not kept in the repository, so the workbook is downloaded on first use and left beside this
script, where git ignores it. Only the generated JSON is committed. Brand and technische
Hilfeleistung have no public equivalent, so those come from sna_authored.py and are marked as
invented. Run from the project root:

    python tools/build_sna_tree.py
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict
from pathlib import Path

import sna_authored

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "tools" / "dispatchcode_to_resource_requirement.xlsx"
WORKBOOK_URL = ("https://github.com/Berliner-Feuerwehr/BF-Open-Data/raw/main/"
                "Datasets/Dispatchcodes/dispatchcode_to_resource_requirement.xlsx")
TARGET = ROOT / "frontend" / "public" / "sna-tree.json"

CODE, QUALIFIER, KATEGORIE, ANLASS, HAUPT, UNTER, SUFFIX = 0, 3, 4, 5, 6, 7, 8


# The workbook carries editing debris that is invisible in a spreadsheet but shows up as
# highlighted boxes in an editor and breaks plain string matching: zero-width spaces inside
# words and non-breaking spaces between them.
UNSICHTBAR = str.maketrans({
    "\u200b": None,   # zero width space
    "\u200c": None,   # zero width non-joiner
    "\u200d": None,   # zero width joiner
    "\ufeff": None,   # byte order mark
    "\u00a0": " ",    # no-break space
    "\u2007": " ",    # figure space
    "\u202f": " ",    # narrow no-break space
})


def saeubern(text):
    """Strips the invisible characters and collapses the whitespace they leave behind."""
    if not isinstance(text, str):
        return text
    return " ".join(text.translate(UNSICHTBAR).split())


def column_index(reference):
    letters = re.match(r"([A-Z]+)", reference).group(1)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_sheet(archive, shared, path):
    for row in ET.fromstring(archive.read(path)).iter(NS + "row"):
        cells = {}
        for cell in row.findall(NS + "c"):
            value = cell.find(NS + "v")
            if value is None:
                cells[column_index(cell.get("r"))] = ""
            elif cell.get("t") == "s":
                cells[column_index(cell.get("r"))] = saeubern(shared[int(value.text)])
            else:
                cells[column_index(cell.get("r"))] = saeubern(value.text or "")
        if cells:
            yield [cells.get(i, "") for i in range(max(cells) + 1)]


def fetch_workbook():
    """Downloads the open data workbook unless it is already here. Prints what it did."""
    if WORKBOOK.exists():
        print(f"Katalog vorhanden: {WORKBOOK.relative_to(ROOT)}")
        return
    print(f"Lade Katalog von {WORKBOOK_URL}")
    with urllib.request.urlopen(WORKBOOK_URL) as antwort:
        WORKBOOK.write_bytes(antwort.read())
    print(f"Gespeichert: {WORKBOOK.relative_to(ROOT)} ({WORKBOOK.stat().st_size // 1024} KB)")


def load_rows():
    fetch_workbook()
    with zipfile.ZipFile(WORKBOOK) as archive:
        shared = [
            saeubern("".join(node.text or "" for node in item.iter(NS + "t")))
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).iter(NS + "si")
        ]
        rows = list(read_sheet(archive, shared, "xl/worksheets/sheet2.xml"))
        legend = list(read_sheet(archive, shared, "xl/worksheets/sheet3.xml"))
    return rows[1:], {saeubern(row[0]): saeubern(row[1]) for row in legend[1:] if len(row) > 1}


class Graph:
    """
    Hash-consed node store. Two nodes with the same content become one node, so paths that
    reach the same outcome — or the same whole sub-branch — converge on a single id instead of
    being duplicated. That makes the result a directed acyclic graph rather than a strict tree;
    building bottom-up from content keys is what rules cycles out.
    """

    def __init__(self):
        self.nodes = {}
        self.by_key = {}

    def add(self, node):
        key = json.dumps(node, ensure_ascii=False, sort_keys=True)
        if key in self.by_key:
            return self.by_key[key]
        node_id = "k%d" % len(self.nodes)
        self.by_key[key] = node_id
        self.nodes[node_id] = node
        return node_id

    def terminal(self, code, kategorie, anlass, stichwort):
        return self.add({"code": code, "kategorie": kategorie, "anlass": anlass,
                         "stichwort": stichwort})

    def branch(self, question, answers):
        return self.add({"frage": question, "antworten": answers})

    def eingabe(self, question, vorlage, platzhalter, leer, ziel, eigen=False):
        """
        A question answered by typing rather than by choosing. An age is a number the caller
        says, and no list of bands is that number — "ungefähr 60" belongs on the sheet as it was
        given. One way on, so this is a node with a `ziel` instead of answers.

        `leer` is what gets recorded when the field is left empty. Where it is None the question
        is simply passed over and nothing is written: not every call happens on a floor.

        `eigen` marks an answer that belongs on the sheet as a Hinweis of its own rather than as
        one of the numbered sentences after the code — where the crew has to go is not part of
        the path to a determinant.
        """
        eingabe = {"vorlage": vorlage, "platzhalter": platzhalter}
        if leer:
            eingabe["leer"] = leer
        if eigen:
            eingabe["eigen"] = True
        return self.add({"frage": question, "ziel": ziel, "eingabe": eingabe})


def leaf(row):
    return {
        "code": row[CODE],
        "kategorie": row[KATEGORIE],
        "anlass": row[ANLASS],
        "stichwort": row[KATEGORIE],
    }


def qualifier_label(row):
    parts = [row[QUALIFIER].strip(), row[SUFFIX].strip()]
    return ", ".join(p for p in parts if p) or "ohne weitere Angabe"


def notfallrettung(graph, rows):
    protocols = OrderedDict()
    for row in rows:
        protocols.setdefault(row[HAUPT], OrderedDict()).setdefault(row[UNTER], []).append(row)

    entries = []
    for name, branches in protocols.items():
        answers = []
        for branch, members in branches.items():
            if len(members) == 1:
                target = graph.terminal(**leaf(members[0]))
            else:
                target = graph.branch("Patientenalter, Patientenanzahl oder Zusatz?", [
                    {"label": qualifier_label(m), "aussage": qualifier_label(m),
                     "ziel": graph.terminal(**leaf(m))}
                    for m in members
                ])
            answers.append({"label": branch or "ohne weitere Angabe",
                            "aussage": branch or "", "ziel": target})
        number = min(row[CODE][:2] for branch in branches.values() for row in branch)
        entries.append((number, name, graph.branch("Welche Situation trifft zu?", answers)))

    entries.sort()
    return graph.branch("Welche Hauptbeschwerde liegt vor?", [
        {"label": name, "aussage": "", "ziel": node, "nr": number}
        for number, name, node in entries
    ])


def authored_answer(graph, entry):
    """
    One answer and whatever hangs below it. Five parts end the interrogation at a determinant,
    four carry a further question, and the nesting goes as deep as an authored protocol needs —
    which for a fire is deeper than for anything else, because the question that sets the
    Stichwort is asked last.
    """
    label, statement = entry[0], entry[1]
    if len(entry) == 5:
        target = graph.terminal(entry[2], entry[3], entry[4], entry[3])
    else:
        question, children = entry[2], entry[3]
        target = graph.branch(question or "Welche Situation trifft zu?",
                              [authored_answer(graph, child) for child in children])
    return {"label": label, "aussage": statement, "ziel": target}


def authored(graph, protocols, question):
    entries = []
    for number, name, protocol_question, branches in protocols:
        entries.append({
            "label": name, "aussage": "", "nr": number,
            "ziel": graph.branch(protocol_question,
                                 [authored_answer(graph, branch) for branch in branches]),
        })
    return graph.branch(question, entries)


HAND = ("Aus welcher Hand kommt die Meldung?", (
    ("1. Hand — der Anrufer ist selbst betroffen",
     "Meldung aus erster Hand: der Anrufer ist selbst betroffen."),
    ("2. Hand — der Anrufer ist beim Betroffenen",
     "Meldung aus zweiter Hand: der Anrufer ist beim Betroffenen."),
    ("3. Hand — der Anrufer meldet für andere",
     "Meldung aus dritter Hand: der Anrufer meldet für andere."),
    ("4. Hand — der Anrufer hat es nur gehört oder gesehen",
     "Meldung aus vierter Hand: der Anrufer hat es nur gehört oder gesehen."),
    ("Automatische Meldung",
     "Die Meldung stammt aus einer automatischen Anlage."),
))

VOR_ORT = ("Ist der Anrufer vor Ort?", (
    ("Ja, der Anrufer ist vor Ort", "Der Anrufer ist am Einsatzort."),
    ("Nein, nicht mehr vor Ort", "Der Anrufer war am Einsatzort, ist es jetzt nicht mehr."),
    ("Nein, war nicht vor Ort", "Der Anrufer ist nicht am Einsatzort."),
    ("Unbekannt", "Ob der Anrufer vor Ort ist, ist nicht bekannt."),
))

ALTER = {
    "frage": "Wie alt ist die betroffene Person?",
    "vorlage": "Die betroffene Person ist {wert} Jahre alt.",
    "platzhalter": "Alter in Jahren, z. B. 54 oder ungefähr 60",
    "leer": {"label": "Alter unbekannt",
             "aussage": "Das Alter der betroffenen Person ist nicht bekannt."},
}

WACH = ("Reagiert die Person normal?", (
    ("Ja, wach und ansprechbar", "Die Person ist wach und ansprechbar."),
    ("Reagiert, aber nicht normal", "Die Person reagiert, aber nicht normal."),
    ("Reagiert nicht", "Die Person reagiert nicht."),
    ("Unbekannt", "Ob die Person normal reagiert, ist nicht bekannt."),
))

ATMUNG = ("Atmet die Person normal?", (
    ("Ja, normale Atmung", "Die Atmung ist normal."),
    ("Atmung auffällig", "Die Atmung ist auffällig."),
    ("Atmet nicht", "Die Person atmet nicht."),
    ("Unbekannt", "Ob die Person normal atmet, ist nicht bekannt."),
))

GESCHLECHT = ("Mann oder Frau?", (
    ("Mann", "Die betroffene Person ist männlich."),
    ("Frau", "Die betroffene Person ist weiblich."),
    ("Divers", "Die betroffene Person ist divers."),
    ("Unbekannt", "Das Geschlecht der betroffenen Person ist nicht bekannt."),
))


ORT = {
    "frage": "Geschoss und Name am Klingelschild?",
    "vorlage": "{wert}",
    "platzhalter": "z. B. 1. OG bei Müller",
    "leer": None,
    "eigen": True,
}


def vorfragen(graph, ziel, *fragen):
    """
    Questions asked before the situation itself and printed as the first Hinweise. None of them
    moves the determinant, so every answer leads to the same next question — a handful of edges
    into one node, which is the plainest case of the graph converging rather than branching.

    Built back to front, because each question has to know the one that follows it.
    """
    for frage in reversed(fragen):
        if isinstance(frage, dict):
            ziel = graph.eingabe(frage["frage"], frage["vorlage"], frage["platzhalter"],
                                 frage["leer"], ziel, frage.get("eigen", False))
        else:
            titel, antworten = frage
            ziel = graph.branch(titel, [{"label": label, "aussage": aussage, "ziel": ziel}
                                        for label, aussage in antworten])
    return ziel


ERFUNDEN = (
    "Erfundene Beispieldaten. Die Alarm- und Ausrückeordnung der Berliner Feuerwehr ist als "
    "Verschlusssache \"Nur für den Dienstgebrauch\" eingestuft und die FPDS-Determinanten sind "
    "lizenzierte IAED-Inhalte, daher steht dieser Baum nicht öffentlich zur Verfügung. Vor dem "
    "Einsatz durch die echte AAO ersetzen."
)


MELDER_HINWEIS = (
    "Die Codes und Anlässe stammen aus den offenen Daten der Berliner Feuerwehr. Die Fragen "
    "davor — Hand der Meldung, Anrufer vor Ort, Alter, Geschlecht, Reaktion, Atmung und "
    "Einsatzort — sind ergänzt."
)


def main():
    rows, legend = load_rows()
    graph = Graph()
    disciplines = [
        {"id": "notf", "label": "Notfallrettung", "quelle": "bf-open-data",
         "hinweis": MELDER_HINWEIS,
         "einstieg": vorfragen(graph, notfallrettung(graph, rows),
                               HAND, VOR_ORT, ALTER, GESCHLECHT, WACH, ATMUNG, ORT)},
        {"id": "brand", "label": "Brand", "quelle": "erfunden", "hinweis": ERFUNDEN,
         "einstieg": vorfragen(graph, authored(graph, sna_authored.BRAND, "Was brennt?"),
                               HAND, VOR_ORT, ORT)},
        {"id": "th", "label": "Technische Hilfeleistung", "quelle": "erfunden",
         "hinweis": ERFUNDEN,
         "einstieg": vorfragen(graph, authored(graph, sna_authored.TH, "Welche Lage liegt vor?"),
                               HAND, VOR_ORT, ORT)},
    ]
    tree = {
        "stand": "2026-05-21",
        "quellen": {
            "bf-open-data": "Berliner-Feuerwehr/BF-Open-Data, "
                            "Datasets/Dispatchcodes/dispatchcode_to_resource_requirement.xlsx",
        },
        "notfallkategorien": legend,
        "knoten": graph.nodes,
        "disziplinen": disciplines,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    counts = reference_counts(graph)
    terminals = sum(1 for n in graph.nodes.values() if "code" in n)
    edges = sum(len(n.get("antworten", ())) for n in graph.nodes.values())
    for discipline in tree["disziplinen"]:
        print(f"{discipline['id']:6} Einstieg {discipline['einstieg']:>6}  ({discipline['quelle']})")
    print(f"\n{len(graph.nodes)} Knoten, davon {terminals} Endpunkte")
    print(f"{edges} Kanten, {sum(1 for c in counts.values() if c > 1)} Knoten mit mehr als einem Vorgänger")
    print(f"{TARGET.relative_to(ROOT)}  {TARGET.stat().st_size / 1024:.0f} KB")


def reference_counts(graph):
    counts = {}
    for node in graph.nodes.values():
        for answer in node.get("antworten", ()):
            counts[answer["ziel"]] = counts.get(answer["ziel"], 0) + 1
    return counts


if __name__ == "__main__":
    main()
