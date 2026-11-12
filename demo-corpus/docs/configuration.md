# Configuration

cagibi lit le fichier `cagibi.toml`, cherché d'abord dans le dossier courant, puis dans
`~/.cagibi/`. Sans ce fichier, les valeurs par défaut s'appliquent.

## Réglages

- `age_minimum` : par défaut, un fichier est oublié après 180 jours sans modification.
- `dossier_archives` : dossier où sont écrites les archives, `.cagibi/archives` par défaut.
- `niveau_compression` : niveau de compression zstd, de 1 à 19, 3 par défaut.

## Priorité

Une option de la ligne de commande l'emporte sur la variable d'environnement `CAGIBI_AGE`, qui
l'emporte sur `cagibi.toml`, qui l'emporte sur les valeurs par défaut.
