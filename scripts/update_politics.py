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

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'politicky-prehled'
SOURCES = [('ČT24', 'https://ct24.ceskatelevize.cz/rss'),
           ('iROZHLAS', 'https://www.irozhlas.cz/rss/irozhlas')]
HOSTS = {'ct24.ceskatelevize.cz', 'www.irozhlas.cz'}
POLITICS = re.compile(r'vlád|premiér|prezident|ministr|sněmov|senát|poslanc|poslanec|volb|voleb|koalic|opozic|parlament|diplomac|sankc|nato|evropsk.{0,15}(uni|komis|rad)|trump|babiš|netanjahu|zelensk|putin|ukrajin|kreml|bíl.{0,4}d[oů]m|spd|demokrat|republikán|starost|zastupitel|válk|příměří|izrael|írán|gaza', re.I)

def clean(value):
    return ' '.join(unescape(re.sub('<[^>]*>', ' ', value or '')).split())

def fetch(url):
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in HOSTS:
        raise ValueError('Unapproved source URL')
    return subprocess.check_output(['curl', '--fail', '--silent', '--show-error',
        '--location', '--proto', '=https', '--proto-redir', '=https',
        '--max-time', '25', '--retry', '1', '--max-filesize', '5000000', url], timeout=55)

def parse_feed(body, source, now):
    rows = []
    for item in ET.fromstring(body).findall('.//item'):
        url = (item.findtext('link') or '').strip()
        path = urlparse(url).path
        if urlparse(url).hostname not in HOSTS:
            continue
        category = ('svet' if '/svet/' in path or '/zpravy-svet/' in path else
                    'domaci' if any(s in path for s in ['/domaci/', '/regiony/', '/zpravy-domov/']) else None)
        title, lead = clean(item.findtext('title')), clean(item.findtext('description'))
        try:
            published = parsedate_to_datetime(item.findtext('pubDate'))
            if published.tzinfo is None:
                continue
        except (TypeError, ValueError, IndexError):
            continue
        if not category or not now-timedelta(hours=24) <= published <= now:
            continue
        if not POLITICS.search(title + ' ' + lead) or not lead:
            continue
        # Short publisher excerpt, explicitly labelled in the UI.
        words = lead.split()
        excerpt = ' '.join(words[:25]) + ('…' if len(words) > 25 else '')
        rows.append(dict(title=title, summary=excerpt, source=source, category=category,
                         published_at=published.isoformat(), url=url))
    return rows

def accessible(row):
    try:
        body = fetch(row['url']).decode('utf-8', 'replace')
        if len(body) < 2000 or not re.search(r'<article\b|"@type"\s*:\s*"(?:NewsArticle|Article)"', body, re.I):
            return None
        if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', body, re.I):
            return None
        return row
    except Exception as exc:
        print(f"Article unavailable: {row['url']} ({type(exc).__name__})")
        return None

def select(rows):
    chosen, tokens = [], []
    for row in sorted(rows, key=lambda r:datetime.fromisoformat(r['published_at']), reverse=True):
        if sum(x['category'] == row['category'] for x in chosen) >= 10:
            continue
        terms = set(re.findall(r'\w{5,}', row['title'].lower()))
        if any(row['url'] == x['url'] for x in chosen):
            continue
        if terms and any(len(terms & other) / max(1, min(len(terms), len(other))) > .65 for other in tokens):
            continue
        chosen.append(row)
        tokens.append(terms)
    return chosen

def render_card(row):
    title, summary, source, category, published, url = (escape(row[k], quote=True) for k in ['title','summary','source','category','published_at','url'])
    label = 'Domácí politika' if category == 'domaci' else 'Zahraniční politika'
    date = datetime.fromisoformat(row['published_at']).astimezone(ZoneInfo('Europe/Prague')).strftime('%d. %m. %Y · %H:%M')
    return f'<article data-category="{category}" data-published="{published}"><div class="meta"><span class="category">{label}</span><time datetime="{published}">{date}</time></div><h2>{title}</h2><p>{summary}</p><div class="source"><span>Výňatek z anotace · {source}</span><a href="{url}" target="_blank" rel="noopener noreferrer">Číst původní článek ↗</a></div></article>'

def publish(rows, now, unavailable):
    data = dict(updated_at=now.isoformat(), window_hours=24, articles=rows, unavailable_sources=unavailable)
    page = (DEST/'index.html').read_text()
    page, count = re.subn(r'<!-- NEWS START -->.*?<!-- NEWS END -->', '<!-- NEWS START -->'+''.join(map(render_card, rows))+'<!-- NEWS END -->', page, flags=re.S)
    assert count == 1
    local = now.astimezone(ZoneInfo('Europe/Prague'))
    page = re.sub(r'(<strong id="editionDate">).*?(</strong>)', lambda m:m[1]+local.strftime('%d. %m. %Y')+m[2], page)
    page = re.sub(r'(<div id="editionTime">).*?(</div>)', lambda m:m[1]+local.strftime('%H:%M %Z')+m[2], page)
    page = re.sub(r'(<span id="count">).*?(</span>)', lambda m:m[1]+f'{len(rows)} zpráv'+m[2], page)
    payload = json.dumps(data, ensure_ascii=False).replace('<','\\u003c')
    page, count = re.subn(r'(<script id="initial-data" type="application/json">).*?(</script>)', lambda m:m[1]+payload+m[2], page, flags=re.S)
    assert count == 1
    (DEST/'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    (DEST/'index.html').write_text(page)
    print(f'Published {len(rows)} articles; checked at {now.isoformat()}; unavailable feeds: {unavailable}')

def main():
    now = datetime.now(timezone.utc)
    rows, unavailable = [], []
    for source, url in SOURCES:
        try:
            rows.extend(parse_feed(fetch(url), source, now))
        except Exception as exc:
            unavailable.append(source)
            print(f'Feed unavailable: {source} ({type(exc).__name__})')
    if len(unavailable) == len(SOURCES):
        raise RuntimeError('All feeds failed; keeping last successful edition and timestamp')
    candidates = select(rows)
    with ThreadPoolExecutor(max_workers=6) as pool:
        checked = [row for row in pool.map(accessible, candidates) if row]
    if candidates and not checked:
        raise RuntimeError('All article checks failed; keeping last successful edition')
    publish(checked, now, unavailable)

if __name__ == '__main__':
    main()
