import os
import json
from functools import lru_cache
from pathlib import Path

from AppContext import AppContext

def getAllImages(imagePath: str) -> list[str]:
    return [f for f in os.listdir(imagePath)]

@lru_cache(maxsize=None)
def getData(imgid: str) -> dict:
    try:
        with open(f"tags/{imgid}.json","r") as f: return json.load(f)
    except Exception as e:
        print("failed to load tags of",imgid,"exception:",e)
        with open(f"tags/default.json","r") as f: return json.load(f)

def setData(imgid: int ,data: dict):
    # timecounter = time.time_ns()
    with open(f"tags/{imgid}.json","w") as f:
        json.dump(data,f)
        # print("imgtags write overhead:",(time.time_ns()-timecounter)/1000000,"ms")
    getData.cache_clear()

def checkExisting(imgid: int, wallpaperFolder: str ,sendnote = True) -> bool:
    images = [f for f in os.listdir(wallpaperFolder)]

    for image in images:
        if(image[:image.find(".")] == str(imgid)): return True

    with open("downloaded.txt","a") as f: f.write(str(imgid)+"\n")
    return False


class ImageStorage:
    def __init__(self, wallpaperDir: Path):
        self.wallpaperDir = wallpaperDir

    def imagePath(self, postID: int | str, extension: str) -> Path:
        return self.wallpaperDir / f"{postID}{extension}"

    def saveImage(self,  postID: int | str, extension: str, content: bytes) -> Path:
        path = self.imagePath(postID,extension)
        path.write_bytes(content)
        return path

    def existsByPostId(self, postID: int | str) -> bool:
        postID = str(postID)
        for item in self.wallpaperDir.iterdir():
            if(item.is_file() and item.stem == postID):
                return True

        with open("downloaded.txt","a") as f: f.write(str(postID)+"\n")
        return False

