import subprocess

def convert_vid(image,out):
    print("converting",image,"to",out)
    subprocess.Popen(f'ffmpeg -loglevel error -i "{image}" "{out}"', shell=True) #-hide_banner
    return True

