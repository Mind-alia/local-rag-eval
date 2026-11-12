# Configurer une extension

Une extension est un programme que cagibi lance à deux moments : avant chaque rangement
(`avant_rangement`) et après (`apres_rangement`).

## Déclaration

Les extensions se déclarent dans la section `[extensions]` du fichier de configuration, une
ligne par extension : son nom, puis le chemin de son exécutable.

## Délai

Une extension doit rendre la main en moins de 10 secondes. Au-delà, cagibi l'arrête et
poursuit le rangement sans elle.
