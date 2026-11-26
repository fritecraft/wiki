#!/usr/bin/env python3
"""Génère la section « Boutiques » du wiki : un tableau des prix (achat / vente, en émeraudes) par boutique.

Usage :  python3 generators/gen_boutiques.py [chemin/vers/EconomyShopGUI]

Source : le dossier de configuration du plugin de shop (EconomyShopGUI), fichiers shops/<boutique>.yml. Par défaut, la dernière
sauvegarde du serveur 1.19 (archives/fritecraft_1.19_2024-01-31/volumes/EconomyShopGUI) : la config locale du shop est la meilleure
source des prix. Relancer avec le nouveau dossier quand le shop du serveur 26.3 sera configuré.
Les noms français des objets viennent du fichier de langue du jeu (téléchargé une fois dans generators/.cache, non commité).
Les pages générées sont commitées ; ne PAS les éditer à la main.
"""
import json, shutil, sys, unicodedata, urllib.request
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'archives/fritecraft_1.19_2024-01-31/volumes/EconomyShopGUI'
OUT = ROOT / 'src/content/docs/boutiques'
CACHE = ROOT / 'generators/.cache/fr_fr.json'
LANG_URL = 'https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21.4/assets/minecraft/lang/fr_fr.json'

# fichier -> (titre, divinité ou thème, description)
BOUTIQUES = {
    'Nuggetsgirl': ('Boutique de Nuggetsgirl', "Outils de culture, produits animaux, cultures."),
    'Fritegirl': ('Boutique de Fritegirl', "Butins d'exploration et de monstres, objets en or."),
    'Hamburgirl': ('Boutique de Hamburgirl', "Équipement de protection, viandes, matériaux de construction et de terrain."),
    'Soupegirl': ('Boutique de Soupegirl', "Objets en provenance du Nether."),
    'Sodagirl': ('Boutique de Sodagirl', "Objets de l'océan (poissons, coraux, algues, prismarin) et équipement de pêche."),
    'Candygirl': ('Boutique de Candygirl', "Objets de l'End et nourritures sucrées."),
    'Flurrygirl': ('Boutique de Flurrygirl', "Minerais, pierres et équipement pratique pour l'exploration souterraine."),
    'Chocogirl': ('Boutique de Chocogirl', "Objets liés aux arbres et à la jungle, équipement de chasseur."),
    'Fringirl': ('Boutique de Fringirl', "Objets obscurs, d'origine surnaturelle, ou qui ne représentent pas les autres divinités."),
    'Redstone': ('Boutique Redstone', "Tous les objets nécessaires aux circuits de redstone."),
}

def lang():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(LANG_URL, timeout=60) as r: CACHE.write_bytes(r.read())
    return json.loads(CACHE.read_text(encoding='utf-8'))

def nom(L, mat, it):
    if mat == 'POTION' and it.get('potiontypes') == ['WATER']: return "Fiole d'eau"
    k = mat.lower()
    for p in ('item', 'block'):
        if f'{p}.minecraft.{k}' in L: return L[f'{p}.minecraft.{k}']
    sys.exit(f'Pas de nom français pour {mat}')

def prix(x):
    if x < 0: return '—'          # -1 dans la config : opération impossible dans cette boutique
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')

def cle(s): return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()

def main():
    if not (SRC / 'shops').is_dir(): sys.exit(f'Config introuvable : {SRC}')
    L = lang()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    index, total = [], 0
    for order, (fic, (titre, desc)) in enumerate(BOUTIQUES.items(), start=1):
        d = yaml.safe_load((SRC / 'shops' / f'{fic}.yml').read_text(encoding='utf-8'))
        lignes = []
        for pg in d['pages'].values():
            for it in (pg.get('items') or {}).values():
                lot = it.get('stack-size')
                n = nom(L, it['material'], it) + (f' (lot de {lot})' if lot and lot > 1 else '')
                lignes.append((n, it['buy'], it['sell']))
        lignes.sort(key=lambda t: cle(t[0]))
        P = ['---', f'title: "{titre}"', f'description: "{desc}"', f'sidebar:\n  order: {order}', '---', '',
             '<!-- Page générée par generators/gen_boutiques.py depuis la configuration du shop : ne pas modifier à la main. -->', '',
             f'{desc} **{len(lignes)} objets.**', '',
             'Prix en émeraudes (un bloc d\'émeraude vaut 9 émeraudes). Un tiret (—) indique que l\'opération est impossible dans cette boutique.', '',
             '| Objet | Achat | Vente |', '| --- | ---: | ---: |']
        P += [f'| {n} | {prix(b)} | {prix(s)} |' for n, b, s in lignes]
        (OUT / f'{fic.lower()}.md').write_text('\n'.join(P) + '\n', encoding='utf-8')
        index.append((fic.lower(), titre, desc, len(lignes))); total += len(lignes)
        print(f'{fic:12} {len(lignes):3} objets')
    I = ['---', 'title: "Boutiques"', 'description: "Les boutiques du serveur et leurs prix"', 'sidebar:\n  order: 0', '---', '',
         '<!-- Page générée par generators/gen_boutiques.py : ne pas modifier à la main. -->', '',
         "Les boutiques sont organisées par affinité avec les divinités, pas par fonction. Chaque page liste les objets que la boutique "
         "achète et vend, avec leurs prix en émeraudes. Le fonctionnement général (vente, commandes) est décrit sur la page [Boutique](/fritecraft/shop/).", '']
    I += [f'- [{t}](/boutiques/{s}/) : {d} ({n})' for s, t, d, n in index]
    (OUT / 'index.md').write_text('\n'.join(I) + '\n', encoding='utf-8')
    print('total', total)

main()
