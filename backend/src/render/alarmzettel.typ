#let data = json(sys.inputs.data)

#let SCHRIFT = "Liberation Serif"

/// The size of every merged value. The original leaves these unsized, so in Word they fall
/// through to its 12pt default, which sits far above the 9pt and 10pt labels around them. The
/// sheet reads better with the two closer together. The line box is derived from this, so the
/// rows keep their proportions whatever size is set here.
#let WERT = 10pt

/// The two lines the eye goes to first on a sheet being read out, so they print above the rest.
#let STICHWORT = WERT + 3pt
#let KURZINFO = WERT + 2pt

/// The address lines are read out with the Kurzinfo and print at its size.
#let ADRESSE = KURZINFO

#let THICK = 2.25pt
#let DOTTED = (paint: black, thickness: 0.75pt, dash: (array: (0.7pt, 0.75pt)))
#let GREY = rgb("#D9D9D9")

#let COLS = (
  1.2451in, 0.2472in, 0.1923in, 0.1840in, 0.6222in, 0.3569in, 0.1388in,
  0.7534in, 0.2840in, 0.4562in, 0.5062in, 0.0340in, 0.1562in, 0.4319in,
  0.3666in, 0.2576in, 0.0541in, 1.1895in, 0.0131in,
)

#set page(paper: "a4", margin: 10mm)
// A row is as tall as the paragraph it sits in, and the original's paragraphs are taller than
// the label spans inside them. Both boxes are set explicitly to the ratios measured off the
// reference render — 1.36em for a paragraph, 1.33em for a label — rather than to the vendored
// font's own ascender and descender, which are tighter than what the original was laid out with.
#set text(font: SCHRIFT, size: WERT, lang: "de", top-edge: 1.09em, bottom-edge: -0.27em)
#set par(leading: 0pt, spacing: 0pt, justify: false)

/// A printed label. Bold unless told otherwise.
#let L(body, size: 10pt, weight: "bold") = text(
  size: size, weight: weight, top-edge: 1.05em, bottom-edge: -0.28em)[#body]

/// A merged field value. Bold, as a filled-in sheet has them, unless told otherwise.
#let V(body, size: WERT, weight: "bold") = text(size: size, weight: weight)[#body]

/// Field values arrive as plain strings carrying newlines and tabs from the dispatch system.
#let VM(body, size: WERT, weight: "bold") = {
  let lines = str(body).split("\n").map(l => l.replace("\t", "\u{2003}"))
  text(size: size, weight: weight)[#lines.join(linebreak())]
}

#let get(dict, key, fallback: "") = if key in dict and dict.at(key) != none { dict.at(key) } else { fallback }

/// "67B03" prints as "67-B-3": protocol, determinant letter, level, then any suffix.
#let format-code(code) = {
  let c = str(code)
  if c.len() < 4 { return c }
  let protocol = c.slice(0, 2)
  let letter = c.slice(2, 3)
  let rest = c.slice(3)
  let digits = rest.split(regex("[^0-9]")).first()
  let suffix = rest.slice(digits.len())
  let level = if digits == "" { "" } else { str(int(digits)) }
  (protocol, letter, level + suffix).join("-")
}

/// Hinweise are a list: free-text notes, plus code entries whose numbered answers
/// are the path taken through the interrogation protocol.
#let hinweise-block(entries) = {
  let lines = ()
  for e in entries {
    let body = if get(e, "typ") == "code" {
      let head = "Code: " + format-code(get(e, "code")) + ": " + get(e, "meldung")
      let answers = get(e, "antworten", fallback: ()).enumerate().map(
        ((i, txt)) => str(i + 1) + ". " + txt)
      (head, ..answers).join(" ")
    } else {
      get(e, "text")
    }
    lines.push("-\u{2003}" + body)
  }
  text(size: WERT, weight: "regular")[#lines.map(l => par(l)).join()]
}

/// The Trupp field holds strength and Trupps in one string — "Stärke=6: SF, AT, WT" — because
/// that is how the dispatch system writes it. It stays one column on the sheet and prints on two
/// lines, broken after the colon. A value carrying none stands on a line of its own.
#let trupp-zeilen(wert) = {
  let roh = str(wert)
  let teile = roh.split(":")
  let zeilen = if teile.len() < 2 { (roh,) }
               else { (teile.first() + ":", teile.slice(1).join(":").trim()) }
  zeilen.filter(z => z != "").map(z => V(z, weight: "regular")).join(linebreak())
}

/// "Straße Nr, PLZ Ort", skipping the parts that are blank. Joining an empty array yields none
/// rather than an empty string, so an address with nothing in it has to drop out here too.
#let address-line(adr) = {
  let street = (get(adr, "strasse"), get(adr, "hnr")).filter(p => p != "").join(" ")
  let town = (get(adr, "plz"), get(adr, "ort")).filter(p => p != "").join(" ")
  (street, town).filter(p => p != none).join(", ")
}

#let cell = table.cell
#let none-stroke = (top: none, bottom: none, left: none, right: none)

/// An empty row still occupies one line in the original, so it needs a glyph to stand on.
#let spacer(size) = text(size: size)[~]

/// Several labels are small spans inside a paragraph the original leaves unsized, which keeps
/// their row a full-size line. A zero-width glyph at that size reproduces the height.
#let strut = text(size: WERT)[\u{200B}]


#let sheet(idx, a) = {
  let adr-an = get(a, "anfahrtsadresse", fallback: (:))
  let adr-ein = get(a, "einsatzadresse", fallback: (:))
  let karte = get(a, "karte", fallback: (:))
  let boxed-l = (left: THICK)
  let boxed-r = (right: THICK)
  let boxed-lr = (left: THICK, right: THICK)

  let legend = align(center,
    L("(Funkrufname / EZP / Status / Trupp / Hinweis)", size: 7pt, weight: "regular"))

  let vehicle-rows = ()
  for grp in get(a, "einsatzmittel", fallback: ()) {
    vehicle-rows.push(cell(colspan: 18, stroke: (bottom: DOTTED))[
      #L("HA:") #V(address-line(adr-ein))
    ])
    vehicle-rows.push(cell(stroke: none-stroke)[])
    vehicle-rows.push(cell(colspan: 18, stroke: none-stroke,
      align(center, L(underline(get(grp, "gruppe")))))) 
    vehicle-rows.push(cell(stroke: none-stroke)[])
    vehicle-rows.push(cell(colspan: 18, stroke: none-stroke)[#strut])
    vehicle-rows.push(cell(stroke: none-stroke)[])
    for fz in get(grp, "fahrzeuge", fallback: ()) {
      // The grey cell marks the one vehicle this sheet is for; every other row is plain.
      let angesprochen = get(fz, "alarmFuer", fallback: false) == true
      vehicle-rows.push(cell(colspan: 2, fill: if angesprochen { GREY } else { none },
                             stroke: none-stroke)[#V(get(fz, "funkrufname"))])
      vehicle-rows.push(cell(colspan: 5, stroke: none-stroke)[#V(get(fz, "ezp"), weight: "regular")])
      vehicle-rows.push(cell(colspan: 3, stroke: none-stroke)[#V(get(fz, "status"), weight: "regular")])
      vehicle-rows.push(cell(colspan: 5, stroke: none-stroke)[#trupp-zeilen(get(fz, "trupp"))])
      vehicle-rows.push(cell(colspan: 3, stroke: none-stroke)[#V(get(fz, "hinweis"), weight: "regular")])
      vehicle-rows.push(cell(stroke: none-stroke)[])
    }
  }

  table(
    columns: COLS,
    inset: (x: 0.075in, y: 0pt),
    stroke: none,
    align: left + top,

    // 1 — Kopfzeile. Repeated on a continuation page so an Alarm that outgrows one sheet still
    // says which sheet it is; the page counter is reset per Alarm, the total read off the
    // marker placed after the last row.
    table.header(
      repeat: true,
      cell(colspan: 6)[#L(get(a, "behoerde"), size: 16pt)],
      cell(colspan: 7, align(center, L(get(a, "titel"), size: 16pt))),
      cell(colspan: 6, align(right, L(
        context {
          let ends = query(label("alarm-end")).filter(e => e.value == idx)
          let total = if ends.len() > 0 { counter(page).at(ends.first().location()).first() } else { 1 }
          [Seite #counter(page).display() von #total]
        }, size: 16pt))),
    ),

    // 2/3 — Einsatz- und Meldungszeitpunkt
    cell[#L("Einsatz", weight: "regular")], cell(colspan: 4)[#L("Einsatz Datum", weight: "regular")],
    cell(colspan: 3)[#L("Einsatz Uhrzeit", weight: "regular")], cell(colspan: 3)[#L("Meldung Datum", weight: "regular")],
    cell(colspan: 5)[#L("Meldung Uhrzeit", weight: "regular")], cell(colspan: 3)[#L("A-Platz", weight: "regular")],

    cell[#V(get(a, "einsatzNr"))], cell(colspan: 4)[#V(get(a, "einsatzDatum"))],
    cell(colspan: 3)[#V(get(a, "einsatzZeit"))], cell(colspan: 3)[#V(get(a, "meldungDatum"))],
    cell(colspan: 5)[#V(get(a, "meldungZeit"))], cell(colspan: 3)[#V(get(a, "aPlatz"))],

    // 4/5 — Polizei, Sonderrechte, Arbeitsgruppe
    cell[#L("Polizei", weight: "regular")], cell(colspan: 4)[#L("Sonderrechte", weight: "regular")],
    cell(colspan: 3)[#L("Arbeitsgruppe", weight: "regular")], cell(colspan: 3)[], cell(colspan: 5)[],
    cell(colspan: 3)[#L("Wachalarm-Nr.", weight: "regular")],

    cell[#V(get(a, "polizei"))], cell(colspan: 4)[#V(get(a, "sonderrechte"))],
    cell(colspan: 3)[#V(get(a, "arbeitsgruppe"))], cell(colspan: 3)[], cell(colspan: 5)[],
    cell(colspan: 3)[#V(get(a, "wachalarmNr"))],

    // 6 — obere Kante des Kastens
    ..((1, 4, 3, 3, 5, 3).map(n => cell(colspan: n, stroke: (bottom: THICK))[#spacer(2pt)])),

    // 7-10 — Stichwort und Kurzinfo, mit Luft um beide
    cell(colspan: 19, stroke: (top: THICK, left: THICK, right: THICK))[#spacer(2pt)],
    cell(colspan: 19, stroke: boxed-lr)[#strut#L("Alarmierungsstichwort", size: 9pt)],
    cell(colspan: 19, stroke: boxed-lr)[#V(get(a, "stichwort"), size: STICHWORT)],
    cell(colspan: 19, stroke: boxed-lr)[#spacer(2pt)],
    cell(colspan: 19, stroke: boxed-lr)[#strut#L("Kurzinfo zum Einsatzanlass", size: 9pt)],
    cell(colspan: 19, stroke: boxed-lr)[#V(get(a, "kurzinfo"), size: KURZINFO)],
    cell(colspan: 19, stroke: boxed-lr)[#spacer(2pt)],

    // 11-18 — Anfahrts- und Einsatzadresse
    cell(colspan: 9, fill: GREY, stroke: boxed-l, align(center, L("Anfahrtsadresse", size: 9pt))),
    cell(colspan: 10, stroke: boxed-r, align(center, L("Einsatzadresse", size: 9pt))),

    cell(colspan: 6, fill: GREY, stroke: boxed-l)[#L("Straße", size: 9pt)],
    cell(colspan: 3, fill: GREY)[#L("H.Nr.:", size: 9pt)],
    cell(colspan: 8)[#L("Straße", size: 9pt)], cell(colspan: 2, stroke: boxed-r)[#L("H.Nr.:", size: 9pt)],

    cell(colspan: 6, fill: GREY, stroke: boxed-l)[#V(get(adr-an, "strasse"), size: ADRESSE)],
    cell(colspan: 3, fill: GREY)[#V(get(adr-an, "hnr"), size: ADRESSE)],
    cell(colspan: 8)[#V(get(adr-ein, "strasse"), size: ADRESSE, weight: "regular")],
    cell(colspan: 2, stroke: boxed-r)[#V(get(adr-ein, "hnr"), size: ADRESSE, weight: "regular")],

    cell(colspan: 3, fill: GREY, stroke: boxed-l)[#L("Objekt", size: 9pt)],
    cell(colspan: 3, fill: GREY)[], cell(colspan: 3, fill: GREY)[],
    cell(colspan: 8)[#L("Objekt", size: 9pt)], cell(colspan: 2, stroke: boxed-r)[],

    cell(colspan: 9, fill: GREY, stroke: boxed-l)[#V(get(adr-an, "objekt"), size: ADRESSE)],
    cell(colspan: 10, stroke: boxed-r)[#V(get(adr-ein, "objekt"), size: ADRESSE, weight: "regular")],

    cell(colspan: 9, fill: GREY, stroke: boxed-l)[#L("Ort")],
    cell(colspan: 10, stroke: boxed-r)[#L("Ort")],

    cell(colspan: 3, fill: GREY, stroke: boxed-l)[#V(get(adr-an, "plz"), size: ADRESSE)],
    cell(colspan: 3, fill: GREY)[], cell(colspan: 3, fill: GREY)[],
    cell(colspan: 4)[#V(get(adr-ein, "plz"), size: ADRESSE, weight: "regular")],
    cell(colspan: 4)[], cell(colspan: 2, stroke: boxed-r)[],

    cell(colspan: 9, fill: GREY, stroke: boxed-l)[#V(get(adr-an, "ort"), size: ADRESSE)],
    cell(colspan: 10, stroke: boxed-r)[#V(get(adr-ein, "ort"), size: ADRESSE, weight: "regular")],

    // 19/20 — Karte und Koordinaten, untere Kante des Kastens
    cell(colspan: 2, stroke: boxed-l)[#L("Karte", size: 9pt, weight: "regular")],
    cell(colspan: 5)[#L("KaB!", size: 9pt, weight: "regular")],
    cell(colspan: 3)[#L("FW-Plan", size: 9pt, weight: "regular")],
    cell(colspan: 5)[#L("E-Plan", size: 9pt, weight: "regular")],
    cell(colspan: 4, stroke: boxed-r)[#L("Polar-Koordinaten", size: 9pt, weight: "regular")],

    cell(colspan: 2, stroke: (left: THICK, bottom: THICK))[#L("KNICK MICH!")],
    cell(colspan: 5, stroke: (bottom: THICK))[#V(get(karte, "kab"))],
    cell(colspan: 3, stroke: (bottom: THICK))[#V(get(karte, "fwPlan"))],
    cell(colspan: 5, stroke: (bottom: THICK))[#V(get(karte, "ePlan"))],
    cell(colspan: 4, stroke: (bottom: THICK, right: THICK))[#V(get(karte, "polarKoordinaten"))],

    // 21 — Abstand
    cell(colspan: 4)[#strut], cell(colspan: 4)[], cell(colspan: 6)[], cell(colspan: 5)[],

    // 22-26 — Meldung und Beteiligte
    cell(colspan: 4)[#L("Meldungsquelle")],
    cell(colspan: 4)[#V(get(a, "meldungsquelle"), weight: "regular")],
    cell(colspan: 4)[#L("Rückrufnummer")],
    cell(colspan: 7)[#V(get(a, "rueckrufnummer"), weight: "regular")],

    cell(colspan: 4)[#L("Anrufer")],
    cell(colspan: 15)[#V(get(a, "anrufer"), weight: "regular")],
    cell(colspan: 4)[#strut#L("Betroffener")],
    cell(colspan: 15)[#V(get(a, "betroffener"), weight: "regular")],
    cell(colspan: 4)[#strut#L("Meldender")],
    cell(colspan: 15)[#V(get(a, "meldender"), weight: "regular")],
    cell(colspan: 4)[#strut#L("Was ist passiert")],
    cell(colspan: 15)[#VM(get(a, "wasIstPassiert"), weight: "regular")],

    // 27/28 — Hinweise
    cell(colspan: 19)[#strut#L("Hinweise")],
    cell(colspan: 19)[#hinweise-block(get(a, "hinweise", fallback: ()))],

    // 29-31 — Einsatzmittelaufgebot
    cell(colspan: 19, align(center, L("Einsatzmittelaufgebot", size: 12pt))),
    cell(colspan: 19, legend),
    cell(colspan: 19)[#spacer(7pt)],

    // Gruppen und Fahrzeuge
    ..vehicle-rows,

    // 36-38 — Abschluss
    cell(colspan: 18)[#align(center)[#strut#L("(Funkrufname / EZP / Status / Trupp / Hinweis)", size: 7pt, weight: "regular")]], cell[],
    cell(colspan: 18)[#spacer(7pt)], cell[],
    cell(colspan: 18, align(center, L("*** Ende des Drucks ***", size: 14pt))), cell[],
  )
  [#metadata(idx)#label("alarm-end")]
}

#for (idx, a) in data.alarme.enumerate() {
  if idx > 0 { pagebreak() }
  counter(page).update(1)
  sheet(idx, a)
}
