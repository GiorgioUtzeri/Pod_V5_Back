# Migration WebTV → Pod V5

Ce document explique comment migrer les données de l'ancienne base WebTV vers Pod V5.
Il est destiné à la **personne qui effectuera la mise en production**.

---

## 1. Ce que fait la migration

La commande `Explosion` transfère dans Pod V5 :

| Données | Table WebTV source |
|---|---|
| Utilisateurs | `Ze4fg_users` + `Ze4fg_user_profile` |
| Vidéos (métadonnées) | `Ze4fg_video` |
| Intervenants | `Ze4fg_speakers` |
| Hyperliens | `Ze4fg_hyperlinks` |
| Documents | `Ze4fg_documents` |
| Groupes de vidéos | `Ze4fg_vdogrouping` |
| Collections | `Ze4fg_collections` |
| Commentaires | `Ze4fg_comments` |

> **Note :** La migration transfère uniquement les **métadonnées**.
> Les fichiers vidéo eux-mêmes ne sont PAS copiés automatiquement.
> Les chemins vers les fichiers sont conservés tels quels dans le champ `video_file`.

---

## 2. Prérequis

### 2.1 Fichier dump SQL

Tu dois avoir le fichier dump de la base WebTV à portée de main, par exemple :
```
dump-webtv-202510281226.sql
```

Place-le dans le répertoire racine du projet (là où se trouve le `Makefile`).

### 2.2 Variable d'environnement

Dans le fichier `.env` du projet, vérifie que `MYSQL_ROOT_PASSWORD` est défini :
```env
MYSQL_ROOT_PASSWORD=ton_mot_de_passe_root
```

### 2.3 Stack Docker démarrée

```bash
make start
```

---

## 3. Étapes de migration

### Étape 1 — Créer la base webtv et importer le dump

```bash
make setup-webtv-db WEBTV_DUMP=dump-webtv-202510281226.sql
```

Cette commande :
1. Crée la base de données `webtv` dans le conteneur MariaDB
2. Importe le fichier SQL dump

> Si ton dump a un autre nom, change le paramètre `WEBTV_DUMP=` en conséquence.

---

### Étape 2 — Tester sans écrire (recommandé)

Avant de migrer pour de vrai, lance une simulation pour vérifier que tout est bien connecté :

```bash
make migrate-webtv-dry-run
```

Tu devrais voir quelque chose comme :
```
DRY-RUN MODE — aucune écriture en base de données
Users mappés  : 0
Vidéos déjà migrées : 0
1247 vidéos trouvées dans webtv
[DRY-RUN] Terminé — 1247 créées, 0 déjà migrées, 12 skippées, 0 erreurs
```

---

### Étape 3 — Lancer la migration complète

```bash
make migrate-webtv
```

Cette commande :
1. Migre toutes les données (users → videos → speakers → … → comments)
2. Affiche la progression toutes les 100 vidéos
3. Reconstruit automatiquement l'index de recherche Redis à la fin

Durée estimée : **15 à 30 minutes** selon le volume de données.

---

### Étape 4 — Vérifier

Connecte-toi à l'interface admin de Pod V5 et vérifie :
- Les utilisateurs sont bien présents
- Les vidéos apparaissent avec leurs titres et métadonnées
- La recherche fonctionne

---

## 4. En cas de problème

### Relancer uniquement une étape

Si la migration a planté à mi-chemin (par exemple sur les vidéos), tu peux relancer **uniquement cette étape** sans tout recommencer depuis zéro. La migration est idempotente : elle ne recrée pas ce qui existe déjà.

```bash
# Depuis dans le conteneur
make enter
python manage.py Explosion --step videos
```

Étapes disponibles : `users`, `videos`, `speakers`, `hyperlinks`, `documents`, `groupings`, `collections`, `comments`

---

### Tester avec un petit lot

```bash
make enter
python manage.py Explosion --step videos --limit 50
```

---

### Reconstruire l'index de recherche manuellement

```bash
make reindex
```

---

## 5. Architecture technique (pour comprendre le code)

```
src/apps/migration/
├── management/commands/
│   └── Explosion.py         ← Point d'entrée (commande Django)
├── models.py                ← UserMapping, VideoMapping (tables de correspondance old_id → new_id)
└── utils/
    ├── userMigrate.py       ← Migration des utilisateurs
    ├── videoMigrate.py      ← Migration des vidéos ⚠️ voir note ci-dessous
    ├── speakerMigrate.py
    ├── hyperlinkMigrate.py
    ├── documentMigrate.py
    ├── groupingMigrate.py
    ├── collectionMigrate.py
    └── commentMigrate.py
```

### Pourquoi les signaux Django sont désactivés pendant la migration ?

Normalement, chaque fois qu'une vidéo est créée dans Pod, Django déclenche automatiquement plusieurs actions :
- Vide le cache Redis
- Lance un thread pour indexer la vidéo dans la recherche
- Tente de lire la durée du fichier vidéo sur le disque

Pendant une migration de 10 000+ vidéos, ces actions se déclenchent des dizaines de milliers de fois pour rien (les fichiers ne sont pas sur le disque, le cache est inutile à rafraîchir autant de fois).

La commande `Explosion` **désactive ces signaux** le temps de la migration, puis les réactive à la fin. C'est pour ça qu'elle est ~10x plus rapide et ne crashe plus.

### Les tables de mapping

`UserMapping` et `VideoMapping` stockent la correspondance entre les anciens IDs WebTV et les nouveaux IDs Pod. Elles permettent à la migration d'être **reprise sans duplication** si elle est interrompue.

---

## 6. Commandes de référence rapide

```bash
# Démarrer l'environnement
make start

# Importer le dump webtv
make setup-webtv-db WEBTV_DUMP=dump-webtv-202510281226.sql

# Simuler la migration (aucune écriture)
make migrate-webtv-dry-run

# Migration complète
make migrate-webtv

# Reconstruire l'index de recherche
make reindex

# Entrer dans le conteneur pour des commandes manuelles
make enter
python manage.py Explosion --help
```
