# 🔍 Stack Overflow Scraper & Analyzer

Un outil complet d'extraction et d'analyse de données Stack Overflow avec support dual (Web Scraping + API) et système d'analyse avancé.

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnement Complet du Pipeline](#-fonctionnement-complet-du-pipeline)
- [Fonctionnalités](#-fonctionnalités)
- [Installation](#-installation)
- [Structure du projet](#-structure-du-projet)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Base de données](#-base-de-données)
- [Analyse et rapports](#-analyse-et-rapports)
- [Tests](#-tests)
- [Utilitaires](#-utilitaires)
- [Dépannage](#-dépannage)

## 🎯 Vue d'ensemble

Le Stack Overflow Scraper est un système complet qui permet de :

1. **Extraire** des données de Stack Overflow (via API ou scraping web)
2. **Stocker** intelligemment en MongoDB avec gestion des doublons
3. **Analyser** les tendances, sentiments et patterns
4. **Générer** des rapports détaillés automatiquement

### Workflow principal

```
Extraction → Stockage → Analyse → Rapport
     ↓           ↓        ↓         ↓
  Questions   MongoDB   Trends   Reports
```

## 🔄 Fonctionnement Complet du Pipeline

### Vue d'ensemble du système

Le Stack Overflow Scraper & Analyzer exécute un pipeline en **3 phases principales** avec génération automatique de rapports :

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  📥 PHASE 1     │    │  💾 PHASE 2     │    │  📊 PHASE 3     │    │  📄 RAPPORT     │
│  EXTRACTION     │───▶│  STOCKAGE       │───▶│  ANALYSE        │───▶│  GÉNÉRATION     │
│                 │    │                 │    │                 │    │                 │
│ • API/Scraping  │    │ • Filtering     │    │ • NLP           │    │ • Markdown      │
│ • Parsing       │    │ • Upsert/Insert │    │ • Trends        │    │ • JSON Export   │
│ • Validation    │    │ • Author Mgmt   │    │ • Statistics    │    │ • Metrics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 📥 PHASE 1 : Extraction des Données

#### 🔍 Sources d'extraction disponibles

**1. API Stack Overflow (Recommandé)**
```bash
python main.py --use-api -n 1000
```
- **Avantages** : Rapide (15s pour 1000 questions), fiable, données structurées
- **Limitations** : 10k requêtes/jour sans clé API, 300 requêtes/jour avec clé gratuite
- **Technique** : Requêtes HTTPS vers `api.stackexchange.com`
- **Format** : JSON direct, pas de parsing HTML nécessaire

**2. Web Scraping (Selenium)**
```bash
python main.py -n 1000  # Mode par défaut
```
- **Avantages** : Illimité, contourne les quotas API
- **Limitations** : Plus lent (60s pour 1000 questions), dépendant du navigateur
- **Technique** : Chrome headless avec Selenium WebDriver
- **Format** : HTML parsing avec BeautifulSoup

#### 📊 Structure des données extraites

Chaque question extraite contient :

```python
QuestionData {
    question_id: int,           # ID unique Stack Overflow
    title: str,                 # Titre de la question
    url: str,                  # URL complète
    summary: str,              # Contenu/corps de la question
    tags: List[str],           # Technologies associées
    author_name: str,          # Nom de l'auteur
    author_profile_url: str,   # Profil de l'auteur
    author_reputation: int,    # Points de réputation
    view_count: int,           # Nombre de vues
    vote_count: int,           # Score (votes up - votes down)
    answer_count: int,         # Nombre de réponses
    publication_date: datetime # Date de publication
}
```

#### 🎯 Filtrage et ciblage

**Filtrage par tags :**
```bash
# Technologies spécifiques
python main.py -t python javascript react -n 1500

# Domaines spécialisés  
python main.py -t "machine-learning" "data-science" -n 800
```

**Logique d'extraction :**
1. Récupération des questions les plus récentes par défaut
2. Filtrage par tags si spécifiés (opérateur OR entre les tags)
3. Parsing et validation des données
4. Enrichissement avec métadonnées d'auteur

### 💾 PHASE 2 : Stockage Intelligent

#### 🗄️ Architecture de stockage

**Base MongoDB avec 3 collections :**

```
stackoverflow_data/
├── questions    (Collection principale - documents de questions)
├── authors      (Métadonnées des auteurs avec agrégations)
└── analysis     (Résultats d'analyses sauvegardés)
```

#### 🔄 Modes de stockage intelligents

**1. Mode `update` (défaut)**
```bash
python main.py --mode update
```
- **Comportement** : Upsert MongoDB avec `question_id` comme clé
- **Logic** : Met à jour les questions existantes ET ajoute les nouvelles
- **Usage** : Maintenance quotidienne, actualisation des métriques
- **Technique** : `db.questions.replaceOne({question_id: X}, data, {upsert: true})`

**2. Mode `append-only`**
```bash
python main.py --mode append-only
```
- **Comportement** : Filtre les doublons AVANT insertion
- **Logic** : Insère seulement les questions avec des `question_id` non-existants
- **Usage** : Collecte initiale, enrichissement sans doublons
- **Technique** : `existing_ids = db.questions.distinct('question_id')` puis filtrage

#### 👥 Gestion intelligente des auteurs

**Tracking automatique des auteurs :**

```python
# Logique de gestion des auteurs lors du stockage
for question in new_questions:
    author_result = store_author(question.author_data)
    # Retourne : 'new', 'updated', ou 'skipped'
    
    if author_result == 'new':
        authors_new += 1
    elif author_result == 'updated':  
        authors_updated += 1
```

**Collection `authors` mise à jour automatiquement :**
- `question_count` : Nombre de questions de cet auteur dans notre base
- `first_seen` / `last_seen` : Dates de première et dernière question collectée
- `reputation` : Mise à jour si elle a changé

#### 📈 Métriques de stockage retournées

```python
storage_result = {
    'questions_stored': 245,    # Nouvelles questions ajoutées
    'authors_new': 12,          # Nouveaux auteurs découverts  
    'authors_updated': 67,      # Auteurs avec réputation mise à jour
    'execution_time': 2.45      # Temps de stockage en secondes
}
```

### 📊 PHASE 3 : Analyse et Intelligence

#### 🎯 Portées d'analyse configurables

**1. Analyse complète (`--analysis-scope all`)**
```bash
python main.py --analysis-scope all
```
- **Données** : TOUTES les questions présentes dans la base
- **Usage** : Tendances globales, vision d'ensemble complète
- **Performance** : Plus lent mais exhaustif
- **Résultat** : Analyse de 5000+ questions si base importante

**2. Analyse ciblée (`--analysis-scope new-only`)**
```bash
python main.py --analysis-scope new-only
```
- **Données** : Seulement les questions traitées lors de cette exécution
- **Usage** : Analyse rapide des nouveautés, optimisation performance
- **Performance** : Très rapide, adapté aux mises à jour fréquentes
- **Logique intelligente** : Annulation automatique si aucune nouvelle question

#### 🧠 Moteurs d'analyse spécialisés

**1. NLP Processor (Analyse de contenu)**

```python
# Analyses effectuées sur titles, summaries, et contenu combiné
nlp_analysis = {
    'keywords_extraction': {
        'title_keywords': tfidf_analysis(titles),
        'summary_keywords': tfidf_analysis(summaries), 
        'combined_keywords': tfidf_analysis(titles + summaries)
    },
    'sentiment_analysis': {
        'title_sentiment': textblob_analysis(titles),
        'summary_sentiment': textblob_analysis(summaries),
        'combined_sentiment': textblob_analysis(combined_content)
    },
    'content_quality': {
        'summary_completeness': percentage_with_substantial_content,
        'technical_richness': technical_terms_ratio,
        'question_clarity': well_structured_questions_ratio
    }
}
```

**2. Trend Analyzer (Analyse des tendances)**

```python
# Calculs de croissance et détection des tendances
trend_analysis = {
    'tag_trends': {
        'growth_calculation': (last_week_count / previous_week_count - 1) * 100,
        'trending_detection': growth_rate > threshold,
        'temporal_distribution': questions_per_time_period
    },
    'temporal_patterns': {
        'hourly_activity': peak_detection_by_hour,
        'daily_patterns': weekday_vs_weekend_analysis,
        'seasonal_trends': monthly_activity_analysis
    }
}
```

**3. Author Analyzer (Analyse des contributeurs)**

```python
# Statistiques sur les auteurs correspondant aux questions analysées
author_analysis = {
    'active_contributors': top_authors_by_question_count,
    'reputation_distribution': reputation_statistics,
    'activity_correlation': author_activity_vs_question_quality,
    'engagement_metrics': response_rates_by_author_tier
}
```

#### 📊 Analyses statistiques avancées

**Métriques calculées automatiquement :**

```python
comprehensive_stats = {
    'general_metrics': {
        'total_questions_analyzed': len(questions),
        'date_range': (earliest_date, latest_date),
        'avg_views_per_question': mean(view_counts),
        'response_rate': percentage_with_answers,
        'vote_distribution': score_statistics
    },
    'technical_metrics': {
        'tags_diversity': unique_tags_count,
        'complexity_indicators': technical_depth_analysis,
        'problem_categories': automated_categorization
    },
    'trend_metrics': {
        'growth_technologies': fastest_growing_tags,
        'declining_technologies': tags_with_negative_growth,
        'stability_index': technology_maturity_indicator
    }
}
```

### 📄 Génération Automatique de Rapports

#### 📝 Rapports Markdown (toujours générés)

**Structure standardisée :**

```markdown
# 📊 RAPPORT COMPLET - STACK OVERFLOW SCRAPER & ANALYZER

## 🚀 INFORMATIONS D'EXÉCUTION GÉNÉRALE
- Configuration utilisée et commande équivalente
- Résumé des phases avec durées et statuts

## 🔍 PHASE 1: EXTRACTION DES DONNÉES  
- Métriques d'extraction (taux, questions/sec)
- Source utilisée (API/Scraping) et paramètres

## 💾 PHASE 2: STOCKAGE EN BASE DE DONNÉES
- Opérations de stockage détaillées
- Gestion intelligente des auteurs (nouveaux/mis à jour)
- Gestion des doublons et mode de stockage

## 📊 PHASE 3: ANALYSE DES DONNÉES
- Configuration d'analyse (scope, durée, période couverte)
- Résultats détaillés par catégorie (si analyse effectuée)
- Ou statut d'analyse (désactivée/annulée) avec recommandations
```

**Gestion intelligente des statuts :**

1. **✅ Analyse complète** : Toutes les sections présentes avec données
2. **❌ Analyse désactivée** : Message explicatif avec suggestion
3. **⚠️ Analyse annulée** : Explication intelligente de l'optimisation

#### 🔄 Exports JSON (données structurées)

```python
# Sauvegarde dans output/analysis/
analysis_export = {
    'metadata': {
        'analysis_date': iso_timestamp,
        'total_questions_analyzed': count,
        'analysis_duration_seconds': duration,
        'scope': 'all' | 'new-only',
        'date_range': {'start': date1, 'end': date2}
    },
    'results': {
        'tag_trends': detailed_trend_data,
        'temporal_patterns': time_analysis_data,
        'content_analysis': nlp_results,
        'author_analysis': contributor_stats,
        'general_stats': comprehensive_metrics
    }
}
```

### 🔧 Logique Intelligente et Optimisations

#### 🧠 Décisions automatiques du système

**1. Optimisation des analyses**
```python
# Annulation intelligente pour performance
if analysis_scope == 'new-only' and questions_stored == 0:
    return "Analyse annulée - aucune nouvelle question"
    
# Limitation automatique des ressources  
if questions_count > 10000:
    enable_sampling = True
    log_warning("Large dataset - échantillonnage activé")
```

**2. Gestion des erreurs et récupération**
```python
# Retry automatique avec backoff
try:
    api_response = call_stackoverflow_api()
except RateLimitError:
    if retries < max_retries:
        sleep(exponential_backoff(retries))
        retry_request()
    else:
        fallback_to_web_scraping()
```

**3. Monitoring des performances**
```python
# Métriques de performance automatiques
execution_metrics = {
    'extraction_rate': questions_extracted / extraction_time,
    'storage_rate': questions_stored / storage_time, 
    'analysis_rate': questions_analyzed / analysis_time,
    'total_pipeline_duration': end_time - start_time
}
```

#### ⚡ Optimisations de performance

**Extraction :**
- Pool de connexions HTTP pour l'API
- Rate limiting intelligent avec respect des quotas
- Mise en cache des métadonnées d'auteurs

**Stockage :**
- Opérations bulk MongoDB pour les insertions
- Index optimisés pour les requêtes fréquentes
- Transactions pour la cohérence des données

**Analyse :**
- Vectorisation NumPy pour les calculs TF-IDF
- Multiprocessing pour l'analyse de sentiment
- Mise en cache des résultats coûteux

### 🎯 Workflows Types d'Utilisation

#### 🚀 **Collecte initiale complète**
```bash
# Nettoyage et collecte massive par technologie
python utils/clear_database.py
python main.py --use-api -n 2500 -t python --mode append-only
python main.py --use-api -n 1500 -t javascript --mode append-only
python main.py --use-api -n 1000 -t react vue.js --mode append-only
# Résultat : Base riche de ~5000 questions sans doublons
```

#### 🔄 **Maintenance quotidienne**
```bash
# Mise à jour avec nouvelles questions + analyse complète
python main.py --use-api -n 500 --mode update --analysis-scope all
# Résultat : Base actualisée + rapport de tendances globales
```

#### ⚡ **Analyse rapide des nouveautés**
```bash
# Collecte + analyse optimisée des nouveautés seulement
python main.py --use-api -n 300 --mode append-only --analysis-scope new-only
# Résultat : Nouvelles données + analyse rapide ciblée
```

#### 🎯 **Enrichissement ciblé**
```bash
# Technologies émergentes sans analyse immédiate
python main.py --use-api -n 500 -t "machine-learning" --mode append-only --no-analysis
# Suivi par analyse complète périodique
python main.py --analysis-scope all --no-extraction
```

### 📊 Métriques et Monitoring

Le système fournit automatiquement des métriques détaillées à chaque exécution :

```
📊 Exemple de métriques d'exécution
═══════════════════════════════════════════════════════════════

🔍 Extraction    : 245 questions en 15.2s (16.1 questions/sec)
💾 Stockage      : 187 nouvelles + 12 auteurs (2.1s, 94.3 op/sec) 
📊 Analyse       : 2,847 questions analysées en 8.7s
📄 Rapport       : Generated in output/reports/rapport_complet_*.md

👥 Auteurs       : 12 nouveaux, 45 mis à jour, 67 inchangés
🏷️ Technologies : 156 tags uniques, Python (23%), JS (18%), React (12%)
📈 Tendances     : React (+89%), TypeScript (+156%), Vue.js (+67%)
⏰ Performance   : Pipeline complet en 26.0s (9.4 questions/sec)
```

Ce pipeline complet assure une collecte intelligente, un stockage optimisé et une analyse approfondie des données Stack Overflow avec une surveillance continue des performances et une adaptation automatique aux différents cas d'usage.

## ✨ Fonctionnalités

### 🔍 Extraction de données
- **API Stack Overflow** : Extraction rapide et fiable (10k requêtes/jour gratuit)
- **Web Scraping** : Extraction via Selenium pour contournement des limites
- **Filtrage par tags** : Ciblage précis des technologies
- **Gestion des quotas** : Respect automatique des limites de l'API

### 💾 Stockage intelligent
- **Base MongoDB** : Stockage NoSQL optimisé avec index
- **Modes de stockage** : `update` (mise à jour) ou `append-only` (ajout uniquement)
- **Gestion des doublons** : Détection et filtrage automatique
- **Suivi des auteurs** : Collection séparée pour les métadonnées des auteurs

### 📊 Analyse avancée
- **NLP (Natural Language Processing)** : Analyse de sentiment, extraction de mots-clés
- **Détection de tendances** : Identification des technologies en croissance
- **Patterns temporels** : Analyse des patterns d'activité (heure, jour, mois)
- **Statistiques complètes** : Métriques détaillées sur l'ensemble des données

### 📈 Reporting automatique
- **Rapports Markdown** : Génération automatique de rapports complets
- **Analyses JSON** : Export des données d'analyse pour intégration
- **Métriques d'exécution** : Suivi des performances du système

## 🚀 Installation

### Prérequis

- **Python 3.8+** (testé avec Python 3.12)
- **MongoDB** (local ou distant)
- **Google Chrome** (pour le scraping web)

### Installation des dépendances

```bash
# Cloner le repository
git clone https://github.com/pierre-mazard/so-scrapper.git
cd so-scrapper

# Installer les dépendances
pip install -r requirements.txt

# Installer les ressources NLTK (pour l'analyse NLP)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### Configuration initiale

1. **Démarrer MongoDB** (si local) :
   ```bash
   # Windows
   net start MongoDB
   
   # Linux/macOS
   sudo systemctl start mongod
   # ou
   brew services start mongodb/brew/mongodb-community
   ```

2. **Vérifier la connexion MongoDB** :
   ```bash
   python utils/check_mongodb.py
   ```

3. **Configuration optionnelle** :
   ```bash
   # Copier le fichier d'exemple
   cp .env.example .env
   # Éditer .env selon vos besoins
   ```

## 📁 Structure du projet

```
so-scrapper/
├── 📁 src/                     # Code source principal
│   ├── __init__.py            # Package principal
│   ├── scraper.py             # Module de scraping (API + Web)
│   ├── database.py            # Gestionnaire MongoDB
│   ├── analyzer.py            # Moteur d'analyse NLP
│   └── config.py              # Gestion de la configuration
│
├── 📁 tests/                   # Suite de tests complète
│   ├── __init__.py            # Package de tests
│   ├── conftest.py            # Configuration pytest
│   ├── test_*.py              # Tests unitaires par module
│   ├── test_logger.py         # Système de logging des tests
│   ├── analyze_logs.py        # Analyseur de logs de tests
│   └── logs/                  # Logs des tests
│
├── 📁 utils/                   # Utilitaires et scripts
│   ├── check_mongodb.py       # Diagnostic MongoDB
│   └── clear_database.py      # Nettoyage de la base
│
├── 📁 output/                  # Résultats générés
│   ├── analysis/              # Analyses JSON
│   ├── reports/               # Rapports Markdown
│   └── visualizations/        # Graphiques 
│
├── 📁 logs/                    # Logs d'exécution
│   └── scraper.log            # Log principal
│
├── 📄 main.py                  # Point d'entrée principal
├── 📄 run_tests.py             # Script de lancement des tests
├── 📄 analysis_notebook.ipynb # Notebook Jupyter d'analyse
├── 📄 config.json             # Configuration par défaut
├── 📄 .env                    # Variables d'environnement
├── 📄 requirements.txt        # Dépendances Python
├── 📄 pytest.ini             # Configuration des tests
└── 📄 README.md               # Documentation (ce fichier)
```

### Modules principaux

| Module | Responsabilité | Classes principales |
|--------|---------------|-------------------|
| `scraper.py` | Extraction de données | `StackOverflowScraper`, `QuestionData` |
| `database.py` | Persistance MongoDB | `DatabaseManager` |
| `analyzer.py` | Analyse des données | `DataAnalyzer`, `NLPProcessor`, `TrendAnalyzer` |
| `config.py` | Configuration | `Config`, `ScraperConfig`, `DatabaseConfig` |

## ⚙️ Configuration

Le système utilise une configuration hiérarchique par ordre de priorité :

1. **Variables d'environnement** (priorité maximale)
2. **Fichier `.env`** 
3. **Fichier `config.json`**
4. **Valeurs par défaut**

### Configuration MongoDB (`config.json`)

```json
{
  "database": {
    "host": "localhost",
    "port": 27017,
    "name": "stackoverflow_data",
    "collection": "questions",
    "max_pool_size": 10,
    "timeout_ms": 30000
  }
}
```

### Configuration API Stack Overflow

```json
{
  "api": {
    "key": "",              // Optionnel - 10k requêtes/jour sans clé
    "rate_limit": 300,      // Requêtes par seconde
    "quota_max": 10000,     // Quota journalier
    "site": "stackoverflow"
  }
}
```

### Variables d'environnement (`.env`)

```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=stackoverflow_data

# Logging
LOG_LEVEL=INFO

# Scraper
SCRAPER_HEADLESS=true
SCRAPER_DELAY=2

# Analysis
ENABLE_NLP=true
ENABLE_SENTIMENT_ANALYSIS=true
```

## 🎯 Utilisation

### Commande de base

```bash
python main.py
```

**Comportement par défaut :**
- Extrait 300 questions via scraping web
- Stocke en mode `update` (met à jour les existantes et ajoute les nouvelles)
- Effectue une analyse complète
- Génère un rapport automatique

### Syntaxe complète

```bash
python main.py [OPTIONS]
```

### 📝 Paramètres et options

| Option | Raccourci | Type | Défaut | Description |
|--------|-----------|------|--------|-------------|
| `--max-questions` | `-n` | int | 300 | Nombre max de questions à extraire |
| `--tags` | `-t` | list | None | Tags à filtrer (ex: python javascript) |
| `--use-api` | | flag | False | Utiliser l'API au lieu du scraping |
| `--no-analysis` | | flag | False | Désactiver complètement l'analyse des données |
| `--log-level` | | choice | INFO | Niveau de logging (DEBUG/INFO/WARNING/ERROR) |
| `--mode` | | choice | update | Mode de stockage (update/append-only) |
| `--analysis-scope` | | choice | all | Portée de l'analyse (all/new-only) |

### Modes de stockage

#### 🔄 Mode `update` (défaut)
```bash
python main.py --mode update
```
- **Comportement** : Met à jour les questions existantes et ajoute les nouvelles
- **Usage** : Maintenance régulière, actualisation des données
- **Technique** : Utilise l'upsert MongoDB sur `question_id`

#### ➕ Mode `append-only`
```bash
python main.py --mode append-only
```
- **Comportement** : Ajoute seulement les nouvelles questions, ignore les doublons
- **Usage** : Enrichissement de la base, éviter les doublons
- **Technique** : Filtre les IDs existants avant insertion

### Portées d'analyse

#### 🌐 Mode `all` (défaut)
```bash
python main.py --analysis-scope all
```
- **Comportement** : Analyse toutes les questions présentes dans la base de données
- **Usage** : Analyse complète des tendances globales
- **Technique** : Récupère et analyse toutes les questions stockées

#### 🎯 Mode `new-only`
```bash
python main.py --analysis-scope new-only
```
- **Comportement** : Analyse seulement les questions nouvellement ajoutées/mises à jour
- **Usage** : Analyse rapide des nouvelles tendances, optimisation des performances
- **Technique** : Filtre et analyse uniquement les questions traitées lors de l'exécution courante
- **Note** : Si aucune nouvelle question, l'analyse est automatiquement annulée

#### 💡 Combinaisons utiles
```bash
# Ajout de nouvelles données + analyse complète
python main.py --mode append-only --analysis-scope all

# Ajout de nouvelles données + analyse des nouveautés seulement
python main.py --mode append-only --analysis-scope new-only

# Mise à jour + analyse des changements seulement
python main.py --mode update --analysis-scope new-only

# Collecte sans analyse immédiate (optimisation performance)
python main.py --use-api -n 2000 --no-analysis
```

#### ⚠️ Mode d'analyse désactivé
```bash
python main.py --no-analysis
```
- **Comportement** : Effectue uniquement l'extraction et le stockage, aucune analyse
- **Usage** : Collecte massive de données sans traitement immédiat
- **Rapport** : Un rapport d'exécution est quand même généré avec le statut "Analyse désactivée"
- **Note** : Permet d'optimiser les performances lors de collectes importantes

### 💡 Exemples d'utilisation

#### 1. Extraction basique
```bash
# 300 questions par défaut
python main.py

# 1000 questions via scraping
python main.py -n 1000
```

#### 2. Extraction via API
```bash
# Plus rapide et fiable
python main.py --use-api -n 2500

# API avec tags spécifiques
python main.py --use-api -t python javascript -n 1000
```

#### 3. Gestion des doublons
```bash
# Mode append-only : évite les doublons
python main.py -n 2500 --use-api --mode append-only

# Enrichissement progressif par tags
python main.py -t python --mode append-only
python main.py -t react --mode append-only
python main.py -t vue.js --mode append-only
```

#### 4. Extraction ciblée
```bash
# Questions Python seulement
python main.py -t python -n 1000

# Multiple tags
python main.py -t python javascript react -n 1500

# Technologies frontend
python main.py -t html css javascript react vue.js --use-api
```

#### 5. Modes avancés
```bash
# Extraction sans analyse (plus rapide)
python main.py -n 1000 --no-analysis

# Mode debug complet
python main.py --log-level DEBUG -n 100

# Production : API + append-only + analyse
python main.py --use-api -n 2500 --mode append-only
```

#### 6. Modes d'analyse optimisés
```bash
# Collecte + analyse complète (défaut)
python main.py --use-api -n 1000 --analysis-scope all

# Collecte + analyse rapide des nouveautés seulement
python main.py --use-api -n 1000 --analysis-scope new-only

# Mode append-only + analyse des nouvelles questions
python main.py --mode append-only --analysis-scope new-only -n 500

# Mise à jour + analyse complète pour recalculer les tendances
python main.py --mode update --analysis-scope all

# Mode économe : collecte sans analyse immédiate
python main.py --use-api -n 2000 --no-analysis
# → Génère quand même un rapport d'exécution avec statut "Analyse désactivée"

# Cas d'analyse annulée automatiquement
python main.py --mode append-only --analysis-scope new-only -n 100
# → Si aucune nouvelle question, l'analyse est annulée intelligemment
# → Le rapport indique "Analyse annulée - Aucune nouvelle question"
```

#### 7. Workflows spécialisés
```bash
# Collecte initiale massive
python main.py --use-api -n 2500 --mode append-only --no-analysis

# Mise à jour quotidienne
python main.py --use-api -n 500 --mode update

# Analyse de technologies spécifiques
python main.py -t "machine-learning" "artificial-intelligence" --use-api
```

## �️ Base de données

### Architecture MongoDB

Le système utilise MongoDB avec une architecture optimisée pour les données Stack Overflow :

```
Database: stackoverflow_data
├── 📄 questions     (Collection principale)
├── 📄 authors       (Métadonnées des auteurs)  
└── 📄 analysis      (Résultats d'analyses)
```

### Collection `questions`

**Structure d'un document :**

```javascript
{
  _id: ObjectId("..."),
  question_id: 79727532,                    // ID Stack Overflow (unique)
  title: "How to use async/await in Python?",
  url: "https://stackoverflow.com/questions/...",
  summary: "I'm trying to understand...",   // Contenu de la question
  tags: ["python", "async-await", "asyncio"],
  
  // Auteur
  author_name: "PythonDev",
  author_profile_url: "https://stackoverflow.com/users/...",
  author_reputation: 5420,
  
  // Métriques
  view_count: 1250,
  vote_count: 15,
  answer_count: 3,
  
  // Dates
  publication_date: ISODate("2025-08-06T10:30:00Z"),
  stored_at: ISODate("2025-08-07T11:45:00Z"),
  last_updated: ISODate("2025-08-07T11:45:00Z")
}
```

**Index configurés :**
- `question_id` (unique) - Clé primaire métier
- `publication_date` (descendant) - Tri chronologique
- `tags` - Recherche par technologie
- `title + summary` (text) - Recherche textuelle complète
- `tags + publication_date` (composé) - Requêtes complexes

### Collection `authors`

```javascript
{
  _id: ObjectId("..."),
  author_name: "PythonDev",               // Nom d'utilisateur (unique)
  profile_url: "https://stackoverflow.com/users/...",
  reputation: 5420,
  question_count: 12,                     // Nombre de questions dans notre base
  first_seen: ISODate("2025-08-06T..."), // Première question collectée
  last_seen: ISODate("2025-08-07T...")   // Dernière question collectée
}
```

### Collection `analysis`

```javascript
{
  _id: ObjectId("..."),
  analysis_type: "comprehensive_trend_analysis",
  analysis_date: ISODate("2025-08-07T..."),
  
  // Métadonnées
  metadata: {
    total_questions_analyzed: 5000,
    analysis_duration: 7.85,
    date_range: {
      start: "2025-05-28T08:54:25",
      end: "2025-08-07T11:26:54"
    }
  },
  
  // Résultats détaillés
  results: {
    tag_trends: { ... },           // Tendances des technologies
    temporal_patterns: { ... },    // Patterns temporels
    content_analysis: { ... },     // Analyse NLP
    author_analysis: { ... },      // Statistiques auteurs
    general_stats: { ... }         // Métriques générales
  }
}
```

### Métriques de performance

- **Questions** : ~557 bytes/document en moyenne
- **Auteurs** : ~193 bytes/document en moyenne
- **Analyses** : ~12KB/document (très détaillées)

### Utilisation des utilitaires

```bash
# Diagnostic complet de la base
python utils/check_mongodb.py

# Nettoyage complet (⚠️ DESTRUCTIF)
python utils/clear_database.py
```

## 📊 Analyse et rapports

### Moteur d'analyse

Le système d'analyse est composé de plusieurs modules spécialisés :

#### 🔍 NLP Processor
- **Preprocessing** : Nettoyage et normalisation des textes
- **Keywords extraction** : TF-IDF pour identifier les termes importants (titles, summaries, contenu combiné)
- **Sentiment analysis** : Analyse du sentiment avec TextBlob (titles, summaries, contenu combiné)
- **Content quality analysis** : Métriques de qualité du contenu (complétude, richesse technique, clarté)
- **Vectorisation** : Préparation pour l'analyse de clustering

#### 📈 Trend Analyzer
- **Tag trends** : Croissance des technologies par période
- **Temporal patterns** : Patterns d'activité (heure, jour, mois)
- **Growth rates** : Calcul des taux de croissance
- **Peak detection** : Identification des pics d'activité

#### 🎯 Data Analyzer (Principal)
- **Orchestration** : Coordonne tous les types d'analyse
- **Content analysis** : Analyse des titres et résumés
- **Author analysis** : Statistiques sur les auteurs actifs
- **General stats** : Métriques globales

### Types d'analyses effectuées

#### 1. Analyse des tendances des tags
```python
{
  "trending_tags": [
    {
      "tag": "react",
      "total_questions": 176,
      "growth_rate": 98.3,
      "last_week": 56,
      "last_month": 117
    }
  ],
  "top_tags": [...]
}
```

#### 2. Patterns temporels
```python
{
  "hourly_patterns": {
    "peak_hour": 17,          // 17h = pic d'activité
    "votes_mean": {...},      // Moyennes de votes par heure
    "answers_mean": {...}     // Moyennes de réponses par heure
  },
  "daily_patterns": {...},   // Patterns par jour de la semaine
  "monthly_patterns": {...}  // Patterns par mois
}
```

#### 3. Analyse de contenu NLP
```python
{
  "title_keywords": [
    ["python", 0.058],        // Mots-clés des titres avec scores TF-IDF
    ["error", 0.048],
    ["function", 0.028]
  ],
  "summary_keywords": [
    ["trying", 0.045],        // Mots-clés des résumés
    ["understand", 0.038],
    ["implement", 0.035]
  ],
  "combined_keywords": [      // Analyse du contenu complet (titre + résumé)
    ["python", 0.062],
    ["function", 0.041],
    ["error", 0.038]
  ],
  "title_sentiment": {
    "positive": 443,
    "negative": 450,
    "neutral": 4107,
    "average": -0.0045        // Légèrement négatif (problèmes techniques)
  },
  "summary_sentiment": {      // Sentiment des résumés
    "positive": 612,
    "negative": 298,
    "neutral": 4090,
    "average": 0.0123         // Plus positif (explications détaillées)
  },
  "content_quality": {        // Nouvelle analyse de qualité
    "summary_completeness": 78.5,     // % de questions avec résumé substantiel
    "content_richness": {
      "technical_word_ratio": 23.4,   // % de mots techniques
      "avg_words_per_question": 42.8,
      "technical_term_count": 1847
    },
    "technical_depth": 15.6,          // % de questions avec termes avancés
    "question_clarity": {
      "clear_questions_ratio": 67.8,  // % de questions bien structurées
      "questions_with_context": 3387
    }
  }
}
```

### Rapports générés

#### 📄 Rapport Markdown (`output/reports/`)
- **Résumé exécutif** avec métriques clés
- **Analyse détaillée** par catégorie (si l'analyse a été effectuée)
- **Tableaux** des tendances et statistiques
- **Recommandations** basées sur les données
- **Génération systématique** : Un rapport est toujours généré, même si l'analyse est désactivée ou annulée

#### 🔄 Statuts d'analyse dans les rapports
- **✅ Analyse complète** : Toutes les sections d'analyse sont présentes
- **❌ Analyse désactivée** : Rapport avec informations d'exécution uniquement
  - Message : "Analyse désactivée par l'utilisateur (--no-analysis)"
  - Suggestion : "Pour activer l'analyse, retirez l'option `--no-analysis`"
- **⚠️ Analyse annulée** : Analyse intelligemment annulée pour optimiser les performances
  - Message : "Aucune nouvelle question à analyser"
  - Suggestion : "Utilisez `--analysis-scope all` pour forcer l'analyse de toutes les questions"

#### 📊 Données JSON (`output/analysis/`)
- **Format structuré** pour intégration
- **Toutes les métriques** calculées
- **Métadonnées** d'exécution
- **Prêt pour visualisation**

### Exemples de métriques

```
📊 Métriques d'exemple (base de 5000 questions)
────────────────────────────────────────────────
• Technologies top 5 : Python (2000), JavaScript (916), HTML (210)
• Taux de réponses : 54.3% des questions ont des réponses
• Auteurs actifs : 4900 auteurs uniques
• Période couverte : 2.5 mois
• Pic d'activité : Mardi 17h
• Sentiment moyen : Légèrement négatif (-0.005)
• Croissance : React (+98%), TypeScript (+140%)
```

## 🧪 Tests

### Architecture de tests

Le projet dispose d'une suite de tests complète avec **70 tests unitaires** couvrant tous les modules :

```
tests/
├── conftest.py              # Configuration pytest + plugin logging
├── test_analyzer.py         # Tests du moteur d'analyse (22 tests)
├── test_config.py           # Tests de configuration (20 tests)  
├── test_database.py         # Tests MongoDB (16 tests)
├── test_scraper.py          # Tests d'extraction (12 tests)
├── test_logger.py           # Système de logging des tests
├── analyze_logs.py          # Analyseur de résultats de tests
└── logs/                    # Logs détaillés des tests
```

### Lancement des tests

#### 🚀 Exécution standard
```bash
# Tous les tests avec rapport automatique
python run_tests.py

# Tests uniquement
pytest tests/ -v

# Tests avec couverture
pytest tests/ --cov=src --cov-report=html
```

#### 🎯 Tests spécifiques
```bash
# Module spécifique
pytest tests/test_scraper.py -v

# Test particulier
pytest tests/test_database.py::TestDatabaseManager::test_store_questions -v

# Tests par marqueur
pytest tests/ -m "not slow" -v
```

#### 🔍 Tests avec options avancées
```bash
# Mode debug avec logs détaillés
pytest tests/ -v --log-cli --log-cli-level=DEBUG

# Tests d'intégration uniquement
pytest tests/ -m integration -v

# Tests rapides (sans intégration)
pytest tests/ -m "not integration" -v
```

### Rapports de tests

#### 📊 Rapport automatique
Le script `run_tests.py` génère automatiquement :

```
output/reports/rapport_tests_YYYYMMDD_HHMMSS.md
```

**Contenu du rapport :**
- ✅ **Résumé exécutif** : 69/70 tests réussis (98.6%)
- 📊 **Statistiques détaillées** par module
- ⏱️ **Temps d'exécution** : ~102 secondes
- 🔍 **Tests échoués** avec détails des erreurs
- 💡 **Recommandations** pour corriger les problèmes

#### 📋 Exemple de résultats
```
🧪 RAPPORT DE TESTS - STACK OVERFLOW SCRAPER
═══════════════════════════════════════════

📊 RÉSUMÉ EXÉCUTIF
────────────────────
• Tests totaux : 70
• Réussis : 69 (98.6%)
• Échoués : 0 (0.0%)  
• Ignorés : 1 (1.4%)
• Durée : 101.61s

📈 RÉSULTATS PAR MODULE
─────────────────────
• test_analyzer.py : 22/22 ✅
• test_config.py : 20/20 ✅
• test_database.py : 15/16 ✅ (1 ignoré)
• test_scraper.py : 12/12 ✅
```

### Configuration des tests

#### 📁 `pytest.ini`
```ini
[tool:pytest]
addopts = 
    -v --tb=short
    --log-cli=true
    --log-cli-level=INFO
    --disable-warnings

markers =
    slow: tests lents (intégration)
    integration: tests d'intégration
    unit: tests unitaires
```

#### 🔧 Fixtures disponibles
- **`db_manager`** : Gestionnaire de base mockée
- **`sample_questions`** : Données de test
- **`config`** : Configuration de test
- **`nlp_processor`** : Processeur NLP mocké

### Tests d'intégration

```bash
# Tests avec vraie base MongoDB (nécessite MongoDB actif)
pytest tests/ -m integration -v

# Test complet bout-en-bout
pytest tests/test_database.py::TestDatabaseIntegration -v
```

⚠️ **Note** : Les tests d'intégration nécessitent MongoDB actif et peuvent modifier la base de test.

## 🛠️ Utilitaires

### Scripts de maintenance

#### 🔍 `utils/check_mongodb.py`
**Diagnostic complet de MongoDB**

```bash
python utils/check_mongodb.py
```

**Fonctionnalités :**
- ✅ Test de connexion MongoDB
- 📊 Informations du serveur (version, plateforme)
- 📋 Liste des bases de données et collections
- 🔍 **Analyse détaillée des collections** :
  - Structure des documents avec types de données
  - Statistiques : taille, nombre de documents, moyennes
  - Index configurés avec détails
  - Plages de dates et métriques numériques
- 💾 Test d'écriture/lecture
- ⚠️ Détection de problèmes courants

**Exemple de sortie :**
```
🔍 VÉRIFICATION DE LA CONFIGURATION MONGODB
═══════════════════════════════════════════
📍 URL : mongodb://localhost:27017/
📍 Base : stackoverflow_data
✅ MongoDB connecté avec succès!
📊 Version MongoDB: 8.0.12

📋 Collections dans 'stackoverflow_data':
   📄 questions (5,581 documents)
   📃 authors (4,900 documents)  
   📃 analysis (5 documents)

🔍 ANALYSE DÉTAILLÉE DES COLLECTIONS
═══════════════════════════════════════════

📄 Collection: questions
──────────────────────────────────────────
📊 Nombre de documents: 5,581
🔍 Structure des documents:
   • question_id         : int    (ex: 79726836)
   • title              : str    (ex: Best project structure...)
   • tags               : Array[str] (ex: ['python', 'api'])
   • view_count         : int    (ex: 62)
   • publication_date   : DateTime (ex: 2025-08-06 06:44)
📈 Statistiques:
   💾 Taille: 2.97 MB
   📅 publication_date: 2025-05-28 08:54 → 2025-08-06 17:44
   🔢 view_count: min=5, max=3856, avg=67.4
🗂️ Index:
   🗂️ question_id_1: question_id:1 (UNIQUE)
   🗂️ publication_date_1: publication_date:1
   🗂️ tags_1: tags:1
```

#### 🗑️ `utils/clear_database.py`
**Nettoyage complet de la base**

```bash
python utils/clear_database.py
```

**⚠️ ATTENTION :** Opération destructive irréversible !

**Protection :** Demande confirmation explicite (taper "OUI")

**Supprime :**
- Toutes les questions
- Tous les auteurs
- Toutes les analyses
- Tous les index personnalisés

#### 📊 `tests/analyze_logs.py`
**Analyseur de logs de tests**

```bash
python tests/analyze_logs.py --show
```

**Génère :**
- Rapport détaillé des résultats de tests
- Statistiques de performance par test
- Analyse des erreurs et échecs
- Recommandations d'amélioration

### Scripts d'exécution

#### 🚀 `run_tests.py`
**Lanceur de tests avec rapport automatique**

```bash
python run_tests.py
```

**Fonctionnalités :**
- Exécution complète de la suite de tests
- Génération automatique de rapport Markdown
- Logging détaillé dans `tests/logs/`
- Statistiques de performance
- Code de sortie approprié pour CI/CD

#### 📓 `analysis_notebook.ipynb`
**Notebook Jupyter pour analyse interactive**

```bash
jupyter notebook analysis_notebook.ipynb
```

**Contenu :**
- Connexion à la base MongoDB
- Analyses interactives des données
- Visualisations personnalisées
- Expérimentation avec les données

## 🔧 Dépannage

### Problèmes courants et solutions

#### 1. 🔄 Gestion des doublons

**Problème :** Moins de questions que prévu après extraction

```bash
# Diagnostic
python utils/check_mongodb.py  # Vérifier le nombre actuel

# Solutions
# Option 1: Mode append-only (recommandé)
python main.py -n 2500 --use-api --mode append-only

# Option 2: Enrichissement progressif par tags
python main.py -t python --mode append-only
python main.py -t javascript --mode append-only
python main.py -t react --mode append-only

# Option 3: Vider et recommencer
python utils/clear_database.py
python main.py -n 5000 --use-api
```

#### 2. 🗄️ Erreurs MongoDB

**Problème :** Connexion MongoDB échouée

```bash
# Diagnostic complet
python utils/check_mongodb.py

# Solutions par OS
# Windows
net start MongoDB

# Linux/Ubuntu
sudo systemctl start mongod
sudo systemctl status mongod

# macOS
brew services start mongodb/brew/mongodb-community

# Docker
docker run -d -p 27017:27017 mongo:latest
```

**Problème :** Base corrompue ou problèmes de performance

```bash
# Nettoyage complet (⚠️ destructif)
python utils/clear_database.py

# Vérification après nettoyage
python utils/check_mongodb.py
```

#### 3. 🌐 Erreurs API Stack Overflow

**Problème :** Quota API dépassé

```bash
# Basculer vers scraping web
python main.py -n 500  # sans --use-api

# Réduire la fréquence
python main.py --use-api -n 50  # petites quantités

# Obtenir une clé API (10k/jour gratuit)
# Éditer config.json:
{
  "api": {
    "key": "votre_clé_ici"
  }
}
```

**Problème :** Timeouts ou erreurs réseau

```bash
# Augmenter les timeouts dans config.json
{
  "scraper": {
    "timeout": 60,
    "retry_count": 5
  }
}

# Mode debug pour diagnostiquer
python main.py --log-level DEBUG -n 10
```

#### 4. 🔍 Erreurs de scraping web

**Problème :** ChromeDriver obsolète

```bash
# Mise à jour automatique
pip install --upgrade webdriver-manager

# Installation manuelle si nécessaire
# Télécharger depuis: https://chromedriver.chromium.org/
```

**Problème :** Chrome non trouvé

```bash
# Vérifier l'installation de Chrome
google-chrome --version  # Linux
chrome --version         # macOS

# Configuration headless dans .env
SCRAPER_HEADLESS=true
```

#### 5. 🧠 Erreurs d'analyse NLP

**Problème :** Ressources NLTK manquantes

```bash
# Installation complète des ressources NLTK
python -c "
import nltk
nltk.download('punkt')
nltk.download('stopwords') 
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
"
```

**Problème :** Erreurs de mémoire lors de l'analyse

```bash
# Réduire la taille des données à analyser
python main.py -n 1000 --use-api  # au lieu de 5000

# Désactiver l'analyse temporairement
python main.py -n 2500 --no-analysis
```

#### 6. 🧪 Erreurs de tests

**Problème :** Tests d'intégration échouent

```bash
# Vérifier MongoDB pour les tests d'intégration
python utils/check_mongodb.py

# Lancer seulement les tests unitaires
pytest tests/ -m "not integration" -v

# Nettoyer les logs de tests
rm -rf tests/logs/*
```

**Problème :** Tests lents

```bash
# Tests rapides seulement
pytest tests/ -m "not slow" -v

# Tests en parallèle (si pytest-xdist installé)
pytest tests/ -n auto
```

### 📝 Logging et débogage

#### Niveaux de logging disponibles

```bash
# Debug complet (très verbeux)
python main.py --log-level DEBUG

# Informations normales (recommandé)
python main.py --log-level INFO

# Avertissements seulement
python main.py --log-level WARNING

# Erreurs critiques seulement
python main.py --log-level ERROR
```

#### Fichiers de logs

```bash
# Log principal de l'application
tail -f logs/scraper.log

# Logs des tests
ls tests/logs/
cat tests/logs/test_run_*.log
```

### 🚨 Problèmes de performance

#### Extraction lente

```bash
# Préférer l'API au scraping web
python main.py --use-api -n 2500  # ~15s vs ~60s

# Réduire les délais de scraping (risqué)
# Éditer config.json:
{
  "scraper": {
    "delay_between_requests": 1  # au lieu de 2
  }
}
```

#### Base MongoDB lente

```bash
# Vérifier les index
python utils/check_mongodb.py

# Requêtes optimisées - vérifier les patterns d'usage
# Les index sont configurés automatiquement
```

### 🔄 Workflows de récupération

#### Récupération après problème majeur

```bash
# 1. Diagnostic complet
python utils/check_mongodb.py

# 2. Sauvegarde si possible
mongodump --db stackoverflow_data --out backup/

# 3. Nettoyage si nécessaire  
python utils/clear_database.py

# 4. Re-collecte progressive
python main.py --use-api -n 1000 --mode append-only
python main.py -t python --use-api --mode append-only
python main.py -t javascript --use-api --mode append-only

# 5. Vérification finale
python utils/check_mongodb.py
```

#### Test de santé rapide

```bash
# Test de bout-en-bout minimal
python main.py -n 10 --use-api --log-level DEBUG

# Vérification de l'analyse
python main.py -n 50 --use-api --mode append-only
```

### 💡 Conseils d'optimisation

1. **Pour la collecte de données :**
   - Utilisez l'API (`--use-api`) autant que possible
   - Mode `append-only` pour éviter les doublons
   - Collecte par tags spécifiques pour cibler

2. **Pour les performances :**
   - MongoDB avec SSD recommandé
   - 8GB+ RAM pour analyses importantes
   - Python 3.9+ pour meilleures performances

3. **Pour la maintenance :**
   - Exécutez `check_mongodb.py` régulièrement
   - Sauvegardez avant les gros changements
   - Utilisez les logs pour diagnostiquer

### 📞 Support

En cas de problème persistant :

1. **Vérifiez les logs** : `logs/scraper.log`
2. **Exécutez le diagnostic** : `python utils/check_mongodb.py`
3. **Testez en mode minimal** : `python main.py -n 10 --log-level DEBUG`
4. **Consultez les issues GitHub** du projet

## 🚀 Workflow de production recommandé

### 1. **Collecte initiale massive**
```bash
# Nettoyage et préparation
python utils/clear_database.py
python utils/check_mongodb.py

# Collecte par technologie (mode append-only)
python main.py --use-api -n 2500 -t python --mode append-only
python main.py --use-api -n 1500 -t javascript --mode append-only  
python main.py --use-api -n 1000 -t react --mode append-only
python main.py --use-api -n 1000 -t vue.js --mode append-only

# Vérification finale
python utils/check_mongodb.py
```

### 2. **Maintenance quotidienne**
```bash
# Mise à jour des questions existantes + nouvelles
python main.py --use-api -n 500 --mode update

# Analyse complète
# (l'analyse est automatique avec la commande ci-dessus)
```

### 3. **Enrichissement périodique**
```bash
# Nouvelles technologies émergentes
python main.py --use-api -n 500 -t "machine-learning" --mode append-only
python main.py --use-api -n 500 -t "artificial-intelligence" --mode append-only

# Langages spécialisés
python main.py --use-api -n 300 -t rust --mode append-only
python main.py --use-api -n 300 -t go --mode append-only
```

### 4. **Monitoring et maintenance**
```bash
# Vérification hebdomadaire
python utils/check_mongodb.py

# Tests mensuels
python run_tests.py

# Analyse de performance
# Consulter output/reports/ pour les tendances
```

---
