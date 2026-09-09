#let data = json(sys.inputs.plan)

#let SCHRIFT = "Liberation Serif"
#let RULE = 0.5pt + luma(180)
#let BLOCK = luma(220)

#set page(paper: "a4", margin: 14mm, numbering: "1")
#set text(font: SCHRIFT, size: 10pt, lang: "de")
#set par(justify: false)

/// Der Kopf eines Blattes: der Name groß, daneben, was ihn einordnet.
#let kopf(name, neben) = {
  block(below: 6pt)[
    #text(size: 17pt, weight: "bold")[#name]
    #if neben != "" [ #h(6pt) #text(size: 10pt, fill: luma(90))[#neben] ]
  ]
  line(length: 100%, stroke: 1pt + black)
  v(4pt)
}

#let zeitspanne(zeile) = [#zeile.von–#zeile.bis]

/// Wie lange die Luftlinie dauern würde, wo sie sich rechnen lässt. Sie steht klein unter der
/// geplanten Zeit — ein Vorschlag, an dem man ablesen kann, ob die geplante knapp ist.
#let geschaetzt(zeile) = {
  if zeile.at("geschaetzt", default: none) == none { return [] }
  linebreak()
  text(size: 7pt, weight: "regular", fill: luma(110))[≈ #str(zeile.geschaetzt) min]
}

/// Ein Tag steht nur dort, wo er wechselt — sonst wiederholt er sich in jeder Zeile.
#let mit_tagen(zeilen) = {
  let bisher = ""
  let ergebnis = ()
  for zeile in zeilen {
    ergebnis.push((zeile, if zeile.datum == bisher { "" } else { zeile.datum }))
    bisher = zeile.datum
  }
  ergebnis
}

#let tabelle(spalten, kopfzeile, zeilen) = table(
  columns: spalten,
  stroke: (x: none, y: RULE),
  inset: (x: 4pt, y: 4pt),
  align: left + horizon,
  table.header(..kopfzeile.map(t => text(size: 8pt, weight: "bold", fill: luma(90))[#upper(t)])),
  ..zeilen.flatten(),
)

#let leerer_hinweis(text_) = text(size: 10pt, fill: luma(120), style: "italic")[#text_]

/// Ein Weg zu einem Ort: das Kennmuster fürs Telefon, darunter der Dienst als anklickbarer Name.
///
/// Beides zeigt auf dieselbe Stelle. Wer den Zettel auf Papier hat, hält die Kamera davor; wer
/// ihn am Bildschirm liest, klickt.
#let wegweiser(ort, dienst, name) = {
  if dienst not in ort or ort.at(dienst) not in data.kennmuster { return [] }
  let ziel = ort.at(dienst)
  link(ziel)[
    #align(center)[
      #image(data.kennmuster.at(ziel), width: 17mm)
      #v(1pt)
      #text(size: 7pt, fill: luma(90))[#underline[#name]]
    ]
  ]
}

/// Die Orte des Blattes mit Adresse und den beiden Kennmustern.
///
/// Der Zettel soll für sich allein genügen: wer ihn in die Hand gedrückt bekommt, hat keine
/// zweite Liste dabei und tippt keine Adresse ab, sondern hält das Telefon davor.
#let orte_block(orte) = {
  if orte.len() == 0 { return }
  v(8pt)
  text(size: 8pt, weight: "bold", fill: luma(90))[#upper("Orte")]
  v(3pt)
  line(length: 100%, stroke: RULE)
  for ort in orte {
    v(4pt)
    grid(
      columns: (1fr, auto, auto),
      column-gutter: 8pt,
      align: (left + horizon, center, center),
      [
        #text(weight: "bold")[#ort.name] \
        #text(size: 9pt, fill: luma(70))[#ort.adresse]
      ],
      wegweiser(ort, "apple", "Apple Maps"),
      wegweiser(ort, "google", "Google Maps"),
    )
  }
}

/// Material und Notiz einer Zeile, untereinander — beides gehört auf den Zettel, sonst weiß es
/// nur der, der geplant hat.
#let beiwerk(zeile) = {
  let teile = ()
  if zeile.material.len() > 0 { teile.push(text(size: 9pt)[#zeile.material.join(", ")]) }
  if zeile.notiz != "" { teile.push(text(size: 9pt, fill: luma(70))[#zeile.notiz]) }
  teile.join(linebreak())
}

/// Ein Blatt je Person — der Zettel, den man morgens in die Hand gedrückt bekommt.
#let personenblatt(person) = {
  let neben = (
    if person.anzahl > 1 { str(person.anzahl) + " Köpfe" } else { "" },
    person.rollen.join(", "),
  ).filter(t => t != "").join(" · ")
  kopf(if person.name != "" { person.name } else { "Ohne Namen" }, neben)
  if person.zeilen.len() == 0 {
    leerer_hinweis("Noch nirgends eingeteilt.")
  } else {
    tabelle(
      (auto, auto, 1fr, auto, auto, 1fr),
      ("Tag", "Zeit", "Wohin", "Lage", "Fahrzeug", "Material und Notiz"),
      mit_tagen(person.zeilen).map(((zeile, tag)) => (
        text(size: 9pt, fill: luma(110))[#tag],
        text(weight: "bold")[#zeitspanne(zeile)#geschaetzt(zeile)],
        if zeile.art == "einsatz" {
          text(style: "italic")[am Ort: #zeile.was]
        } else [#zeile.was],
        text(fill: luma(70))[#zeile.lage],
        [#zeile.fahrzeug#if zeile.faehrt [ #text(weight: "bold")[· fährt]]],
        beiwerk(zeile),
      )),
    )
    orte_block(person.orte)
  }
}

/// Ein Blatt je Fahrzeug — der Zettel fürs Armaturenbrett.
#let fahrzeugblatt(fahrzeug) = {
  kopf(if fahrzeug.name != "" { fahrzeug.name } else { "Ohne Namen" }, "")
  if fahrzeug.zeilen.len() == 0 {
    leerer_hinweis("Nichts geplant.")
  } else {
    tabelle(
      (auto, auto, 1fr, auto, 1fr, 1fr),
      ("Tag", "Zeit", "Wohin", "Lage", "Besatzung", "Material und Notiz"),
      mit_tagen(fahrzeug.zeilen).map(((zeile, tag)) => (
        text(size: 9pt, fill: luma(110))[#tag],
        text(weight: "bold")[#zeitspanne(zeile)#geschaetzt(zeile)],
        [#zeile.was],
        text(fill: luma(70))[#zeile.lage],
        zeile.besatzung.map(sitzt => {
          let name = sitzt.name + if sitzt.anzahl > 1 { " (" + str(sitzt.anzahl) + ")" } else { "" }
          if sitzt.faehrt { text(weight: "bold")[#name] } else { [#name] }
        }).join(", "),
        beiwerk(zeile),
      )),
    )
    orte_block(fahrzeug.orte)
  }
}

/// Was eine Zelle des Bogens für eine ist — daran hängt ihre Farbe.
#let FLAECHE = (
  einsatz: rgb("#f3cfcb"),
  fahrt: rgb("#e6e6e6"),
  aufenthalt: rgb("#f2f2f2"),
)

/// Der Bogen für die Wand: Zeit nach unten, je eine Spalte pro Kette.
///
/// Die Farbe sagt, was läuft: ein Einsatz steht im Signalton, eine Fahrt schraffiert dazwischen,
/// ein Aufenthalt ohne Lage blass. Wo ein Block endet, trennt ein kräftiger Strich — so sieht
/// man den Wechsel, ohne jede Zelle zu lesen.
#let gesamtblock(block_) = {
  kopf("Gesamtplan", block_.datum)
  let zellen = ()
  let vorher = block_.spalten.map(_ => (text: "", art: ""))
  let zeilen = block_.zeilen
  for (reihe, zeile) in zeilen.enumerate() {
    zellen.push(table.cell(fill: none, text(size: 8pt, fill: luma(110))[#zeile.zeit]))
    for (nummer, inhalt) in zeile.zellen.enumerate() {
      let davor = vorher.at(nummer)
      let danach = if reihe + 1 < zeilen.len() { zeilen.at(reihe + 1).zellen.at(nummer) }
                   else { (text: "", art: "") }
      let anfang = inhalt.text != "" and inhalt.text != davor.text
      let schluss = inhalt.text != "" and inhalt.text != danach.text
      zellen.push(table.cell(
        fill: FLAECHE.at(inhalt.art, default: none),
        stroke: if schluss { (bottom: 1.2pt + luma(90)) } else { none },
        if anfang { text(size: 9pt)[#inhalt.text] } else { [] },
      ))
    }
    vorher = zeile.zellen
  }
  table(
    columns: (auto, ..block_.spalten.map(_ => 1fr)),
    stroke: RULE,
    inset: (x: 3pt, y: 2.5pt),
    align: left + horizon,
    table.header(
      [],
      ..block_.spalten.map(spalte => text(size: 8pt, weight: "bold")[#upper(spalte.name)]),
    ),
    ..zellen,
  )
}

#let blaetter = ()
#for person in data.personen { blaetter.push(personenblatt(person)) }
#for fahrzeug in data.fahrzeuge { blaetter.push(fahrzeugblatt(fahrzeug)) }

#for (nummer, blatt) in blaetter.enumerate() {
  if nummer > 0 { pagebreak() }
  blatt
}

#let quer = data.gesamt.bloecke.map(block_ => gesamtblock(block_))

#if quer.len() > 0 {
  if blaetter.len() > 0 { pagebreak() }
  set page(flipped: true)
  for (nummer, blatt) in quer.enumerate() {
    if nummer > 0 { pagebreak() }
    blatt
  }
}
