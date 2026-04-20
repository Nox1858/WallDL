from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
import time

from webreq_helpers import PostQuery, GelbooruClient
from filehandler import ImageStorage
from timer import printtime

@dataclass
class DownloadStats:
    attempted: int = 0
    downloaded: int = 0
    skippedExisting: int = 0
    failed: int = 0

@dataclass
class DownloadPostResult:
    post : dict | None = None
    filename : str | None = None
    downloaded : bool = False
    skippedExisting : bool = False
    failed : bool = False

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
        self.maxThreads = 10

    def __downloadPost(self, post: dict) -> DownloadPostResult:
        postID = post["id"]
        fileURL = post["file_url"]
        extension = Path(post["image"]).suffix

        if(extension in {".mp4", ".webm"}):
            print(f"Failed to download {postID} due to wrong file Format, conversion not implemented")
            return DownloadPostResult(failed=True)

        try:
            timer = time.time_ns()
            content = self.client.downloadImageBytes(fileURL)
            self.storage.saveImage(postID, extension, content)
            printtime(timer, f"Downloaded Post {postID} in: ")
            return DownloadPostResult(
                post=post,
                filename=f"{postID}{extension}",
                downloaded=True,
            )
        except Exception as e:
            print(e)
            return DownloadPostResult(failed=True)


    def downloadPosts(self, query: PostQuery, maxTries: int = 5):
        result = DownloadBatchResult()
        remaining = max(query.limit, 1)
        triesLeft = maxTries

        workingQuery = PostQuery(query.tags, random=query.random, limit=query.limit)

        while remaining > 0 and triesLeft > 0:
            apiLimit = 0 if remaining > 100 else remaining
            workingQuery.limit = apiLimit

            timer = time.time_ns()
            posts = self.client.getPosts(workingQuery)
            if not posts:
                triesLeft -= 1
                continue
            printtime(timer, f"Got {len(posts)} Posts in: ")

            candidates = posts[:remaining]
            timer = time.time_ns()
            for item in self.storage.wallpaperDir.iterdir():
                for post in candidates:
                    if(item.stem == str(post["id"])): #removed item.is_file() since it makes it over 4x  slower for whathever reason (just don't put anything but wallpaper images in that folder)
                        result.stats.skippedExisting += 1
                        candidates.remove(post)
            # if(len(candidates) < remaining and len(candidates) > 0): # in case you actually want your limit of images, but since we decrease the return size each time this can take a while
            #     triesLeft += 1
            printtime(timer, f"Checked existing and found {len(candidates)} in: ")

            with ThreadPoolExecutor(max_workers=self.maxThreads) as executor:
                futures = {
                        executor.submit(self.__downloadPost, post) : post for post in candidates
                    }

                for future in as_completed(futures):
                    result.stats.attempted += 1
                    downloadResult = future.result()

                    if(downloadResult.failed):
                        print("Failed")
                        result.stats.failed += 1
                        continue

                    if downloadResult.downloaded:
                        result.latestFilename = downloadResult.filename
                        result.downloadedPosts.append(downloadResult.post)
                        result.stats.downloaded += 1
                        remaining -= 1

                        if remaining <= 0:
                            break

                triesLeft -= 1

        return result

"""
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
"""
