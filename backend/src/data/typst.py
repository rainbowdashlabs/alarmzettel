import json
import shutil
import subprocess
import uuid
from pathlib import Path

from entities.alarm import Arbeitsmappe
from web.settings import settings


class RenderError(RuntimeError):
    """The renderer refused the document; the message carries what typst reported."""


def render(arbeitsmappe: Arbeitsmappe) -> bytes:
    """
    Compiles the Alarmzettel to PDF: one sheet per Alarm, in the order given.

    typst is confined to the render directory, so the data file is written into a scratch
    directory below it and removed afterwards. Nothing survives the call.
    """
    if not arbeitsmappe.alarme:
        raise RenderError("Keine Alarme zum Rendern.")

    root = settings.render_root
    scratch = root / "tmp" / uuid.uuid4().hex
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        data = scratch / "data.json"
        data.write_text(arbeitsmappe.model_dump_json(), encoding="utf-8")
        output = scratch / "alarmzettel.pdf"
        relative = data.relative_to(root).as_posix()

        result = subprocess.run(
            [settings.typst_binary, "compile",
             "--ignore-system-fonts",
             "--font-path", str(root / "fonts"),
             "--root", str(root),
             "--input", f"data=/{relative}",
             str(root / "alarmzettel.typ"),
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
