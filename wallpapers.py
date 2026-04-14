#!/usr/bin/python3

import requests
import json
import os
from ntpath import join
import subprocess
import time

import shutil

import sys
from random import randrange

from datetime import datetime as d
from datetime import timedelta

from threading import Thread

from concurrent.futures.process import BrokenProcessPool

#Custom Stuff
from dl_library import *

import filters

from env import Environment
from timer import printtime, notify, formattime
from filehandler import getData, getAllImages, setData, checkExisting

from cache import SearchCache
from AppContext import AppContext

env = Environment(".env")

API_KEY = env.get("API_KEY")
USER_ID = env.get("USER_ID")

ctx = AppContext(env=env)
cache = SearchCache("searchcache.json", ctx)

Wallpaper_Folder = env.get("WALLPAPER_IMAGES")

DESKTOP_PATH = env.get("DESKTOP_PATH")
WALL_HOME_PATH = env.get("WALLPAPER_CACHE")
COPY_OUT_PATH = env.get("COPY_OUTPUT_DESTINATION")


HELPSTRING = """Fun Utility for downloading Wallpapers from a questionable Source :)
Possible args:
get [args]
    gets an image using args as geltags

    --limit:NUM gets NUM images instead of just one (Gel can return less than this number if there are duplicates or less results)

    --max_tries:NUM changes number of maxtries, usually not necessary, only really usefull if you look for random images and most but not all are already downloaded

    --safe short for "rating:general"

    --sort returns images in descending order of ID (newest image first) instead of randomly ordered

exist [args]
    this:IMAGE_ID sets this image

    flag:FLAG looks for all images with this flag

    --wide images where width > height (incl square)

    --narrow images where width < height (incl square)

    --square images where width = height

    height:NUM images with this minimum height (accepts 1k,2k,4k as shorts for the corresponding pixelsizes)

    width:NUM same as height but for width

    any other arg is used as tags (including appending "-" to exclude tags, and also including "rating:XYZ")

flag FLAG
    sets the flag of the current image to FLAG

fixtags
    currently broken (-_-)

getags
    prints tags of the current image

recache
    refreshes all searches in cache that have been used a bit (deletes the rest)

prev [num]
    sets the previous image, or goes the specifed number of images back. Careful: [num] is WIP and since we just add the latest image to the queue, it will get flooded and you will get the same image if you repeateldy do it.

prevsearch
    triggers the last used search with exist or direct name search again (very cool, I love this one)

addfave NAME [TAGS]
    adds an entry in the fave list with the given name and tags, so that you can subsequently use udpate_faves to get the newest images of your favorite searches

update_faves [NUM]
    gets the newest NUM images (default is 99) of all your faves

reset:
    sets the image "default.png" as wallpaper (will fail if it doesn't exist obviously)

copy:
    if no further arguments added copies the current wallpaper to the default copyout directory. Otherwise looks for ALL images matching the given tags and copies them to the default directory,
printflags
    looks through all images and prints all flags that you set (just to remind you if you forgot how you called something)

refresh
    should set the current wallpaper to latest if your wallpaper manager messed up, but you wallpaper manager messes up and it currently doesn't work

qer
    QuickRandomExist (no typo here) is a way quicker version of "exist" over all images

compare
    WIP should print stats and allow comparing tags and stuff but I lost the implementation file :(

taginfo
    WIP

help
    prints this thing here

If you pass an argument that is not in this list it'll cache a new search using the first argument as the name and the remaining ones as tags and subsequently you can access this search by just using the name (so just "./wallpapers.py NAME")

"""

fullTagData = {}
ImgThreads = []
InitThreads = []
ReqThreads = []
allTagRequests = {}
totalDLTime = []
totalSaveTime = []
totalDLSize = []
totalPostReqTime = []
rawReqTimes = []
rawDLTimes = []



def sendwallpaper(filepath, plugin='org.kde.image'):
    jscript = """
    var allDesktops = desktops();
    print (allDesktops);
    for (i=0;i<allDesktops.length;i++) {
        d = allDesktops[i];
        d.wallpaperPlugin = "%s";
        d.currentConfigGroup = Array("Wallpaper", "%s", "General");
        d.writeConfig("Image", "file://%s")
    }
    """
    bus = dbus.SessionBus()
    plasma = dbus.Interface(bus.get_object(
        'org.kde.plasmashell', '/PlasmaShell'), dbus_interface='org.kde.PlasmaShell')
    plasma.evaluateScript(jscript % (plugin, plugin, filepath))


def setWallpaper(image):
    filepath = f"{Wallpaper_Folder}{image}"
    if("." in image):
        imgid = image[:image.find(".")]
    else:
        imgid = image
    subprocess.Popen(f'plasma-apply-wallpaperimage "{filepath}"', shell=True)
    with open(f"{DESKTOP_PATH}/wallpaperURL.desktop","w") as f: f.write(f"[Desktop Entry]\nIcon=/{WALL_HOME_PATH}/gelbooru-logo.svg\nName=wallpaperURL\nType=Link\nURL[$e]=https://gelbooru.com/index.php?page=post&s=view&id={imgid}")
    with open ("latest.txt","w") as f: f.write(imgid)
    with open ("history.txt","a") as f: f.write(f"{imgid}; {d.now()}\n")
    imgdata = getData(imgid, ctx.cache_dir)
    try:
        imgdata["occurances"] += 1
    except:
        imgdata["occurances"] = 1
    setData(imgid, imgdata, ctx.cache_dir)


def setflag(imgid,flag):
    data = getData(imgid, ctx.cache_dir)
    data["flag"] = flag
    setData(imgid,data, ctx.cache_dir)


def initdata(imgid,predata,fix=False):
    timecounter = time.time_ns()
    # print("initializing data for",imgid)
    tags = predata["tags"]
    artist = []; copyright = []; character = []; meta = []; general = []; failed = []
    try:
        tags = tags.split()
    except:
        True
    for tag in tags:
        try:
            tagtype = fullTagData[tag]["type"]
            match tagtype:
                case "general": general.append(tag)
                case "artist": artist.append(tag)
                case "copyright": copyright.append(tag)
                case "character": character.append(tag)
                case "meta": meta.append(tag)
                case "unknown":
                    print("found tag with unknown type:",tag,tagtype)
                    general.append(tag)
                    with open("unknowntags.txt","a") as f: f.write(tag+"\n")
        except Exception as e:
            print("failed to find",tag,e)
            failed.append(tag)

    if(fix):
        if(len(artist) == 0):
            print(imgid,"doesn't have an artist, setting unknown. Link:",predata["url"])
            artist = ["_unknown_"]
        data = {
            "download-date":predata["download-date"],
            "flag":predata["flag"],
            "rating":predata["rating"],
            "width":predata["width"],
            "height":predata["height"],
            "artist":artist,
            "character":character,
            "copyright":copyright,
            "meta":meta,
            "tags":tags,
            "url":predata["url"]
            }
    else:
        if(len(artist) == 0):
            print(imgid,"doesn't have an artist, setting unknown. Link:",predata["file_url"])
            artist = ["_unknown_"]
        data = {
            "download-date":str(d.now()),
            "flag":"none",
            "rating":predata["rating"],
            "width":predata["width"],
            "height":predata["height"],
            "artist":artist,
            "character":character,
            "copyright":copyright,
            "meta":meta,
            "tags":tags,
            "url":predata["file_url"]
            }

    setData(imgid,data, ctx.cache_dir)
    if(len(failed) == 0): return False
    return failed
    # printtime(timecounter,f"handled tags for {imgid} in: ")


def handleTagRequests(fixing=False):
    timecounter = time.time_ns()
    fullRequests = {}
    for req in allTagRequests:
        tags = allTagRequests[req]["tags"]
        try:
            tags = tags.split()
        except:
            True
        for tag in tags:
            #Checks if data on a tag is present, otherwise or if too old add to update list
            try:
                tagdata = fullTagData[tag]
                date = d.strptime((tagdata["date-added"]), "%Y-%m-%d %H:%M:%S.%f")
                if(d.now()-date > timedelta(days = 10)):
                    # print("updating",tag,"since it's more than 10d old'")
                    fullRequests[tag] = True
            except Exception as e:
                fullRequests[tag] = True
    print("need to update",len(fullRequests),"tags...")
    # printtime(timecounter,"tagrequest setup overhead: ")
    # time.sleep(3)
    while(len(fullRequests) > 0):
        reqs = []
        while(len(reqs) < 100 and len(fullRequests) > 0):
            for thing in fullRequests:
                value = thing
                break
            fullRequests.pop(value)
            reqs.append(value)
        if(len(fullRequests) > 0):
            t1 = Thread(target=handleTagWebRequest, args=[reqs, ctx])
            t1.start()
            ReqThreads.append(t1)
        else:
            handleTagWebRequest(reqs, ctx)
    # print("started threads, waiting on finish")
    # time.sleep(3)
    for t in ReqThreads:
        t.join()
    # print("all req threads done, startign initdata threads...")
    # time.sleep(20)
    for imgid in allTagRequests:
        t2 = Thread(target=initdata, args=(imgid,allTagRequests[imgid],fixing))
        t2.start()
        InitThreads.append(t2)


selectimgs = []


def filterImgs(args):
    parsedArgs = filters.parseLocalArgs(args)
    print("parsed args")
    try:
        images = filters.filterLocalImages(parsedArgs, Wallpaper_Folder, latestImg, ctx)
        print(f"filtered images {len(images)}")
    except BaseException as e:
        print("test")
        print(e)
    except BrokenProcessPool as e:
        print(e)
    return images

def copyout(image,folder = ""):
    shutil.copyfile(Wallpaper_Folder+image, COPY_OUT_PATH+folder+image)

def randomExist(args = [],copy=False,copydest="",name=False):
    timecounter = time.time_ns()
    if(name):
        selectimgs = cache.get(querry = [], name = name)
        if(not selectimgs):
            selectimgs = filterImgs(args)
            cache.add(args,selectimgs,name = name)
    else:
        if(len(args) == 0):
            selectimgs = cache.get(querry = [], name = "any")
            if(not selectimgs):
                selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
                cache.add(args,selectimgs,"any")
        else:
            #print("Getting Cache Querry")
            selectimgs = cache.get(querry = args)
            if(not selectimgs):
                #print("Not in Cache")
                try:
                    selectimgs = filterImgs(args)
                    #print(f"Imgs selected {len(selectimgs)}")
                    cache.add(args,selectimgs)
                    #print("added to cache?")
                except Exception as e:
                    #print("Crashed Query??")
                    print(e)

            # selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
            #print(type(selectimgs))
            print(f"found {len(selectimgs)}, images with given tags")

    if(copy):
        for image in selectimgs:
            copyout(image,copydest)
    # printtime(timecounter,"filtered images in ")
    if(len(selectimgs) == 0):
        notify("failed to find images with given filter")
    else:
        randimg = selectimgs[randrange(0,len(selectimgs))]
        setWallpaper(randimg)
        printtime(timecounter,f"set one out of {len(selectimgs)} in ",notification=True)
        # notify()
    # timecounter = time.time_ns()
    # timecounter2 = time.time_ns()
    # printtime(timecounter2,"did absolutely nothing technically in ")
    # printtime(timecounter,"completed doing nothing in ")
    # printtime(timecounter,"completed doing nothing again in ")

def latestImg():
    with open ("latest.txt","r") as f:
        return f.read().replace("\n","")

def fixImgTags(imgid):
    timecounter = time.time_ns()
    tags = []
    tags.append(f"id:{imgid}")
    post = apirequest(tags,False,1)[0]
    imgid = post["id"]
    failed = initdata(imgid,post)
    while(failed):
        handleTagWebRequest(failed, ctx)
        failed = initdata(imgid,post)

    printtime(timecounter,f"redownloaded tags for {imgid} in ")

def fixALLImgTags(maxnum=10):
    print("try to fix",maxnum,"images...")
    timecounter = time.time_ns()
    maxnum = int(maxnum)
    images = [f for f in os.listdir(Wallpaper_Folder)]
    print(len(images))
    tofix = []
    fixing = []
    for image in images:
        imgid = image[:image.find(".")]
        try:
            f = open(f"tags/{imgid}.json","r")
        except Exception as e:
            print("failed to load tags of",imgid,"exception:",e)
            tofix.append(imgid)
            # with open(f"tags/default.json","r") as f: return json.load(f)

    fixThreads = []
    for i in range(maxnum):
        imgid = tofix.pop(randrange(0,len(tofix)))
        fixing.append(imgid)
        t1 = Thread(target=fixImgTags, args=(imgid,))
        t1.start()
        fixThreads.append(t1)
    print("prepared all threads to fix images.")
    for t in fixThreads:
        t.join()
    # for imgid in tofix:
    #     setflag(imgid,"-")
    for imgid in fixing:
        setflag(imgid,"fixed")
    print("(hopefully) fixed",len(fixing),"images.",len(tofix),"remaining")

    printtime(timecounter,f"fixed all tags in: ")


def quickrandexist():
    images = [f for f in os.listdir(Wallpaper_Folder)]
    randimg = images[randrange(0,len(images))]
    setWallpaper(randimg)

def printallflags():
    images = [f for f in os.listdir(Wallpaper_Folder)]
    flags = {}
    # print("getting all flags...")
    for image in images:
        imid = image[:image.find(".")]
        imdata = getData(imid, ctx.cache_dir)
        flag = imdata["flag"]
        if(flag in flags):
            flags[flag] += 1
        else:
            flags[flag] = 1
        # print(flags)
    print("found following flags:")
    for thing in flags:
        print(thing,":",flags[thing])

def getprevwall(num): #0 is current, 1 is last, 2 is the one before last etc
    latest = latestImg()
    imid = latest
    num = int(num)
    with open("history.txt","r") as f: history = f.readlines()
    print(latest)
    while(int(imid) == int(latest)):
        num += 1
        imstr = history[len(history)-num]
        imid = imstr[:imstr.find(";")]
    print(num-1,"wallpapers ago was",imid)
    history.remove(imstr)
    histring = ""
    for thing in history:
        histring += thing
    with open("history.txt","w") as f: f.write(histring)
    images = [f for f in os.listdir(Wallpaper_Folder)]
    for image in images:
        if(image[:image.find(".")] == str(imid)):
            setWallpaper(image)
    return imid

def add_fave(name, querry):
    querry.append("--sort")
    querry.sort()
    with open("faves.json", "r") as f: data = json.load(f)
    try:
        print("already added",name,"on",data[name]["added"])
    except:
        data[name] = {"querry":querry,"added":str(d.now()),"updated":str(d.now())}
    with open("faves.json", "w") as f: json.dump(data,f)


def update_faves(getnum = 99):
    with open("faves.json", "r") as f: data = json.load(f)
    updates = 0
    for entry in data:
        # date = d.strptime(data[entry]["date"], "%Y-%m-%d %H:%M:%S.%f")
        querry = data[entry]["querry"]
        # print(date,used)
        updated = d.strptime((data[entry]["updated"]), "%Y-%m-%d %H:%M:%S.%f")
        try:
            cutoff = data[entry]["cutoff"]
        except:
            cutoff = 0
        if(d.now()-updated > timedelta(days = cutoff)):
            print("updating",entry,querry,"...")
            querry.append(f"--limit:{getnum}")
            updates += get(querry,quiet = True, setwall = False,max_tries=1)
            querry.remove(f"--limit:{getnum}")
            print("finished getting stuff")
            data[entry]["updated"] = str(d.now())
            # updates += 1

        else:
            print(entry,querry,"was recently updated")

    if(updates > 0):
        print("updated",updates,"faves, refreshing cache now...")
        with open("faves.json", "w") as f: json.dump(data,f)
        cache.refresh(filterFunc=filterImgs)
    else:
        print("no new images found :(")

def printstats(querry):
    total = 0
    safe = 0
    questionable = 0
    sensitive = 0
    explicit = 0
    print(querry)
    print(f"total results: {total}")
    print(f"distribution: ")

def getcount(tags):
    selectimgs = getcache(querry = tags, quiet = True)
    if(not selectimgs): selectimgs = filterImgs(tags)
    return len(selectimgs)

def taginfo(tag):
    with open(f"tagdata.json", "r") as f: fullTagData = json.load(f)
    tagdata = fullTagData[tag]
    print("total",tagdata["count"])
    print("total g/q/s/e:","TODO")
    totcount = getcount([tag])
    print("local images with tag:",totcount)
    gperc = int(10000*getcount([tag,"rating:general"])/totcount)/100
    qperc = int(10000*getcount([tag,"rating:questionable"])/totcount)/100
    sperc = int(10000*getcount([tag,"rating:sensitive"])/totcount)/100
    eperc = int(100*(100-gperc-qperc-sperc))/100
    print("local g/q/s/e:",f"{gperc}/{qperc}/{sperc}/{eperc}")
    print("most common subtags:","TODO")
    print("previous appearances:","TODO")

def main():
    timecounter = time.time_ns()
    result = False
    args = sys.argv
    # print("finished fixing tagdata")
    if(len(args) < 2):
        print("please provide arguments")
        return
    match args[1]:
        # case "qgr":
        #     quickdl() #ended up being slower than whathever I did last time, dunno how, appearently I did well...
        case "taginfo":
            for arg in args[2:]:
                taginfo(arg)
        case "compare":
            for thing in args[2:]:
                printstats(thing)
        case "prevsearch":
            with open("prevsearch.txt","r") as f: name = f.read()
            print(name)
            randomExist({"rating:general"},name=name)
        case "qer":
            quickrandexist()

        case "recache":
            cache.refresh(filterFunc=filterImgs)

        case "addfave":
            add_fave(args[2],args[3:])

        case "update_faves":
            update_faves(getnum = args[2])

        case "refresh":
            latest = str(latestImg())
            print(latest)
            images = [f for f in os.listdir(Wallpaper_Folder)]
            for image in images:
                if(image[:image.find(".")] == latest):
                    setWallpaper(image)
        case "prev":
            try:
                imid = getprevwall(args[2])
                notify("set previous",args[2],"steps back")
            except:
                imid = getprevwall(1)
                notify("set previous")

        case "printflags":
            printallflags()

        case "fixtags":
            # fixtagdata()
            fixALLImgTags(args[2])

        case "gettags":
            img = latestImg()
            data = getData(img, ctx.cache_dir)
            print(img)
            for thing in data:
                print(f"{thing}: {data[thing]}")

        case "flag":
            try:
                flag = args[2]
            except:
                print("please supply a flag")
                return
            notify(f"flagged {flag}")
            setflag(latestImg(),flag)

        case "get":
            get(args[2:],ctx)

        case "exist":
            randomExist(args[2:])

        case "copy":
            copydest = ""
            for arg in args:
                if("folder:" in arg):
                    args.remove(arg)
                    copydest = arg[arg.find(":")+1:]+"/"
                    os.makedirs(COPY_OUT_PATH+copydest,exist_ok=True)
            if(len(args) < 3):
                randomExist([f"this:{latestImg()}"],True,copydest)
            else:
                randomExist(args[2:],True,copydest)

        case "reset":
            notify("resetting wallpaper...")
            setWallpaper("default.png")

        case "help":
            print(HELPSTRING)

        case _:
            randomExist(args[2:],name = args[1])
            with open("prevsearch.txt","w") as f: f.write(args[1])

    printtime(timecounter,f"finished all execution in: ")
    # print("dumped tagdata")
if __name__ == "__main__":
    main()
