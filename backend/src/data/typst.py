import json
import shutil
import subprocess
import uuid
from pathlib import Path

import segno

from entities.alarm import Arbeitsmappe
from web.settings import settings


class RenderError(RuntimeError):
    """The renderer refused the document; the message carries what typst reported."""


def _compile(vorlage: str, eingaben: dict[str, str], name: str, beilagen=None) -> bytes:
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
            if beilagen is not None:
                geladen = json.loads(inhalt)
                geladen["kennmuster"] = beilagen(geladen, scratch)
                inhalt = json.dumps(geladen, ensure_ascii=False)
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


def _kennmuster(daten: dict, scratch: Path) -> dict[str, str]:
    """
    Zu jedem Kartenlink ein Kennmuster als Bild. Es liegt neben den Daten im Kritzelverzeichnis
    und verschwindet mit ihm; das Template legt es aufs Blatt, damit ein Telefon den Weg kennt,
    ohne dass jemand eine Adresse abtippt.
    """
    verweise = sorted({verweis
                       for blaetter in (daten["personen"], daten["fahrzeuge"])
                       for blatt in blaetter for ort in blatt["orte"]
                       for verweis in (ort.get("apple"), ort.get("google")) if verweis})
    muster = {}
    for nummer, verweis in enumerate(verweise):
        datei = scratch / f"qr-{nummer}.svg"
        segno.make(verweis, error="m").save(str(datei), kind="svg", scale=4, border=0,
                                            dark="black", light=None)
        muster[verweis] = datei.relative_to(settings.render_root).as_posix()
    return muster


def render_plan(daten: dict) -> bytes:
    """Der Ablaufplan: ein Blatt je Person, eines je Fahrzeug, dann der Gesamtplan quer."""
    if not daten["personen"] and not daten["fahrzeuge"] and not daten["gesamt"]["bloecke"]:
        raise RenderError("Der Ablaufplan ist leer.")
    return _compile("ablaufplan.typ", {"plan": json.dumps(daten, ensure_ascii=False)},
                    "ablaufplan.pdf", beilagen=_kennmuster)


LEERER_PLAN = {"personen": [], "fahrzeuge": [], "gesamt": {"bloecke": []}}


def _dateiname(name: str, art: str) -> str:
    """
    Ein Name, den jedes Dateisystem annimmt. Umlaute bleiben — der Zettel gehört einem Menschen,
    und „Jörg“ soll auch so heißen.
    """
    sauber = "".join("-" if zeichen in '/\\:*?"<>|' or zeichen.isspace() else zeichen
                     for zeichen in name).strip("-")
    while "--" in sauber:
        sauber = sauber.replace("--", "-")
    return f"{art}-{sauber or 'ohne-namen'}.pdf"


def plan_blattweise(daten: dict) -> list[tuple[str, dict]]:
    """
    Derselbe Plan, zerlegt in ein Dokument je Blatt: eines für jede Person, eines für jedes
    Fahrzeug, und der Gesamtplan mit dem Bewegungsbild für sich. So bekommt jeder genau seinen
    Zettel in die Hand, statt den Stapel aller.
    """
    teile = [(_dateiname(blatt["name"], "person"), {**LEERER_PLAN, "personen": [blatt]})
             for blatt in daten["personen"]]
    teile += [(_dateiname(blatt["name"], "fahrzeug"), {**LEERER_PLAN, "fahrzeuge": [blatt]})
              for blatt in daten["fahrzeuge"]]
    if daten["gesamt"]["bloecke"]:
        teile.append(("gesamtplan.pdf", {**LEERER_PLAN, "gesamt": daten["gesamt"]}))
    return teile


def render(arbeitsmappe: Arbeitsmappe) -> bytes:
    """Compiles the Alarmzettel to PDF: one sheet per Alarm, in the order given."""
    if not arbeitsmappe.alarme:
        raise RenderError("Keine Alarme zum Rendern.")
    return _compile("alarmzettel.typ", {"data": arbeitsmappe.model_dump_json()},
                    "alarmzettel.pdf")
