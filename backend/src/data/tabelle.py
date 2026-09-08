"""
Reads the spreadsheet the Alarmzettel used to be merged from.

Both formats the old workflow produced are handled: the LibreOffice `.ods` and the Excel `.xlsx`
the Word mail merge actually pointed at. Both are zip archives of XML, so neither needs a
dependency beyond the standard library.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile

ODS_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODS_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
XLSX_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class TabellenFehler(ValueError):
    """The upload is not a spreadsheet this importer understands."""


def _spaltenindex(bezug: str) -> int:
    treffer = re.match(r"([A-Z]+)", bezug)
    if not treffer:
        return 0
    index = 0
    for buchstabe in treffer.group(1):
        index = index * 26 + ord(buchstabe) - 64
    return index - 1


def _ods_zellentext(zelle: ET.Element) -> str:
    """
    A cell holds one paragraph per line and marks tabs with an element rather than a character.
    Both matter: the Hinweise column is a bullet list whose lines and tabs carry its structure.
    """
    absaetze = []
    for absatz in zelle.findall(ODS_TEXT + "p"):
        teile = []

        def sammeln(knoten: ET.Element):
            if knoten.text:
                teile.append(knoten.text)
            for kind in knoten:
                if kind.tag == ODS_TEXT + "tab":
                    teile.append("\t")
                elif kind.tag == ODS_TEXT + "s":
                    teile.append(" " * int(kind.get(ODS_TEXT + "c", "1")))
                elif kind.tag == ODS_TEXT + "line-break":
                    teile.append("\n")
                else:
                    sammeln(kind)
                if kind.tail:
                    teile.append(kind.tail)

        sammeln(absatz)
        absaetze.append("".join(teile))
    return "\n".join(absaetze)


def _ods_zeilen(archiv: zipfile.ZipFile) -> list[list[str]]:
    wurzel = ET.fromstring(archiv.read("content.xml"))
    tabelle = next(wurzel.iter(ODS_TABLE + "table"), None)
    if tabelle is None:
        raise TabellenFehler("Die Datei enthält keine Tabelle.")

    zeilen = []
    for zeile in tabelle.iter(ODS_TABLE + "table-row"):
        zellen: list[str] = []
        for zelle in zeile.findall(ODS_TABLE + "table-cell"):
            wiederholt = int(zelle.get(ODS_TABLE + "number-columns-repeated", "1"))
            text = _ods_zellentext(zelle)
            zellen.extend([text] * (1 if wiederholt > 100 else wiederholt))
        zeilen.append(zellen)
    return zeilen


def _xlsx_zeilen(archiv: zipfile.ZipFile) -> list[list[str]]:
    texte: list[str] = []
    if "xl/sharedStrings.xml" in archiv.namelist():
        geteilt = ET.fromstring(archiv.read("xl/sharedStrings.xml"))
        texte = ["".join(k.text or "" for k in eintrag.iter(XLSX_MAIN + "t"))
                 for eintrag in geteilt.iter(XLSX_MAIN + "si")]

    blaetter = sorted(n for n in archiv.namelist() if n.startswith("xl/worksheets/sheet"))
    if not blaetter:
        raise TabellenFehler("Die Datei enthält kein Tabellenblatt.")

    zeilen = []
    for zeile in ET.fromstring(archiv.read(blaetter[0])).iter(XLSX_MAIN + "row"):
        zellen: dict[int, str] = {}
        for zelle in zeile.findall(XLSX_MAIN + "c"):
            wert = zelle.find(XLSX_MAIN + "v")
            if wert is None:
                inline = zelle.find(XLSX_MAIN + "is")
                text = "".join(k.text or "" for k in inline.iter(XLSX_MAIN + "t")) if inline is not None else ""
            elif zelle.get("t") == "s":
                text = texte[int(wert.text or "0")]
            else:
                text = wert.text or ""
            zellen[_spaltenindex(zelle.get("r", "A1"))] = text
        zeilen.append([zellen.get(i, "") for i in range(max(zellen) + 1)] if zellen else [])
    return zeilen


def zeilen(inhalt: bytes) -> list[dict[str, str]]:
    """The first sheet as dictionaries keyed by the header row, blank rows dropped."""
    try:
        archiv = zipfile.ZipFile(io.BytesIO(inhalt))
    except zipfile.BadZipFile as fehler:
        raise TabellenFehler("Die Datei ist keine ODS- oder XLSX-Datei.") from fehler

    namen = archiv.namelist()
    if "content.xml" in namen:
        roh = _ods_zeilen(archiv)
    elif "xl/workbook.xml" in namen:
        roh = _xlsx_zeilen(archiv)
    else:
        raise TabellenFehler("Die Datei ist keine ODS- oder XLSX-Datei.")

    if not roh:
        raise TabellenFehler("Die Tabelle ist leer.")

    kopf = [wert.strip() for wert in roh[0]]
    if not any(kopf):
        raise TabellenFehler("Der Tabelle fehlt die Kopfzeile.")

    ergebnis = []
    for zeile in roh[1:]:
        if not any(wert.strip() for wert in zeile):
            continue
        ergebnis.append({kopf[i]: zeile[i].strip()
                         for i in range(min(len(kopf), len(zeile))) if kopf[i]})
    return ergebnis
