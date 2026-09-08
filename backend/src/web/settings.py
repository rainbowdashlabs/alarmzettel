from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Working sets live in the browser, so most of this is about how long the two things the server
    does keep survive: the render session in memory, and a shared working set on disk.
    """

    # Outside a container this sits beside the sources and is gitignored; the image points it
    # at the mounted volume instead. Die alten FREIGABE_*-Namen gelten weiter, damit eine
    # laufende Installation beim Umbenennen nicht ihre Daten verliert.
    sitzung_verzeichnis: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "data" / "freigaben",
        validation_alias=AliasChoices("sitzung_verzeichnis", "freigabe_verzeichnis"))
    sitzung_tage: int = Field(
        default=30, validation_alias=AliasChoices("sitzung_tage", "freigabe_tage"))
    sitzung_max_bytes: int = Field(
        default=8 * 1024 * 1024,
        validation_alias=AliasChoices("sitzung_max_bytes", "freigabe_max_bytes"))
    """Wie viele Sitzungen im Speicher liegen dürfen und wie lange unbenutzt. Reine Kostenfrage:
    die Platte ist die Wahrheit, Verdrängung kostet nie Daten."""
    sitzung_cache_eintraege: int = 64
    sitzung_cache_minuten: int = Field(
        default=30, validation_alias=AliasChoices("sitzung_cache_minuten", "session_ttl_minutes"))
    sitzung_sweep_seconds: int = Field(
        default=3600, validation_alias=AliasChoices("sitzung_sweep_seconds", "session_sweep_seconds"))
    # Beside the shares, and in the image on the same volume: it is downloaded, never shipped.
    adressen_datei: Path = Path(__file__).resolve().parent.parent.parent / "data" / "adressen.sqlite"
    adressen_tage: int = 30
    adressen_laden: bool = True
    typst_binary: str = "typst"
    render_timeout_seconds: int = 30
    render_root: Path = Path(__file__).resolve().parent.parent / "render"
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
