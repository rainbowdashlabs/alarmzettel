import unittest

from data.dokument import Dokument, TRENNER, flach, rund

MAPPE = {
    "version": 1,
    "alarme": [{
        "id": "a1", "sortierung": 0, "einsatzNr": "0", "stichwort": "BRAND K.",
        "kurzinfo": "Brand im Freien",
        "anfahrtsadresse": {"strasse": "Musterstraße", "hnr": "1", "objekt": "",
                            "plz": "10000", "ort": "Musterort"},
        "einsatzadresse": {"strasse": "Musterstraße", "hnr": "1", "objekt": "",
                           "plz": "10000", "ort": "Musterort"},
        "karte": {"kab": "S.00 A0", "fwPlan": "", "ePlan": "", "polarKoordinaten": ""},
        "hinweise": [{"id": "h1", "sortierung": 0, "typ": "text", "text": "DRITTMELDER"}],
        "einsatzmittel": [{
            "id": "g1", "sortierung": 0, "gruppe": "keine Gruppe",
            "adresse": {"strasse": "Musterstraße", "hnr": "1", "objekt": "",
                        "plz": "10000", "ort": "Musterort"},
            "fahrzeuge": [{"id": "f1", "sortierung": 0, "funkrufname": "LHF 0001.1",
                           "ezp": "6", "status": "R2(A1)", "staerke": "6",
                           "trupp": "Stärke=6: SF, AT, WT", "hinweis": "", "alarmFuer": True}],
        }],
    }],
    "kataloge": {"stichwoerter": [{"id": "s1", "text": "BRAND K."}],
                 "status": ["R2(A1)"], "trupp": [],
                 "fahrzeuge": [{"funkrufname": "LHF 0001.1", "staerke": "6", "ezp": "6",
                                "status": "R2(A1)"}]},
}


def pfad(*teile: str) -> str:
    return TRENNER.join(teile)


class RundreiseTest(unittest.TestCase):
    def test_a_working_set_survives_flattening_and_rebuilding(self):
        zurueck = rund(flach(MAPPE))
        self.assertEqual(1, len(zurueck["alarme"]))
        alarm = zurueck["alarme"][0]
        self.assertEqual("BRAND K.", alarm["stichwort"])
        self.assertEqual("Musterstraße", alarm["anfahrtsadresse"]["strasse"])
        self.assertEqual("DRITTMELDER", alarm["hinweise"][0]["text"])
        self.assertEqual("LHF 0001.1", alarm["einsatzmittel"][0]["fahrzeuge"][0]["funkrufname"])
        self.assertTrue(alarm["einsatzmittel"][0]["fahrzeuge"][0]["alarmFuer"])

    def test_a_stichwort_keeps_its_text_and_its_identity(self):
        mappe = dict(MAPPE, kataloge=dict(
            MAPPE["kataloge"],
            stichwoerter=[{"id": "s9", "text": "Allergie / Kontakt mit Tieren"}]))
        self.assertEqual([{"id": "s9", "text": "Allergie / Kontakt mit Tieren"}],
                         rund(flach(mappe))["kataloge"]["stichwoerter"])

    def test_catalogue_entries_containing_a_slash_stay_one_entry(self):
        """A status is still keyed by its own text, so the path separator cannot be a slash."""
        mappe = dict(MAPPE, kataloge=dict(MAPPE["kataloge"], status=["R2 / A1"]))
        self.assertEqual(["R2 / A1"], rund(flach(mappe))["kataloge"]["status"])

    def test_a_stichwort_written_before_the_catalogue_had_ids_still_loads(self):
        mappe = dict(MAPPE, kataloge=dict(MAPPE["kataloge"], stichwoerter=["BRAND K."]))
        self.assertEqual([{"id": "BRAND K.", "text": "BRAND K."}],
                         rund(flach(mappe))["kataloge"]["stichwoerter"])

    def test_entries_come_back_in_sort_order(self):
        mappe = dict(MAPPE)
        mappe["alarme"] = [
            dict(MAPPE["alarme"][0], id="a2", sortierung=2, stichwort="ZWEITER"),
            dict(MAPPE["alarme"][0], id="a1", sortierung=1, stichwort="ERSTER"),
        ]
        self.assertEqual(["ERSTER", "ZWEITER"],
                         [a["stichwort"] for a in rund(flach(mappe))["alarme"]])


class ZusammenfuehrenTest(unittest.TestCase):
    def setUp(self):
        self.dokument = Dokument.aus_arbeitsmappe(MAPPE)
        self.basis = self.dokument.stand

    def test_two_fields_of_one_alarm_both_survive(self):
        """The case the whole design is for: two people, one Alarm, different fields."""
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"}], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "anrufer"), "wert": "Ben"}], "ben")
        alarm = self.dokument.arbeitsmappe()["alarme"][0]
        self.assertEqual("TH 2", alarm["stichwort"])
        self.assertEqual("Ben", alarm["anrufer"])

    def test_two_alarms_edited_at_once_both_survive(self):
        zweiter = dict(MAPPE["alarme"][0], id="a2")
        self.dokument.anwenden(
            [{"pfad": p, "wert": w} for p, w in flach({"alarme": [zweiter]}).items()], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 1"}], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a2", "stichwort"), "wert": "TH 3"}], "ben")
        stichwoerter = {a["id"]: a["stichwort"] for a in self.dokument.arbeitsmappe()["alarme"]}
        self.assertEqual({"a1": "TH 1", "a2": "TH 3"}, stichwoerter)

    def test_the_later_write_to_one_field_wins(self):
        ziel = pfad("alarme", "a1", "stichwort")
        self.dokument.anwenden([{"pfad": ziel, "wert": "ZUERST"}], "anna")
        self.dokument.anwenden([{"pfad": ziel, "wert": "DANACH"}], "ben")
        self.assertEqual("DANACH", self.dokument.arbeitsmappe()["alarme"][0]["stichwort"])

    def test_a_stale_write_does_not_overwrite_a_newer_one(self):
        """A client that was offline must not undo what happened while it was away."""
        ziel = pfad("alarme", "a1", "stichwort")
        self.dokument.anwenden([{"pfad": ziel, "wert": "NEU"}], "ben")
        self.dokument.eintraege[ziel]["stand"] = self.dokument.stand + 5
        self.dokument.anwenden([{"pfad": ziel, "wert": "ALT"}], "anna")
        self.assertEqual("NEU", self.dokument.arbeitsmappe()["alarme"][0]["stichwort"])

    def test_deleting_an_alarm_removes_it_with_everything_below(self):
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1"), "weg": True}], "anna")
        self.assertEqual([], self.dokument.arbeitsmappe()["alarme"])

    def test_a_deleted_alarm_is_not_resurrected_by_a_client_that_missed_it(self):
        """Without the tombstone, the next push from an unaware client brings it back."""
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1"), "weg": True}], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "stichwort"), "wert": "BRAND K."}],
                               "ben")
        self.assertEqual([], self.dokument.arbeitsmappe()["alarme"])

    def test_deleting_one_hinweis_leaves_the_others(self):
        self.dokument.anwenden([
            {"pfad": pfad("alarme", "a1", "hinweise", "h2", "typ"), "wert": "text"},
            {"pfad": pfad("alarme", "a1", "hinweise", "h2", "text"), "wert": "ZWEITER"},
            {"pfad": pfad("alarme", "a1", "hinweise", "h2", "sortierung"), "wert": 1},
        ], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "hinweise", "h1"), "weg": True}],
                               "ben")
        hinweise = self.dokument.arbeitsmappe()["alarme"][0]["hinweise"]
        self.assertEqual(["ZWEITER"], [h["text"] for h in hinweise])

    def test_one_person_deletes_while_another_edits_the_same_alarm(self):
        """The deletion is newer, so it stands; the edit does not bring the Alarm back."""
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1"), "weg": True}], "anna")
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "anrufer"), "wert": "Ben"}], "ben")
        self.assertEqual([], self.dokument.arbeitsmappe()["alarme"])

    def test_the_same_sequence_of_writes_always_lands_the_same_way(self):
        """
        There is one document on the server and writes reach it one after another, so the order
        of arrival decides. What has to hold is that the same order always gives the same result.
        """
        ziel = pfad("alarme", "a1", "stichwort")
        stapel = [(["A"], "anna"), (["B"], "ben"), (["C"], "anna")]
        ergebnisse = []
        for _ in range(2):
            dokument = Dokument.aus_arbeitsmappe(MAPPE)
            for werte, wer in stapel:
                dokument.anwenden([{"pfad": ziel, "wert": w} for w in werte], wer)
            ergebnisse.append(dokument.arbeitsmappe()["alarme"][0]["stichwort"])
        self.assertEqual(["C", "C"], ergebnisse)

    def test_replaying_a_change_a_client_already_sent_changes_nothing(self):
        """A retry after a dropped response must not move anything backwards."""
        ziel = pfad("alarme", "a1", "stichwort")
        self.dokument.anwenden([{"pfad": ziel, "wert": "TH 2"}], "anna")
        vorher = self.dokument.arbeitsmappe()
        self.dokument.anwenden([{"pfad": ziel, "wert": "TH 2"}], "anna")
        self.assertEqual(vorher, self.dokument.arbeitsmappe())

    def test_changes_since_a_revision_are_what_a_client_needs(self):
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"}], "anna")
        seit = self.dokument.seit(self.basis)
        self.assertEqual([pfad("alarme", "a1", "stichwort")], [e["pfad"] for e in seit])

    def test_nothing_changed_means_nothing_to_send(self):
        self.assertEqual([], self.dokument.seit(self.dokument.stand))

    def test_an_empty_batch_does_not_move_the_revision(self):
        self.assertEqual(self.basis, self.dokument.anwenden([], "anna"))

    def test_a_write_into_a_deleted_alarm_is_not_handed_on(self):
        """
        Whoever wrote it had not heard about the deletion. Storing the value would mean sending
        it to everyone else, who would rebuild the deleted Alarm out of that one field.
        """
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1"), "weg": True}], "anna")
        stand = self.dokument.stand
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "anrufer"), "wert": "Ben"}], "ben")
        nachher = [e["pfad"] for e in self.dokument.seit(stand)]
        self.assertNotIn(pfad("alarme", "a1", "anrufer"), nachher)
        self.assertEqual([], self.dokument.arbeitsmappe()["alarme"])

    def test_a_tombstone_is_handed_on_even_though_it_is_a_deletion(self):
        """It hides what is under it, not itself, or nobody would learn of the deletion."""
        stand = self.dokument.stand
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1"), "weg": True}], "anna")
        self.assertIn(pfad("alarme", "a1"), [e["pfad"] for e in self.dokument.seit(stand)])

    def test_list_order_is_kept_when_the_entries_carry_no_sort_key(self):
        """
        A file or an import states its order by the order of its lists. Without stamping that
        into the sort key, entries come back ordered by their random ids instead.
        """
        mappe = {"version": 1, "kataloge": {}, "alarme": [{
            "id": "a1", "hinweise": [
                {"id": "zzz", "typ": "text", "text": "ZUERST"},
                {"id": "aaa", "typ": "text", "text": "DANACH"},
            ], "einsatzmittel": []}]}
        dokument = Dokument.aus_arbeitsmappe(mappe)
        hinweise = dokument.arbeitsmappe()["alarme"][0]["hinweise"]
        self.assertEqual(["ZUERST", "DANACH"], [h["text"] for h in hinweise])

    def test_the_document_survives_being_written_out_and_read_back(self):
        self.dokument.anwenden([{"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"}], "anna")
        wieder = Dokument.laden(self.dokument.sichern())
        self.assertEqual(self.dokument.stand, wieder.stand)
        self.assertEqual("TH 2", wieder.arbeitsmappe()["alarme"][0]["stichwort"])


if __name__ == "__main__":
    unittest.main()
