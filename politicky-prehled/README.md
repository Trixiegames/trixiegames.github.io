# Politický přehled

Veřejná stránka: https://davhab.com/politicky-prehled/

Workflow `.github/workflows/politicky-prehled.yml` běží nepřetržitě každou hodinu (17. minuta UTC), případně ručně přes Actions. GitHub může plánované spuštění zpozdit. Nejde o úlohu v chatu a neposílá chatové zprávy.

`scripts/update_politics.py` načte veřejné RSS ČT24 a iROZHLASu, ponechá jen články vydané za posledních 24 hodin, vybere domácí a zahraniční politiku podle rubriky a výrazů, odstraní stejné URL a podobné titulky a ověří dostupnost odkazů. Nejvýše 10 článků na rubriku; počet se nedoplňuje starými zprávami. Anotace jsou označené krátké výňatky (nejvýše 25 slov), nikoli nově vytvořené AI analýzy či nezávislé ověření tvrzení. Výběr podle výrazů může některá témata vynechat či zahrnout nepřesně. Datum vydání článku není automaticky datem popisované události.

Na webu je vždy jen poslední vydání. Starší data se nepřipojují; vývojová historie repozitáře zůstává zachovaná. Otevřená stránka kontroluje nové vydání každých 5 minut a průběžně skrývá články starší než 24 hodin. Časy jsou v Europe/Prague. Po více než dvou hodinách bez úspěšné aktualizace zobrazí upozornění. Při výpadku všech zdrojů nebo kontrol článků se poslední vydání ani čas úspěšné aktualizace nepřepisují; částečný výpadek zdrojů je uveden na stránce.

Workflow uloží nové HTML a JSON a výslovně požádá o sestavení branch-based GitHub Pages (commit s GITHUB_TOKEN sám sestavení nespouští). Používá pouze oprávnění contents:write a pages:write, bez dalších API klíčů. Nezasahuje do ostatních projektů.

Ověření: `python -m unittest discover -s scripts -p 'test_update_politics.py'`. Ruční obnova: `python scripts/update_politics.py` (Python 3.12+, curl).

Rámeček „Proč je to důležité“ obsahuje automatický tematický kontext podle titulku článku (pravidla v `scripts/restore_context.py`). V JSON je uložen v poli `importance`, s typem `topic_context`. Nejde o nezávislé ověření, citaci zdroje ani nově vytvořenou AI analýzu. Konkrétní pravidla mají přednost před obecnými a rozlišují návrhy, rozhodnutí a podezření. Kontext se generuje při každé aktualizaci a vykresluje shodně v HTML i JavaScriptu.
