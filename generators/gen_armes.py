#!/usr/bin/env python3
"""Génère la section « Armes » du wiki depuis l'inventaire YAML du resourcepack.

Usage :  python3 generators/gen_armes.py [chemin/vers/resourcepack]

- une page par famille (src/content/docs/armes/<famille>.md) + un index
- icônes recadrées (première image des textures animées) dans public/armes/<famille>/<id>.png
- toutes les icônes sont affichées à la même échelle (2 px écran par pixel de texture) : une arme au petit
  format paraît donc plus petite qu'une arme au grand format, comme en jeu
- les pages et icônes sont commitées (le déploiement ne voit que GitHub) : relancer après un changement
  de l'inventaire ; ne PAS éditer les pages générées à la main
- palier et dégâts de l'ancienne configuration MMOItems ne sont pas publiés (MMOItems sera recréé)
"""
import re, shutil, sys, unicodedata
from pathlib import Path
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'resourcepack'
INV = PACK / 'inventaire'
TEX = PACK / 'assets/minecraft/textures/fritecraft'
OUT_IMG = ROOT / 'public' / 'armes'
OUT_DOC = ROOT / 'src' / 'content' / 'docs' / 'armes'
PX = 2  # pixels écran par pixel de texture

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

def sort_key(nom):
    return unicodedata.normalize('NFKD', nom.lower()).encode('ascii', 'ignore').decode()

def main():
    if not INV.is_dir(): sys.exit(f'Inventaire introuvable : {INV}')
    for d in (OUT_IMG, OUT_DOC):
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)
    fams = yaml.safe_load((INV / 'familles.yml').read_text(encoding='utf-8'))['familles']
    summary = []
    for order, (fam, f) in enumerate((k, v) for k, v in fams.items() if v.get('statut') != 'a_venir' and v.get('fichier')):
        slug = Path(f['fichier']).stem
        armes = yaml.safe_load((INV / f['fichier']).read_text(encoding='utf-8'))['armes']
        armes.sort(key=lambda a: sort_key(a['nom']))
        (OUT_IMG / fam).mkdir()
        prov = sum(1 for a in armes if a.get('nom_statut') == 'a_valider')
        L = ['---', f'title: "{f["nom"]}"', f'description: "Les {len(armes)} {f["nom"].lower()} personnalisées de Fritecraft."',
             f'sidebar:\n  order: {order + 1}', '---', '',
             '<!-- Page générée par generators/gen_armes.py depuis l\'inventaire du resourcepack : ne pas modifier à la main. -->', '',
             f'Fritecraft compte **{len(armes)} {f["nom"].lower()}** aux noms et aux textures uniques.', '',
             ":::note\nToutes les armes sont affichées à la même échelle : une arme au petit format paraît plus petite "
             "qu'une arme au grand format, comme en jeu."
             + (f"\n\nUn astérisque (*) signale un nom provisoire ({prov} armes)." if prov else '') + "\n:::", '']
        grouped = len(armes) > 100; cur = None; open_grid = False
        for a in armes:
            im = Image.open(TEX / a['texture']).convert('RGBA'); w, h = im.size
            if h > w and h % w == 0: im = im.crop((0, 0, w, w)); h = w
            im.save(OUT_IMG / fam / f'{a["id"]}.png', optimize=True)
            letter = sort_key(a['nom'])[:1].upper()
            if grouped and letter != cur:
                if open_grid: L += ['</div>', '']; open_grid = False
                cur = letter; L += [f'## {letter}', '']
            if not open_grid: L.append('<div class="arme-grid">'); open_grid = True
            name = esc(a['nom']) + (' *' if a.get('nom_statut') == 'a_valider' else '')
            L.append(f'<figure><div class="arme-icone"><img src="/armes/{fam}/{a["id"]}.png" alt="{esc(a["nom"])}" '
                     f'width="{w * PX}" height="{h * PX}" loading="lazy"></div><figcaption>{name}</figcaption></figure>')
        if open_grid: L += ['</div>']
        (OUT_DOC / f'{slug}.md').write_text('\n'.join(L).rstrip() + '\n')
        summary.append((slug, f['nom'], len(armes)))
        print(f'{slug:8} {len(armes):4} armes ({prov} noms provisoires)')
    total = sum(n for *_, n in summary)
    I = ['---', 'title: "Armes"', 'description: "Les armes personnalisées de Fritecraft"', 'sidebar:\n  order: 0', '---', '',
         '<!-- Page générée par generators/gen_armes.py : ne pas modifier à la main. -->', '',
         f"Fritecraft propose **{total} armes personnalisées**, chacune avec son nom et sa texture.", '']
    I += [f'- [{t}](/armes/{s}/) ({n})' for s, t, n in summary]
    (OUT_DOC / 'index.md').write_text('\n'.join(I) + '\n')
    print('total', total)

main()
