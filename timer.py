import subprocess
import time
from env import Environment

def printtime(timer: int,message="",notification=False,out=True) -> int:
    timeval = (time.time_ns()-timer)
    timestr = formattime(timeval)
    if(out): print(f"{message}{timestr}")
    if(notification): notify(f"{message}{timestr}")
    return timeval

def formattime(timenum: int):
    timesize = "ns"
    if(timenum > 1000):
        timenum = timenum/1000
        timesize = " microsec"
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

def notify(message: str):
    env = Environment(".env")
    dm = env.get("DESKTOP_MANAGER")
    match dm:
        case "Plasma":
            subprocess.Popen(f'notify-send "{message}"', shell=True)
        case "MacOS":
            print("notify for macos not implemented")
        case "Android":
            print("notify for android not implemented")

