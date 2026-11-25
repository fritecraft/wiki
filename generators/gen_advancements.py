#!/usr/bin/env python3
"""Génère la section « Progrès » du wiki depuis le datapack (data/fritecraft/advancements).

Usage :  python3 generators/gen_advancements.py [chemin/vers/datapack] [--include-broken]

- une page par divinité (src/content/docs/progres/<divinite>.md) + un index avec les totaux
- ne PAS éditer ces fichiers à la main : ils sont régénérés
- par défaut, seuls les progrès réellement chargés par Minecraft sont publiés : un progrès dont
  la chaîne de parents mène à un progrès inexistant n'est jamais chargé en jeu. La liste des
  progrès exclus est affichée à la fin (--include-broken pour les publier quand même).
- les progrès cachés (hidden) ne sont pas détaillés, seulement comptés.
"""
import json, shutil, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith('--')]
INCLUDE_BROKEN = '--include-broken' in sys.argv
DATAPACK = Path(args[0]) if args else ROOT.parent / 'datapack'
ADV = DATAPACK / 'data' / 'fritecraft' / 'advancements'
OUT = ROOT / 'src' / 'content' / 'docs' / 'progres'
ORDER = ['nuggetsgirl', 'fritegirl', 'hamburgirl', 'soupegirl', 'sodagirl', 'candygirl', 'flurrygirl', 'chocogirl']
FRAME = {'task': 'Progrès', 'goal': 'Objectif', 'challenge': 'Défi'}

def cell(s):
    return str(s).replace('|', '\\|').replace('\n', ' ').strip()

def main():
    if not ADV.is_dir():
        sys.exit(f'Datapack introuvable : {ADV}')
    adv = {p.relative_to(ADV).with_suffix('').as_posix(): json.loads(p.read_text(encoding='utf-8'))
           for p in ADV.rglob('*.json')}

    def parent_of(k):
        p = adv[k].get('parent')
        if not p: return None
        ns, _, path = p.partition(':')
        return path if ns == 'fritecraft' else p

    def loadable(k):
        while True:
            if k not in adv: return False
            p = parent_of(k)
            if p is None: return True
            k = p

    broken = sorted(k for k in adv if not loadable(k))
    keep = {k for k in adv if INCLUDE_BROKEN or k not in set(broken)}

    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    stats = []
    for order, div in enumerate(ORDER, start=1):
        keys = sorted(k for k in keep if k.startswith(div + '/'))
        root = adv.get(f'{div}/root')
        if not root: continue
        name = div.capitalize()
        children = collections.defaultdict(list)
        for k in keys:
            if k.endswith('/root'): continue
            p = parent_of(k)
            # un parent d'une autre divinité (ou absent) : on rattache à la racine de la divinité du progrès
            children[p if (p in keep and p.startswith(div + '/')) else f'{div}/root'].append(k)
        rows, hidden = [], 0
        def walk(k):
            nonlocal hidden
            for c in sorted(children.get(k, []), key=lambda x: adv[x]['display']['title'].lower()):
                d = adv[c]['display']
                if d.get('hidden'): hidden += 1
                else:
                    p = parent_of(c)
                    pre = '' if p == f'{div}/root' or p not in adv else adv[p]['display']['title']
                    rows.append((d['title'], d['description'], FRAME.get(d.get('frame', 'task'), 'Progrès'), pre, c))
                walk(c)
        walk(f'{div}/root')
        n_all = sum(1 for k in adv if k.startswith(div + '/') and not k.endswith('/root'))
        counts = collections.Counter(r[2] for r in rows)
        stats.append((div, name, root['display']['description'], len(rows), counts, hidden, n_all))
        L = ['---', f'title: "{name}"', f'description: "{cell(root["display"]["description"])}"',
             f'sidebar:\n  order: {order}', '---', '',
             '<!-- Page générée par generators/gen_advancements.py : ne pas modifier à la main. -->', '',
             f'{root["display"]["description"]}', '',
             f'**{len(rows)} progrès** ({counts["Progrès"]} progrès, {counts["Objectif"]} objectifs, {counts["Défi"]} défis)'
             + (f', plus {hidden} progrès caché{"s" if hidden > 1 else ""} à découvrir.' if hidden else '.'), '',
             '| Progrès | Description | Type | Débloqué après |', '|---|---|---|---|']
        L += [f'| **{cell(t)}** | {cell(d)} | {ty} | {cell(pre) or "—"} |' for t, d, ty, pre, _ in rows]
        (OUT / f'{div}.md').write_text('\n'.join(L) + '\n')
        print(f'{div:12} {len(rows):3} publiés, {hidden} cachés, {n_all - len(rows) - hidden} exclus')

    total = sum(s[3] for s in stats)
    I = ['---', 'title: "Progrès"', 'description: "Les progrès du datapack Fritecraft, par divinité"',
         'sidebar:\n  order: 0', '---', '',
         '<!-- Page générée par generators/gen_advancements.py : ne pas modifier à la main. -->', '',
         "Le datapack de Fritecraft réorganise les Progrès de Minecraft selon les divinités du serveur et en ajoute de nouveaux. "
         f"Il y a actuellement **{total} progrès** répertoriés.", '',
         '| Divinité | Thème | Progrès | Objectifs | Défis |', '|---|---|---|---|---|']
    I += [f'| [{n}](/progres/{d}/) | {cell(desc)} | {c["Progrès"]} | {c["Objectif"]} | {c["Défi"]} |'
          for d, n, desc, _, c, _, _ in stats]
    (OUT / 'index.md').write_text('\n'.join(I) + '\n')
    print(f'total {total}')
    if broken and not INCLUDE_BROKEN:
        print(f'\nATTENTION : {len(broken)} progrès exclus (jamais chargés par Minecraft : parent introuvable) :')
        for k in broken:
            p = adv[k].get('parent')
            print(f'  {k}  (parent : {p})')

main()
