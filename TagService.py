from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import time

from concurrent.futures import ProcessPoolExecutor

from webreq_helpers import GelbooruClient, PostQuery
from filehandler import setData
from timer import printtime


@dataclass
class TagRecord:
    name: str
    id: int
    count: int
    type: str
    ambiguous: str
    dateAdded: str

class TagService:
    def __init__(self, client: GelbooruClient, tagData: dict[str, dict] | None = None):
        self.client = client
        self.tagData = tagData or {}
        self.maxThreads = 8

    def normalizeTagType(self, value: int) -> str:
        mapping = {
                0: "general",
                1: "artist",
                3: "copyright",
                4: "character",
                5: "meta"
            }
        return mapping.get(value, "unknown")


    def getTagRecords(self, tags: list[str]) -> dict[str, TagRecord]:
        records = {}
        for tagdata in self.client.getTags(tags):
            record = TagRecord(
                name=tagdata["name"],
                id=tagdata["id"],
                count=tagdata["count"],
                type=self.normalizeTagType(tagdata["type"]),
                ambiguous=tagdata["ambiguous"],
                dateAdded=str(datetime.now())
                )
            records[record.name] = record

        return records

    def loadTagData(self, path: Path) -> None:
        if path.exists():
            self.tagData = json.loads(path.read_text())
        else:
            self.tagData = {}

    def saveTagData(self, path: Path) -> None:
        path.write_text(json.dumps(self.tagData))

    def ensureTagRecords(self, tags: list[str]) -> None:
        missing = [tag for tag in tags if tag not in self.tagData]
        if not missing:
            return

        fetched = self.getTagRecords(missing)
        for name, record in fetched.items():
            self.tagData[name] = asdict(record)

    def buildImageMetadata(self, post: dict) -> dict:
        rawTags = post["tags"]
        tags = rawTags.split() if isinstance(rawTags, str) else list(rawTags)

        self.ensureTagRecords(tags)

        artist = []
        copyright = []
        character = []
        meta = []
        general = []

        for tag in tags:
            tagType = self.tagData.get(tag, {}).get("type", "unknown")

            if tagType == "artist":
                artist.append(tag)
            elif tagType == "copyright":
                copyright.append(tag)
            elif tagType == "character":
                character.append(tag)
            elif tagType == "meta":
                meta.append(tag)
            else:
                general.append(tag)

        if not artist:
            artist = ["_unknown_"]


        return {
            "download-date": str(datetime.now()),
            "flag": "none",
            "rating": post["rating"],
            "width": post["width"],
            "height": post["height"],
            "artist": artist,
            "character": character,
            "copyright": copyright,
            "meta": meta,
            "tags": general,
            "url": post["file_url"],
        }

    def ensureTagsForPosts(self, posts: list[dict]) -> None:
        all_tags = set()

        for post in posts:
            raw_tags = post["tags"]
            tags = raw_tags.split() if isinstance(raw_tags, str) else list(raw_tags)
            all_tags.update(tags)

        self.ensureTagRecords(list(all_tags))


    def saveSingleImageMetadata(self, post : dict, cacheDir : Path) -> None:
        img_id = int(post["id"])
        metadata = self.buildImageMetadata(post)
        setData(img_id, metadata, cacheDir)

    def saveImageMetadata(self, posts: list[dict]) -> None:
        self.ensureTagsForPosts(posts)
        #timer = time.time_ns()
        with ProcessPoolExecutor(max_workers=self.maxThreads) as executor:
            [executor.submit(self.saveSingleImageMetadata, post, self.client.ctx.cache_dir) for post in posts]

        #printtime(timer, "Saved Tags in ")
        #for post in posts:
            #self.saveSingleImageMetadata(post, self.client.ctx.cache_dir)
            #print(f"{img_id} : {metadata}")

    def refreshImageMetadata(self, imageID: int) -> bool:
        posts = self.client.getPosts(PostQuery(tags=[f"id:{imageID}"], random=False, limit=1))

        if not posts:
            print(f"failed to refetch post {imageID}")
            return False

        post = posts[0]
        metadata = self.buildImageMetadata(post)
        setData(int(post["id"]), metadata, self.client.ctx.cache_dir)
        return True

