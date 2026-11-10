# Politický přehled

Veřejná stránka: https://davhab.com/politicky-prehled/

Workflow `.github/workflows/politicky-prehled.yml` běží nepřetržitě každou hodinu (17. minuta UTC), případně ručně přes Actions. GitHub může plánované spuštění zpozdit. Nejde o úlohu v chatu a neposílá chatové zprávy.

`scripts/update_politics.py` načte veřejné RSS/Atom ze seznamu `politicky-prehled/sources.json` (16 českých redakcí), ponechá jen články vydané za posledních 24 hodin, vybere domácí a zahraniční politiku podle rubriky a výrazů, odstraní stejné URL a podobné titulky a ověří dostupnost odkazů. Nejvýše 20 článků na rubriku a čtyři články jedné redakce v rubrice; počet se nedoplňuje starými zprávami. Anotace jsou označené krátké výňatky (nejvýše 25 slov), nikoli nově vytvořené AI analýzy či nezávislé ověření tvrzení. Výběr podle výrazů může některá témata vynechat či zahrnout nepřesně. Datum vydání článku není automaticky datem popisované události.

Výchozí je aktuální vydání. Archiv obsahuje samostatné neměnné JSON snímky každé úspěšné aktualizace a seznam v `archive/index.json`. Výběr data a času načte tehdejší obsah, který se při dalších aktualizacích nepřepisuje. V archivu se starší články neskrývají podle dnešního data. Časy jsou uvedeny v Praze; archiv obsahuje pouze skutečně uložená vydání. Otevřená stránka kontroluje nové vydání každých 5 minut a průběžně skrývá články starší než 24 hodin. Časy jsou v Europe/Prague. Po více než dvou hodinách bez úspěšné aktualizace zobrazí upozornění. Při výpadku všech zdrojů nebo kontrol článků se poslední vydání ani čas úspěšné aktualizace nepřepisují; částečný výpadek zdrojů je uveden na stránce.

Workflow uloží nové HTML a JSON a výslovně požádá o sestavení branch-based GitHub Pages (commit s GITHUB_TOKEN sám sestavení nespouští). Používá pouze oprávnění contents:write a pages:write, bez dalších API klíčů. Nezasahuje do ostatních projektů.

Ověření: `python -m unittest discover -s scripts -p 'test_update_politics.py'`. Ruční obnova: `python scripts/update_politics.py` (Python 3.12+, curl).

Rámeček „Proč je to důležité“ obsahuje automatický tematický kontext podle titulku článku (pravidla v `scripts/restore_context.py`). V JSON je uložen v poli `importance`, s typem `topic_context`. Nejde o nezávislé ověření, citaci zdroje ani nově vytvořenou AI analýzu. Konkrétní pravidla mají přednost před obecnými a rozlišují návrhy, rozhodnutí a podezření. Kontext se generuje při každé aktualizaci a vykresluje shodně v HTML i JavaScriptu.

Rozbalovací Seznam zdrojů používá stejný schválený katalog jako aktualizační skript. Výběr vychází z dohledatelné redakce, redakčních standardů a veřejných podkladů NFNZ (https://www.nfnz.cz/rating-medii/, https://www.nfnz.cz/dezinformacni-a-konspiracni-media/), ověřeno 10. 11. 2026. Nejde o automatický slib pokrytí každého českého webu ani o záruku správnosti všech tvrzení. Nové domény vyžadují výslovné zařazení; přesměrování mimo schválené domény se odmítá.

U smíšených placených/volných webů se vyžaduje pozitivní `isAccessibleForFree` nebo ověřený příznak volného článku konkrétního vydavatele (`locked:false`, `content=free` a `premium=false`); záporný příznak či zjištěná výzva k odemčení vede k vyřazení. Zároveň je vyžadován dostupný text článku. Konzervativní kontrola může vynechat i volný článek bez potřebných metadat. U veřejných zdrojů se vyžaduje dostupný text a nepřítomnost zjištěného uzamčení. Kontrola nenahrazuje ruční čtení či ověření tvrzení.

Z každé redakce se kontroluje nejvýše osm aktuálních politických kandidátů při jednom běhu, poté se odstraňují podobné titulky a uplatňuje pestrost redakcí. Výpadky a počty vybraných článků jsou uloženy v datech vydání a uvedeny v Seznamu zdrojů. České noviny slouží pro titulky a odkazy; jejich anotace se nepřebírají. Běžný informační pruh je odstraněn; případné upozornění na zpoždění nebo výpadek se zobrazí pouze při problému.
