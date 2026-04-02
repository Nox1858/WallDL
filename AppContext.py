from env import Environment
from dataclasses import dataclass, field

@dataclass
class AppContext:
    env: Environment | None
    fullTagData: dict = field(default_factory=dict)
    allTagRequests: dict = field(default_factory=dict)
