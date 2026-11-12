# Commandes

## cagibi scan

`cagibi scan <dossier>` liste les fichiers oubliés du dossier, avec leur taille et la date de
leur dernière modification. Cette commande ne déplace rien.

## cagibi range

`cagibi range <dossier>` copie les fichiers oubliés dans une archive `.tar.zst`, vérifie
l'archive, puis supprime les originaux.

- `--simulation` : affiche ce qui serait rangé, sans rien déplacer ni supprimer.
- `--age <jours>` : remplace le seuil de la configuration pour cette commande seulement.
- `--exclure <motif>` : ignore les fichiers qui correspondent au motif. L'option peut être
  répétée.

## cagibi restaure

`cagibi restaure <archive>` remet tous les fichiers d'une archive à leur place d'origine.
Avec `--fichier <chemin>`, seul ce fichier est restauré.
