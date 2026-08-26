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
| Groupes de vidéos / Channels | `Ze4fg_vdogrouping` |
| Collections, Favoris, Playlists | `Ze4fg_collections` |
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

### 2.2 Variables d'environnement

Dans le fichier `.env` du projet, vérifie que ces variables sont définies :
```env
# Mot de passe root de la base MariaDB (nécessaire pour créer la BDD webtv)
MYSQL_ROOT_PASSWORD=ton_mot_de_passe_root

# Chemin racine des fichiers médias de Pod (vidéos, miniatures, documents)
# Doit pointer vers le même dossier que les fichiers copiés depuis WebTV
MEDIA_ROOT=/chemin/vers/media/pod/
MEDIA_URL=/media/
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

**Exemple de sortie (adapté aux vraies données WebTV) :**
```
STEP: USERS
  28 users migrés

STEP: VIDEOS
  7393 vidéos trouvées dans webtv
  [DRY-RUN] Terminé — 7393 créées, 0 déjà migrées, 0 skippées, 0 erreurs

STEP: GROUPINGS
  737 Channels créés
  9 Themes créés
  0 vidéos affectées à leur(s) Channel(s)   ← NORMAL en dry-run (voir explication ci-dessous)

STEP: SPEAKERS
  Videos mappées: 0   ← NORMAL en dry-run
  6908 contributors créés

Migration complète en ~22s
```

> #### ⚠️ Pourquoi "0 vidéos affectées" en dry-run ?
>
> En mode dry-run, les vidéos **ne sont pas écrites en base**. Du coup, quand les
> étapes suivantes (Channels, Speakers, Hyperlinks…) cherchent les vidéos dans la
> table `VideoMapping`, elles n'en trouvent aucune et affichent `0`.
>
> **C'est un comportement normal et attendu.** Lors de la vraie migration (`make migrate-webtv`),
> les vidéos seront créées en premier et tout sera correctement lié.

---

### Étape 3 — Lancer la migration complète

```bash
make migrate-webtv
```

Cette commande :
1. Migre toutes les données dans l'ordre : users → videos → speakers → hyperlinks → documents → groupings → collections → comments
2. Affiche la progression toutes les 100 vidéos
3. Reconstruit automatiquement l'index de recherche Redis à la fin

Durée estimée : **15 à 30 minutes** selon le volume de données.

---

### Étape 4 — Copier les fichiers vidéo physiques

Les métadonnées sont dans Pod, mais les **fichiers `.mp4` eux-mêmes** ne sont pas copiés par la migration. Il faut les transférer manuellement depuis l'ancien serveur WebTV :

```bash
# Adapter les chemins selon ton environnement
rsync -avz --progress \
    ancien-serveur-webtv:/chemin/webtv/media/ \
    /chemin/vers/media/pod/
```

> Assure-toi que `MEDIA_ROOT` dans ton `.env` pointe vers le bon répertoire de destination.

---

### Étape 5 — Vérifier

Connecte-toi à l'interface admin de Pod V5 et vérifie :
- Les utilisateurs sont bien présents
- Les vidéos apparaissent avec leurs titres et métadonnées
- Les Channels et Themes sont créés
- La recherche fonctionne (`make reindex` si nécessaire)

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

## 6. Récapitulatif — Comprendre les chiffres de la migration

Une fois la **vraie migration** terminée (`make migrate-webtv`), voici comment interpréter les résultats de chaque étape :

### USERS
```
28 users migrés
```
→ Tous les comptes WebTV ont été recréés dans Pod. Les mots de passe ne sont pas transférés (les users devront se reconnecter via CAS ou réinitialiser leur mot de passe).

---

### VIDEOS
```
7393 vidéos trouvées dans webtv
Terminé — 7393 créées, 0 déjà migrées, 0 skippées, 0 erreurs
```
→ **7393 créées** = vidéos migrées avec succès.
→ **skippées** = vidéos dont le propriétaire n'existe pas dans Pod (ne peut pas arriver si tous les users ont été migrés avant).
→ **déjà migrées** = si tu relances, ce nombre augmente (idempotence).

---

### GROUPINGS (Channels & Themes)
```
737 Channels créés, 9 Themes créés
7393 vidéos affectées à leur(s) Channel(s)
```
→ Chaque Collection WebTV est devenue un **Channel** dans Pod.
→ Une vidéo peut maintenant appartenir à **plusieurs Channels** (contrairement à l'ancienne limitation).
→ Les 9 Thématiques WebTV sont devenues des **Themes** globaux dans Pod.

---

### SPEAKERS
```
6908 contributors créés
X contributions créées
```
→ Chaque intervenant WebTV est devenu un `Contributor` dans Pod.
→ Les liens intervenant ↔ vidéo sont recréés comme `Contribution` (role="speaker").

---

### HYPERLINKS & DOCUMENTS
```
X liens créés, Y ignorés
```
→ **ignorés** = liens dont la vidéo cible n'est pas dans le VideoMapping (vidéo skippée à l'étape précédente).

---

### COMMENTS
```
X créés, Y skippés, 0 erreurs
```
→ Les commentaires imbriqués (réponses) sont correctement liés via `parent` / `direct_parent`.
→ **skippés** = commentaires dont le user ou la vidéo n'a pas été migré.

---

## 7. Commandes de référence rapide

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
