import os
import json

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import time
import subprocess

from AppContext import AppContext
from timer import printtime, notify
from webreq_helpers import GelbooruClient, PostQuery
from filehandler import ImageStorage, getData, setData
from TagService import TagRecord, TagService
from DownloadService import DownloadService, DownloadOptions

from wallpaper_setters import *

def parseDownloadArgs(args: list[str], defaultMaxTries: int = 5) -> DownloadOptions:
    options = DownloadOptions(
        tags=[],
        random=True,
        limit=1,
        maxTries=defaultMaxTries,
        notifications=True,
        download=True,
        setWallpaper=True
        )

    safe = True
    for arg in args:
        if arg.startswith("--limit:"):
            options.limit = int(arg.split(":", 1)[1])

        elif arg.startswith("--max_tries:"):
            options.maxTries = int(arg.split(":", 1)[1])

        elif arg == "--unsafe":
            safe = False

        elif arg == "--sort":
            options.random = False

        else:
            options.tags.append(arg)

    if options.limit > 400:
        options.maxTries = max(options.maxTries, int(options.limit / 100) + 1)

    if(safe):
        options.tags.append("rating:general")

    return options


def get(args: list[str], ctx: AppContext, quiet: bool = False, setwall: bool = True, maxTries:int = 5) ->int :
    startTime = time.time_ns()

    tagdataPath = ctx.cache_dir / "tagdata.json"
    wallpaperDir = ctx.wallpaper_dir

    options = parseDownloadArgs(args, defaultMaxTries=maxTries)

    if not quiet:
        notify("getting wallpaper...")


    client = GelbooruClient(ctx)
    storage = ImageStorage(wallpaperDir)
    downloadService = DownloadService(client, storage)
    tagService = TagService(client)

    tagService.loadTagData(tagdataPath)

    if not quiet:
        printtime(startTime, "loaded entire tagdata in ")

    query = PostQuery(
        tags=options.tags,
        random=options.random,
        limit=options.limit,
    )

    result = downloadService.downloadPosts(query, maxTries=options.maxTries)

    if result.downloadedPosts:
        timer = time.time_ns()
        tagService.saveImageMetadata(result.downloadedPosts)
        tagService.saveTagData(tagdataPath)
        printtime(timer, "Saved all Tags in: ")
        print("Saved Tag Data")

    if result.latestFilename and setwall and options.setWallpaper:
        setWallpaper(result.latestFilename, ctx)

    if not quiet:
        print(result.stats)

    printtime(
        startTime,
        f"got {result.stats.downloaded} images in: ",
        notification=not quiet,
    )

    return result.stats.downloaded
