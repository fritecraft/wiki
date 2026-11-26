#!/usr/bin/env python3
"""Génère la section « Objets » du wiki depuis l'inventaire YAML du resourcepack (resourcepack/inventaire/objets).

Usage :  python3 generators/gen_items.py [chemin/vers/resourcepack]

- une page par famille d'objets (src/content/docs/objets/<famille>.md) + un index
- icônes copiées (première image des textures animées) dans public/items/<famille>/<id>.png
- chaque objet porte son nom français et son identifiant `fritecraft:<id>` (utile aux admins pour le donner en jeu)
- les objets à plusieurs états (arcs, arbalètes, cannes à pêche, boucliers, élytras) montrent leurs variantes en miniature
- les objets `a_traiter` (textures inutilisables en l'état) ne sont pas publiés
- un astérisque (*) signale un nom provisoire (nom_statut a_valider)
- pages et icônes sont commitées (le déploiement ne voit que GitHub) : relancer après un changement de l'inventaire ;
  ne PAS éditer les pages générées à la main. Rien de l'ancien système (numéros, regles OptiFine) n'est publié.
"""
import hashlib, shutil, sys, unicodedata
from pathlib import Path
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'resourcepack'
INV = PACK / 'inventaire'
OUT_IMG = ROOT / 'public' / 'items'
OUT_DOC = ROOT / 'src' / 'content' / 'docs' / 'objets'
ETATS = {'standby': 'Repos', 'pulling_start': 'Tension 1', 'pulling_middle': 'Tension 2', 'pulling_end': 'Tension 3',
         'arrow': 'Chargé (flèche)', 'firework': 'Chargé (feu d\'artifice)', 'uncast': 'Non lancée', 'cast': 'Lancée',
         'animated': 'Lancée', 'broken': 'Cassé', 'icon': 'Normal'}
# familles décrites sur la page (ordre d'affichage dans la barre latérale)
ORDRE = ['nourritures', 'boissons_miel', 'potions', 'livres', 'livres_enchantes', 'sacs', 'objets_divers', 'diamants', 'totems',
         'arcs', 'arbaletes', 'boucliers', 'cannes_a_peche', 'ciseaux', 'houes', 'pioches', 'pelles', 'briquets', 'elytras', 'armures_cheval']

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
def sort_key(nom): return unicodedata.normalize('NFKD', nom.lower()).encode('ascii', 'ignore').decode()

def premiere_image(chemin):
    im = Image.open(PACK / chemin).convert('RGBA'); w, h = im.size
    return im.crop((0, 0, w, w)) if h > w and h % w == 0 else im

def sauver(im, dossier, nom):
    p = OUT_IMG / dossier / nom; p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p, optimize=True)
    return f'/items/{dossier}/{nom}?v={hashlib.md5(p.read_bytes()).hexdigest()[:8]}'

def main():
    if not INV.is_dir(): sys.exit(f'Inventaire introuvable : {INV}')
    for d in (OUT_IMG, OUT_DOC):
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)
    fams = yaml.safe_load((INV / 'objets/familles.yml').read_text(encoding='utf-8'))['familles']
    summary = []
    for order, fam in enumerate(ORDRE, start=1):
        f = fams[fam]
        objets = [o for o in yaml.safe_load((INV / f['fichier']).read_text(encoding='utf-8'))['objets'] if o.get('statut') != 'a_traiter']
        objets.sort(key=lambda o: sort_key(o['nom']))
        prov = sum(1 for o in objets if o.get('nom_statut') == 'a_valider')
        L = ['---', f'title: "{f["nom"]}"', f'description: "Les {f["nom"].lower()} personnalisés de Fritecraft."',
             f'sidebar:\n  order: {order}', '---', '',
             '<!-- Page générée par generators/gen_items.py depuis l\'inventaire du resourcepack : ne pas modifier à la main. -->', '',
             f'**{len(objets)} objets.** L\'identifiant sous chaque nom sert à donner l\'objet en jeu.']
        if prov: L += ['', f':::note\nUn astérisque (*) signale un nom provisoire ({prov} objets).\n:::']
        L.append('')
        grouped = len(objets) > 100; cur = None; ouvert = False
        for o in objets:
            letter = sort_key(o['nom'])[:1].upper()
            if grouped and letter != cur:
                if ouvert: L += ['</div>', '']; ouvert = False
                cur = letter; L += [f'## {letter}', '']
            if not ouvert: L.append('<div class="item-grid">'); ouvert = True
            src = sauver(premiere_image(o['texture']), fam, f'{o["id"]}.png')
            nom = esc(o['nom']) + (' *' if o.get('nom_statut') == 'a_valider' else '')
            etats = ''
            roles = o.get('textures') or {}
            if len(roles) > 1:
                vus = {o['texture']}; mini = []
                for r, p in sorted(roles.items()):
                    if r in ETATS and p not in vus and not (r == 'icon' and o['texture'] == p):
                        vus.add(p)
                        try: u = sauver(premiere_image(p), fam, f'{o["id"]}_{r}.png')
                        except Exception: continue
                        mini.append(f'<img src="{u}" alt="{ETATS[r]}" title="{ETATS[r]}" loading="lazy">')
                if mini: etats = '<span class="item-etats">' + ''.join(mini) + '</span>'
            L.append(f'<figure><img src="{src}" alt="{esc(o["nom"])}" width="64" height="64" loading="lazy">{etats}'
                     f'<figcaption>{nom}<code class="item-id">fritecraft:{o["id"]}</code></figcaption></figure>')
        if ouvert: L.append('</div>')
        (OUT_DOC / f'{fam}.md').write_text('\n'.join(L).rstrip() + '\n')
        summary.append((fam, f['nom'], len(objets)))
        print(f'{fam:16} {len(objets):4} objets ({prov} noms provisoires)')
    total = sum(n for *_, n in summary)
    I = ['---', 'title: "Objets"', 'description: "Galeries des objets personnalisés de Fritecraft"', 'sidebar:\n  order: 0', '---', '',
         '<!-- Page générée par generators/gen_items.py : ne pas modifier à la main. -->', '',
         f"Fritecraft propose **{total} objets personnalisés** : nourritures, potions, livres, sacs, outils…", '',
         "Chaque objet est repéré par un identifiant `fritecraft:<nom>`, utilisable par les administrateurs pour le donner en jeu "
         "(exemple : `/give @s minecraft:stick[item_model=\"fritecraft:<nom>\"]`).", '']
    I += [f'- [{t}](/objets/{s}/) ({n})' for s, t, n in summary]
    (OUT_DOC / 'index.md').write_text('\n'.join(I) + '\n')
    print('total', total)

main()
