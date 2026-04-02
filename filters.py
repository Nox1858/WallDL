from dataclasses import dataclass, field
import concurrent.futures
import json
import os
from math import ceil
from timer import printtime, notify
from filehandler import getAllImages, getData
import time

@dataclass
class LocalFilterArgs:
    selection: str | None = None
    rating: str | None = None
    exrating: str | None = None
    tags: list[str] = field(default_factory=list)
    extags: list[str] = field(default_factory=list)
    min_height: int = 0
    min_width: int = 0
    wide: bool = False
    narrow: bool = False
    flag: str | None = None

def parse_dimension(value: str) -> int:
    presets = {
        "1k": 960,
        "2k": 1920,
        "4k": 3840,
    }
    if value in presets:
        return presets[value]
    return int(value)

def parseLocalArgs(args: list[str]) -> LocalFilterArgs:

    parsed = LocalFilterArgs()

    for raw_arg in args:
        arg = raw_arg.strip()
        if not arg:
            continue

        if arg.startswith("this:"):
            parsed.selection = arg.split(":", 1)[1].strip()

        elif arg.startswith("-rating:"):
            parsed.exrating = arg.split(":", 1)[1].strip()

        elif arg.startswith("rating:"):
            parsed.rating = arg.split(":", 1)[1].strip()

        elif arg.startswith("flag:"):
            parsed.flag = arg.split(":", 1)[1].strip()

        elif arg == "--wide":
            parsed.wide = True

        elif arg == "--narrow":
            parsed.narrow = True

        elif arg == "--square":
            parsed.wide = True
            parsed.narrow = True

        elif arg.startswith("height:"):
            parsed.min_height = parse_dimension(arg.split(":", 1)[1])

        elif arg.startswith("width:"):
            parsed.min_width = parse_dimension(arg.split(":", 1)[1])

        elif arg.startswith("-") and len(arg) > 1:
            parsed.extags.append(arg[1:].strip())

        else:
            parsed.tags.append(arg)

    return parsed


def splitList(l :list[str], n: int) -> list[list[str]]:
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]

def filterLocalImages(parsedArgs: LocalFilterArgs, imagePath: str, latest: str) -> list[str]:
    images = getAllImages(imagePath)
    if parsedArgs.selection is not None:
        selection_image = next(
            (image for image in images if image.rsplit(".", 1)[0] == parsedArgs.selection),
            None
        )

        if selection_image is not None:
            return [selection_image]
        return []


    thread_count = max(min(16, len(images)),1)
    chunk_size = ceil(len(images) / thread_count)
    part_imgs = splitList(images, chunk_size)

    filtered_images: list[str] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=thread_count) as executor:
        futures = [
            executor.submit(filterThreadHandler, chunk, parsedArgs, latest)
            for chunk in part_imgs
        ]

        for future in concurrent.futures.as_completed(futures):
            filtered_images.extend(future.result())

    return filtered_images

def filterThreadHandler(images: list[str], args: LocalFilterArgs, latest: str) -> list[str]:
    selection = []
    t = time.time_ns()
    for image in images:
        image_id = image.rsplit(".", 1)[0]

        if latest is not None and image_id == latest:
            continue

        if handleImg(image, args):
            selection.append(image)
    printtime(t, message="Thread Time: ", out=True)
    return selection

def handleImg(image: str, args: LocalFilterArgs) -> bool:

    img_id = image.rsplit(".", 1)[0]
    imgdata = getData(img_id)
    ##print(imgdata)

    try:
        if "exclude" in imgdata['flag']:
            return False
    except Exception as e:
        print(image)
        print(imgdata)
        exit()

    if args.rating and args.rating not in imgdata["rating"]:
        return False

    if args.exrating and args.exrating in imgdata["rating"]:
        return False

    if args.flag and args.flag not in imgdata["flag"]:
        return False

    if imgdata["width"] < args.min_width or imgdata["height"] < args.min_height:
        return False

    if args.wide and imgdata["width"] < imgdata["height"]:
        return False

    if args.narrow and imgdata["width"] > imgdata["height"]:
        return False

    alltags = (
        imgdata["tags"]
        + imgdata["character"]
        + imgdata["copyright"]
        + imgdata["artist"]
        + imgdata["meta"]
    )

    for tag in args.extags:
        if tag in alltags:
            return False

    for tag in args.tags:
        if tag not in alltags:
            return False

    return True
