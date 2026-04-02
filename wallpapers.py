import requests
import json
import os
from ntpath import join
import subprocess
import time

import sys
from random import randrange

from datetime import datetime as d
from datetime import timedelta

from threading import Thread

API_KEY = "your stuff here"
USER_ID = "your stuff here"

Wallpaper_Folder = 'path/where/images/will/be/stored'

DESKTOP_PATH = "/home/user/Desktop/"
WALL_HOME_PATH = "/path/where/cache/and/stuff/will/be/stored/"
COPY_OUT_PATH = "/output/if/you/want/an/image"


HELPSTRING = """Fun Utility for downloading Wallpapers from a questionable Source :)

ALL OF THIS IS OUTDATED, WILL NEED TO UPDATE (Status Oct-2025)
add 'repeat:x:y' for repeating the following command x times with y sec delay
add 'tries:x' for changing retry amount
add 'keepprev' to flag the previous wallpaper for keeping, by default the _latest flag is just moved

You can use the following modes
str(d.now())
flag [specify glag]: sets latest's flag to the specified

get [flag] [tags]:  gets a random image with default filter and tags
    --limit         specify the number of images to download
    --max_tries     change maximum number of retries (usually not necessary)
    --safe          general only
    --sort          sort by id instead of randomly

exist [flag] [tags]:gets an existing image based on tags
    --wide          only wide images
    --narrow        only narrow images
    --square        only square images
    height:int      min int height
    width:int       min int width
    flag:string     img has this flag ("exclude" doesn't work)

'reset'             applies the default wallpaper
'help'              show this       """

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

def addtocache(querry,results,name = False,used = 0):
    querry.sort()
    with open("searchcache.json", "r") as f: data = json.load(f)
    found = False
    if(name):
        try:
            used = data[name]["used"]
        except:
            True
        data[name] = {"querry":querry,"used":used,"date":str(d.now()),"results":results}
        found = True
    else:
        for entry in data:
            if(data[entry]["querry"] == querry):
                used = data[entry]["used"]
                data[entry] = {"querry":querry,"used":used,"date":str(d.now()),"results":results}
                found = True
                break
    if(not found):
        data[str(len(data))] = {"querry":querry,"used":used,"date":str(d.now()),"results":results}
    print("cached",querry)
    with open("searchcache.json", "w") as f: json.dump(data,f)

def getcache(querry,name=False,quiet=False):
    with open("searchcache.json", "r") as f: data = json.load(f)
    if(name):
        try:
            used = data[name]["used"] + 1
            data[name]["used"] = used
            date = d.strptime(data[name]["date"], "%Y-%m-%d %H:%M:%S.%f")
            if(not quiet): print("previously used this search",used,"times")
            if(d.now()-date > timedelta(days = 3)):
                notify("this cache is >3d old, maybe update it? cached on",date)
            with open("searchcache.json", "w") as f: json.dump(data,f)
            return data[name]["results"]
        except:
            if(not quiet): print("search not cached")
            return False
    else:
        querry.sort()
        for entry in data:
            if(data[entry]["querry"] == querry):
                used = data[entry]["used"] + 1
                data[entry]["used"] =  used
                date = data[entry]["date"]
                if(not quiet): print("previously used this search",used,"times")
                date = d.strptime(data[entry]["date"], "%Y-%m-%d %H:%M:%S.%f")
                if(d.now()-date > timedelta(days = 3) and used > 3):
                    notify("this cache is >3d old, maybe update it? cached on",date)
                with open("searchcache.json", "w") as f: json.dump(data,f)
                return data[entry]["results"]
    if(not quiet): print("search not cached")
    return False

def refresh_cache():
    with open("searchcache.json", "r") as f: data = json.load(f)
    with open("searchcache.json", "w") as f: f.write("{}")
    for entry in data:
        date = d.strptime(data[entry]["date"], "%Y-%m-%d %H:%M:%S.%f")
        used = data[entry]["used"]

        # print(date,used)
        if(used < 2):
            print(entry,data[entry]["querry"],"is not used often, skipping update...")
        else:
            results = []
            querry = []
            querry = data[entry]["querry"]
            print("updating",entry,querry,used,date)
            prevlen = len(data[entry]["results"])
            if(len(querry) == 0):
                # results = [f for f in os.listdir(Wallpaper_Folder)]
                print("empty querry, skipping...")
            else:
                results = filterImgs(querry)
                # selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
                print("found",len(results),"images with given tags, previously was",prevlen)
                addtocache(querry,results,entry,used)
    addtocache([],[f for f in os.listdir(Wallpaper_Folder)],"any",data["any"]["used"])
    print("refreshed 'any'")

def formattime(timenum):
    timesize = "ns"
    if(timenum > 1000):
        timenum = timenum/1000
        timesize = "microsec"
        if(timenum > 1000):
            timenum = timenum/1000
            timesize = "ms"
            if(timenum > 1000):
                timenum = timenum/1000
                timesize = "s"
                if(timenum > 100):
                    timenum = timenum/60
                    timesize = "min"
    return str(timenum)[:6]+timesize

def notify(message):
    subprocess.Popen(f'notify-send "{message}"', shell=True)

def printtime(timer,message="",notification=False,out=True):
    timeval = (time.time_ns()-timer)
    timestr = formattime(timeval)
    if(out): print(f"{message}{timestr}")
    if(notification): notify(f"{message}{timestr}")
    return timeval


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


def getdata(imgid):
    try:
        with open(f"tags/{imgid}.json","r") as f: return json.load(f)
    except Exception as e:
        print("failed to load tags of",imgid,"exception:",e)
        with open(f"tags/default.json","r") as f: return json.load(f)

def setdata(imgid,data):
    # timecounter = time.time_ns()
    with open(f"tags/{imgid}.json","w") as f:
        json.dump(data,f)
        # print("imgtags write overhead:",(time.time_ns()-timecounter)/1000000,"ms")

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
    imgdata = getdata(imgid)
    try:
        imgdata["occurances"] += 1
    except:
        imgdata["occurances"] = 1
    setdata(imgid, imgdata)




def checkExisting(imgid,sendnote = True):
    images = [f for f in os.listdir(Wallpaper_Folder)]
    for image in images:
        if(image[:image.find(".")] == str(imgid)): return True
    # with open ("downloaded.txt","r") as f: data = f.read()
    # if (str(imgid) in data):
        # # print(f"already downloaded {imgid}")
        # return True
    with open("downloaded.txt","a") as f: f.write(str(imgid)+"\n")
    # if(sendnote): notify(f"added {imgid}")
    return False


# def retryTags(imgid):
#     print(f"{imgid} has ill formatted or no tags, retrying...")
#     post = apirequest([f"id:{imgid}"])[0]
#     initdata(imgid,post)



def setflag(imgid,flag):
    data = getdata(imgid)
    data["flag"] = flag
    setdata(imgid,data)

def tagrequest(tags):
    cookies={
        #your stuff here
    }

    link = f"https://gelbooru.com/index.php?page=dapi&s=tag&q=index&json=1&api_key={API_KEY}&user_id={USER_ID}&limit=0&names="
    tags = tags.replace("&#039;","'").replace("+","%2b").replace("&gt;",">").replace("&lt;","<").replace("&amp;","%26").replace("&quot;",'"').replace("#","%23").replace("/","%2f")
    link += tags
    # print(tags)
    # print("requesting info about: "+tags)
    timeout = 0
    while(timeout < 5):
        # if(timeout > 0.5): print("sleeping",timeout,"on",link)
        time.sleep(timeout)
        timecounter2 = time.time_ns()
        r = requests.get(link,cookies=cookies)
        # printtime(timecounter2,"raw request time:")
        if(r.status_code == 200): timeout = 10
        timeout += randrange(200,1000)/20000
    r = r.json()
    try:
        return r["tag"]
    except:
        print("didn't find any tags")
        return []


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

    setdata(imgid,data)
    if(len(failed) == 0): return False
    return failed
    # printtime(timecounter,f"handled tags for {imgid} in: ")


def handleTagWebRequest(fullReq):
    timecounter = time.time_ns()
    streq = ""
    for thing in fullReq:
        streq += thing+" "
    newdata = tagrequest(streq)
    for tagdata in newdata:
        match tagdata["type"]:
            case 0:
                tagtype = "general"
            case 1:
                tagtype = "artist"
            case 3:
                tagtype = "copyright"
            case 4:
                tagtype = "character"
            case 5:
                tagtype = "meta"
            case _:
                print("found tag with type unknwon",tagdata["type"])
                tagtype = "unknown"
                with open("unknowntags.txt","a") as f: f.write(tagdata["name"]+"\n")
        # print("updated",tagdata["name"])
        fullTagData[tagdata["name"]] = {'name':tagdata["name"],'id': tagdata["id"], 'count': tagdata["count"], 'type': tagtype, 'ambiguous': tagdata["ambiguous"], 'date-added':str(d.now())}
    # printtime(timecounter,"finished tagrequest in: ")

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
            t1 = Thread(target=handleTagWebRequest, args=[reqs])
            t1.start()
            ReqThreads.append(t1)
        else:
            handleTagWebRequest(reqs)
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

# from moviepy.video.io.VideoFileClip import VideoFileClip

def saveImg(link,imgid,ext):
    timecounter = time.time_ns()
    timeout = 0
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
        # "Accept": "image/avif,image/webp,image/apng,image/,/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": link,
        "Connection": "keep-alive",
    }
    while(timeout < 2):
        # if(timeout > 0.5): print("sleeping",timeout,"on",link)
        time.sleep(timeout)
        timecounter2 = time.time_ns()
        # print("trying to get",link)
        r = requests.get(link,headers=headers)
        # print(r.content)
        rawDLTimes.append(printtime(timecounter2,f"downloaded {imgid}{ext} in ",out=False))
        if(r.status_code == 200): timeout = 10
        timeout += randrange(200,1000)/20000
    imgdata = r.content
    size = len(imgdata)/1000
    totalDLSize.append(size)
    if(size > 1000):
        size = str(size/1000)[:6]+"mb"
    else:
        size = str(size)[:6]+"kb"
    totalDLTime.append(printtime(timecounter,f"downloaded {imgid}{ext} of {size} in: "))
    timecounter = time.time_ns()
    if("webm" in ext or "mp4" in ext):
        print("You'll probably not want to convert to gifs right now, so we'll skip this...")
        with open(Wallpaper_Folder+str(imgid)+ext, 'wb') as f: f.write(imgdata)

        # with open("videotmp/"+str(imgid)+ext, 'wb') as f: f.write(imgdata)
        # clip = VideoFileClip("videotmp/"+str(imgid)+ext)
        # clip.write_gif("videotmp/"+str(imgid)+".gif")
    else:
        with open(Wallpaper_Folder+str(imgid)+ext, 'wb') as f: f.write(imgdata)
    totalSaveTime.append(printtime(timecounter,f"saved {imgid} of {size} in: ",out=False))

def getImg(link,imgid,ext,notify=True,download=True):
    if(checkExisting(imgid,notify)):
        return False
    timecounter = time.time_ns()
    if("mp4" in ext or "webm" in ext):
        print("this is a video, conversion still wip...")
        return False
    #     ext = ".gif"
    elif(download):
        t1 = Thread(target=saveImg, args=(link,imgid,ext))
        t1.start()
        ImgThreads.append(t1)
    # print("download thread creation overhead:",(time.time_ns()-timecounter)/1000000,"ms")
    return f"{imgid}{ext}"


def apirequest(tags,random=True,limit=0):
    # timecounter = time.time_ns()
    cookies={
        #your stuff here
    }

    link = f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&api_key={API_KEY}&user_id={USER_ID}&limit={limit}&tags="
    for tag in tags:
        link += str(tag)+"+"
    if(random): link += "sort:random"

    timeout = 0
    # print("link preperation overhead:",(time.time_ns()-timecounter)/1000,"microsec")
    while(timeout < 2):
        # if(timeout > 0.5): print("sleeping",timeout,"on",link)
        time.sleep(timeout)
        timecounter2 = time.time_ns()
        r = requests.get(link,cookies=cookies)
        rawReqTimes.append(printtime(timecounter2,"Post request completed in ",out=False))
        if(r.status_code == 200): timeout = 10
        else: print(r.status_code, timeout)
        timeout += randrange(200,1000)/20000
    r = r.json()

    try:
        # print("got posts in total",(time.time_ns()-timecounter)/1000000,"ms")
        return r["post"]
    except:
        print("failed to find any posts matching filters")
        return False

def downloadImgs(tags=[], random=True, limit=1, max_tries = 5, notifications=True,download=True):
    timecounter = time.time_ns()
    if(max_tries < 1): return False
    apilimit = limit
    if(limit > 100): apilimit = 0
    posts = apirequest(tags,random,apilimit)
    downloaded = 0
    latest = False
    if(limit > 10):
        notifications = False
    totalPostReqTime.append(printtime(timecounter,"post request finished in: ",out=False))
    if(posts):
        timecounter = time.time_ns()
        for post in posts:
            if(downloaded < limit):
                postid = post["id"]
                url = post["file_url"]
                # print(url)
                ext = post["image"][post["image"].find("."):]
                img = getImg(url,postid,ext,notifications,download)
                # if("webm" in ext or "mp4" in ext):
                #     ext = ".gif"
                if(img):
                    latest = postid
                    # timecounter = time.time_ns()
                    # print("adding",img,"to tagreq list")
                    allTagRequests[post["id"]] = post
                    # print("initdata thread creation overhead:",(time.time_ns()-timecounter)/1000000,"ms")
                    downloaded += 1
        if(downloaded < limit):
            if(not random): tags.append(f"id:<{latest}")
            return downloadImgs(tags,random,limit-downloaded,max_tries-1,notifications)
        if(latest):
            # printtime(timecounter,"post handling and setup overhead: ")
            return str(latest)+ext
    return downloadImgs(tags,random,limit-downloaded,max_tries-1,notifications)

def quickdl(tags=[]):
    timecounter = time.time_ns()
    posts = apirequest(tags,True,1)
    cookies={
        #your stuff here
    }
    link = f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&api_key={API_KEY}&user_id={USER_ID}&limit=1&tags=sort:random"
    r = requests.get(link,cookies=cookies).json()
    post = r["post"][0]
    postid = post["id"]
    url = post["file_url"]
    ext = post["image"][post["image"].find("."):]
    if(getImg(url,postid,ext,False,True)):
        allTagRequests[post["id"]] = post
        timecounter = timeselectimgs.time_ns()
        tags = post["tags"]
        tags = tags.split()
        tagreq = []
        for tag in tags:
            #Checks if data on a tag is present, otherwise or if too old add to update list
            try:
                tagdata = fullTagData[tag]
                # date = d.strptime((tagdata["date-added"]), "%Y-%m-%d %H:%M:%S.%f")
                # if(d.now()-date > timedelta(days = 10)):
                #     print("updating",tag,"since it's more than 10d old'")
                #     fullRequests[tag] = True
            except Exception as e:
                tagreq.append(tag)
        print("need to update",len(tagreq),"tags...")
        # printtime(timecounter,"tagrequest setup overhead: ")
        # time.sleep(3)
        handleTagRequests(tagreq)
        initdata(postid,post,False)


    #     timecounter = time.time_ns()
    # print("initializing data for",imgid)
    # tags = predata["tags"]
    # artist = []; copyright = []; character = []; meta = []; general = []; failed = []
    # try:
    #     tags = tags.split()
    # except:
    #     True
    # for tag in tags:
    #     try:
    #         tagtype = fullTagData[tag]["type"]
    #         match tagtype:
    #             case "general": general.append(tag)
    #             case "artist": artist.append(tag)
    #             case "copyright": copyright.append(tag)
    #             case "character": character.append(tag)
    #             case "meta": meta.append(tag)
    #             case "unknown":
    #                 print("found tag with unknown type:",tag,tagtype)
    #                 general.append(tag)
    #                 with open("unknowntags.txt","a") as f: f.write(tag+"\n")
    #     except Exception as e:
    #         print("failed to find",tag,e)
    #         failed.append(tag)
    #
    # if(fix):
    #     if(len(artist) == 0):
    #         print(imgid,"doesn't have an artist, setting unknown. Link:",predata["url"])
    #         artist = ["_unknown_"]
    #     data = {
    #         "download-date":predata["download-date"],
    #         "flag":predata["flag"],
    #         "rating":predata["rating"],
    #         "width":predata["width"],
    #         "height":predata["height"],
    #         "artist":artist,
    #         "character":character,
    #         "copyright":copyright,
    #         "meta":meta,
    #         "tags":tags,
    #         "url":predata["url"]
    #         }
    # else:
    #     if(len(artist) == 0):
    #         print(imgid,"doesn't have an artist, setting unknown. Link:",predata["file_url"])
    #         artist = ["_unknown_"]
    #     data = {
    #         "download-date":str(d.now()),
    #         "flag":"none",
    #         "rating":predata["rating"],
    #         "width":predata["width"],
    #         "height":predata["height"],
    #         "artist":artist,
    #         "character":character,
    #         "copyright":copyright,
    #         "meta":meta,
    #         "tags":tags,
    #         "url":predata["file_url"]
    #         }
    #
    # setdata(imgid,data)
    # if(len(failed) == 0): return False
    # return failed


        # print("finished handling tagrequests")
        for t in InitThreads:
            t.join()
        for t in ImgThreads:
            t.join()
        setWallpaper(str(postid)+ext)

def handleImg(image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag):
    selectimgs = []
    # timecounter = time.time_ns()
    imgdata = getdata(image[:image.find(".")])
    # printtime(timecounter,"loaded imgdata in ")
    # timecounter = time.time_ns()
    if("exclude" not in imgdata["flag"]):
        if((not rating) or str(rating) in imgdata["rating"]):
            if((not exrating) or str(rating) not in imgdata["rating"]):
                if((not flag) or str(flag) in imgdata["flag"]):
                    if(imgdata["width"] >= minwidth and imgdata["height"] >= minheight):
                        if(not wide or imgdata["width"] >= imgdata["height"]):
                            if(not narrow or imgdata["width"] <= imgdata["height"]):
                                exok = True
                                tagok = True
                                # printtime(timecounter, "handled pre exclusions in ")
                                timecounter = time.time_ns()
                                alltags = imgdata["tags"] + imgdata["character"] + imgdata["copyright"] + imgdata["artist"] + imgdata["meta"]
                                # printtime(timecounter, "joined tag lists in ")
                                for tag in extags:
                                    if (tag in  alltags):
                                        exok = False
                                        break
                                for tag in tags:
                                    if (tag not in alltags):
                                        tagok = False
                                        break
                                if(exok and tagok):
                                    # printtime(timecounter, "added image to list in ")
                                    return True
                                    # print("found",image)
                                    # printtime(timecounter, "actually added image to list in ")
    return False
# printtime(timecounter,"completed image check in ")

# handleThreads = []

# def handleImgs(images,start,end,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag):
#     # threads = []
#     if(end-start > 3000):
#         timecounter = time.time_ns()
#         mid = start+int((end-start)/2)
#         t1 = Thread(target=handleImgs, args=(images,start,mid,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag))
#         t2 = Thread(target=handleImgs, args=(images,mid,end,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag))
#         t1.start()
#         t2.start()
#         handleThreads.append(t1)
#         handleThreads.append(t2)
#         printtime(timecounter,"thread setup overhead ")
#         timecounter = time.time_ns()
#
#         # handleImgs(images,mid,end,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag)
#         # printtime(timecounter, "handling completed in ")
#     else:
#         print(start,end)
#         for image in images[start:end]:
#             handleImg(image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag)
selectimgs = []

def filterThreadHandler(images,latest,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag):
    global selectimgs
    timecounter = time.time_ns()
    for image in images:
        if(not latest in image):
            if(handleImg(image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag)):
                selectimgs.append(image)
    printtime(timecounter, "thread took ")

def filterImgs(args):
    # timecounter4 = time.time_ns()
    # printtime(timecounter4, "initialization took ")
    # timecounter4 = time.time_ns()
    selection = False
    rating = False
    exrating = False
    tags = []
    extags = []
    minheight = 0
    minwidth = 0
    wide = False
    narrow = False
    flag = False
    # printtime(timecounter4, "initialization took ")
    # printtime(timecounter4, "initialization took ")
    for arg in args:
        if("this:" in arg): selection = arg[arg.find(":")+1:]
        elif("-rating:" in arg): exrating = arg[arg.find(":")+1:]
        elif("rating:" in arg): rating = arg[arg.find(":")+1:]
        elif("flag:" in arg): flag = arg[arg.find(":")+1:]
        elif("--wide" in arg): wide = True
        elif("--narrow" in arg): narrow = True
        elif("--square" in arg):
            wide = True
            narrow = True
        elif("height:" in arg):
            match arg[arg.find(":")+1:]:
                case "1k":
                    minheight = 960
                case "2k":
                    minheight = 1920
                case "4k":
                    minheight = 3840
                case _:
                    minheight = int(arg[arg.find(":")+1:])
        elif("width:" in arg):
            match arg[arg.find(":")+1:]:
                case "1k":
                    minwidth = 960
                case "2k":
                    minwidth = 1920
                case "4k":
                    minwidth = 3840
                case _:
                    minwidth = int(arg[arg.find(":")+1:])
        elif('-' == arg[0]):
            extags.append(arg[1:])
        else:
            tags.append(arg)
    # printtime(timecounter4,"prehandling done in ")
    images = [f for f in os.listdir(Wallpaper_Folder)]
    global selectimgs
    latest = latestImg()
    selectimgs = []
    # print(latest)
    # print(images[0])
    # printtime(timecounter4,"prehandling and loading imgs done in ")
    if(selection):
        for image in images: #TODO this is horrible, fix it (checking all images just to find file extension)
            if(selection == image[:image.find(".")]):
                selectimgs.append(image)
    else:
        timecounter = time.time_ns()
        # print("starting partitioning of image array...")
        parts = 1
        partlen = int(len(images)/parts)
        fthreads = []
        for i in range(parts-1):
            partimages = images[i*partlen:(i+1)*partlen]
            t = Thread(target=filterThreadHandler, args=(partimages,latest,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag))
            t.start()
            fthreads.append(t)
            # t.join()
        # print("starting thread 15")
        partimages = images[(parts-1)*partlen:]
        t = Thread(target=filterThreadHandler, args=(partimages,latest,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag))
        t.start()
        fthreads.append(t)
        t.join()
        printtime(timecounter, "initializing threads took ")
        # print("started thread 15")
        for t in fthreads:
            print("joining thread",t)
            t.join()
        print("done filtering")
        # for image in images:
        #     filterThreadHandler(latest,image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag)


    # handlethread = []
    # for image in images:
    #     timecounter3 = time.time_ns()
    #     if(latest not in image):
    #         if(len(handlethread) < 500):
    #             timecounter = time.time_ns()
    #             t = Thread(target=hanldeImg,args=(image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag))
    #             t.start()
    #             handlethread.append(t)
    #         else:
    #             hanldeImg(image,rating,exrating,tags,extags,minheight,minwidth,wide,narrow,flag)
    #         printtime(timecounter,"thread setup overhead ")
    # for t in handlethread:
    #     t.join()

    # printtime(timecounter4,"filtering done in ")
    print(len(selectimgs))
    return selectimgs


import shutil
def copyout(image,folder = ""):
    shutil.copyfile(Wallpaper_Folder+image, COPY_OUT_PATH+folder+image)

def randomExist(args = [],copy=False,copydest="",name=False):
    timecounter = time.time_ns()
    if(name):
        selectimgs = getcache(querry = [], name = name)
        if(not selectimgs):
            selectimgs = filterImgs(args)
            addtocache(args,selectimgs,name = name)
    else:
        if(len(args) == 0):
            selectimgs = getcache(querry = [], name = "any")
            if(not selectimgs):
                selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
                addtocache(args,selectimgs,"any")
        else:
            selectimgs = getcache(querry = args)
            if(not selectimgs):
                selectimgs = filterImgs(args)
                addtocache(args,selectimgs)
            # selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
            print("found",len(selectimgs),"images with given tags")

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
        handleTagWebRequest(failed)
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

        # artist = predata["artist"]
        # flag = predata["flag"]
        # # print(artist,flag)
        # if("_unknown_" in artist):
        #     if(flag == "none"):
        #         tofix.append(imgid)
        #     else:
        #         print(imgid,flag)
        # else:
        #     if(flag!="none"):
        #         print(imgid,flag)

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



    # norating = []
    # failedTags = []
    # for image in images:
    #     # print(f"handling {image}")
    #     imgid = image[:image.find(".")]
    #     predata = getdata(imgid)
    #     flag = predata["flag"]
    #     copyright = predata["copyright"]
    #     character = predata["character"]
    #     meta = predata["meta"]
    #     tags = predata["tags"]
    #     try:
    #         tags = tags.split()
    #     except:
    #         True
    #     for tag in tags:
    #         try:
    #             tagtype = fullTagData[tag]["type"]
    #             match tagtype:
    #                 case "general": general.append(tag)
    #                 case "artist": artist.append(tag)
    #                 case "copyright": copyright.append(tag)
    #                 case "character": character.append(tag)
    #                 case "meta": meta.append(tag)
    #                 case "unknown": general.append(tag)
    #         except Exception as e:
    #             # print("failed to find",tag,e)
    #             general.append(tag)
    #             failedTags.append(tag)
        # if(len(artist) == 0): noartist.append(imgid)
        # if(len(artist) == 1 and artist[0] == "_unknown_"): noartist.append(imgid)
            # print(image,"has unknown artist")
    #     # print(predata["rating"])
    #     data = {
    #         "download-date":predata["download-date"],
    #         "flag":predata["flag"],
    #         "rating":predata["rating"],
    #         "width":predata["width"],
    #         "height":predata["height"],
    #         "artist":artist,
    #         "character":character,
    #         "copyright":copyright,
    #         "meta":meta,
    #         "tags":tags,
    #         "url":predata["url"]
    #         }
    #     setdata(imgid,data)
    #     # printtime(timecounter2,f"fixed tags for {imgid} in: ")
    # print("failed to find",failedTags)
    # print("these have no artist:",noartist)


# def fixtagdata():
#     for image in images

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
        imdata = getdata(imid)
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



def get(args,quiet = False, setwall = True, max_tries = 5):
    timecounter102 = time.time_ns()
    global fullTagData
    with open(f"tagdata.json", "r") as f:
        fullTagData= json.load(f)

    if(not quiet): printtime(timecounter102,"loaded entire tagdata in ")

    limit = 1
    tags = []
    random = True
    for thing in args:
        if("--limit" in thing):
            limit = int(thing[thing.find(":")+1:])
        elif("--max_tries" in thing):
            max_tries = int(thing[thing.find(":")+1:])
        elif("--safe" in thing):
            tags.append("rating:general")
        elif("--sort" in thing):
            random = False
        else:
            tags.append(thing)

    if(not quiet):  notify(f"getting wallpaper...")

    if(limit > 400): max_tries = int(limit/100)+1
    latest = downloadImgs(tags,random,limit,max_tries)
    handleTagRequests()
    if(not quiet): print("finished handling tagrequests")

    for t in InitThreads:
        t.join()
    if(not quiet): print("finished handling all imgtags")

    for t in ImgThreads:
        t.join()
    if(latest and setwall):
        setWallpaper(latest)

    if(not quiet):
        avrsize = 0
        totalsize = 0
        avrdltime = 0
        avrsavetime = 0
        avrpostreqtime = 0
        maxRawDLtime = 0
        maxRawReqtime = 0

        for size in totalDLSize: totalsize += (size/1000)
        for times in totalDLTime: avrdltime += (times/1000000)/limit
        for times in totalSaveTime: avrsavetime += (times/1000000)/limit
        for times in totalPostReqTime: avrpostreqtime += (times/1000000)/limit
        for times in rawDLTimes:
            if(times > maxRawDLtime): maxRawDLtime = times
        for times in rawReqTimes:
            if(times > maxRawReqtime): maxRawReqtime = times

        avrTotalImgTime = avrpostreqtime + avrdltime + avrsavetime

        avrsize = str(totalsize/limit)[:6]+"mb"
        totalsize = str(totalsize)[:6]+"mb"
        avrdltime = str(avrdltime/1000)[:6]+"sec"
        avrsavetime = str(avrsavetime)[:6]+"ms"
        avrTotalImgTime = str(avrTotalImgTime/1000)[:6]+"sec"
        maxRawTotaltime = maxRawDLtime+maxRawReqtime
        maxRawTotal = str(maxRawTotaltime/1000000000)[:6]+"sec"
        maxRawDLtime = str((maxRawDLtime)/1000000000)[:6]+"sec"
        maxRawReqtime = str((maxRawReqtime)/1000000000)[:6]+"sec"


        print(f"total size: {totalsize}\naverage Size: {avrsize}\naverage DL time: {avrdltime}\naverage save time: {avrsavetime}\naverage total time for image DL: {avrTotalImgTime}\nmax raw request time: {maxRawReqtime}\nmax raw DL time: {maxRawDLtime}\ntotal max raw time: {maxRawTotal}")
    endtime = printtime(timecounter102,f"got {len(totalDLTime)} images in: ",True)
    if(not quiet): print(f"total overhead: {formattime(endtime-maxRawTotaltime)}")

    with open(f"tagdata.json", "w") as f: json.dump(fullTagData,f)
    return len(totalDLTime)


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
        refresh_cache()
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
            refresh_cache()

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

        case "getags":
            img = latestImg()
            data = getdata(img)
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
            get(args[2:])

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
