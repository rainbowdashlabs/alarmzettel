"""
Prints the paths the server's flattener produces, for comparison with the browser's.

    python tools/pfade_vergleichen.py <arbeitsmappe.json> [--rund]

The two implementations have to agree exactly: a path only one side knows would look to the other
like an entry that was never there. `--rund` prints the working set rebuilt from those paths
instead, because comparing only the paths leaves the way back untested — a flattener that writes
a path its own rebuilder ignores passes the path check and still loses that data on every sync.
`./toolchain.sh sync-pfade` runs both directions and diffs them.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from data.dokument import TRENNER, flach, rund, sortierung_setzen  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Aufruf: python tools/pfade_vergleichen.py <arbeitsmappe.json>")

mappe = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
flachbild = flach(sortierung_setzen(mappe))

def vergleichbar(wert):
    """
    JavaScript kennt nur eine Zahl. Eine Sortierung, die hier 0.0 heißt und dort 0, ist keine
    Abweichung zwischen den Seiten, sondern zwischen den Sprachen.
    """
    if isinstance(wert, dict):
        return {schluessel: vergleichbar(inhalt) for schluessel, inhalt in wert.items()}
    if isinstance(wert, list):
        return [vergleichbar(inhalt) for inhalt in wert]
    if isinstance(wert, float) and wert.is_integer():
        return int(wert)
    return wert


if "--rund" in sys.argv:
    print(json.dumps(vergleichbar(rund(flachbild)), indent=1, ensure_ascii=False, sort_keys=True))
else:
    for pfad in sorted(flachbild):
        print(pfad.replace(TRENNER, " / "))
