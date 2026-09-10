/**
 * Ein Ort so verlinkt, dass man ihn vom Blatt aus findet: einmal für Apple Karten, einmal für
 * Google Maps. Wer den Zettel auf dem Telefon liest, tippt keine Adresse ab.
 *
 * Dieselben Links druckt der Server auf das Papier (`backend/src/data/karten.py`), dort als
 * Kennmuster zum Abscannen.
 */
const APPLE = 'https://maps.apple.com/?address='
const GOOGLE = 'https://www.google.com/maps/search/?api=1&query='

export function kartenLinks(adresse: string): { apple: string, google: string } {
    const text = encodeURIComponent(adresse)
    return {apple: APPLE + text, google: GOOGLE + text}
}
