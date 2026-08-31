# Guide de Migration Esup-Pod : V3 → V5 en Production

> Ce document est la **source de vérité unique** pour passer une instance Esup-Pod V3 en production vers la V5. Il synthétise l'analyse du code source, des scripts de migration existants et de la documentation officielle.
>
> **Navigation :** [Retour à l'overview Déploiement](../README.md) | [Retour à l'Index](../../README.md)

---

## Légende des invites de commande

Toutes les commandes de ce guide sont préfixées par un prompt simulé indiquant **où la commande doit être exécutée** :

| Prompt | Contexte |
|:---|:---|
| `[serveur-v3]$` | SSH sur le serveur hébergeant Pod V3 |
| `[serveur-v4]$` | SSH sur le serveur hébergeant Pod V4 (peut être le même que V3) |
| `[serveur-v5]$` | SSH sur le serveur hébergeant Pod V5 |
| `[conteneur-api]$` | À l'intérieur du conteneur Docker `pod-api` |
| `[local]$` | Votre machine locale (pour les rsync, scp, etc.) |

---

## Vue d'ensemble de la trajectoire de migration

La migration directe V3 → V5 **n'est pas possible** en une seule étape. La trajectoire obligatoire est :

```
Esup-Pod V3 (Django 3.2)
        │
        │  ÉTAPE 1 : Mise à jour du code & migrations Django
        ▼
Esup-Pod V4 (Django 4.2)    ← Intermédiaire OBLIGATOIRE
        │
        │  ÉTAPE 2 : Export des données via script
        ▼
 Fichier JSON d'export       ← v4_exported_to_v5.json
        │
        │  ÉTAPE 3 : Import dans la nouvelle stack V5
        ▼
Esup-Pod V5 (Django 5.2)    ← Architecture découplée (API Django + Frontend Next.js)
```

> [!IMPORTANT]
> **Pourquoi passer par la V4 ?**
> V5 est une **réécriture architecturale complète** (API REST Django + Frontend Next.js découplés). Le script d'export `export_data_from_v4.py` est conçu pour lire la structure de base de données V4 spécifiquement. La V3 a un schéma trop différent (tags, encodage, playlists) pour être exportée directement vers V5.

---

## Scénarios d'infrastructure et pièges associés

Avant de commencer, **identifiez votre scénario d'infrastructure**. Les pièges diffèrent selon l'organisation.

### Scénario A — Mono-serveur (V3 et V5 sur la même machine)

```
┌────────────────────────────────────────────────────────┐
│                    Serveur unique                       │
│                                                        │
│  Pod V3 (actif)  ──────────────►  Pod V5 (nouveau)    │
│  port 80 (nginx)                 port 8000 (api)       │
│  /srv/pod/media                  port 3000 (frontend)  │
└────────────────────────────────────────────────────────┘
```

**Pièges spécifiques :**

- ⚠️ **Conflit de ports** : V3 tourne sur le port 80. Nginx V5 doit être mis en place en parallèle, puis basculé. Planifiez une fenêtre de maintenance.
- ⚠️ **Conflit de nom de service systemd** : Si V3 utilise `uwsgi` ou `gunicorn` sur le port 8000, V5 entrera en conflit. Changez le port d'exposition V5 (`EXPOSITION_PORT=8001`) pendant la cohabitation.
- ⚠️ **`MEDIA_ROOT` partagé** : Le dossier des médias est utilisé par V3 et potentiellement monté dans Docker V5. Docker écrit en `root` par défaut — utilisez `USER_UID`/`USER_GID` dans `.env` pour aligner les droits.
- ⚠️ **Base de données partagée** : Ne pointez **jamais** V5 vers la base de données V3. V5 a un schéma totalement différent.

### Scénario B — Bi-serveur (V3 et V5 sur des machines séparées)

```
┌─────────────────┐         ┌─────────────────────────────┐
│   Serveur V3    │  rsync  │         Serveur V5           │
│   (ancien)      │ ──────► │                              │
│   /srv/media    │         │  Docker (API + DB + Redis)   │
│   MariaDB V3    │         │  Next.js                     │
└─────────────────┘         └─────────────────────────────┘
```

**Pièges spécifiques :**

- ⚠️ **Transfert des médias** : Plusieurs centaines de Go peuvent prendre des heures. Faites le transfert initial **avant** la fenêtre de maintenance, puis un rsync différentiel (`--checksum`) au moment de la bascule.
- ⚠️ **DNS / reverse proxy** : Pendant la transition, le DNS pointe encore vers V3. Préparez la configuration Nginx V5 en avance et basculez le DNS seulement quand V5 est validé.
- ⚠️ **Accès SSH entre serveurs** : Le rsync nécessite un accès SSH de V5 vers V3 (ou inversement). Assurez-vous que les clés SSH sont en place avant le jour J.

### Scénario C — Stockage médias partagé (NFS, Ceph, S3-compatible)

```
┌─────────────────┐         ┌─────────────────────────────┐
│   Serveur V3    │         │         Serveur V5           │
│                 │  ←────► │  Docker (API + DB + Redis)   │
│         ╲       │   NFS   │   ╱                          │
│          ╲      │         │  ╱                           │
└──────────────────────────────────────────────────────────┘
                   ┌────────▼───────┐
                   │  Stockage NFS  │
                   │  /srv/pod/media│
                   └────────────────┘
```

**Pièges spécifiques :**

- ⚠️ **Droits NFS dans Docker** : Le conteneur `pod-api` tourne avec un UID/GID. Si le montage NFS impose des droits différents (`nobody`, `root_squash`), les écritures échoueront silencieusement. Testez avant la migration :
  ```bash
  [conteneur-api]$ touch /app/media/test_write && echo "Droits OK" || echo "Droits insuffisants"
  ```
- ⚠️ **Latence NFS** : L'import avec `--verify-files` effectue des `stat()` sur chaque fichier média. Sur NFS, cela peut rendre l'import **extrêmement lent**. Faites d'abord l'import sans `--verify-files`, puis vérifiez séparément.
- ⚠️ **`MEDIA_PATH` dans le compose** : Le chemin du montage NFS doit être déclaré dans `MEDIA_PATH` du `.env`. Un chemin local non monté dans Docker rend tous les médias invisibles pour l'application.

### Scénario D — Serveur dédié encodage (Esup-Runner séparé)

V5 introduit **Esup-Runner Manager** pour l'encodage. Si vous avez un serveur d'encodage dédié :

**Pièges spécifiques :**

- ⚠️ **Le Runner doit accéder aux médias** : Esup-Runner lit les fichiers vidéo bruts. Son `STORAGE_DIR` doit pointer vers le même espace de stockage que `MEDIA_ROOT` de l'API.
- ⚠️ **Tokens d'authentification** : `RUNNER_TOKEN` (API → Runner) et `AUTHORIZED_TOKENS__*` (Runner → API webhook) doivent être cohérents entre les deux services.
- ⚠️ **`NOTIFY_URL_ALLOWED_HOSTS`** : Le Runner envoie des webhooks à l'API. Si l'API est derrière un reverse proxy, ajoutez le nom de domaine ou l'IP externe à cette liste.

---

## Prérequis

### Environnement cible (serveur V5)

| Composant | Version requise |
|:---|:---|
| Système d'exploitation | Debian 12 (Bookworm) ou équivalent |
| Python | **≥ 3.11** (uniquement pour exécuter le script d'export sur V4) |
| Docker | ≥ 24.x |
| Docker Compose | ≥ 2.x (plugin, `docker compose` sans tiret) |
| Node.js | ≥ 18.x (pour le build du frontend Next.js) |
| Nginx | ≥ 1.24 (reverse proxy) |
| Espace disque | Médias V3 × 1,2 (marge) + ~10 Go pour Docker volumes |

> [!NOTE]
> MariaDB et Redis ne sont **pas installés sur l'hôte** : ils tournent dans des conteneurs Docker. Pas besoin de les installer manuellement.

### Accès requis

- [ ] Accès SSH au serveur hébergeant Pod V3/V4
- [ ] Accès à la base de données MariaDB/MySQL de V3
- [ ] Accès `sudo` sur le serveur V5
- [ ] Sauvegarde complète de la BDD V3 avant toute opération
- [ ] Accès en lecture aux fichiers médias V3 (`MEDIA_ROOT`)

---

## Vue d'ensemble des différences majeures entre versions

| Aspect | V3 | V4 | V5 |
|:---|:---|:---|:---|
| Framework Django | 3.2 | 4.2 | 5.2 |
| Python minimum | 3.8 | 3.10 | 3.11 |
| Système de tags | `django-tagging` | `django-tagulous` | `django-tagulous` |
| Recherche full-text | Elasticsearch 6 | Elasticsearch 8 | **Redis Search** |
| Frontend | Templates Django | Templates Django | **Next.js découplé** |
| Chaînes/Thèmes/Playlists | apps séparées | apps séparées | **`collection` app** centralisée |
| Tâches d'encodage | Celery local | Celery local | **Esup-Runner Manager** |
| Auth API | Non | DRF Token | JWT (SimpleJWT) |
| Configuration | `settings_local.py` monolithique | `settings_local.py` monolithique | **Pydantic** + fichiers modulaires |

> [!WARNING]
> **Fonctionnalités non encore portées en V5** (à vérifier selon la version cible) :
> - Module `meeting` (BigBlueButton)
> - Module `live` (streaming)
> - Module `enrichment`
> - Intégration LTI
> - Notifications WebPush
>
> Si votre V3 utilise ces modules, vérifiez la [roadmap V5](https://github.com/EsupPortail/Pod_V5_Back/releases) avant de planifier la migration.

---

## ÉTAPE 1 : Migration V3 → V4

### 1.1 Sauvegarde obligatoire

> [!CAUTION]
> **NE JAMAIS SAUTER CETTE ÉTAPE.** Toute migration sans sauvegarde préalable est une prise de risque inacceptable en production.

```bash
[serveur-v3]$ cd /opt/pod  # Adaptez à votre répertoire d'installation

# Sauvegarde de la base de données
[serveur-v3]$ mysqldump -u <db_user> -p <db_name> > backup_podv3_$(date +%Y%m%d_%H%M).sql

# Vérifier que le dump est non vide
[serveur-v3]$ ls -lh backup_podv3_*.sql

# Sauvegarde des fichiers médias
[serveur-v3]$ tar -czf backup_media_v3_$(date +%Y%m%d).tgz /srv/pod/media/
```

> [!WARNING]
> Ne stockez pas les sauvegardes sur le même disque que la BDD. En cas de panne disque, vous perdez tout.

### 1.2 Prérequis de l'environnement V4

V4 requiert **Python ≥ 3.10** et **Django 4.2**. Vérifiez la version Python sur le serveur :

```bash
[serveur-v4]$ python3 --version
# Attendu : Python 3.10.x ou supérieur

# Si Python < 3.10, installez une version plus récente :
[serveur-v4]$ sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-dev
```

### 1.3 Procédure de mise à jour V3 → V4

> [!IMPORTANT]
> La procédure officielle complète est disponible sur : **https://esupportail.github.io/Esup-Pod/**
> Section : **Installation > Stand-alone upgrade** et **Migration V3 → V4**

```bash
# Passer Pod V3 en mode maintenance
[serveur-v3]$ cd /opt/pod/podv3
[serveur-v3]$ source venv/bin/activate
(venv) [serveur-v3]$ python manage.py shell -c \
    "from pod.main.models import Configuration; Configuration.objects.filter(key='maintenance_mode').update(value='1')"

# Récupérer le code V4 dans un nouveau répertoire (conserver V3 intact)
[serveur-v4]$ git clone https://github.com/EsupPortail/Esup-Pod.git /opt/pod/podv4
[serveur-v4]$ cd /opt/pod/podv4
[serveur-v4]$ git checkout tags/<version_v4_stable>  # ex: v4.2.x

# Créer un environnement virtuel dédié à V4
[serveur-v4]$ python3.11 -m venv venv
[serveur-v4]$ source venv/bin/activate

# Installer les dépendances V4
(venv) [serveur-v4]$ pip install -r requirements.txt

# Adapter votre settings_local.py V3 pour V4
# Changements obligatoires :
#   - Elasticsearch : ES_VERSION doit passer à 8
#   - django-cas-client  →  django-cas-ng  (USE_CAS, CAS_SERVER_URL restent inchangés)
#   - django-tagging     →  django-tagulous (automatique via migrate)
(venv) [serveur-v4]$ cp /opt/pod/podv3/pod/custom/settings_local.py \
                         /opt/pod/podv4/pod/custom/settings_local.py
# Éditez ensuite le fichier pour adapter ES_VERSION et autres changements

# Appliquer les migrations Django (V3 → V4)
(venv) [serveur-v4]$ python manage.py migrate

# Migration des tags : django-tagging → django-tagulous
# CRITIQUE : sans cette commande, les tags des vidéos seront perdus
(venv) [serveur-v4]$ python manage.py initial_migrate_tags

# Collecter les fichiers statiques
(venv) [serveur-v4]$ python manage.py collectstatic --noinput

# Redémarrer selon votre configuration (uwsgi, gunicorn, systemd...)
[serveur-v4]$ sudo systemctl restart pod-uwsgi
# OU
[serveur-v4]$ sudo supervisorctl restart pod
```

> [!NOTE]
> **Migration des tags V3 → V4** : V3 utilisait `django-tagging` (tables `tagging_tag` et `tagging_taggeditem`). V4 utilise `django-tagulous` (tables `video_tagulous_video_tags`, `video_video_tags`). Le script `export_data_from_v4.py` gère les deux cas — il inclut une compatibilité ascendante si les tables `tagging_*` sont encore présentes en base.

### 1.4 Vérification post-migration V4

```bash
(venv) [serveur-v4]$ python manage.py check --deploy

# Comparer les comptages avec V3 pour validation
(venv) [serveur-v4]$ python manage.py shell -c \
    "from pod.video.models import Video; print(Video.objects.count(), 'vidéos')"
(venv) [serveur-v4]$ python manage.py shell -c \
    "from django.contrib.auth.models import User; print(User.objects.count(), 'utilisateurs')"
```

> [!WARNING]
> Si les comptages ne correspondent pas à V3, **n'allez pas plus loin**. Revenez sur V3 (qui est toujours intact dans son répertoire) et analysez les erreurs de migration avant de continuer.

---

## ÉTAPE 2 : Export des données de V4 vers un fichier JSON

Cette étape se fait **depuis le serveur hébergeant Pod V4**.

### 2.1 Déployer le script d'export dans V4

Le script `export_data_from_v4.py` est fourni dans le dépôt Pod V5 (`src/apps/core/management/commands/`). Placez-le dans l'instance V4 :

```bash
# Option A : Télécharger depuis GitHub
[serveur-v4]$ curl -o /opt/pod/podv4/pod/video/management/commands/export_data_from_v4.py \
    https://raw.githubusercontent.com/EsupPortail/Pod_V5_Back/main/src/apps/core/management/commands/export_data_from_v4.py

# Option B : Si V5 est déjà cloné sur le même serveur
[serveur-v4]$ cp /opt/pod/podv5/api/src/apps/core/management/commands/export_data_from_v4.py \
                  /opt/pod/podv4/pod/video/management/commands/
```

> [!IMPORTANT]
> Le script vérifie que `VERSION` dans vos settings commence par `"4."`. Il échouera sur une instance V3 ou V5.
> Assurez-vous que `VERSION = "4.x.x"` est défini dans votre `settings_local.py` V4.

### 2.2 Lancer l'export

```bash
[serveur-v4]$ cd /opt/pod/podv4
[serveur-v4]$ source venv/bin/activate

(venv) [serveur-v4]$ python manage.py export_data_from_v4
```

**Sortie attendue :**
```
***Start export Pod4 database tables to a JSON file***
 - Pod version: 4.x.x. This script can be achieved with this Pod version. The process continues.
 - Create directory data if necessary
 - Table auth_user has been processed.
 - Table video_video has been processed.
 ...
 - The JSON file /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json was created.
```

**Tables exportées (principales) :**
- `auth_user`, `auth_group`, `auth_group_permissions`
- `authentication_owner`, `authentication_accessgroup`, `authentication_groupsite`
- `video_video`, `video_channel`, `video_theme`, `video_type`, `video_discipline`
- `video_video_tags`, `video_tagulous_video_tags` (tags Tagulous)
- `video_tagging_tag_2_tagulous` (si tables `tagging_*` legacy présentes)
- `completion_track`, `completion_contributor`, `completion_document`, `completion_overlay`
- `playlist_playlist`, `playlist_playlistcontent`
- `chapter_chapter`, `dressing_dressing`
- `recorder_*`, `meeting` (si modules actifs)

**Correction automatique appliquée lors de l'export :**
- Table `meeting` : Si `recurring_until <= start_at` (bug de fuseau horaire), la valeur est mise à `NULL` pour éviter une violation de contrainte en V5.

### 2.3 Localisation du fichier généré

Le fichier JSON est généré **deux niveaux au-dessus du `BASE_DIR`** du projet V4 :

```
BASE_DIR de V4 (ex: /opt/pod/podv4/pod)
        │
        └── ../../data_from_v4_to_v5/v4_exported_to_v5.json
            → /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json
```

```bash
# Vérifier l'emplacement et la taille (typiquement 500 Mo à 1 Go+)
[serveur-v4]$ ls -lh /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json
```

> [!TIP]
> Ce script peut être relancé autant de fois que nécessaire — le fichier JSON est entièrement régénéré à chaque exécution. C'est idéal pour faire des tests avant la bascule définitive.

### 2.4 Vérification du fichier exporté

```bash
# Valider le JSON et afficher un résumé des tables non vides
[serveur-v4]$ python3 -c "
import json
with open('/opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json') as f:
    data = json.load(f)
non_empty = {k: len(v) for k, v in data.items() if v}
for table, count in sorted(non_empty.items()):
    print(f'  {table}: {count} lignes')
print(f'Total tables non vides: {len(non_empty)}')
"
```

> [!WARNING]
> Si `video_video` retourne 0 lignes, votre `BASE_DIR` dans les settings V4 pointe peut-être vers une mauvaise base de données. Vérifiez `DATABASES` dans `settings_local.py`.

---

## ÉTAPE 3 : Installation et déploiement de Pod V5

### 3.1 Architecture de Pod V5

Pod V5 est une **architecture découplée** composée de deux applications indépendantes :

```
                    ┌─────────────────────────────────────────┐
                    │         Nginx (port 80 / 443)            │
                    │         Reverse Proxy + SSL              │
                    └──────┬──────────────────┬───────────────┘
                           │ /                │ /api/, /admin/,
                           │                  │ /media/, /static/
               ┌───────────▼────┐    ┌────────▼──────────────┐
               │  Next.js       │    │  Django API (Docker)   │
               │  port 3000     │    │  port 8000             │
               └───────────────┘    └────────┬──────────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
               ┌──────────▼──────┐  ┌───────▼────────┐  ┌─────▼────────────┐
               │  MariaDB        │  │  Redis Stack   │  │  Celery Worker   │
               │  (conteneur)    │  │  (conteneur)   │  │  (conteneur)     │
               └─────────────────┘  └────────────────┘  └──────────────────┘
```

Pour le détail de l'architecture Redis (4 bases isolées), voir [Deployment Overview](../README.md#redis-architecture).

### 3.2 Cloner les dépôts V5

```bash
[serveur-v5]$ mkdir -p /opt/pod/podv5
[serveur-v5]$ cd /opt/pod/podv5

# Backend (API Django)
[serveur-v5]$ git clone https://github.com/EsupPortail/Pod_V5_Back.git api
[serveur-v5]$ cd api && git checkout tags/<version_v5_stable> && cd ..

# Frontend (Next.js)
[serveur-v5]$ git clone https://github.com/EsupPortail/Esup-Pod-front.git front
[serveur-v5]$ cd front && git checkout tags/<version_v5_stable> && cd ..
```

### 3.3 Configuration du Backend (API Django)

#### 3.3.1 Fichier `.env` (Infrastructure & Secrets)

```bash
[serveur-v5]$ cd /opt/pod/podv5/api
[serveur-v5]$ cp .env.example .env
[serveur-v5]$ vim .env
```

```bash
# --- Django Core ---
DJANGO_SETTINGS_MODULE=config.django.dev.docker
SECRET_KEY=<générer avec: python3 -c "import secrets; print(secrets.token_hex(50))">
VERSION=5.0.0
EXPOSITION_PORT=8000

# --- Base de données (gérée par Docker) ---
MYSQL_DATABASE=pod_db
MYSQL_USER=pod_user
MYSQL_PASSWORD=<mot-de-passe-fort>
MYSQL_ROOT_PASSWORD=<mot-de-passe-root-fort>
MYSQL_HOST=db        # Nom du service Docker — NE PAS CHANGER
MYSQL_PORT=3306      # Port interne Docker — NE PAS CHANGER

# --- Admin initial ---
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@votre-universite.fr
DJANGO_SUPERUSER_PASSWORD=<mot-de-passe-admin-fort>

# --- Droits du conteneur (aligner avec les droits des médias sur l'hôte) ---
# Récupérez votre UID/GID : id -u && id -g
USER_UID=1000
USER_GID=1000

# --- Redis ---
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
REDIS_CACHE_URL=redis://redis:6379/1
REDIS_SESSION_URL=redis://redis:6379/2

# --- Médias (adapter à votre infrastructure) ---
# Scénario A (mono-serveur, chemin local) :
MEDIA_PATH=/srv/pod/media
# Scénario C (NFS, point de montage) :
# MEDIA_PATH=/mnt/nfs-pod/media

# --- URL publique du site ---
SITE_URL=https://pod.votre-universite.fr

# --- CAS (si utilisé) ---
# CAS_SERVER_URL=https://cas.votre-universite.fr/

# --- CORS (si frontend et API sur domaines différents) ---
# CORS_ALLOWED_ORIGINS=https://front.votre-universite.fr
```

> [!WARNING]
> `MYSQL_HOST=db` est le **nom du service Docker**, pas `localhost`. Ne le modifiez pas sauf si vous changez aussi le nom du service dans le `docker-compose.yml`.

#### 3.3.2 Configuration des fonctionnalités (Feature Flags)

V5 remplace `settings_local.py` par des **fichiers Python modulaires** validés par Pydantic dans `src/config/settings/`. Pour plus de détails, voir le [Configuration Guide](../../configuration.md).

**Correspondance des paramètres V3/V4 → V5 :**

| Paramètre V3/V4 | Fichier V5 | Paramètre V5 |
|:---|:---|:---|
| `USE_CAS = True` + `CAS_SERVER_URL` | `.env` | `CAS_SERVER_URL=https://...` |
| `ES_URL`, `ES_VERSION` | N/A | Supprimé — remplacé par Redis Search (`SEARCH_REDIS_URL`) |
| `TEMPLATE_VISIBLE_SETTINGS` | `settings/core.py` | Variables individuelles |
| `USE_PODFILE = True` | N/A | Supprimé (système intégré) |
| `THIRD_PARTY_APPS` | N/A | Apps intégrées nativement |
| `USE_MEETING` | N/A | Non porté (vérifier roadmap) |
| `MEDIA_ROOT` | `.env` | `MEDIA_PATH=/srv/pod/media` |
| `MAX_UPLOAD_SIZE_GB` | `settings/video.py` | `MAX_UPLOAD_SIZE_GB = 10` |
| `USE_STATS_VIEW` | `settings/video.py` | `USE_STATS_VIEW = True` |
| `CAS_FORCE_LOWERCASE_USERNAME` | `settings/authentication.py` | `CAS_FORCE_CHANGE_USERNAME_CASE = "lower"` |

### 3.4 Démarrer l'infrastructure V5 (Docker)

```bash
[serveur-v5]$ cd /opt/pod/podv5/api

# Construire et démarrer tous les services
[serveur-v5]$ make start

# Vérifier que tous les conteneurs sont en santé
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml ps

# Surveiller les logs au démarrage (attendre que l'API soit prête)
[serveur-v5]$ make logs
```

> [!NOTE]
> Le conteneur `pod-api` attend que `pod-db` soit **healthy** avant de démarrer. Si MariaDB prend du temps à initialiser (première exécution), patientez 30 à 60 secondes avant de consulter les logs.

### 3.5 Vérifier l'initialisation de la base de données

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash

[conteneur-api]$ python manage.py showmigrations | grep '\[ \]'
# Si des migrations sont listées (non appliquées) :
[conteneur-api]$ python manage.py migrate

[conteneur-api]$ python manage.py ensure_superuser
[conteneur-api]$ exit
```

---

## ÉTAPE 4 : Import des données V4 dans V5

### 4.1 Transférer le fichier JSON vers le serveur V5

```bash
# Depuis le serveur V4, pousser vers V5
[serveur-v4]$ rsync -avz --progress \
    /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json \
    user@serveur-v5:/opt/pod/data_from_v4_to_v5/

# OU depuis le serveur V5, tirer depuis V4
[serveur-v5]$ mkdir -p /opt/pod/data_from_v4_to_v5
[serveur-v5]$ rsync -avz --progress \
    user@serveur-v4:/opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json \
    /opt/pod/data_from_v4_to_v5/
```

### 4.2 Rendre le fichier accessible dans le conteneur Docker

Le script cherche par défaut `.tmp/v4_exported_to_v5.json` (relatif à `/app` dans le conteneur).

```bash
[serveur-v5]$ cd /opt/pod/podv5/api
[serveur-v5]$ mkdir -p .tmp

# Option A : Copie simple
[serveur-v5]$ cp /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json .tmp/

# Option B : Lien symbolique (évite la duplication si fichier volumineux)
# Attention : le chemin cible doit aussi être accessible depuis le conteneur
[serveur-v5]$ ln -s /opt/pod/data_from_v4_to_v5/v4_exported_to_v5.json .tmp/v4_exported_to_v5.json
```

### 4.3 Test à blanc (DRY-RUN) — Fortement recommandé

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash

[conteneur-api]$ python manage.py import_data_from_v4_to_v5 --dry-run
# La transaction est annulée en fin de dry-run : aucun changement n'est écrit en BDD

[conteneur-api]$ exit
```

Vérifiez attentivement la sortie pour détecter des erreurs (`ERROR`) avant l'import réel.

### 4.4 Import réel des données

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash

# Import standard
[conteneur-api]$ python manage.py import_data_from_v4_to_v5

# Import avec chemin explicite vers le JSON
[conteneur-api]$ python manage.py import_data_from_v4_to_v5 \
    --file /app/.tmp/v4_exported_to_v5.json

# Import avec vérification physique des médias (déconseillé sur NFS, voir Scénario C)
[conteneur-api]$ python manage.py import_data_from_v4_to_v5 --verify-files

# Import avec batch réduit (si erreurs de mémoire)
[conteneur-api]$ python manage.py import_data_from_v4_to_v5 --batch-size 200

[conteneur-api]$ exit
```

**Arguments disponibles :** voir [Maintenance & Management Commands](../../core/details.md#3-migration--import_data_from_v4_to_v5)

**Ordre d'import du script :**
1. Sites Django → Utilisateurs + Owners + Groupes
2. Types, Disciplines, Chaînes, Thèmes, Blocs
3. Tags vidéo → Vidéos avec métadonnées
4. Playlists + contenus → Commentaires, Votes, ViewCounts
5. Relations ManyToMany → Sous-titres, vidéos encodées

> [!NOTE]
> **Reprise sur erreur** : Le script utilise une table `core_migrationmapping` pour suivre les enregistrements déjà migrés. En cas d'interruption, relancez la commande : elle reprendra là où elle s'est arrêtée.

### 4.5 Vérification post-import

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash

[conteneur-api]$ python manage.py shell -c "
from django.contrib.auth.models import User
from src.apps.video.models import Video
from src.apps.collection.models import Channel, Theme
print(f'Utilisateurs : {User.objects.count()}')
print(f'Vidéos       : {Video.objects.count()}')
print(f'Chaînes      : {Channel.objects.count()}')
print(f'Thèmes       : {Theme.objects.count()}')
"

[conteneur-api]$ exit
```

Comparez ces chiffres avec ceux de V4 (étape 1.4). Tout écart significatif mérite investigation avant de continuer.

---

## ÉTAPE 5 : Actions post-migration

### 5.1 Transférer les fichiers médias

Commencez le transfert **bien avant** la fenêtre de maintenance :

```bash
# Transfert initial (peut durer des heures selon le volume)
[serveur-v5]$ rsync -avz --progress \
    user@serveur-v4:/srv/pod/media/ \
    /srv/pod/media/

# Au moment de la bascule : synchronisation différentielle (rapide)
[serveur-v5]$ rsync -avz --checksum \
    user@serveur-v4:/srv/pod/media/ \
    /srv/pod/media/
```

```bash
# Vérifier que les médias sont bien montés dans le conteneur
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash
[conteneur-api]$ ls /app/media/
# Si vide : vérifier MEDIA_PATH dans .env et redémarrer les conteneurs
[conteneur-api]$ exit
```

### 5.2 Reconstruire l'index de recherche Redis Search

V5 remplace Elasticsearch par Redis Search. L'index doit être entièrement reconstruit après l'import :

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api \
    python manage.py reindex_videos --drop
```

> [!WARNING]
> `--drop` supprime l'index existant avant de le recréer. **Pendant la réindexation, la recherche retourne zéro résultat.** Planifiez cette opération en dehors des heures de pointe.

### 5.3 Préchauffer le cache

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api \
    python manage.py warm_cache
```

### 5.4 Valider la configuration

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash

[conteneur-api]$ python manage.py validate_config
[conteneur-api]$ python manage.py comparesettings

[conteneur-api]$ exit
```

### 5.5 Changer le mot de passe admin par défaut

> [!CAUTION]
> Si aucun superutilisateur V4 n'a été importé, le script crée `admin` avec le mot de passe défini dans `DJANGO_SUPERUSER_PASSWORD` (ou `admin` par défaut). **Changez ce mot de passe immédiatement !**

```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml exec api bash
[conteneur-api]$ python manage.py changepassword admin
[conteneur-api]$ exit
```

---

## ÉTAPE 6 : Configuration du Frontend Next.js

### 6.1 Variables d'environnement frontend

```bash
[serveur-v5]$ cd /opt/pod/podv5/front
[serveur-v5]$ cp env.example .env
[serveur-v5]$ vim .env
```

```bash
# URL de l'API backend (accessible depuis le navigateur des utilisateurs)
NEXT_PUBLIC_API_URL=https://pod.votre-universite.fr

# URL publique du site
NEXT_PUBLIC_BASE_URL=https://pod.votre-universite.fr
```

> [!IMPORTANT]
> **Piège CORS** : Si le frontend et l'API sont sur des origines différentes (domaines, sous-domaines ou ports distincts), configurez CORS dans `.env` de l'API :
> ```bash
> CORS_ALLOWED_ORIGINS=https://front.votre-universite.fr
> ```
> Si Nginx sert les deux sur le même domaine, aucune configuration CORS n'est nécessaire.

### 6.2 Build et démarrage du Frontend (production)

```bash
[serveur-v5]$ cd /opt/pod/podv5/front

# Installer les dépendances
[serveur-v5]$ corepack yarn install

# Générer le thème Cunningham
[serveur-v5]$ corepack yarn build-theme

# Build de production Next.js
[serveur-v5]$ corepack yarn build

# Démarrage robuste avec pm2 (recommandé en production)
[serveur-v5]$ npm install -g pm2
[serveur-v5]$ pm2 start "corepack yarn start -p 3000" --name pod-frontend
[serveur-v5]$ pm2 save && pm2 startup

# Alternativement, démarrage simple :
[serveur-v5]$ nohup corepack yarn start -p 3000 > frontend.log 2>&1 &
```

---

## ÉTAPE 7 : Configuration Nginx

### 7.1 Configuration de base

```bash
[serveur-v5]$ sudo cp /opt/pod/podv5/pod_v5_nginx.conf \
    /etc/nginx/sites-available/pod-v5

# Adapter les valeurs obligatoires dans le fichier :
[serveur-v5]$ sudo vim /etc/nginx/sites-available/pod-v5
```

Valeurs à adapter :

```nginx
server_name pod.votre-universite.fr;       # Votre FQDN

location /media/ {
    alias /srv/pod/media/;                  # Votre MEDIA_ROOT
}
location /static/ {
    alias /opt/pod/podv5/api/staticfiles/;  # Votre STATIC_ROOT
}
```

```bash
[serveur-v5]$ sudo ln -s /etc/nginx/sites-available/pod-v5 \
                          /etc/nginx/sites-enabled/
[serveur-v5]$ sudo nginx -t
[serveur-v5]$ sudo systemctl reload nginx
```

**Routes configurées :**

| Route | Destination | Notes |
|:---|:---|:---|
| `/` | Next.js `:3000` | Frontend SPA |
| `/api/` | Django `:8000` | API REST |
| `/admin/` | Django `:8000` | Interface Django Admin |
| `/media/` | Fichier système | Médias publics |
| `/static/` | Fichier système | Statiques Django |
| `/protected_media/` | `internal` (X-Accel-Redirect) | Vidéos protégées |

### 7.2 HTTPS (obligatoire en production)

```bash
[serveur-v5]$ sudo apt install certbot python3-certbot-nginx
[serveur-v5]$ sudo certbot --nginx -d pod.votre-universite.fr
```

> [!IMPORTANT]
> Le header `Strict-Transport-Security` est inclus dans la configuration Nginx fournie. Ne l'activez qu'une fois HTTPS configuré, sous peine de rendre le site inaccessible en HTTP.

---

## ÉTAPE 8 : Supervision et maintenance

### 8.1 Commandes de maintenance courantes

Pour la référence complète, voir [Maintenance & Management Commands](../../core/details.md).

```bash
[serveur-v5]$ docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml \
    exec api bash

# Reconstruire l'index de recherche
[conteneur-api]$ python manage.py reindex_videos --drop

# Préchauffer le cache
[conteneur-api]$ python manage.py warm_cache

# Vérifier/créer le superutilisateur
[conteneur-api]$ python manage.py ensure_superuser

# Valider la configuration Pydantic
[conteneur-api]$ python manage.py validate_config

[conteneur-api]$ exit
```

### 8.2 Logs

```bash
# Logs de tous les services Docker
[serveur-v5]$ docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml logs -f

# Logs d'un service spécifique
[serveur-v5]$ docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml logs -f api

# Logs du frontend
[serveur-v5]$ pm2 logs pod-frontend
```

### 8.3 Crons recommandés

```cron
# Préchauffage du cache toutes les 10 minutes
*/10 * * * * docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml exec -T api python manage.py warm_cache >> /var/log/pod/warm_cache.log 2>&1

# Sauvegarde quotidienne de la BDD à 2h
0 2 * * * docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml exec -T db mysqldump -u pod_user -ppod_password pod_db | gzip > /backup/pod_v5_$(date +\%Y\%m\%d).sql.gz
```

---

## Vérification finale complète

```bash
# ✅ Check 1 : API Django répond
[serveur-v5]$ curl -sf http://localhost:8000/api/ -o /dev/null \
    && echo "✅ API OK" || echo "❌ API non accessible"

# ✅ Check 2 : Frontend répond
[serveur-v5]$ curl -sf http://localhost:3000 -o /dev/null \
    && echo "✅ Frontend OK" || echo "❌ Frontend non accessible"

# ✅ Check 3 : Nginx répond via le domaine public
[serveur-v5]$ curl -sf https://pod.votre-universite.fr -o /dev/null \
    && echo "✅ Nginx OK" || echo "❌ Nginx KO"

# ✅ Check 4 : Comptage des vidéos importées
[serveur-v5]$ docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml \
    exec api python manage.py shell -c \
    "from src.apps.video.models import Video; print(f'✅ {Video.objects.count()} vidéos')"

# ✅ Check 5 : Redis cache fonctionnel
[serveur-v5]$ docker compose -f /opt/pod/podv5/api/deployment/dev/docker-compose.yml \
    exec api python manage.py shell -c \
    "from django.core.cache import cache; cache.set('test','1'); \
    print('✅ Redis OK' if cache.get('test') else '❌ Redis KO')"

# ✅ Check 6 : Nginx config valide
[serveur-v5]$ sudo nginx -t && echo "✅ Nginx config OK"
```

---

## Résolution des problèmes courants

### ❌ `VERSION` check échoue dans `export_data_from_v4.py`

**Symptôme :** `This script can only be used for Pod version 4.x.`

**Solution :** Vérifiez `settings_local.py` V4 :
```python
VERSION = "4.x.x"  # Doit commencer par "4."
```

### ❌ Erreur `Table does not exist` lors de l'import

**Symptôme :** Import échoue sur une table manquante.

**Solution :** La BDD V5 n'est pas initialisée.
```bash
[conteneur-api]$ python manage.py migrate
```

### ❌ Tags non importés

**Symptôme :** Vidéos importées sans tags.

**Solution :** Vérifiez que `initial_migrate_tags` a été exécuté en V4 (étape 1.3). Vérifiez dans le JSON que `video_tagulous_video_tags` ou `video_video_tags` contient des données.

### ❌ Médias invisibles après migration

**Symptôme :** Vignettes et vidéos non affichées.

**Solution :**
```bash
[conteneur-api]$ ls /app/media/
# Si vide : vérifier MEDIA_PATH dans .env puis redémarrer les conteneurs

[serveur-v5]$ grep MEDIA_PATH /opt/pod/podv5/api/.env
[serveur-v5]$ stat /srv/pod/media
```

### ❌ Recherche renvoie zéro résultat

**Solution :**
```bash
[conteneur-api]$ python manage.py reindex_videos --drop
[conteneur-api]$ python manage.py warm_cache --clear-only
```

### ❌ CORS error dans le navigateur

**Symptôme :** `Access-Control-Allow-Origin` manquant.

**Solution :** Ajoutez dans `.env` de l'API :
```bash
CORS_ALLOWED_ORIGINS=https://front.votre-universite.fr
```
Si Nginx sert les deux sur le même domaine, pas de CORS nécessaire.

### ❌ Conteneur API ne démarre pas (erreur BDD)

**Symptôme :** `django.db.OperationalError: Can't connect to MySQL server on 'db'`

**Solution :** MariaDB n'est pas encore prêt.
```bash
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml ps pod-db
[serveur-v5]$ docker compose -f deployment/dev/docker-compose.yml logs db
```

### ❌ Erreur de contrainte `recurring_until`

**Symptôme :** Violation de contrainte sur la table `meeting`.

**Solution :** Le script `export_data_from_v4.py` corrige automatiquement cette valeur. Assurez-vous d'utiliser la version la plus récente du script (téléchargée depuis le dépôt Pod V5).

---

## Références

- **Documentation officielle V4** : https://esupportail.github.io/Esup-Pod/
- **GitHub Esup-Pod (V4)** : https://github.com/EsupPortail/Esup-Pod
- **GitHub Pod V5 Backend** : https://github.com/EsupPortail/Pod_V5_Back
- **GitHub Pod V5 Frontend** : https://github.com/EsupPortail/Esup-Pod-front
- **Script d'export V4** : [`src/apps/core/management/commands/export_data_from_v4.py`](../../src/apps/core/management/commands/export_data_from_v4.py)
- **Script d'import V5** : [`src/apps/core/management/commands/import_data_from_v4_to_v5.py`](../../src/apps/core/management/commands/import_data_from_v4_to_v5.py)
- **Guide migration V4 → V5** : [migration_v4_to_v5_fr.md](migration_v4_to_v5_fr.md)
- **Guide déploiement V5** : [Deployment Overview](../README.md)
- **Configuration guide** : [configuration.md](../../configuration.md)
- **Commandes de maintenance** : [core/details.md](../../core/details.md)
