import json
from datetime import datetime as d
from datetime import timedelta
from typing import Callable
from AppContext import AppContext
import os


class SearchCache:

    def __init__(self, cacheFile:str, ctx:AppContext):
        self.cacheFile = os.path.join(ctx.env.get("WALLPAPER_CACHE"), cacheFile)
        self.ctx = ctx


    def clear(self):
        with open(self.cacheFile, "w") as f: f.write("{}")


    def refresh(self, filterFunc: Callable[[list[str]],list[str]]):
        with open(self.cacheFile, "r") as f: data = json.load(f)
        with open(self.cacheFile, "w") as f: f.write("{}")
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
                    results = filterFunc(querry)
                    # selectimgs = [f for f in os.listdir(Wallpaper_Folder)]
                    print("found",len(results),"images with given tags, previously was",prevlen)
                    self.add(querry,results,entry,used)
        self.add([],[f for f in os.listdir(self.ctx.env.get("WALLPAPER_IMAGES"))],"any",data["any"]["used"])
        print("refreshed 'any'")


    def add(self, querry: list[str], result: list[str], name = None, used = 0):
        querry.sort()
        with open(self.cacheFile, "r") as f: data = json.load(f)
        found = False
        if(name is not None):
            try:
                used = data[name]["used"]
            except:

                data[name] = {"querry":querry,"used":used,"date":str(d.now()),"results":result}
                found = True
        else:
            for entry in data:
                if(data[entry]["querry"] == querry):
                    used = data[entry]["used"]
                    data[entry] = {"querry":querry,"used":used,"date":str(d.now()),"results":result}
                    found = True
                    break
        if(not found):
            data[str(len(data))] = {"querry":querry,"used":used,"date":str(d.now()),"results":result}
        print("cached ",querry)
        with open(self.cacheFile, "w") as f: json.dump(data,f)


    def get(self, querry: list[str], name = None, used = 0, quiet=True):
        with open(self.cacheFile, "r") as f: data = json.load(f)
        if(name is not None):
            try:
                used = data[name]["used"] + 1
                data[name]["used"] = used
                date = d.strptime(data[name]["date"], "%Y-%m-%d %H:%M:%S.%f")
                if(not quiet): print("previously used this search",used,"times")
                if(d.now()-date > timedelta(days = 3)):
                    notify("this cache is >3d old, maybe update it? cached on",date)
                with open(self.cacheFile, "w") as f: json.dump(data,f)
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
                    with open(self.cacheFile, "w") as f: json.dump(data,f)
                    return data[entry]["results"]
        if(not quiet): print("search not cached")
        return False

