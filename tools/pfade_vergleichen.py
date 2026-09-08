"""
Prints the paths the server's flattener produces, for comparison with the browser's.

    python tools/pfade_vergleichen.py <arbeitsmappe.json>

The two implementations have to agree exactly: a path only one side knows would look to the other
like an entry that was never there. `./toolchain.sh sync-pfade` runs both and diffs them.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from data.dokument import TRENNER, flach, sortierung_setzen  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Aufruf: python tools/pfade_vergleichen.py <arbeitsmappe.json>")

mappe = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for pfad in sorted(flach(sortierung_setzen(mappe))):
    print(pfad.replace(TRENNER, " / "))
