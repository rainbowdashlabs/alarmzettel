from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Working sets live in the browser, so most of this is about how long the two things the server
    does keep survive: the render session in memory, and a shared working set on disk.
    """

    session_ttl_minutes: int = 30
    session_sweep_seconds: int = 60
    # Outside a container this sits beside the sources and is gitignored; the image points it
    # at the mounted volume instead.
    freigabe_verzeichnis: Path = Path(__file__).resolve().parent.parent.parent / "data" / "freigaben"
    freigabe_tage: int = 30
    freigabe_max_bytes: int = 4 * 1024 * 1024
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
