#!/usr/bin/env python3
"""Génère les galeries d'icônes du wiki (section « Objets ») depuis resourcepack/_wiki.

Usage :  python3 generators/gen_items.py [chemin/vers/resourcepack/_wiki]

- copie les icônes dans public/items/<categorie>/
- écrit src/content/docs/objets/*.md (ne PAS éditer ces fichiers à la main : ils sont régénérés)

Les noms affichés sont dérivés des noms de fichiers (provisoire : voir l'issue
« Harmoniser les noms des items » dans le Fritecraft Tracker).
"""
import re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'resourcepack' / '_wiki'
OUT_IMG = ROOT / 'public' / 'items'
OUT_DOC = ROOT / 'src' / 'content' / 'docs' / 'objets'

# (dossier source, slug, titre, description, préfixe si le nom est un simple numéro)
CATEGORIES = [
    ('consommable/nourriture', 'nourriture', 'Nourritures', "Les nourritures personnalisées du serveur.", None),
    ('consommable/potions',    'potions',    'Potions et boissons', "Potions, alcools et infusions.", None),
    ('consommable/tomes',      'tomes',      'Tomes', "Les tomes et grimoires des divinités.", None),
    ('items/quetes',           'quetes',     'Objets de quête', "Objets obtenus ou utilisés pendant les quêtes.", None),
    ('items/divers',           'divers',     'Objets divers', "Objets décoratifs, emblèmes et curiosités.", None),
    ('items/sacs',             'sacs',       'Sacs', "Les sacs de récompenses.", 'Sac'),
    ('items/keys',             'cles',       'Clés', "Clés et accès aux donjons et coffres.", None),
    ('items/drops',            'drops',      'Drops', "Objets obtenus en tuant des monstres.", None),
    ('items/jetons',           'jetons',     'Jetons', "Les jetons du serveur.", 'Jeton'),
]
SMALL = {'de', 'du', 'des', 'la', 'le', 'les', 'd', 'l', 'et', 'a', 'au', 'aux', 'en', 'of', 'the'}
IGNORE = {'transparent'}

def pretty(stem, prefix):
    if prefix and stem.isdigit():
        return f'{prefix} {stem}'
    words = re.split(r'[_\-\s]+', stem)
    out = [w if (i and w.lower() in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words) if w]
    return ' '.join(out) or stem

def sort_key(stem):
    return (0, int(stem), '') if stem.isdigit() else (1, 0, stem.lower())

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

def main():
    if not SRC.is_dir():
        sys.exit(f'Source introuvable : {SRC}')
    for d in (OUT_IMG, OUT_DOC):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    summary = []
    for order, (folder, slug, title, desc, prefix) in enumerate(CATEGORIES, start=1):
        files = sorted((p for p in (SRC / folder).glob('*.png') if p.stem not in IGNORE),
                       key=lambda p: sort_key(p.stem))
        (OUT_IMG / slug).mkdir()
        for p in files:
            shutil.copy2(p, OUT_IMG / slug / p.name)

        lines = ['---', f'title: "{title}"', f'description: "{desc}"',
                 f'sidebar:\n  order: {order}', '---', '',
                 '<!-- Page générée par generators/gen_items.py : ne pas modifier à la main. -->', '',
                 f'{desc} **{len(files)} objets.**', '',
                 ":::note\nLes noms affichés sont provisoires : ils sont déduits des noms de fichiers.\n:::", '']
        grouped = len(files) > 100
        cur = None; open_grid = False
        def close():
            nonlocal open_grid
            if open_grid:
                lines.append('</div>'); lines.append(''); open_grid = False
        for p in files:
            letter = p.stem[:1].upper()
            if grouped and letter != cur:
                close(); cur = letter
                lines += [f'## {letter if letter.isalpha() else "0-9"}', '']
            if not open_grid:
                lines.append('<div class="item-grid">'); open_grid = True
            name = esc(pretty(p.stem, prefix))
            lines.append(f'<figure><img src="/items/{slug}/{p.name}" alt="{name}" width="64" height="64" loading="lazy"><figcaption>{name}</figcaption></figure>')
        close()
        (OUT_DOC / f'{slug}.md').write_text('\n'.join(lines).rstrip() + '\n')
        summary.append((slug, title, desc, len(files)))
        print(f'{slug:10} {len(files):4} icônes')

    total = sum(n for *_, n in summary)
    idx = ['---', 'title: "Objets"', 'description: "Galeries des objets personnalisés de Fritecraft"',
           'sidebar:\n  order: 0', '---', '',
           '<!-- Page générée par generators/gen_items.py : ne pas modifier à la main. -->', '',
           f"Fritecraft propose **{total} objets personnalisés** : nourritures, potions, tomes, objets de quête…", '']
    idx += [f'- [{t}](/objets/{s}/) : {d} ({n})' for s, t, d, n in summary]
    (OUT_DOC / 'index.md').write_text('\n'.join(idx) + '\n')
    print(f'total {total}')

main()
