"""Refresh the public latest-only digest from publisher RSS (no AI/API key)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from restore_context import importance
from edition_archive import archive_edition
from source_reader import CATALOG, HOSTS, fetch, parse_feed as read_feed, inspect_article

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'politicky-prehled'
def parse_feed(body, source, now):
    config = next(x for x in CATALOG if x['name'] == source)
    return read_feed(body, config, now)

def accessible(row):
    try:
        source = next(x for x in CATALOG if x['name'] == row['source'])
        raw = fetch(row['url'])
        encoding = 'windows-1250' if b'charset=windows-1250' in raw[:10000].lower() or b'charset="windows-1250"' in raw[:10000].lower() else 'utf-8'
        return inspect_article(row, raw.decode(encoding, 'replace'), source)
    except Exception as exc:
        print(f"Article unavailable: {row['url']} ({type(exc).__name__})", flush=True)
        return None

def select(rows):
    chosen, tokens = [], []
    for row in sorted(rows, key=lambda r:datetime.fromisoformat(r['published_at']), reverse=True):
        if sum(x['category'] == row['category'] for x in chosen) >= 20:
            continue
        if sum(x.get('source') == row.get('source') and x['category'] == row['category'] for x in chosen) >= 4:
            continue
        terms = set(re.findall(r'\w{5,}', row['title'].lower()))
        if any(row['url'] == x['url'] for x in chosen):
            continue
        if terms and any(len(terms & other) >= 3 and len(terms & other) / max(1, min(len(terms), len(other))) > .65 for other in tokens):
            continue
        chosen.append(row)
        tokens.append(terms)
    return chosen

def render_card(row):
    title, summary, source, category, published, url = (escape(row[k], quote=True) for k in ['title','summary','source','category','published_at','url'])
    label = 'Domácí politika' if category == 'domaci' else 'Zahraniční politika'
    date = datetime.fromisoformat(row['published_at']).astimezone(ZoneInfo('Europe/Prague')).strftime('%d. %m. %Y · %H:%M')
    context = escape(row.get("importance") or importance(row), quote=True)
    return f'<article data-category="{category}" data-published="{published}"><div class="meta"><span class="category">{label}</span><time datetime="{published}">{date}</time></div><h2><a href="{url}">{title}</a></h2><p>{summary}</p><div class="why"><b>Proč je to důležité</b>{context}<small class="small" style="display:block;margin-top:6px">Tematický kontext</small></div><div class="source"><span>Výňatek z anotace · {source}</span><a href="{url}" target="_blank" rel="noopener noreferrer">Číst původní článek ↗</a></div></article>'

def publish(rows, now, unavailable, source_status=None):
    rows = [dict(row, importance=row.get("importance") or importance(row), importance_kind="topic_context") for row in rows]
    data = dict(updated_at=now.isoformat(), window_hours=24, articles=rows, unavailable_sources=unavailable, sources=source_status or [])
    page = (DEST/'index.html').read_text()
    catalog_payload = json.dumps(CATALOG, ensure_ascii=False).replace('<', '\\u003c')
    page = re.sub(r'(<script id="source-config" type="application/json">).*?(</script>)', lambda m:m[1]+catalog_payload+m[2], page, flags=re.S)
    page, count = re.subn(r'<!-- NEWS START -->.*?<!-- NEWS END -->', '<!-- NEWS START -->'+''.join(map(render_card, rows))+'<!-- NEWS END -->', page, flags=re.S)
    assert count == 1
    local = now.astimezone(ZoneInfo('Europe/Prague'))
    page = re.sub(r'(<strong id="editionDate">).*?(</strong>)', lambda m:m[1]+local.strftime('%d. %m. %Y')+m[2], page)
    page = re.sub(r'(<div id="editionTime">).*?(</div>)', lambda m:m[1]+local.strftime('%H:%M %Z')+m[2], page)
    page = re.sub(r'(<span id="count">).*?(</span>)', lambda m:m[1]+f'{len(rows)} zpráv'+m[2], page)
    payload = json.dumps(data, ensure_ascii=False).replace('<','\\u003c')
    page, count = re.subn(r'(<script id="initial-data" type="application/json">).*?(</script>)', lambda m:m[1]+payload+m[2], page, flags=re.S)
    assert count == 1
    previous = DEST / 'data.json'
    if previous.exists():
        archive_edition(DEST, json.loads(previous.read_text()))
    archive_edition(DEST, data)
    (DEST/'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    (DEST/'index.html').write_text(page)
    print(f'Published {len(rows)} articles; checked at {now.isoformat()}; unavailable feeds: {unavailable}')

def main():
    now = datetime.now(timezone.utc)
    def load_source(source):
        rows, successes = [], 0
        for url in source['feeds']:
            try:
                rows.extend(read_feed(fetch(url), source, now, url))
                successes += 1
            except Exception as exc:
                print(f"Feed unavailable: {source['name']} ({type(exc).__name__})", flush=True)
        status = dict(name=source['name'],site=source['site'],feeds_ok=successes,feeds_total=len(source['feeds']),
            status='ok' if successes==len(source['feeds']) else 'partial' if successes else 'unavailable',
            candidates=len(rows),selected=0)
        unique = {row['url']:row for row in rows}
        candidates = sorted(unique.values(),key=lambda r:datetime.fromisoformat(r['published_at']),reverse=True)[:8]
        return candidates, status
    with ThreadPoolExecutor(max_workers=6) as pool:
        loaded = list(pool.map(load_source, CATALOG))
    candidates = [row for rows, status in loaded for row in rows]
    statuses = [status for rows,status in loaded]
    unavailable = [s['name'] for s in statuses if s['status']!='ok']
    if all(s['status']=='unavailable' for s in statuses):
        raise RuntimeError('All feeds failed; keeping last successful edition and timestamp')
    with ThreadPoolExecutor(max_workers=8) as pool:
        checked = [row for row in pool.map(accessible, candidates) if row]
    if candidates and not checked:
        raise RuntimeError('All article checks failed; keeping last successful edition')
    selected = select(checked)
    for status in statuses:
        status['selected'] = sum(row['source']==status['name'] for row in selected)
        status['free_articles_checked'] = sum(row['source']==status['name'] for row in checked)
    publish(selected, now, unavailable, statuses)

if __name__ == '__main__':
    main()
