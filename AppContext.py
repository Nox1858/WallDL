from env import Environment
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AppContext:
    env: Environment | None
    fullTagData: dict = field(default_factory=dict)
    allTagRequests: dict = field(default_factory=dict)

    @property
    def api_key(self) -> str:
        return self.env.get("API_KEY")

    @property
    def user_id(self) -> str:
        return self.env.get("USER_ID")

    @property
    def wallpaper_dir(self) -> Path:
        return Path(self.env.get("WALLPAPER_IMAGES"))

    @property
    def cache_dir(self) -> Path:
        return Path(self.env.get("WALLPAPER_CACHE"))

    @property
    def desktop_manager(self) -> str:
        return self.env.get("DESKTOP_MANAGER")
    @property
    def home(self) -> Path:
        return Path(self.env.get("HOME_PATH"))
