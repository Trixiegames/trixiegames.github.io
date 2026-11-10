import unittest
from datetime import datetime, timezone
from update_politics import parse_feed, select, render_card
from restore_context import importance

class UpdateTests(unittest.TestCase):
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
