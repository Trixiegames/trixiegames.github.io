"""Topic context for the automated digest; never a second source or prediction."""
import re

RULES = [
    (r'oslav.*izrael|listopad.*izrael', 'Termín zahraniční návštěvy ukazuje, jak premiér rozděluje pozornost mezi mezinárodní jednání a připomínku demokratických změn v Česku.'),
    (r'špion', 'Případ propojuje národní bezpečnost s mezinárodními vztahy. Podezření ani zahájené vyšetřování samy o sobě neprokazují vinu.'),
    (r'plakát|kauz.*spd|spd.*soud', 'Jde o hranice politické kampaně a svobody projevu. Pro právní výsledek je podstatné rozhodnutí soudu, nikoli názory komentátorů.'),
    (r'letoun|leteck.*základ|bombard', 'Rozmístění vojenských letadel souvisí s bezpečností základen, ochranou spojenců a možnostmi dalšího vojenského působení.'),
    (r'volb.*neplatn|hlasování.*neplatn|volit znovu', 'Soudní přezkum chrání důvěryhodnost voleb. Neplatné hlasování může změnit, kdy a jak obec získá řádně zvolené vedení.'),
    (r'uměl.*inteligenc|\bai\b|openai', 'Dohled nad umělou inteligencí řeší odpovědnost technologických firem a ochranu veřejnosti. Rozhodující bude konkrétní podoba a účinnost pravidel.'),
    (r'manžel.*okupac|okupac.*rodin', 'Příběh ukazuje dlouhodobé dopady okupace na civilisty a rozdělené rodiny, které se v souhrnných údajích o válce snadno ztrácejí.'),
    (r'hraniční.*zdi|hranic.*mexik|zdi.*park', 'Spor propojuje migrační politiku s ochranou území a pravomocemi vlády. Soudní rozhodnutí určuje, jaké kroky smí administrativa podniknout.'),
    (r'průzkum', 'Přesnost průzkumů ovlivňuje očekávání veřejnosti i strategii stran. Průzkum je odhad zatížený nejistotou, nikoli náhrada skutečného volebního výsledku.'),
    (r'unijní rozpočet|rozpočet.*ukrajin', 'Jednání propojuje financování Evropské unie s podporou Ukrajiny. Požadavek jedné vlády ještě neznamená dohodu všech členských států.'),
    (r'ocenil zachránce|záchranářsk', 'Ocenění upozorňuje na práci záchranářů a občanskou pomoc. Jde především o společenskou a symbolickou roli prezidenta.'),
    (r'ostřelov|kyjevsk.*čtvrť', 'Reportáž přibližuje dopady války na každodenní život civilistů a fungování měst. Doplňuje vojenské zprávy o pohled místních obyvatel.'),
    (r'pomoc.*izrael|izrael.*pomoc', 'Složení amerického Kongresu může ovlivnit podobu podpory Izraele i dohled nad zahraniční politikou. Možná změna však ještě není přijatým rozhodnutím.'),
    (r'kybernet', 'Vedení kybernetických a informačních sil souvisí s obranou státu proti digitálním hrozbám. Personální změna sama o sobě neprokazuje změnu obranné strategie.'),
    (r'macinka.*hokej|hokej.*macinka', 'Výroky ministra zahraničí mají vedle domácí debaty i diplomatický rozměr. Je důležité rozlišovat jeho vyjádření od formálních kroků státu.'),
    (r'e-žádank|elektronick.*žádank', 'Digitalizace žádanek se týká práce lékařů i přístupu pacientů k vyšetření. Souhlas vlády s návrhem ještě nemusí znamenat, že povinnost již platí.'),
    (r'zákon|novel|legislativ', 'Legislativní změna může ovlivnit práva a povinnosti lidí nebo institucí. Je nutné rozlišovat návrh, schválení a datum, kdy pravidla skutečně začnou platit.'),
    (r'volb|voleb|mandát|koalic|starost|zastupitel', 'Výsledek voleb a navazující jednání určují, kdo bude rozhodovat o veřejných penězích a prioritách. Samotný volební zisk ještě nezaručuje účast na vedení.'),
    (r'rozpoč|daně|důchod|dávk', 'Rozhodování o veřejných financích se promítá do dostupnosti služeb i peněz domácností. Konkrétní dopad závisí na schválené podobě opatření.'),
    (r'příměří|mírov|válk|ukrajin|gaza|írán', 'Vývoj souvisí s bezpečností obyvatel a možnostmi diplomatického řešení. Oznámení nebo návrh je třeba odlišovat od dohody, která se skutečně dodržuje.'),
    (r'prezident|premiér|ministr|vlád|diplomat', 'Zpráva pomáhá sledovat priority a odpovědnost představitelů státu. Pro praktický dopad je důležité, které výroky se promění v konkrétní rozhodnutí.'),
]

def importance(row):
    for pattern, context in RULES:
        if re.search(pattern, row['title'], re.I):
            return context
    return ('Téma je součástí domácí politické debaty; pro veřejnost je podstatné, koho se týká a jaké konkrétní kroky příslušné instituce podniknou.'
            if row['category'] == 'domaci' else
            'Zpráva doplňuje obraz mezinárodního dění. Její širší význam závisí na dalších krocích zúčastněných států a institucí.')
