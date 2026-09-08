import io
import unittest
import zipfile

from fastapi.testclient import TestClient

from main import app
from services.tabellenimport import _code_kompakt, _hinweise, alarm_aus_zeile

KOPF = ["Einsatz Nr", "Datum", "Zeit", "Stichwort", "Kurzinfo", "Straße", "H.Nr.", "Objekt",
        "PLZ", "Ort", "KaB", "Polar-Koord", "Meldungsquelle", "Rückrufnummer", "Anrufer",
        "Betroffener", "Meldender", "Was ist passiert", "Hinweise", "Funkrufname", "EZP",
        "Status", "Trupp", "FzHinweis"]

ZEILE = ["7", "01.01.2026", "12:00", "BRAND K.", "Brand im Freien", "Musterstraße", "1", "",
         "10000", "Musterort", "S.00 A0", "0,0°/ ,000 km", "49300000000000", "", "Max Mustermann",
         "", "", "", "-\tANRUFER IST DRITTMELDER\n-\tCode: 67-B-3: Notfallmeldung: Test. "
         "1. Erste Antwort. 2. Zweite Antwort.", "LHF 0001.1 (0000)", "6", "R2(A1)",
         "Stärke=6:11F", ""]


def ods(zeilen: list[list[str]]) -> bytes:
    def zelle(wert: str) -> str:
        sicher = wert.replace("&", "&amp;").replace("<", "&lt;")
        absaetze = "".join(f"<text:p>{teil}</text:p>" for teil in sicher.split("\n"))
        return f"<table:table-cell>{absaetze}</table:table-cell>"

    koerper = "".join(
        "<table:table-row>" + "".join(zelle(w) for w in zeile) + "</table:table-row>"
        for zeile in zeilen)
    inhalt = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        f'<office:body><office:spreadsheet><table:table table:name="Tabelle1">{koerper}'
        '</table:table></office:spreadsheet></office:body></office:document-content>')
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as archiv:
        archiv.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archiv.writestr("content.xml", inhalt)
    return puffer.getvalue()


class CodeTest(unittest.TestCase):
    def test_printed_code_becomes_stored_code(self):
        self.assertEqual("67B03", _code_kompakt("67-B-3"))
        self.assertEqual("01A01", _code_kompakt("1-A-1"))
        self.assertEqual("29A00U", _code_kompakt("29-A-0U"))


class HinweiseTest(unittest.TestCase):
    def test_plain_note_stays_a_note(self):
        eintraege = _hinweise("-\tANRUFER IST DRITTMELDER")
        self.assertEqual(1, len(eintraege))
        self.assertEqual("ANRUFER IST DRITTMELDER", eintraege[0].text)

    def test_code_line_becomes_code_and_path(self):
        eintraege = _hinweise("-\tCode: 67-B-3: Notfallmeldung: Test. 1. Erste. 2. Zweite.")
        self.assertEqual("code", eintraege[0].typ)
        self.assertEqual("67B03", eintraege[0].code)
        self.assertEqual("Notfallmeldung: Test.", eintraege[0].meldung)
        self.assertEqual(["Erste.", "Zweite."], eintraege[0].antworten)

    def test_notes_and_codes_keep_their_order(self):
        eintraege = _hinweise(ZEILE[18])
        self.assertEqual(["text", "code"], [e.typ for e in eintraege])

    def test_an_ordinal_inside_a_sentence_does_not_split_it(self):
        """The dispatch text says "(Anrufer 4. Hand)" inside answer one; only a number that
        continues the sequence starts a new answer."""
        eintraege = _hinweise(
            "-\tCode: 67-B-3: Meldung. 1. Der Anrufer ist nicht am Einsatzort (Anrufer 4. Hand). "
            "2. Es brennt im Freien.")
        self.assertEqual(2, len(eintraege[0].antworten))
        self.assertEqual("Der Anrufer ist nicht am Einsatzort (Anrufer 4. Hand).",
                         eintraege[0].antworten[0])

    def test_empty_cell_yields_nothing(self):
        self.assertEqual([], _hinweise("   "))


class ZeileTest(unittest.TestCase):
    def setUp(self):
        self.alarm = alarm_aus_zeile(dict(zip(KOPF, ZEILE)))

    def test_one_date_fills_both_pairs(self):
        self.assertEqual("01.01.2026", self.alarm.einsatzDatum)
        self.assertEqual("01.01.2026", self.alarm.meldungDatum)
        self.assertEqual("12:00", self.alarm.meldungZeit)

    def test_single_address_fills_both_blocks(self):
        self.assertEqual("Musterstraße", self.alarm.anfahrtsadresse.strasse)
        self.assertEqual("Musterstraße", self.alarm.einsatzadresse.strasse)

    def test_the_single_vehicle_becomes_one_group(self):
        self.assertEqual(1, len(self.alarm.einsatzmittel))
        fahrzeug = self.alarm.einsatzmittel[0].fahrzeuge[0]
        self.assertEqual("LHF 0001.1 (0000)", fahrzeug.funkrufname)

    def test_the_imported_vehicle_is_the_one_the_sheet_is_for(self):
        self.assertTrue(self.alarm.einsatzmittel[0].fahrzeuge[0].alarmFuer)

    def test_identification_numbers_are_replaced_by_the_trupp_line(self):
        fahrzeug = self.alarm.einsatzmittel[0].fahrzeuge[0]
        self.assertEqual("6", fahrzeug.staerke)
        self.assertEqual("Stärke=6: SF, AT, WT", fahrzeug.trupp)

    def test_a_trupp_cell_without_a_strength_is_kept_as_written(self):
        zeile = dict(zip(KOPF, ZEILE))
        zeile["Trupp"] = "Reserve"
        fahrzeug = alarm_aus_zeile(zeile).einsatzmittel[0].fahrzeuge[0]
        self.assertEqual("Reserve", fahrzeug.trupp)
        self.assertEqual("", fahrzeug.staerke)


class ImportEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def hochladen(self, inhalt: bytes, name: str = "alarme.ods"):
        return self.client.post("/api/import", files={"datei": (name, inhalt)})

    def test_ods_upload_returns_an_arbeitsmappe(self):
        antwort = self.hochladen(ods([KOPF, ZEILE, [str(i) for i in range(len(KOPF))]]))
        self.assertEqual(200, antwort.status_code)
        mappe = antwort.json()
        self.assertEqual(2, len(mappe["alarme"]))
        self.assertEqual("BRAND K.", mappe["alarme"][0]["stichwort"])

    def test_blank_rows_are_skipped(self):
        antwort = self.hochladen(ods([KOPF, ZEILE, [""] * len(KOPF)]))
        self.assertEqual(1, len(antwort.json()["alarme"]))

    def test_a_file_that_is_not_a_spreadsheet_is_refused(self):
        self.assertEqual(422, self.hochladen(b"kein zip").status_code)

    def test_a_spreadsheet_without_rows_is_refused(self):
        self.assertEqual(422, self.hochladen(ods([KOPF])).status_code)

    def test_line_breaks_inside_a_cell_survive_the_import(self):
        """A cell holds one paragraph per line; joining them without a separator ran the
        Hinweise bullets together and the code line was never recognised."""
        mappe = self.hochladen(ods([KOPF, ZEILE])).json()
        eintraege = mappe["alarme"][0]["hinweise"]
        self.assertEqual(["text", "code"], [e["typ"] for e in eintraege])
        self.assertEqual("ANRUFER IST DRITTMELDER", eintraege[0]["text"])
        self.assertEqual("67B03", eintraege[1]["code"])


if __name__ == "__main__":
    unittest.main()
