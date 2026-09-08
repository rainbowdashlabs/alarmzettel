#!/usr/bin/env bash
#
# Common build and verification commands for this repository.
#
# Every command runs from the repository root regardless of the caller's working directory, so
# callers never need their own `cd`.
#
# Every command also runs inside the project's nix environment via `direnv exec`, so python, node
# and typst are the versions shell.nix pins. Without that, a caller whose shell has not entered
# the directory gets whatever is on PATH - and with typst missing the render tests quietly skip
# themselves, which is how a broken template passes a test run.
#
# Usage: ./toolchain.sh <command> [args...]
#        ./toolchain.sh <group> <command> [args...]
#        ./toolchain.sh help

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"
RENDER="$BACKEND/src/render"
PORT_BACKEND="${PORT_BACKEND:-8000}"

# Runs a command inside the project's direnv/nix environment, falling back to running it directly
# when direnv is not installed so the script still works on a plain checkout.
run() {
    if [ -f "$ROOT/.envrc" ] && command -v direnv >/dev/null 2>&1; then
        # A blocked .envrc makes direnv print its refusal and exit, which on its own reads as the
        # command having failed for some other reason. Say what to do about it instead.
        if ! direnv exec "$ROOT" true >/dev/null 2>&1; then
            echo "Die nix-Umgebung steht nicht bereit. Einmalig freigeben mit:" >&2
            echo "    direnv allow $ROOT" >&2
            exit 2
        fi
        direnv exec "$ROOT" "$@"
    else
        "$@"
    fi
}

usage() {
    cat <<'EOF'
Usage: ./toolchain.sh <command> [args...]
       ./toolchain.sh <group> <command> [args...]

The first hyphen of a name also reads as a space, so `docker app` and `docker-app` are the same
command. `./toolchain.sh docker` lists what is in a group.

Frontend
  fe-build              Type-check with vue-tsc, then build
  fe-typecheck          vue-tsc only
  fe-dev                Vite dev server, proxying /api to the backend
  fe-install            npm install - reconciles node_modules and the lock file with package.json
  fe-deploy             Build and copy the result to backend/static, which is how the backend
                        serves the whole app from one port as the image does

Backend
  be-test [args]        All tests. Needs typst on PATH or the render cases skip themselves
  be-test1 <pattern>    One module or test, e.g. `be-test1 test_import`
  be-dev                uvicorn with --reload on port 8000 (PORT_BACKEND overrides)
  be-serve              Build the frontend into backend/static first, then serve everything

Render
  render-sample [out]   Compile the checked-in sample to a PDF (default /tmp/alarmzettel.pdf)
  render-file <json> [out]
                        Compile any working set, e.g. one saved out of the app
  render-compare <reference.pdf> [json]
                        Render and compare against a reference PDF, row by row. The reference
                        and its data carry real call details, so neither is in this repository

Abgleich
  sync-pfade [json]     Compare the browser's flattener with the server's, path by path. They
                        have to agree exactly, or an edit from one side reads as an entry the
                        other never had
  sync-probe            Two clients on one workspace, running the browser's real sync module
                        outside a browser: concurrent edits, deletion against a stale client,
                        a dropped connection. Brings its own server (PORT_PROBE, Vorgabe 8131)

Adressen
  adressen-laden        Download the Berlin address list into the cache the backend queries.
                        The server does this by itself on startup when the copy is missing or
                        old; this is for doing it on purpose. Never committed
  adressen-stand        What the cache holds and when it was fetched
  adressen-polar        Check the Polar-Koordinaten against the values a real slip carries

Abfragebaum
  sna-build             Regenerate frontend/public/sna-tree.json. Downloads the open data
                        workbook on first use; spreadsheets are not kept in the repository
  sna-check             Verify the graph: no dangling edges, no cycles, nothing unreachable

Docker
  docker-build [args]   Build the production image
  docker-app            Start it detached on port 8080
  docker-app-down       Stop it again
  docker-app-logs       Follow what it prints
  docker-dev            Start the dev stack: backend with --reload, Vite on 5175

Combined
  verify                be-test, fe-build, sna-check and the two sync checks plus the
                        Polar-Koordinaten - what CI runs
EOF
}

fe() { cd "$FRONTEND"; }
be() { cd "$BACKEND/src"; }

# The command names are hyphenated, and the first hyphen also reads as a group: `docker app` is
# accepted for `docker-app`, and both reach the same arm below. Naming the group alone lists what
# is in it.
COMMAND_GROUPS=(fe be render sna sync docker adressen)

is_group() {
    local candidate
    for candidate in "${COMMAND_GROUPS[@]}"; do
        [ "$1" = "$candidate" ] && return 0
    done
    return 1
}

# What is in a group, read back out of the case arms below so the listing cannot drift from what
# actually runs.
list_group() {
    sed -n 's/^    \([a-z][a-z0-9|_-]*\)).*/\1/p' "$ROOT/toolchain.sh" |
        tr '|' '\n' | sed -n "s/^$1-//p"
}

if is_group "${1:-}"; then
    if [ $# -ge 2 ]; then
        set -- "$1-$2" "${@:3}"
    else
        echo "Commands in '$1':" >&2
        list_group "$1" | sed "s|^|  $1 |" >&2
        exit 2
    fi
fi

# Compiles a working set. typst is confined to the render directory, so the data file is copied
# into the scratch directory below it and removed again.
render_json() {
    local quelle="$1" ziel="${2:-/tmp/alarmzettel.pdf}"
    [ -f "$quelle" ] || { echo "Keine Datei: $quelle" >&2; exit 2; }
    mkdir -p "$RENDER/tmp"
    local name="toolchain-$$.json"
    cp "$quelle" "$RENDER/tmp/$name"
    # Expanded now, not when the trap fires: by then the local is gone and `set -u` would abort.
    trap "rm -f '$RENDER/tmp/$name'" EXIT
    cd "$RENDER"
    run typst compile --ignore-system-fonts --font-path fonts --root . \
        --input "data=/tmp/$name" alarmzettel.typ "$ziel"
    echo "$ziel"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
    fe-build)      fe; run npm run build "$@" ;;
    fe-typecheck)  fe; run npx vue-tsc -b "$@" ;;
    fe-dev)        fe; run npm run dev -- "$@" ;;
    fe-install)    fe; run npm install "$@" ;;
    fe-deploy)
        # The backend serves backend/static when it exists, which is how the image runs the whole
        # app on one port. Copying the build there reproduces that outside Docker.
        fe; run npm run build
        rm -rf "$BACKEND/static"
        cp -r "$FRONTEND/dist" "$BACKEND/static"
        echo "backend/static aktualisiert"
        ;;

    be-test)       be; run python -m unittest discover -s services -t . "$@" ;;
    be-test1)
        [ $# -ge 1 ] || { echo "be-test1 braucht ein Modul oder einen Test, z. B. test_import" >&2; exit 2; }
        pattern="$1"; shift
        be; run python -m unittest "services.$pattern" -v "$@"
        ;;
    be-dev)        be; run uvicorn main:app --reload --port "$PORT_BACKEND" "$@" ;;
    be-serve)
        "$ROOT/toolchain.sh" fe-deploy
        be; run uvicorn main:app --port "$PORT_BACKEND" "$@"
        ;;

    render-sample) render_json "$RENDER/sample/sample.json" "${1:-/tmp/alarmzettel.pdf}" ;;
    render-file)
        [ $# -ge 1 ] || { echo "render-file braucht eine JSON-Datei" >&2; exit 2; }
        render_json "$1" "${2:-/tmp/alarmzettel.pdf}"
        ;;
    render-compare)
        # The reference is a LibreOffice export of the original document. It and the data behind
        # it stay out of the repository, so both are named on the command line.
        [ $# -ge 1 ] || { echo "render-compare braucht eine Referenz-PDF" >&2; exit 2; }
        referenz="$1"; shift
        daten="${1:-$RENDER/sample/sample.json}"
        ausgabe="$(mktemp -t alarmzettel-XXXXXX.pdf)"
        render_json "$daten" "$ausgabe" > /dev/null
        cd "$ROOT"; run python tools/compare_reference.py "$referenz" "$ausgabe"
        ;;

    sync-pfade)
        # Both sides flatten the same working set; anything the diff shows is a disagreement
        # between browser and server about what a path is called.
        cd "$ROOT"
        daten="${1:-$RENDER/sample/sample.json}"
        server="$(mktemp)"; browser="$(mktemp)"
        trap "rm -f '$server' '$browser'" EXIT
        run python tools/pfade_vergleichen.py "$daten" > "$server"
        run node tools/pfade_vergleichen.mjs "$daten" > "$browser"
        if diff -u "$server" "$browser"; then
            echo "$(wc -l < "$server") Pfade, Browser und Server gleich"
        else
            echo "Die Pfade unterscheiden sich." >&2
            exit 1
        fi
        ;;

    sync-probe)
        # The probe starts its own server on its own port with its own share directory and takes
        # both down again, so nothing here has to manage that.
        cd "$ROOT"; run node tools/sync_probe.mjs "$@"
        ;;

    adressen-laden) be; run python -c "
from data.adressen import Adressen
from web.settings import settings
laden = Adressen(settings.adressen_datei, settings.adressen_tage)
print(f'{laden.laden()} Adressen in {laden.datei}')" ;;
    adressen-polar) cd "$ROOT"; run node tools/polar_pruefen.mjs ;;
    adressen-stand) be; run python -c "
from data.adressen import Adressen
from web.settings import settings
print(Adressen(settings.adressen_datei, settings.adressen_tage).bestand())" ;;
    sna-build)     cd "$ROOT"; run python tools/build_sna_tree.py "$@" ;;
    sna-check)
        cd "$ROOT"
        run python - <<'PY'
import json, sys
from pathlib import Path

baum = json.loads(Path("frontend/public/sna-tree.json").read_text(encoding="utf-8"))
knoten = baum["knoten"]

offen = {a["ziel"] for n in knoten.values() for a in n.get("antworten", ()) if a["ziel"] not in knoten}
if offen:
    sys.exit(f"Kanten ohne Ziel: {sorted(offen)[:5]}")

sys.setrecursionlimit(50000)
farbe = dict.fromkeys(knoten, 0)
zyklen = []

def besuchen(kid):
    if farbe[kid] == 1:
        zyklen.append(kid)
        return
    if farbe[kid] == 2:
        return
    farbe[kid] = 1
    for antwort in knoten[kid].get("antworten", ()):
        besuchen(antwort["ziel"])
    farbe[kid] = 2

for disziplin in baum["disziplinen"]:
    besuchen(disziplin["einstieg"])

if zyklen:
    sys.exit(f"Zyklen im Graphen: {zyklen[:5]}")
unerreichbar = [k for k, f in farbe.items() if f == 0]
if unerreichbar:
    sys.exit(f"{len(unerreichbar)} Knoten sind von keiner Disziplin aus erreichbar")

endpunkte = sum(1 for n in knoten.values() if "code" in n)
kanten = sum(len(n.get("antworten", ())) for n in knoten.values())
print(f"{len(knoten)} Knoten, {endpunkte} Endpunkte, {kanten} Kanten, "
      f"keine Zyklen, alles erreichbar")
PY
        ;;

    docker-build)     cd "$ROOT"; run docker build -t alarmzettel:dev . "$@" ;;
    docker-app)       cd "$ROOT"; run docker compose up -d --build "$@" ;;
    docker-app-down)  cd "$ROOT"; run docker compose down "$@" ;;
    docker-app-logs)  cd "$ROOT"; run docker compose logs -f "$@" ;;
    docker-dev)       cd "$ROOT"; run docker compose -f compose.dev.yml up --build "$@" ;;

    verify)
        "$ROOT/toolchain.sh" be-test
        "$ROOT/toolchain.sh" fe-build
        "$ROOT/toolchain.sh" sna-check
        "$ROOT/toolchain.sh" sync-pfade
        "$ROOT/toolchain.sh" sync-probe
        "$ROOT/toolchain.sh" adressen-polar
        ;;

    help|-h|--help) usage ;;
    *) echo "Unknown command: $cmd" >&2; echo >&2; usage >&2; exit 2 ;;
esac
