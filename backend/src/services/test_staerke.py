import unittest

from data.staerke import staerke_aus_text, trupp_text


class TruppTextTest(unittest.TestCase):
    def test_the_four_strengths_that_were_given(self):
        self.assertEqual("Stärke=4: SF, AT", trupp_text(4))
        self.assertEqual("Stärke=6: SF, AT, WT", trupp_text(6))
        self.assertEqual("Stärke=8: SF, AT, WT, ST", trupp_text(8))
        self.assertEqual("Stärke=9: SF, AT, WT, ST, ME", trupp_text(9))

    def test_a_partly_filled_trupp_is_still_named(self):
        self.assertEqual("Stärke=3: SF, AT", trupp_text(3))
        self.assertEqual("Stärke=5: SF, AT, WT", trupp_text(5))
        self.assertEqual("Stärke=7: SF, AT, WT, ST", trupp_text(7))

    def test_one_person_is_the_leader_alone(self):
        self.assertEqual("Stärke=1: SF", trupp_text(1))

    def test_more_than_nine_names_every_trupp(self):
        self.assertEqual("Stärke=12: SF, AT, WT, ST, ME", trupp_text(12))

    def test_no_crew_prints_nothing(self):
        self.assertEqual("", trupp_text(0))


class StaerkeLesenTest(unittest.TestCase):
    def test_reads_the_old_format_with_identification_numbers(self):
        self.assertEqual(6, staerke_aus_text("Stärke=6:51F, 52F,38F"))

    def test_reads_the_new_format(self):
        self.assertEqual(9, staerke_aus_text("Stärke=9: SF, AT, WT, ST, ME"))

    def test_reads_a_spaced_or_unaccented_spelling(self):
        self.assertEqual(4, staerke_aus_text("Staerke = 4"))

    def test_text_without_a_strength_gives_none(self):
        self.assertIsNone(staerke_aus_text("Reserve"))
        self.assertIsNone(staerke_aus_text(""))


if __name__ == "__main__":
    unittest.main()
