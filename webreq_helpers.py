import requests
import time
from random import randint
from dataclasses import dataclass, field

from AppContext import AppContext

@dataclass
class GelbooruRequestOptions:
    timeout_seconds: float = 10.0
    max_retries: int = 5
    backoff_min_ms: int = 200
    backoff_max_ms: int = 1000
    cookies: dict[str, str] | None = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )

@dataclass
class PostQuery:
    tags: list[str] = field(default_factory=list)
    random: bool = True
    limit: int = 0

@dataclass
class DownloadedImage:
    post_id: int
    file_url: str
    extension: str
    content: bytes

class GelbooruError(Exception):
    pass

class GelbooruRequestError(GelbooruError):
    pass

class GelbooruResponseError(GelbooruError):
    pass


class GelbooruClient:
    BASE_URL = "https://gelbooru.com/index.php"

    def __init__(self, ctx: AppContext, options: GelbooruRequestOptions | None = None):
        self.ctx = ctx
        self.options = options or GelbooruRequestOptions()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.options.user_agent,
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        })

        if self.options.cookies:
            self.session.cookies.update(self.options.cookies)

    def _auth_params(self) -> dict[str, str]:
        return {
            "json": "1",
            "api_key": self.ctx.api_key,
            "user_id": self.ctx.user_id
        }

    def _request_json(self, params: dict[str, any]) -> dict[str, any]:
        last_error = None

        for attempt in range(self.options.max_retries):
            try:
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.options.timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.options.max_retries - 1:
                    delay = randint(
                        self.options.backoff_min_ms,
                        self.options.backoff_max_ms,
                    ) / 1000
                    time.sleep(delay)

        raise GelbooruRequestError(f"Gelbooru request failed: {last_error}")

    def getPosts(self, query: PostQuery) -> list[dict[str, any]]:
        tag_string = " ".join(query.tags)
        if query.random:
            tag_string = f"{tag_string} sort:random".strip()

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "limit": query.limit,
            "tags": tag_string,
            **self._auth_params(),
        }

        payload = self._request_json(params)
        return payload.get("post", [])

    def getTags(self, tags: list[str]) -> list[dict[str, any]]:
        params = {
            "page": "dapi",
            "s": "tag",
            "q": "index",
            "limit": 0,
            "names": " ".join(tags),
            **self._auth_params(),
        }

        payload = self._request_json(params)
        return payload.get("tag", [])

    def downloadImageBytes(self, url: str, max_retries: int = 2) -> bytes:
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=self.options.timeout_seconds,
                    headers={"Referer": url},
                )
                response.raise_for_status()
                return response.content
            except requests.RequestException as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    delay = randint(
                        self.options.backoff_min_ms,
                        self.options.backoff_max_ms,
                    ) / 1000
                    time.sleep(delay)

        raise GelbooruRequestError(f"Image download failed: {last_error}")
