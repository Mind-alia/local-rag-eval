# cagibi

cagibi est un outil en ligne de commande qui repère les fichiers oubliés d'un dossier et les
range dans une archive compressée. Rien n'est perdu : chaque rangement est noté dans un journal,
et tout peut être remis en place.

## Principes

- Un fichier est oublié quand il n'a pas été modifié depuis longtemps. Le seuil se règle dans la
  configuration.
- Chaque archive est accompagnée d'une empreinte SHA-256. cagibi la contrôle avant de supprimer
  le moindre original.
- Le journal garde, pour chaque fichier rangé, son chemin d'origine et le nom de son archive.

## Premier essai

```sh
cagibi scan ~/Téléchargements
```

Cette commande liste les fichiers oubliés du dossier, sans rien déplacer.
