"""Approved Czech newsroom feeds and conservative article accessibility checks."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin
import json
import re
import subprocess
import xml.etree.ElementTree as ET

CATALOG = json.loads((Path(__file__).resolve().parents[1]/'politicky-prehled/sources.json').read_text())
HOSTS = {h for source in CATALOG for h in source['hosts']}
POLITICS = re.compile(r'vlád|premiér|prezident|ministr|sněmov|senát|poslanc|poslanec|volb|voleb|koalic|opozic|parlament|diplomac|sankc|\bnato\b|evropsk.{0,15}(uni|komis|rad)|trump|babiš|netanjahu|zelensk|putin|ukrajin|kreml|spd|demokrat|republikán|starost|zastupitel|válk|příměří|izrael|írán|gaza|kybernet', re.I)

def clean(value):
    return ' '.join(unescape(re.sub('<[^>]*>', ' ', value or '')).split())

def normalize_url(url):
    p = urlparse(url)
    if p.hostname not in HOSTS or p.scheme not in {'http','https'}:
        raise ValueError('Unapproved source URL')
    query = urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_')])
    return urlunparse(('https', p.netloc, p.path, p.params, query, ''))

def fetch(url):
    url = normalize_url(url)
    # Inspect each redirect before following it; never fetch an unapproved host.
    for _ in range(5):
        result = subprocess.check_output(['curl','--silent','--show-error','--fail','--compressed',
            '--proto','=https','--max-time','18','--max-filesize','5000000','--include',url], timeout=22)
        # curl through a proxy can prepend a CONNECT response.
        while result.startswith(b'HTTP/'):
            head, sep, body = result.partition(b'\r\n\r\n')
            if not sep:
                head, sep, body = result.partition(b'\n\n')
            status = int(head.splitlines()[0].split()[1])
            if status == 200 and body.startswith(b'HTTP/'):
                result = body
                continue
            if 300 <= status < 400:
                location = re.search(rb'(?im)^location:\s*(.+?)\r?$', head)
                if not location: raise ValueError('Redirect without location')
                url = normalize_url(urljoin(url, location[1].decode().strip()))
                break
            if status != 200: raise ValueError('Source HTTP error')
            return body
        else:
            raise ValueError('Missing HTTP response')
    raise ValueError('Too many redirects')

def classify(url, categories):
    path = urlparse(url).path.lower()
    labels = ' '.join(categories).lower()
    if re.search(r'dom[aá]c[ií]|zpravy-domov|z_domova|česko|čr', path+' '+labels): return 'domaci'
    if re.search(r'zahrani|zpravy-svet|ze_sveta|/svet|svět|evropa|amerika|asij|asii',path+' '+labels): return 'svet'
    return None

def parse_feed(body, source, now, feed_url=''):
    root = ET.fromstring(body)
    if root.tag not in {'rss','{http://www.w3.org/2005/Atom}feed','{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'}:
        raise ValueError('Not a news feed')
    rows = []
    atom = '{http://www.w3.org/2005/Atom}'
    items = root.findall('.//item') or root.findall(atom+'entry')
    for item in items:
        is_atom = item.tag == atom+'entry'
        def val(key): return item.findtext((atom if is_atom else '')+key)
        links = item.findall(atom+'link') if is_atom else []
        raw_url = next((x.get('href') for x in links if x.get('rel','alternate')=='alternate'), '') if is_atom else val('link')
        try: url = normalize_url(raw_url or '')
        except ValueError: continue
        if urlparse(url).hostname not in source['hosts']: continue
        title, lead = clean(val('title')), clean(val('summary') or val('content') if is_atom else val('description'))
        categories = [clean(x.get('term','') if is_atom else x.text) for x in item.findall((atom if is_atom else '')+'category')]
        if re.search(r'koment[aá]ř|názor|glos|podcast|rozhovor|analýz', ' '.join(categories)+' '+url, re.I): continue
        try:
            raw_date = (val('published') or val('updated')) if is_atom else val('pubDate')
            published = datetime.fromisoformat(raw_date.replace('Z','+00:00')) if is_atom else parsedate_to_datetime(raw_date)
            if published.tzinfo is None: continue
        except (TypeError,ValueError,IndexError,AttributeError): continue
        if not now-timedelta(hours=24) <= published <= now: continue
        if not title or not POLITICS.search(title+' '+lead): continue
        category = classify(url, categories)
        if source['name']=='ČTK / České noviny': category = 'domaci' if '/cr.php' in feed_url else 'svet'
        words = lead.split()
        excerpt = ' '.join(words[:25]) + ('…' if len(words)>25 else '')
        if source['access']=='links_only': excerpt = 'Zpráva ČTK. Celý článek si přečtěte na webu České noviny.'
        rows.append(dict(title=title,summary=excerpt,source=source['name'],category=category,
            published_at=published.isoformat(),url=url))
    return rows

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.script=False; self.script_text=[]; self.jsonld=[]
        self.article_depth=0; self.p=False; self.paragraphs=[]; self.paragraph=[]; self.sections=[]; self.skip=0; self.stack=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        container = tag=='article' or a.get('itemprop')=='articleBody' or a.get('id') in {'articlebody','art-text'} or 'article-body' in a.get('class','').split()
        if tag not in {'meta','link','img','br','hr','input','source','wbr','area','base','embed','param','track'}:
            self.stack.append((tag,container))
            self.article_depth += int(container)
        if tag=='script':
            self.script=a.get('type')=='application/ld+json';self.script_text=[]
        if tag in {'script','style','noscript','template'}: self.skip+=1
        if tag=='meta' and (a.get('property')=='article:section' or a.get('name')=='section'): self.sections.append(a.get('content',''))
        if tag=='p' and self.article_depth and not self.skip: self.p=True;self.paragraph=[]
    def handle_endtag(self,tag):
        if tag=='script' and self.script:
            try:self.jsonld.append(json.loads(''.join(self.script_text)))
            except ValueError:pass
            self.script=False
        if tag=='p' and self.p:
            self.paragraphs.append(clean(' '.join(self.paragraph)));self.p=False
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                self.article_depth=max(0,self.article_depth-sum(int(flag) for _,flag in self.stack[i:]))
                del self.stack[i:]
                break
        if tag in {'script','style','noscript','template'}:self.skip=max(0,self.skip-1)
    def handle_data(self,text):
        if self.script:self.script_text.append(text)
        if self.p and not self.skip:self.paragraph.append(text)

def article_nodes(value):
    if isinstance(value,list):
        for x in value:yield from article_nodes(x)
    if isinstance(value,dict):
        types=value.get('@type',[]);types=[types] if isinstance(types,str) else types
        if any(t in {'NewsArticle','Article','ReportageNewsArticle','BlogPosting','InfoArticle'} for t in types):yield value
        if '@graph' in value:yield from article_nodes(value['@graph'])

def inspect_article(row, body, source):
    parser=ArticleParser();parser.feed(body)
    nodes=list(article_nodes(parser.jsonld))
    access=[n.get('isAccessibleForFree') for n in nodes if 'isAccessibleForFree' in n]
    if any(x is False or str(x).lower()=='false' for x in access):return None
    decoded=unescape(body)
    explicit_free=any(x is True or str(x).lower()=='true' for x in access)
    # Publisher-specific flags confirmed in publicly delivered article pages.
    patterns={
        'Aktuálně.cz':r'"locked"\s*:\s*false',
        'Deník':r'\blocked\s*:\s*"false"',
        'iDNES.cz':r'content=free[^\n]{0,100}premium=false',
    }
    if source['name'] in patterns:
        explicit_free=explicit_free or bool(re.search(patterns[source['name']],decoded,re.I))
    if source['access']=='mixed' and not explicit_free:return None
    text=' '.join(parser.paragraphs)
    if len(text)<400:return None
    if re.search(r'článek (?:je dostupný|si mohou přečíst|je určen) (?:pouze|jen)|odemknout (?:celý )?článek|pro pokračování.{0,50}(předplaťte|přihlaste)',text,re.I):return None
    sections=parser.sections+[str(n.get('articleSection','')) for n in nodes]
    category=row['category'] or classify(row['url'],sections)
    if not category:return None
    return dict(row,category=category)
