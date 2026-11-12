# Questions fréquentes

## cagibi peut-il perdre un fichier ?

Non. Un original n'est supprimé qu'après la vérification de l'archive qui le contient. Si la
vérification échoue, l'original reste en place et l'erreur est notée dans le journal.

## Que se passe-t-il si le disque est plein ?

cagibi s'arrête avant de supprimer quoi que ce soit et renvoie le code de sortie 75. Il suffit
de libérer de la place, puis de relancer la même commande.

## Les liens symboliques sont-ils suivis ?

Non. cagibi ignore les liens symboliques et ne range que les fichiers ordinaires.
