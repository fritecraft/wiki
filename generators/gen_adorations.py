#!/usr/bin/env python3
"""Génère la section « Adorations » du wiki : une page par divinité avec les actions qui rapportent de l'XP d'adoration.

Usage :  python3 generators/gen_adorations.py [chemin/vers/adorations.yml]

Source : code/adorations/adorations.yml (source unique des adorations, voir code/adorations/README.md). Les valeurs d'XP publiées
sont celles du fichier (« experience » de chaque action), sans multiplicateur de niveau de métier.
Les noms français viennent du fichier de langue du jeu 26.3 (téléchargé une fois dans generators/.cache, non commité) : objets, blocs,
mobs, enchantements et disques de musique (titre du morceau).
Les pages générées sont commitées ; ne PAS les éditer à la main.
"""
import json, re, shutil, sys, urllib.request
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'code/adorations/adorations.yml'
OUT = ROOT / 'src/content/docs/adorations'
CACHE = ROOT / 'generators/.cache/fr_fr_26.3.json'
VERSION = '26.3'

DIVINITES = [  # identifiant Jobs -> (nom, thème en une phrase)
    ('Frite', 'Fritegirl', "Or, butins de monstres, exploration, épées."),
    ('Burger', 'Hamburgirl', "Armures, viandes, briques, terrain."),
    ('Nuggets', 'Nuggetsgirl', "Cultures, animaux de ferme, laine, cuir."),
    ('Soupe', 'Soupegirl', "Nether, lave, quartz, netherite."),
    ('Soda', 'Sodagirl', "Océan, pêche, coraux."),
    ('Candy', 'Candygirl', "Sucre, miel, gâteaux, baies, abeilles."),
    ('Flurry', 'Flurrygirl', "Glace, neige, cavernes, minerais."),
    ('Choco', 'Chocogirl', "Cacao, bois, arcs, montures."),
    ('Faim', 'Fringirl', "La faim, la nourriture avariée."),
]

# section Jobs -> (titre de la rubrique, phrase d'introduction, genre de cible)
SECTIONS = [
    ('Break', "Casser des blocs", "Casser ces blocs.", 'bloc'),
    ('TNTBreak', "Casser avec de la TNT", "Faire sauter ces blocs avec de la TNT.", 'bloc'),
    ('Place', "Poser des blocs", "Poser ces blocs.", 'bloc'),
    ('Collect', "Récolter dans les blocs", "Récolter dans ces blocs (baies, miel, compost…).", 'bloc'),
    ('Brush', "Brosser", "Brosser ces blocs avec un pinceau.", 'bloc'),
    ('Fish', "Pêcher", "Pêcher ces objets.", 'objet'),
    ('Kill', "Tuer des mobs", "Tuer ces créatures.", 'mob'),
    ('Breed', "Faire se reproduire des animaux", "Faire se reproduire ces animaux.", 'mob'),
    ('Tame', "Apprivoiser des animaux", "Apprivoiser ces animaux.", 'mob'),
    ('Milk', "Traire", "Traire ces animaux.", 'mob'),
    ('Shear', "Tondre des moutons", "Tondre des moutons de ces couleurs.", 'couleur'),
    ('Eat', "Manger", "Manger ces aliments.", 'objet'),
    ('Bake', "Cuire (four, fumoir…)", "Faire cuire ces aliments.", 'objet'),
    ('Smelt', "Fondre ou cuire (fourneau)", "Obtenir ces objets au fourneau.", 'objet'),
    ('Craft', "Fabriquer", "Fabriquer ces objets.", 'objet'),
    ('Brew', "Préparer des potions", "Préparer des potions avec ces ingrédients.", 'objet'),
    ('Repair', "Réparer", "Réparer ces objets.", 'objet'),
    ('Enchant', "Enchanter", "Enchanter ces objets, ou obtenir ces enchantements.", 'enchant'),
]
COULEURS = {'light_gray': 'light_gray', 'light_blue': 'light_blue'}


def lang():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        def g(u):
            req = urllib.request.Request(u, headers={'User-Agent': 'fritecraft-wiki'})
            with urllib.request.urlopen(req, timeout=60) as r: return r.read()
        m = json.loads(g("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
        e = next(v for v in m['versions'] if v['id'] == VERSION)
        idx = json.loads(g(json.loads(g(e['url']))['assetIndex']['url']))
        h = idx['objects']['minecraft/lang/fr_fr.json']['hash']
        CACHE.write_bytes(g(f"https://resources.download.minecraft.net/{h[:2]}/{h}"))
    return json.loads(CACHE.read_text(encoding='utf-8'))


def roman(L, n):
    return L.get(f'enchantment.level.{n}', str(n))


manquants = set()


def nom_objet(L, ident):
    k = ident.lower()
    if k.startswith('music_disc_') and f'item.minecraft.{k}.desc' in L:
        return 'Disque : ' + L[f'item.minecraft.{k}.desc']
    for p in ('item', 'block', 'entity'):
        if f'{p}.minecraft.{k}' in L: return L[f'{p}.minecraft.{k}']
    manquants.add(ident)
    return ident


def nom(L, genre, cle, section):
    base = cle
    m = re.match(r'^(.*?)-(\d+)$', cle)
    suffixe = ''
    if m:
        base, n = m.group(1), int(m.group(2))
        if genre == 'enchant':
            k = base.lower()
            nm = L.get(f'enchantment.minecraft.{k}')
            if nm is None:
                manquants.add(cle); nm = base
            return nm + ' ' + roman(L, n), 'enchantement'
        # ex. WHEAT-7, COCOA-4 : stade de croissance ; BEEHIVE-5 : niveau de miel
        suffixe = ' (pleine de miel)' if base.lower() in ('beehive', 'bee_nest') else ' (à maturité)'
    k = base.lower()
    if genre == 'mob':
        return L.get(f'entity.minecraft.{k}', nom_objet(L, base)), 'x'
    if genre == 'couleur':
        return L.get(f'color.minecraft.{k}', base), 'x'
    if genre == 'enchant':
        return nom_objet(L, base), 'objet'
    return nom_objet(L, base) + suffixe, 'x'


def fmt(x):
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def tri_cle(s):
    import unicodedata
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()


def tableau(lignes):
    out = ['| Cible | XP |', '| --- | ---: |']
    for n, xp in lignes:
        out.append(f'| {n} | {fmt(xp)} |')
    return '\n'.join(out)


def main():
    doc = yaml.safe_load(SRC.read_text(encoding='utf-8'))
    L = lang()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    index = []
    for ordre, (jid, nomdiv, theme) in enumerate(DIVINITES, start=1):
        actions = doc['divinities'][jid].get('actions') or {}
        corps, total = [], 0
        sommaire = []
        for sec, titre, intro, genre in SECTIONS:
            entrees = actions.get(sec) or {}
            if not entrees: continue
            lignes, ench = [], []
            for cle, val in entrees.items():
                xp = (val or {}).get('experience')
                if xp is None: continue
                n, type_ = nom(L, genre, str(cle), sec)
                (ench if type_ == 'enchantement' else lignes).append((n, xp))
                total += 1
            lignes.sort(key=lambda t: tri_cle(t[0])); ench.sort(key=lambda t: tri_cle(t[0]))
            corps.append(f'## {titre}\n')
            if genre == 'enchant':
                if lignes:
                    corps.append("Enchanter ces objets :\n")
                    corps.append(tableau(lignes) + '\n')
                if ench:
                    corps.append("Obtenir ces enchantements :\n")
                    corps.append(tableau(ench) + '\n')
            else:
                corps.append(intro + '\n')
                corps.append(tableau(lignes) + '\n')
            sommaire.append((titre, len(lignes) + len(ench)))
        entete = (f'---\ntitle: "Adorations de {nomdiv}"\n'
                  f'description: "Les actions qui rapportent de l\'XP d\'adoration à {nomdiv}."\n'
                  f'sidebar:\n  label: "{nomdiv}"\n  order: {ordre}\n---\n\n'
                  '<!-- Page générée par generators/gen_adorations.py depuis adorations.yml : ne pas modifier à la main. -->\n\n')
        intro = (f"{theme} Retrouvez la déesse dans la page [Divinités](/lore/divinites/) et le fonctionnement des niveaux dans la page "
                 f"[Adorations](/fritecraft/adorations/).\n\n"
                 f"Chaque action ci-dessous fait gagner de l'XP d'adoration à **{nomdiv}**. **{total} actions** au total.\n\n")
        (OUT / f'{nomdiv.lower()}.md').write_text(entete + intro + '\n'.join(corps), encoding='utf-8')
        index.append((nomdiv, theme, total, ordre))
    idx = ['---', 'title: "Actions des adorations"',
           'description: "Toutes les actions qui font gagner de l\'XP d\'adoration, par divinité."',
           'sidebar:\n  label: "Présentation"\n  order: 0', '---', '',
           '<!-- Page générée par generators/gen_adorations.py depuis adorations.yml : ne pas modifier à la main. -->', '',
           "Chaque divinité récompense des actions précises : casser un bloc, tuer un mob, fabriquer, enchanter, pêcher… "
           "Une page par divinité liste ces actions avec l'XP d'adoration qu'elles rapportent. "
           "Le principe des adorations, les niveaux et leurs bonus sont expliqués dans la page [Adorations](/fritecraft/adorations/).", '',
           '| Divinité | Thème | Actions |', '| --- | --- | ---: |']
    for nomdiv, theme, total, _ in index:
        idx.append(f'| [{nomdiv}](/adorations/{nomdiv.lower()}/) | {theme} | {total} |')
    (OUT / 'index.md').write_text('\n'.join(idx) + '\n', encoding='utf-8')
    if manquants:
        print('Noms français manquants (affichés tels quels) :', ', '.join(sorted(manquants)))
    print('Pages écrites :', len(index) + 1, '| actions :', sum(t for _, _, t, _ in index))


if __name__ == '__main__':
    main()
