print("Now setting up requirements for this script...")
import os
desktop_path = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
home_path = os.getcwd()

api_key = input("Please enter your API key: ")
user_id = input("Please enter your User ID: ")
wallpaper_images = input("Please enter the path to your Wallpaper Folder: ")
wallpaper_cache = input("Please enter the path for saving data (tags, cache, etc.): ")
copyout_path = input("Please enter the path where you want to output copied images: ")
desktop_manager = input("Please enter your desktop manager (Plasma, MacOS or Android): ")



from env import Environment
env = Environment(".env")
env.add("API_KEY",api_key)
env.add("USER_ID",user_id)
env.add("WALLPAPER_IMAGES",wallpaper_images)
env.add("DESKTOP_PATH",desktop_path)
env.add("HOME_PATH",home_path)
env.add("WALLPAPER_CACHE",wallpaper_cache)
env.add("COPY_OUTPUT_DESTINATION",copyout_path)
env.add("DESKTOP_MANAGER",desktop_manager)
env.save()

os.makedirs(f"{wallpaper_cache}/tags",exist_ok=True)
with open(f"{wallpaper_cache}/searchcache.json","w") as f: f.write('{"any":{"querry": [""], "used": 0, "date": "2026-01-31 23:59:59.0", "results":[]}"')
with open(f"{wallpaper_cache}/tagdata.json","w") as f: f.write("{}")
with open(f"{wallpaper_cache}/faves.json","w") as f: f.write("{}")

print("and we're done, have fun :)")
