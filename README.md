# Menus de la semaine — app familiale

App web minimale, sans aucune dépendance externe (Python 3 standard uniquement), pour :

- planifier les **menus de la semaine** (midi / soir, lundi → dimanche) via une **liste déroulante des recettes** (intégrées + perso) — la sélection met à jour automatiquement la liste de courses ;
- gérer la **liste de courses** (ajouter, cocher, supprimer) ;
- lister **ce qu'on a déjà à la maison** (inventaire) ;
- indiquer pour chaque repas si on est **2 ou 3 (avec bébé)** à manger, avec un champ « repas bébé » quand on est 3 ;
- obtenir des **suggestions de repas** selon l'inventaire, avec badge « adapté 18 mois »
  (textures molles, morceaux adaptés, peu salé) et possibilité d'ajouter d'un clic
  les ingrédients manquants à la liste de courses ;
- **générer automatiquement la liste de courses depuis le menu** : les ingrédients des
  recettes reconnues dans les menus sont ajoutés, sauf s'ils sont déjà dans « Chez nous »,
  avec une **quantité adaptée à 2 ou 3 personnes** (selon le réglage « avec bébé » du repas) ;
- la liste de courses se **met à jour avec « Chez nous »** : ajouter un ingrédient à l'inventaire
  le retire des courses, et « Générer depuis le menu » nettoie aussi les articles désormais en stock ;
- **ajouter ses propres recettes** (onglet Suggestions), en plus des recettes de base intégrées.

Les données sont stockées dans `data.json` (créé automatiquement au premier lancement).

## Lancer sur le Mac

```bash
python3 app.py
```

Puis ouvrir http://127.0.0.1:8000 dans Safari.

## Accéder depuis l'iPad et l'iPhone (même Wi-Fi)

Lancer sur le Mac en écoutant sur le réseau local :

```bash
python3 app.py --host 0.0.0.0 --port 8000
```

Repérer l'adresse IP locale du Mac (`Préférences Système > Réseau`, ex. `192.168.1.42`),
puis ouvrir sur iPad/iPhone : `http://192.168.1.42:8000`.

> À n'utiliser que sur son propre réseau Wi-Fi de confiance, jamais exposé sur Internet.

## API (JSON)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/api/menu` | Lire le menu |
| POST | `/api/menu` | `{day, meal, field, value}` : `field` = `text` (repas), `persons` (`2` ou `3`, 3 = avec bébé) ou `baby` (repas bébé). Si le texte correspond à une recette connue, ses ingrédients manquants sont ajoutés aux courses |
| POST | `/api/menu/sync-shopping` | Ajoute aux courses les ingrédients de toutes les recettes reconnues dans le menu (hors inventaire) |
| GET | `/api/recipes/all` | Toutes les recettes (intégrées + perso) pour la liste déroulante du menu |
| GET / POST | `/api/recipes` | Lire / ajouter une recette perso `{name, ingredients, child_friendly}` |
| DELETE | `/api/recipes/{id}` | Supprimer une recette perso |
| GET / POST | `/api/shopping` | Lire / ajouter un article |
| POST | `/api/shopping/toggle` | `{id}` : cocher/décocher |
| DELETE | `/api/shopping/{id}` | Supprimer un article |
| GET / POST | `/api/inventory` | Lire / ajouter un ingrédient en stock |
| DELETE | `/api/inventory/{id}` | Retirer du stock |
| GET | `/api/suggestions` | Recettes triées selon l'inventaire |
| POST | `/api/suggestions/{id}/add-missing` | Ajouter les ingrédients manquants aux courses |
