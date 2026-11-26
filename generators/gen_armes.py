#!/usr/bin/env python3
"""Génère la section « Armes » du wiki depuis l'inventaire YAML du resourcepack.

Usage :  python3 generators/gen_armes.py [chemin/vers/resourcepack]

- une page par famille (src/content/docs/armes/<famille>.md) + un index
- icônes recadrées (première image des textures animées) dans public/armes/<famille>/<id>.png
- toutes les icônes sont affichées avec des pixels de dessin de même taille (PX px écran) : certaines textures
  (64x64) sont des dessins de résolution 32 agrandis par blocs 2x2, on les ramène à leur résolution réelle
- l'illustration est recadrée sur sa zone non transparente (le grand canevas vide n'apporte rien au wiki)
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
PX = 4  # pixels écran par pixel de dessin (après réduction des agrandissements par blocs)

def block_factor(im):
    """Plus grand f (4, 2) tel que l'image soit un agrandissement par blocs f x f d'une image plus petite."""
    w, h = im.size
    for f in (4, 2):
        if w % f or h % f: continue
        if im.resize((w // f, h // f), Image.NEAREST).resize((w, h), Image.NEAREST).tobytes() == im.tobytes(): return f
    return 1

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
             ":::note\nLes illustrations sont recadrées et affichées avec des pixels de même taille : "
             "la taille à l'écran reflète le dessin de l'arme, pas la taille de sa texture dans le jeu."
             + (f"\n\nUn astérisque (*) signale un nom provisoire ({prov} armes)." if prov else '') + "\n:::", '']
        grouped = len(armes) > 100; cur = None; open_grid = False
        for a in armes:
            im = Image.open(TEX / a['texture']).convert('RGBA'); w, h = im.size
            if h > w and h % w == 0: im = im.crop((0, 0, w, w))          # première image d'une animation
            bf = block_factor(im)
            if bf > 1: im = im.resize((im.width // bf, im.height // bf), Image.NEAREST)   # résolution réelle du dessin
            bbox = im.getchannel('A').getbbox()
            if bbox: im = im.crop(bbox)                                   # recadrage sur le dessin
            w, h = im.size
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
