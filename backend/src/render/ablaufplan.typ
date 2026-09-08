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
      (auto, auto, 1fr, auto, auto),
      ("Tag", "Zeit", "Wohin", "Lage", "Fahrzeug"),
      mit_tagen(person.zeilen).map(((zeile, tag)) => (
        text(size: 9pt, fill: luma(110))[#tag],
        text(weight: "bold")[#zeitspanne(zeile)],
        [#zeile.was],
        text(fill: luma(70))[#zeile.lage],
        [#zeile.fahrzeug#if zeile.faehrt [ #text(weight: "bold")[· fährt]]],
      )),
    )
  }
}

/// Ein Blatt je Fahrzeug — der Zettel fürs Armaturenbrett.
#let fahrzeugblatt(fahrzeug) = {
  kopf(if fahrzeug.name != "" { fahrzeug.name } else { "Ohne Namen" }, "")
  if fahrzeug.zeilen.len() == 0 {
    leerer_hinweis("Nichts geplant.")
  } else {
    tabelle(
      (auto, auto, 1fr, auto, 1fr),
      ("Tag", "Zeit", "Wohin", "Lage", "Besatzung"),
      mit_tagen(fahrzeug.zeilen).map(((zeile, tag)) => (
        text(size: 9pt, fill: luma(110))[#tag],
        text(weight: "bold")[#zeitspanne(zeile)],
        [#zeile.was],
        text(fill: luma(70))[#zeile.lage],
        zeile.besatzung.map(sitzt => {
          let name = sitzt.name + if sitzt.anzahl > 1 { " (" + str(sitzt.anzahl) + ")" } else { "" }
          if sitzt.faehrt { text(weight: "bold")[#name] } else { [#name] }
        }).join(", "),
      )),
    )
  }
}

/// Der Bogen für die Wand: Zeit nach unten, je eine Spalte pro Kette.
#let gesamtblock(block_) = {
  kopf("Gesamtplan", block_.datum)
  let zellen = ()
  let vorher = block_.spalten.map(_ => "")
  for zeile in block_.zeilen {
    zellen.push(table.cell(fill: none, text(size: 8pt, fill: luma(110))[#zeile.zeit]))
    for (nummer, inhalt) in zeile.zellen.enumerate() {
      let anfang = inhalt != "" and inhalt != vorher.at(nummer)
      zellen.push(table.cell(
        fill: if inhalt == "" { none } else { BLOCK },
        if anfang { text(size: 9pt)[#inhalt] } else { [] },
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

#if data.gesamt.bloecke.len() > 0 {
  if blaetter.len() > 0 { pagebreak() }
  set page(flipped: true)
  for (nummer, block_) in data.gesamt.bloecke.enumerate() {
    if nummer > 0 { pagebreak() }
    gesamtblock(block_)
  }
}
