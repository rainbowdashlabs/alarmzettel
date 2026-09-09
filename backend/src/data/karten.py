"""
Ein Ort so aufgeschrieben, dass man ihn vom Blatt aus findet.

Auf dem Papier steht die Adresse, und daneben zwei Kennmuster: eines für Apple Karten, eines für
Google Maps. Wer den Zettel in der Hand hat, hält das Telefon davor und wird hingeführt — ohne
eine Adresse abzutippen, die zur Hälfte im Regen steht.
"""

from urllib.parse import quote

from entities.basis import Adresse

APPLE = "https://maps.apple.com/?address="
GOOGLE = "https://www.google.com/maps/search/?api=1&query="


def adresstext(adresse: Adresse) -> str:
    """Straße und Hausnummer, dann Postleitzahl und Ort — was fehlt, fehlt einfach."""
    strasse = " ".join(teil for teil in (adresse.strasse, adresse.hnr) if teil.strip())
    ort = " ".join(teil for teil in (adresse.plz, adresse.ort) if teil.strip())
    return ", ".join(teil for teil in (strasse, ort) if teil)


def karten(adresse: Adresse) -> dict[str, str]:
    """Die beiden Kartenlinks, oder nichts, solange die Adresse keine Straße nennt."""
    text = adresstext(adresse)
    if not adresse.strasse.strip():
        return {}
    return {"apple": APPLE + quote(text), "google": GOOGLE + quote(text)}
