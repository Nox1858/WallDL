from webreq_helpers import *
from AppContext import AppContext
import os
import json
from timer import printtime, notify

def handleTagWebRequest(fullReq):
    # timecounter = time.time_ns()
    newdata = tagrequest(fullReq)
    if(not newdata):
        return False
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
        tagjson = {'name':tagdata["name"],'id': tagdata["id"], 'count': tagdata["count"], 'type': tagtype, 'ambiguous': tagdata["ambiguous"], 'date-added':str(d.now())}
        return tagjson
    # printtime(timecounter,"finished tagrequest in: ")



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



def get(args, ctx: AppContext, quiet = False, setwall = True, max_tries = 5):
    timecounter102 = time.time_ns()
    global fullTagData
    with open(os.path.join(ctx.env.get("WALLPAPER_CACHE"), "tagdata.json"), "r") as f:
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

    with open(os.path.join(ctx.evn.get("WALLPAPER_CACHE"), "tagdata.json"), "w") as f: json.dump(fullTagData,f)
    return len(totalDLTime)
