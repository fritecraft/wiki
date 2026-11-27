#!/usr/bin/env python3
"""Génère la section « Adorations » du wiki : une page par divinité avec les actions qui rapportent de l'XP d'adoration.

Usage :  python3 generators/gen_adorations.py [chemin/vers/adorations.yml]

Source : code/adorations/adorations.yml (source unique des adorations, voir code/adorations/README.md). Les valeurs d'XP publiées
sont celles du fichier (« experience » de chaque action), sans multiplicateur de niveau de métier.
Les noms français viennent du fichier de langue du jeu 26.3 (téléchargé une fois dans generators/.cache, non commité) : objets, blocs,
mobs, enchantements et disques de musique (titre du morceau).
Icônes : rendus d'inventaire de mc.nerothe.com (comme les boutiques), sinon dessinées depuis les textures du client 26.3
(objets plats agrandis, blocs pleins en cube isométrique). Les icônes sont téléchargées une fois dans public/boutiques/icones/.
Les pages générées sont commitées ; ne PAS les éditer à la main.
"""
import io, json, re, shutil, sys, urllib.error, urllib.request, zipfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'code/adorations/adorations.yml'
OUT = ROOT / 'src/content/docs/adorations'
CACHE = ROOT / 'generators/.cache/fr_fr_26.3.json'
VERSION = '26.3'
ICONES = ROOT / 'public/boutiques/icones'      # dossier partagé avec la section Boutiques
ICON_URL = 'https://mc.nerothe.com/img/{v}/minecraft_{i}.png'
ICON_VERSIONS = ('1.21.4', '1.21.8', '1.21.11')  # rendus d'inventaire disponibles (26.x absent)
JAR = ROOT / 'generators/.cache/client-26.3.jar'
# identifiant d'action -> identifiant de l'objet dont on affiche l'icône (blocs sans objet, anciens noms)
ICON_ALIAS = {'beetroots': 'beetroot', 'carrots': 'carrot', 'potatoes': 'potato', 'cocoa': 'cocoa_beans',
              'sweet_berry_bush': 'sweet_berries', 'end_crystal_spawn_egg': 'end_crystal'}
CUBES = {'potent_sulfur'}   # blocs pleins à dessiner en cube isométrique quand il n'existe pas de rendu

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


_zip = None


def jar():
    global _zip
    if _zip is None:
        if not JAR.exists():
            def g(u):
                req = urllib.request.Request(u, headers={'User-Agent': 'fritecraft-wiki'})
                with urllib.request.urlopen(req, timeout=120) as r: return r.read()
            m = json.loads(g("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
            e = next(v for v in m['versions'] if v['id'] == VERSION)
            JAR.write_bytes(g(json.loads(g(e['url']))['downloads']['client']['url']))
        _zip = zipfile.ZipFile(JAR)
    return _zip


def texture(i):
    from PIL import Image
    z = jar()
    for d in ('item', 'block'):
        n = f'assets/minecraft/textures/{d}/{i}.png'
        if n in z.namelist():
            im = Image.open(io.BytesIO(z.read(n))).convert('RGBA')
            return im.crop((0, 0, im.width, im.width)) if im.height > im.width else im, d
    return None, None


def cube(im):
    """Cube isométrique 64x64 : dessus clair, face gauche sombre, face droite moyenne (même texture sur les trois faces)."""
    from PIL import Image
    t = im.resize((16, 16), Image.NEAREST)
    out = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    faces = [  # origine, axe u, axe v, luminosité
        ((32, 6), (28, 14), (-28, 14), 1.15),    # dessus
        ((4, 20), (28, 14), (0, 28), 0.7),       # gauche
        ((32, 34), (28, -14), (0, 28), 0.85),    # droite
    ]
    n = 160
    for o, au, av, k in faces:
        for i in range(n):
            for j in range(n):
                u, v = (i + 0.5) / n, (j + 0.5) / n
                x, y = int(o[0] + au[0] * u + av[0] * v), int(o[1] + au[1] * u + av[1] * v)
                c = t.getpixel((int(u * 16), int(v * 16)))
                if c[3] and 0 <= x < 64 and 0 <= y < 64:
                    out.putpixel((x, y), (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)), 255))
    return out


def icone(ident):
    """Chemin web de l'icône de l'objet (téléchargée ou dessinée une fois), ou None."""
    i = ICON_ALIAS.get(ident, ident)
    f = ICONES / f'{i}.png'
    if not f.exists():
        ICONES.mkdir(parents=True, exist_ok=True)
        for v in ICON_VERSIONS:
            try:
                req = urllib.request.Request(ICON_URL.format(v=v, i=i), headers={'User-Agent': 'wiki-icons'})
                with urllib.request.urlopen(req, timeout=60) as r: f.write_bytes(r.read())
                break
            except urllib.error.HTTPError:
                continue
        if not f.exists():
            im, kind = texture(i)
            if im is None:
                manquants_icones.add(ident); return None
            from PIL import Image
            (cube(im) if i in CUBES else im.resize((64, 64), Image.NEAREST)).save(f)
    return f'/boutiques/icones/{f.name}'


def roman(L, n):
    return L.get(f'enchantment.level.{n}', str(n))


manquants = set()
manquants_icones = set()


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


def icone_ident(genre, cle, type_):
    base = re.sub(r'-\d+$', '', cle).lower().replace(' ', '_')
    if type_ == 'enchantement': return 'enchanted_book'
    if genre == 'mob': return base + '_spawn_egg'
    if genre == 'couleur': return base + '_wool'
    return base


def tableau(lignes):
    out = ['| Cible | XP |', '| --- | ---: |']
    for n, xp, ic in lignes:
        img = f'<img class="shop-ico" src="{ic}" alt="" width="32" height="32" loading="lazy"> ' if ic else ''
        out.append(f'| {img}{n} | {fmt(xp)} |')
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
                ic = icone(icone_ident(genre, str(cle), type_))
                (ench if type_ == 'enchantement' else lignes).append((n, xp, ic))
                total += 1
            lignes.sort(key=lambda t: tri_cle(t[0])); ench.sort(key=lambda t: tri_cle(t[0]))
            corps.append(f'## {titre}\n')
            if genre == 'enchant':
                if lignes:
                    corps.append("### Objets enchantés\n")
                    corps.append(tableau(lignes) + '\n')
                if ench:
                    corps.append("### Enchantements\n")
                    corps.append(tableau(ench) + '\n')
            else:
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
    if manquants_icones:
        print('Icônes introuvables (lignes sans icône) :', ', '.join(sorted(manquants_icones)))
    if manquants:
        print('Noms français manquants (affichés tels quels) :', ', '.join(sorted(manquants)))
    print('Pages écrites :', len(index) + 1, '| actions :', sum(t for _, _, t, _ in index))


if __name__ == '__main__':
    main()
