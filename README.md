# Alarmzettel

A tool for producing the Berlin fire brigade's alarm slips and printing them as PDF.

The slip used to come out of a Word mail merge fed by a spreadsheet with one row per alarm. That
row holds exactly one vehicle; the printed slip holds as many as you like, in several groups at
several addresses. This gives that flexibility back, and makes entering a batch of alarms in one
sitting bearable.

The interface is German throughout — it is a German fire service document, and the field names on
screen are the ones printed on the slip.

## What it does

- **Enter alarms** — a list with add, duplicate, delete and reorder; the editor is split into
  Einsatz, Stichwort, addresses, map, people involved, Hinweise and Einsatzmittelaufgebot.
- **Einsatzmittelaufgebot** — any number of groups, each with its own HA address and any number of
  vehicles. Exactly one vehicle is the one the slip is addressed to; it prints on grey.
- **Interrogation dialog** — instead of looking a code up, you click through the questions. The
  path you took becomes the Hinweis, because that is precisely what the numbered sentences after
  the code on the slip are.
- **Preview** — the same Typst output as the download, 400 ms after the last keystroke.
- **PDF** — one sheet per alarm, all of them in one file or singly.
- **JSON** — the working set downloads and uploads again. Old ODS or XLSX spreadsheets are
  imported.
- **Catalogues** — your own lists of Stichwörter, vehicles, status and Trupp. A vehicle carries its
  crew strength, EZP and status, and fills them in when you pick it.
- **Share and edit together** — a working set gets a link. Whoever opens it either works on their
  own copy or joins everyone else on the same one.

## Where the data lives

In the browser. The working set sits in `localStorage` and goes out and back in as JSON.

The server keeps a session, but only as scratch space for rendering: an entry in memory that
expires after 30 minutes without use and is gone on the next restart anyway. Nothing is written to
disk for it, there is no database and therefore no login. If a session expires while someone is
typing, the next request creates a new one and resends the working set — nothing is lost.

The one exception is a shared working set, below.

## Shared workspaces

Anyone wanting to hand a working set on creates a link. Behind it is a copy as a JSON file in a
volume, managed through a small SQLite file beside it. Whoever opens the link either takes a copy
into their own browser or joins the workspace and works on the same state as everyone else.

The retention runs from the **last use**, not from creation: a link that stays in use stays alive,
one nobody opens disappears after 30 days along with its file. Cleanup runs at startup and hourly;
it also removes files with no index entry, of the kind an unclean shutdown leaves behind.

### Editing together

Browsers exchange every three seconds and send their changes 400 ms after typing stops.

Merging happens **field by field**. The server does not hold the working set as a finished
document but as a set of paths, each carrying the revision it was written at:

```
alarme / <id> / stichwort
alarme / <id> / hinweise / <entry> / text
alarme / <id> / einsatzmittel / <group> / fahrzeuge / <vehicle> / funkrufname
```

Change the Stichwort while somebody else fills in the Anrufer of the same alarm and you do not
disturb them — different paths. Only writing the very same field at the very same moment lets the
later writer win. List entries carry ids and a fractional sort key, so moving one entry between
two others rewrites that entry rather than the list. Deleting leaves a tombstone, or a browser
that has not yet heard about the deletion would send the entry back on its next exchange and
resurrect it.

Anything that produces something from the working set — printing a PDF, saving the JSON, opening a
further share — exchanges first, so it is made from what everyone has rather than from what this
browser saw a few seconds ago. The preview deliberately does not: it shows your own state and
picks up other people's changes on the next beat by itself.

Browser and server each have their own implementation of the path flattening
(`frontend/src/scripts/flach.ts`, `backend/src/data/dokument.py`) and they have to agree exactly.
`./toolchain.sh sync-pfade` diffs them line by line. `./toolchain.sh sync-probe` goes further: it
loads the browser's real sync module twice outside a browser, brings up its own server and puts
two participants against each other — concurrent edits on one alarm, a deletion reaching someone
still typing into it, a dropped connection. Both run in CI.

**The link is the password.** There is no other authentication — whoever has it can read the
working set and change it. The token is long and random, but a forwarded link is a forwarded
working set. The slips are exercise material with invented personal details; nothing else belongs
in them.

## Running it

```bash
docker compose up
```

That builds the image from this checkout. A prebuilt one is published to GHCR on every push to
`main`, so `ghcr.io/rainbowdashlabs/alarmzettel:latest` works instead of `build: .` if you would
rather not build it yourself.

The application is then on <http://localhost:8080>. The `freigaben` volume holds the shared
working sets; everything else is stateless.

Behind a reverse proxy, pass `X-Forwarded-Proto` and `X-Forwarded-Host` through, or the share link
it hands out will name the wrong scheme.

| Variable | Default | What it does |
| --- | --- | --- |
| `SESSION_TTL_MINUTES` | `30` | how long an unused render session survives |
| `SESSION_SWEEP_SECONDS` | `60` | how often expired sessions are cleared out |
| `FREIGABE_TAGE` | `30` | how long a share stays available after its last use |
| `FREIGABE_VERZEICHNIS` | `/data/freigaben` | where shared working sets live |
| `FREIGABE_MAX_BYTES` | `4194304` | size limit for one shared working set |
| `CORS_ORIGINS` | `*` | allowed origins, comma separated |
| `TYPST_BINARY` | `typst` | path to the renderer |
| `RENDER_TIMEOUT_SECONDS` | `30` | give up when a render hangs |

## Development

`shell.nix` provides Node 24, Python 3.14 and Typst; direnv picks it up.

```bash
./toolchain.sh be-dev     # uvicorn with --reload on 8000
./toolchain.sh fe-dev     # Vite, proxying /api
```

`./toolchain.sh help` lists the rest; `./toolchain.sh verify` is what CI runs. Every command goes
through `direnv exec` into the nix environment so that Typst is really there — without it the
render tests skip themselves in silence, and a broken template passes.

Or with Docker:

```bash
docker compose -f compose.dev.yml up
```

### Tests

```bash
./toolchain.sh be-test
```

They talk to the real API and really render; where Typst is missing they skip themselves.

### Layout

```
backend/src/
  entities/     the models, and with them the API schema
  data/         session store, shares, the Typst call, the spreadsheet reader, Stärke derivation
  services/     one module per router, with the tests beside them
  render/       alarmzettel.typ and the bundled fonts
frontend/src/
  views/        pages, lazy-loaded by the router
  components/   editor sections, interrogation dialog, preview
  store/        the working set in localStorage, and the sync layer
  api/          axios, one file per resource
  i18n/         the German string catalogue
tools/          dispatch graph generation, comparison against the original
toolchain.sh    every build and verification command
```

Three things worth knowing before touching the code:

- **No user-facing text belongs in a template.** It goes into `frontend/src/i18n/de.ts` and is
  fetched with `t('…')`.
- **The slip is measured, not estimated.** `backend/src/render/alarmzettel.typ` reproduces a
  19-column grid with fixed inch widths. `tools/compare_reference.py` compares an output against a
  reference PDF row by row, which is worth a look after any change to the template. Measured
  against the LibreOffice print of the original: 0.8 pt horizontal deviation, 607.6 pt against
  610.0 pt total height.
- **The two flatteners have to stay in step.** `./toolchain.sh sync-pfade` after touching either.

## Data sources

The interrogation graph for the medical branch comes from the Berlin fire brigade's open data
([BF-Open-Data](https://github.com/Berliner-Feuerwehr/BF-Open-Data),
`Datasets/Dispatchcodes/dispatchcode_to_resource_requirement.xlsx`, as of 21.05.2026) and covers
the AMPDS codes — 35 protocols, 2234 codes. Spreadsheets are not kept in this repository, so
`tools/build_sna_tree.py` downloads the workbook when it is missing; only the generated JSON is
committed.

**Fire and technical rescue are invented.** The Berlin fire brigade's Alarm- und Ausrückeordnung is
classified *Nur für den Dienstgebrauch*, and the FPDS determinants are licensed IAED material;
neither is publicly available. The two branches in `tools/sna_authored.py` are built to be
plausible, but they are made up. They are marked as such in the dialog and should be replaced with
the real AAO before anyone relies on them.

Callers, phone numbers and callback numbers are generated rather than typed: the slips are written
as exercise material, and that way no real personal data ends up on a sheet that gets printed and
passed around.

## Fonts

Times New Roman and Aptos cannot be redistributed. Instead `backend/src/render/fonts/` holds
**Liberation Serif** — metrically identical to Times New Roman, so the labels keep their widths —
and **Inter** for the values. Both travel inside the image, so a render never depends on what
happens to be installed on the machine.

Both are under the SIL Open Font License 1.1, which is not the licence covering the rest of this
repository. Their licence texts sit beside them, along with a note on what each stands in for.

## Licence

GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`) — see `LICENSE`.

The Affero clause is the point: anyone who runs a modified copy of this as a network service owes
its users the source. The bundled fonts are the exception noted above, and the dispatch code data
belongs to the Berlin fire brigade under its own terms.
