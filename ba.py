from wallpaper_setters import setRawWallpaper as setWall
import time

def getstrnum(num):
    if(num<1000):
        if(num<100):
            if(num<10):
                strnum = "000"+str(num)
            else:
                strnum = "00"+str(num)
        else:
            strnum = "0"+str(num)
    else:
        strnum = str(num)
    return strnum

def run_ba(badir,ctx):
    timer = time.time_ns()
    for i in range(500):
        timedif = (1/10) - ((time.time_ns()-timer)/1000000000)
        time.sleep(max(timedif,0))
        timer = time.time_ns()
        strnum = getstrnum(i*3)
        setWall(f"{badir}/output_{strnum}.jpg",ctx)

def set_ba(badir,ctx):
    setWall(f"{badir}/ba.gif",ctx)

"ffmpeg -i in.mp4 out.gif"
