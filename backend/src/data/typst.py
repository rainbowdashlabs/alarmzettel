import json
import shutil
import subprocess
import uuid
from pathlib import Path

from entities.alarm import Arbeitsmappe
from web.settings import settings


class RenderError(RuntimeError):
    """The renderer refused the document; the message carries what typst reported."""


def _compile(vorlage: str, eingaben: dict[str, str], name: str) -> bytes:
    """
    Ruft typst auf. Es ist auf das Render-Verzeichnis eingesperrt, also wird die Datei in ein
    Verzeichnis darunter geschrieben und danach entfernt. Nichts überlebt den Aufruf.
    """
    root = settings.render_root
    scratch = root / "tmp" / uuid.uuid4().hex
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        argumente = []
        for schluessel, inhalt in eingaben.items():
            datei = scratch / f"{schluessel}.json"
            datei.write_text(inhalt, encoding="utf-8")
            argumente += ["--input", f"{schluessel}=/{datei.relative_to(root).as_posix()}"]

        output = scratch / name
        result = subprocess.run(
            [settings.typst_binary, "compile",
             "--ignore-system-fonts",
             "--font-path", str(root / "fonts"),
             "--root", str(root),
             *argumente,
             str(root / vorlage),
             str(output)],
            capture_output=True, text=True, timeout=settings.render_timeout_seconds)

        if result.returncode != 0:
            raise RenderError(result.stderr.strip() or "typst ist fehlgeschlagen.")
        return output.read_bytes()
    except FileNotFoundError as error:
        raise RenderError(f"typst nicht gefunden ({settings.typst_binary}).") from error
    except subprocess.TimeoutExpired as error:
        raise RenderError("Das Rendern hat zu lange gedauert.") from error
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def render_plan(daten: dict) -> bytes:
    """Der Ablaufplan: ein Blatt je Person, eines je Fahrzeug, dann der Gesamtplan quer."""
    if not daten["personen"] and not daten["fahrzeuge"] and not daten["gesamt"]["bloecke"]:
        raise RenderError("Der Ablaufplan ist leer.")
    return _compile("ablaufplan.typ", {"plan": json.dumps(daten, ensure_ascii=False)},
                    "ablaufplan.pdf")


def render(arbeitsmappe: Arbeitsmappe) -> bytes:
    """Compiles the Alarmzettel to PDF: one sheet per Alarm, in the order given."""
    if not arbeitsmappe.alarme:
        raise RenderError("Keine Alarme zum Rendern.")
    return _compile("alarmzettel.typ", {"data": arbeitsmappe.model_dump_json()},
                    "alarmzettel.pdf")
