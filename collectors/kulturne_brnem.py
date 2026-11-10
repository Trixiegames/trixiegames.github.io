"""Experimental cultural programme importer for Kulturně Brnem.
The first source is the official structured programme of Městské divadlo Brno.
Never fabricate event dates, prices, coordinates or ticket links.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = "https://www.mdb.cz/data/program.json"
TZ = ZoneInfo("Europe/Prague")
OUTPUT = Path(__file__).resolve().parents[1] / "kultura" / "data"

def walk(value):
    if isinstance(value, list):
        for item in value:
            yield from walk(item)
    elif isinstance(value, dict):
        if value.get("@type") or value.get("type"):
            yield value
        for key in ("@graph", "items", "events", "data"):
            if key in value:
                yield from walk(value[key])

def value(x):
    if isinstance(x, list):
        return value(x[0]) if x else None
    if isinstance(x, dict):
        return x.get("@value") or x.get("name") or x.get("url")
    return x

def when(v):
    v=value(v)
    if not isinstance(v,str): return None
    try:
        result=dt.datetime.fromisoformat(v.replace("Z","+00:00"))
        return (result.replace(tzinfo=TZ) if result.tzinfo is None else result).astimezone(TZ)
    except ValueError:
        return None

def normalize(raw, now=None):
    now=now or dt.datetime.now(TZ)
    until=now+dt.timedelta(days=90)
    seen=set()
    result=[]
    for event in walk(raw):
        t=event.get("@type",event.get("type",""))
        types=t if isinstance(t,list) else [t]
        if not any(str(x).lower().endswith("event") for x in types):
            continue
        start=when(event.get("startDate") or event.get("start"))
        end=when(event.get("endDate") or event.get("end"))
        title=value(event.get("name"))
        if start is None or not isinstance(title,str) or not title.strip() or not now<=start<=until:
            continue
        location=event.get("location")
        venue=value(location) or "Městské divadlo Brno"
        url=value(event.get("url") or event.get("@id"))
        if not isinstance(url,str) or not url.startswith("https://"):
            url=SOURCE
        ident=f"{url}|{start.isoformat()}|{title}"
        uid="mdb-"+hashlib.sha256(ident.encode()).hexdigest()[:16]
        if uid in seen:continue
        seen.add(uid)
        result.append({"id":uid,"title":title.strip(),"category":"Divadlo",
          "start":start.isoformat(),"end":end.isoformat() if end else None,
          "venue":{"name":str(venue),"city":"Brno","lat":None,"lon":None},
          "price":{"status":"unknown"},"source":{"name":"Městské divadlo Brno","url":url},
          "status":"scheduled"})
    return sorted(result,key=lambda e:e["start"])

def main():
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"Kulturne-Brnem/0.2 (https://davhab.com/kultura/)","Accept":"application/ld+json, application/json"})
    with urllib.request.urlopen(req,timeout=30) as response:
        data=json.load(response)
    events=normalize(data)
    if not events:
        raise RuntimeError("No valid upcoming events; keeping previous published data")
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"events.json").write_text(json.dumps(events,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    meta={"updatedAt":dt.datetime.now(TZ).isoformat(),"count":len(events),
          "scope":"Zatím pouze Městské divadlo Brno; pokrytí celého regionu a 90 dnů není zaručeno",
          "sources":[{"name":"Městské divadlo Brno","url":SOURCE}]}
    (OUTPUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Imported {len(events)} events")
if __name__=="__main__":
    main()
