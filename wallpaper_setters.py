import subprocess
from pathlib import Path
from datetime import datetime
from filehandler import getData, setData
from AppContext import AppContext

def add_occurance(img_id, ctx: AppContext):
    Path("latest.txt").write_text(img_id)
    with open("history.txt", "a") as f:
        f.write(f"{img_id}; {datetime.now()}\n")

    imgdata = getData(img_id, ctx.cache_dir)
    imgdata["occurances"] = imgdata.get("occurances", 0) + 1
    setData(img_id, imgdata, ctx.cache_dir)

def setWallpaper_Android(wallpaper_path, img_id, ctx: AppContext):
    subprocess.Popen(f'am start -a android.intent.action.ATTACH_DATA -t "image/*" -d file:{wallpaper_path}', shell=True)
    add_occurance(img_id, ctx)


def setWallpaper_MacOS(wallpaper_path, img_id, ctx: AppContext):
    HOME_PATCH = ctx.env.get(HOME_PATH)
    script = f"""
    tell application "System Events"
        tell desktop 1
            set picture to "{HOME_PATH}{wallpaper_path}"
        end tell
    end tell
    """
    subprocess.run(["osascript","-e",script])
    add_occurance(img_id, ctx)


def setWallpaper_Plasma(wallpaper_path, img_id, ctx: AppContext):
    subprocess.run(
        ["plasma-apply-wallpaperimage", str(wallpaper_path)],
        check=False,
    )

    desktop_link_path = Path(ctx.env.get("DESKTOP_PATH")) / "wallpaperURL.desktop"
    desktop_link_path.write_text(
        (
            "[Desktop Entry]\n"
            f"Icon={ctx.cache_dir / 'gelbooru-logo.svg'}\n"
            "Name=wallpaperURL\n"
            "Type=Link\n"
            f"URL[$e]=https://gelbooru.com/index.php?page=post&s=view&id={img_id}"
        )
    )

    add_occurance(img_id, ctx)

def setWallpaper(image: str, ctx: AppContext) -> None:
    wallpaper_path = ctx.wallpaper_dir / image
    img_id = Path(image).stem
    DESKTOP_MANAGER = ctx.env.get("DESKTOP_MANAGER")
    match DESKTOP_MANAGER:
        case "Plasma":
            setWallpaper_Plasma(wallpaper_path, img_id, ctx)
        case "MacOS":
            setWallpaper_MacOS(wallpaper_path, img_id, ctx)
        case "Android":
            setWallpaper_Android(wallpaper_path, img_id, ctx)


