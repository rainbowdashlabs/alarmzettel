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
    typst_binary: str = "typst"
    render_timeout_seconds: int = 30
    render_root: Path = Path(__file__).resolve().parent.parent / "render"
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
