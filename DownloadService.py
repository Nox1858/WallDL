from dataclasses import dataclass, field
from pathlib import Path

from webreq_helpers import PostQuery

@dataclass
class DownloadStats:
    attempted: int = 0
    downloaded: int = 0
    skippedExisting: int = 0
    failed: int = 0


@dataclass
class DownloadBatchResult:
    latestFilename: str | None = None
    downloadedPosts: list[dict] = field(default_factory=list)
    stats: DownloadStats = field(default_factory=DownloadStats)

@dataclass
class DownloadOptions:
    tags: list[str] = field(default_factory=list)
    random: bool = True
    limit: int = 1
    maxTries: int = 5
    notifications: bool = True
    download: bool = True
    setWallpaper: bool = True

class DownloadService:

    def __init__(self, client: GelbooruClient, storage: ImageStorage):
        self.client = client
        self.storage = storage

    def downloadPosts(self, query: PostQuery, maxTries: int = 5):
        result = DownloadBatchResult()
        remaining = max(query.limit, 1)
        triesLeft = maxTries

        workingQuery = PostQuery(query.tags, random=query.random, limit=query.limit)

        while remaining > 0 and triesLeft > 0:
            apiLimit = 0 if remaining > 100 else remaining
            workingQuery.limit = apiLimit

            posts = self.client.getPosts(workingQuery)
            if not posts:
                triesLeft -= 1
                continue

            for post in posts:
                if remaining <= 0:
                    break
                result.stats.attempted += 1
                postID = post["id"]
                fileUrl = post["file_url"]
                extension = Path(post["image"]).suffix

                if extension in {".mp4", ".webm"}:
                    result.stats.failed += 1
                    continue

                if self.storage.existsByPostId(postID):
                    result.stats.skippedExisting += 1
                    continue

                content = self.client.downloadImageBytes(fileUrl)
                self.storage.saveImage(postID, extension, content)
                fileName = f"{postID}{extension}"
                result.latestFilename = fileName
                result.downloadedPosts.append(post)
                result.stats.downloaded += 1
                remaining -=1

            triesLeft -= 1

        return result
