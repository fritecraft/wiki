#!/usr/bin/env bash
# Déploiement automatique du wiki : reconstruit et redémarre le conteneur
# uniquement si la branche main du dépôt GitHub a changé.
# Prévu pour être lancé à intervalle régulier (timer systemd). Aucun accès entrant requis.
set -euo pipefail

REPO="https://github.com/fritecraft/wiki.git"
BRANCH="main"
IMAGE="fritecraft-wiki:latest"

cd "$(dirname "$(readlink -f "$0")")"
exec 9>/tmp/fritecraft-wiki-deploy.lock
flock -n 9 || { echo "déploiement déjà en cours"; exit 0; }

remote=$(git ls-remote "$REPO" "refs/heads/$BRANCH" | cut -f1)
[ -n "$remote" ] || { echo "impossible de lire $REPO ($BRANCH)" >&2; exit 1; }

current=$(docker image inspect "$IMAGE" --format '{{index .Config.Labels "wiki.commit"}}' 2>/dev/null || true)
if [ "$remote" = "$current" ]; then
  exit 0
fi

echo "$(date -Is) déploiement ${current:-<aucun>} -> $remote"
# Construit directement depuis GitHub : la copie de travail locale n'est jamais utilisée.
docker build --label "wiki.commit=$remote" -t "$IMAGE" "$REPO#$remote"
docker compose up -d --no-build
echo "$(date -Is) déploiement terminé"
