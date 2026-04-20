import requests

def getGlobalCount(ctx, tags):
    r = requests.get(f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&api_key={ctx.api_key}&user_id={ctx.user_id}&tags={tags}")
    if(r.status_code == 200):
        r = r.json()
        return int(r["@attributes"]["count"])
    else:
        return False

def getGlobalStats(ctx, querry):
    qstr = ""
    for thing in querry:
        qstr += thing+"+"
    qstr = qstr[:-1]
    total = getGlobalCount(ctx, qstr)
    if(total == 0):
        return False
    safe = getGlobalCount(ctx, qstr+"+rating:general")
    questionable = getGlobalCount(ctx, qstr+"+rating:questionable")
    sensitive = getGlobalCount(ctx, qstr+"+rating:sensitive")
    explicit = getGlobalCount(ctx, qstr+"+rating:explicit")
    return [total, safe, questionable, sensitive, explicit]
