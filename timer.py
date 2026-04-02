import subprocess
import time

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

def notify(message: str):
    subprocess.Popen(f'notify-send "{message}"', shell=True)
