import requests
import time

API_KEY = "your stuff here"
USER_ID = "your stuff here"

cookies={
    "your stuff here too"
}


def Grequest(page, extra, limit = 0):
    #page = tag/post
    link = f"https://gelbooru.com/index.php?page=dapi&s={page}&q=index&json=1&api_key={API_KEY}&user_id={USER_ID}&limit={limit}&{extra}"
    global cookies
    timeout = 0
    while(timeout < 5):
        # if(timeout > 0.5): print("sleeping",timeout,"on",link)
        time.sleep(timeout)
        # timecounter2 = time.time_ns()
        r = requests.get(link,cookies=cookies)
        # rawReqTimes.append(printtime(timecounter2,"request completed in ",out=False))
        # printtime(timecounter2,"raw request time:")
        if(r.status_code == 200): timeout = 10
        timeout += randrange(200,1000)/20000
    if(timeout == 10): return r.json()
    print("failed to complete request")
    return False


def tagrequest(tags):
    streq = ""
    for tag in tags:
        streq += tag+" "
    tags = streq.replace("&#039;","'").replace("+","%2b").replace("&gt;",">").replace("&lt;","<").replace("&amp;","%26").replace("&quot;",'"').replace("#","%23").replace("/","%2f")
    link = "names="+tags

    r = Grequest("tag",link)
    if(r):
        try:
            return r["tag"]
        except:
            print("didn't find tags")
    return False

def apirequest(tags,random=True,limit=0):
    link = "tags="
    for tag in tags:
        link += str(tag)+"+"
    if(random): link += "sort:random"

    r = Grequest("post",link,limit)
    if(r):
        try:
            return r["post"]
        except:
            print("failed to find any posts matching filters")
    return False


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
        # timecounter2 = time.time_ns()
        # print("trying to get",link)
        r = requests.get(link,headers=headers)
        # print(r.content)
        # rawDLTimes.append(printtime(timecounter2,f"downloaded {imgid}{ext} in ",out=False))
        if(r.status_code == 200): timeout = 10
        timeout += randrange(200,1000)/20000
    imgdata = r.content
    size = len(imgdata)/1000
    # totalDLSize.append(size)
    if(size > 1000):
        size = str(size/1000)[:6]+"mb"
    else:
        size = str(size)[:6]+"kb"
    # totalDLTime.append(printtime(timecounter,f"downloaded {imgid}{ext} of {size} in: "))
    # timecounter = time.time_ns()
    if("webm" in ext or "mp4" in ext):
        print("You'll probably not want to convert to gifs right now, so we'll skip this...")
        with open(Wallpaper_Folder+str(imgid)+ext, 'wb') as f: f.write(imgdata)

        # with open("videotmp/"+str(imgid)+ext, 'wb') as f: f.write(imgdata)
        # clip = VideoFileClip("videotmp/"+str(imgid)+ext)
        # clip.write_gif("videotmp/"+str(imgid)+".gif")
    else:
        with open(Wallpaper_Folder+str(imgid)+ext, 'wb') as f: f.write(imgdata)
    # totalSaveTime.append(printtime(timecounter,f"saved {imgid} of {size} in: ",out=False))
