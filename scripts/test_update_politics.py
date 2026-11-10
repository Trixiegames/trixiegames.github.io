import unittest
import json
import tempfile
from unittest.mock import patch
from source_reader import CATALOG, inspect_article, normalize_url, fetch, parse_feed as read_feed
from pathlib import Path
from edition_archive import archive_edition
from datetime import datetime, timezone
from update_politics import parse_feed, select, render_card
from restore_context import importance

class UpdateTests(unittest.TestCase):
    def test_mixed_source_requires_positive_free_access(self):
        row=dict(title='Vláda jedná',category='domaci',url='https://www.novinky.cz/clanek/domaci-a')
        source=next(s for s in CATALOG if s['name']=='Novinky.cz')
        text='<article><p>'+('Článek o jednání vlády. '*30)+'</p></article>'
        schema=lambda flag:'<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','isAccessibleForFree':flag})+'</script>'
        self.assertIsNone(inspect_article(row,text,source))
        self.assertIsNone(inspect_article(row,text+schema(False),source))
        self.assertIsNotNone(inspect_article(row,text+schema(True),source))

    def test_unapproved_domain_and_redirect_are_rejected(self):
        with self.assertRaises(ValueError):normalize_url('https://unapproved.invalid/news')
        response=b'HTTP/2 302\r\nlocation: https://unapproved.invalid/news\r\n\r\n'
        with patch('source_reader.subprocess.check_output',return_value=response) as request:
            with self.assertRaises(ValueError):fetch('https://ct24.ceskatelevize.cz/rss')
            self.assertEqual(request.call_count,1)

    def test_atom_and_all_rss_categories_are_supported(self):
        body='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Vláda projedná návrh</title><link href="https://tn.nova.cz/zpravodajstvi/clanek/test"/><published>2026-11-10T08:00:00Z</published><category term="Zprávy"/><category term="Domácí"/><summary>Jednání vlády.</summary></entry></feed>'''
        source=next(s for s in CATALOG if s['name']=='TN.cz')
        rows=read_feed(body,source,datetime(2026,11,10,9,tzinfo=timezone.utc))
        self.assertEqual(rows[0]['category'],'domaci')

    def test_archive_preserves_old_editions_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            first = dict(updated_at='2026-11-09T17:00:00+00:00', articles=[{'title':'Původní titulek'}])
            latest = dict(updated_at='2026-11-10T09:00:00+00:00', articles=[])
            path = archive_edition(folder, first)
            archive_edition(folder, latest)
            archive_edition(folder, dict(first, articles=[{'title':'Změněný titulek'}]))
            self.assertEqual(json.loads(path.read_text())['articles'][0]['title'], 'Původní titulek')
            index = json.loads((Path(folder)/'archive/index.json').read_text())
            self.assertEqual(len(index), 2)
            self.assertEqual(index[0]['updated_at'], latest['updated_at'])

    def test_only_recent_political_articles(self):
        body = '<rss><channel>' + ''.join(f'<item><title>{title}</title><link>https://ct24.ceskatelevize.cz/clanek/{section}/{i}</link><description>Krátká anotace článku.</description><pubDate>{date}</pubDate></item>' for i, (title, section, date) in enumerate([
            ('Vláda projedná návrh', 'domaci', 'Tue, 10 Nov 2026 08:00:00 GMT'),
            ('Prezident jedná', 'svet', 'Mon, 09 Nov 2026 07:00:00 GMT'),
            ('Premiér jedná', 'domaci', 'Wed, 11 Nov 2026 08:00:00 GMT'),
            ('Hokejové výsledky', 'sport', 'Tue, 10 Nov 2026 08:00:00 GMT'),
            ('Předpověď počasí', 'domaci', 'Tue, 10 Nov 2026 08:00:00 GMT')])) + '</channel></rss>'
        rows = parse_feed(body, 'ČT24', datetime(2026,11,10,9,tzinfo=timezone.utc))
        self.assertEqual([r['title'] for r in rows], ['Vláda projedná návrh'])

    def test_sort_respects_timezone_and_removes_duplicates(self):
        a = dict(title='Prezident oznámil návštěvu sousedního státu', category='domaci', url='https://a', published_at='2026-11-10T10:00:00+01:00')
        b = dict(title='Ministři projednají rozpočet', category='domaci', url='https://b', published_at='2026-11-10T09:30:00+00:00')
        self.assertEqual([r['url'] for r in select([a,b,a])], ['https://b','https://a'])

    def test_source_text_is_escaped(self):
        row = dict(title='<script>alert(1)</script>', summary='A & B', source='ČT24', category='domaci', published_at='2026-11-10T09:00:00+00:00', url='https://ct24.ceskatelevize.cz/clanek/a')
        html = render_card(row)
        self.assertNotIn('<script>', html)
        self.assertIn('A &amp; B', html)
        self.assertIn('Proč je to důležité', html)
        row['importance'] = '<img src=x onerror=alert(1)>'
        self.assertNotIn('<img', render_card(row))

    def test_context_distinguishes_proposal_from_effective_law(self):
        context = importance(dict(title='Vláda souhlasila s novelou zákona', category='domaci'))
        self.assertIn('návrh, schválení', context)

    def test_specific_context_precedes_generic_politics(self):
        context = importance(dict(title='Vláda zavede povinné e-žádanky', category='domaci'))
        self.assertIn('pacientů', context)
        self.assertIn('ještě nemusí znamenat', context)

    def test_allegation_is_not_presented_as_proven_guilt(self):
        context = importance(dict(title='FBI vyšetřuje podezření ze špionáže', category='svet'))
        self.assertIn('neprokazují vinu', context)

if __name__ == '__main__':
    unittest.main()
