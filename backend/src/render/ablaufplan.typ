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

/// Zeit in Minuten seit Mitternacht, wie sie über dem Bewegungsbild steht.
#let stundenmarke(minute) = {
  let innerhalb = calc.rem(minute, 1440)
  let stunde = calc.div-euclid(innerhalb, 60)
  let rest = calc.rem(innerhalb, 60)
  (if stunde < 10 { "0" } else { "" } + str(stunde) + ":"
   + if rest < 10 { "0" } else { "" } + str(rest))
}

/// Die Gesamtansicht: jeder Ort ein Band, die Zeit nach rechts, jede Bewegung eine Linie
/// zwischen zwei Bändern. Was sich bewegt, ist damit das Bild selbst und nicht eine Zeile in
/// einer Tabelle.
#let bewegungsblatt(bild) = {
  let SPALTE = 34mm
  let FLAECHE = 235mm
  let REIHE = 7mm
  let LUFT = 3mm
  let KOPF = 6mm

  let spanne = calc.max(bild.bis - bild.von, 1)
  let x = minute => SPALTE + FLAECHE * (minute - bild.von) / spanne

  let oben = (:)
  let hoehe = KOPF
  for band in bild.baender {
    oben.insert(band.ortId, hoehe)
    hoehe = hoehe + band.reihen * REIHE + LUFT
  }
  let mitte = (ortId, reihe) => oben.at(ortId) + reihe * REIHE + REIHE / 2

  kopf("Bewegungsbild", bild.datum)
  block(width: SPALTE + FLAECHE, height: hoehe, {
    for minute in range(bild.von, bild.bis + 1, step: 60) {
      place(dx: x(minute), dy: KOPF, line(end: (0mm, hoehe - KOPF), stroke: 0.4pt + luma(200)))
      place(dx: x(minute) - 6mm, dy: 0mm,
            box(width: 12mm, align(center, text(size: 7pt, fill: luma(110))[
              #stundenmarke(minute)])))
    }

    for band in bild.baender {
      place(dx: SPALTE, dy: oben.at(band.ortId),
            rect(width: FLAECHE, height: band.reihen * REIHE, fill: luma(246), stroke: none))
      place(dx: 0mm, dy: oben.at(band.ortId) + band.reihen * REIHE / 2 - 2mm,
            box(width: SPALTE - 2mm, align(right, text(size: 8pt, weight: "bold")[
              #band.name])))
    }

    for linie in bild.linien {
      let x1 = x(linie.von)
      let x2 = x(linie.bis)
      let y1 = mitte(linie.vonOrtId, linie.vonReihe)
      let y2 = mitte(linie.nachOrtId, linie.nachReihe)
      place(dx: x1, dy: y1, line(
        end: (x2 - x1, y2 - y1),
        stroke: (paint: black, thickness: 0.8pt,
                 dash: if linie.mittel == "fahrzeug" { none } else { "dashed" })))
    }

    for balken in bild.balken {
      let x1 = x(balken.von)
      let breite = calc.max(x(balken.bis) - x1, 2mm)
      let wer = balken.besatzung.filter(name => name != "")
      let text_ = balken.name + if wer.len() > 0 { " · " + wer.join(", ") } else { "" }
      place(dx: x1, dy: mitte(balken.ortId, balken.reihe) - REIHE / 2 + 0.8mm,
            rect(width: breite, height: REIHE - 1.6mm, radius: 1mm,
                 fill: luma(228), stroke: 0.4pt + luma(140)))
      place(dx: x1 + 1mm, dy: mitte(balken.ortId, balken.reihe) - 1.8mm,
            box(width: FLAECHE, text(size: 7pt)[
              #text_#if balken.lage != "" [ #text(fill: luma(90))[· #balken.lage]]]))
    }
  })
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

#let quer = (
  data.gesamt.bloecke.map(block_ => gesamtblock(block_))
    + data.bewegung.filter(bild => bild.baender.len() > 0).map(bild => bewegungsblatt(bild))
)

#if quer.len() > 0 {
  if blaetter.len() > 0 { pagebreak() }
  set page(flipped: true)
  for (nummer, blatt) in quer.enumerate() {
    if nummer > 0 { pagebreak() }
    blatt
  }
}
