import subprocess
import os

def convert_vid(image,out):
    print("converting",image,"to",out)
    subprocess.Popen(f'ffmpeg -loglevel error -i "{image}" "{out}"', shell=True) #-hide_banner
    return True


def fix_vids(max_files: int, Wallpaper_Folder: Path):
    images = [f for f in os.listdir(Wallpaper_Folder)]
    vids = 0
    for image in images:
        extension = image[image.find("."):]
        imgid = image[:image.find(".")]
        if(extension in {".mp4", ".webm"}):
            convert = True
            for image_2 in images:
                imgid_2 = image_2[:image.find(".")]
                if(imgid == imgid_2 and image != image_2):
                    print("found duplicate:",image_2)
                    if("gif" in image_2):
                        print("dupe is a gif, deleting original...")
                        convert = False
                        print("deleting",f"{Wallpaper_Folder}{image}")
                        os.remove(f"{Wallpaper_Folder}{image}")
            if(convert):
                print("found video:",image,"starting conversion...")
                try:
                    if(convert_vid(f"{Wallpaper_Folder}{image}",f"{Wallpaper_Folder}/{imgid}.gif")):
                        vids += 1
                    else:
                        print("failed to convert",image)
                except Exception as e:
                    print(e)
            else:
                print("Skipped",image)
        if(vids >= max_files):
            break
    print(f"started conversion of {vids} vids...")
    while(True):
        checker = subprocess.run('ps -C ffmpeg | wc -l', shell= True, capture_output=True, text = True)
        ffmpegNum = int(checker.stdout.strip())
        if(ffmpegNum == 1):
            print("completed conversion :D")
            break




