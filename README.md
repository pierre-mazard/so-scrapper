# 🔍 Stack Overflow Scraper

Un outil complet d'extraction et d'analyse de données Stack Overflow avec support dual (Web Scraping + API).

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Paramètres et options](#-paramètres-et-options)
- [Exemples d'utilisation](#-exemples-dutilisation)
- [Structure des données](#-structure-des-données)
- [Tests](#-tests)
- [Dépannage](#-dépannage)

## ✨ Fonctionnalités

- **Extraction de données** : Scraping web (Selenium) ou API officielle Stack Overflow
- **Stockage intelligent** : Base de données MongoDB avec gestion des doublons
- **Analyse complète** : NLP, analyse de sentiment, détection de tendances
- **Rapports détaillés** : Génération automatique de rapports complets
- **Logging avancé** : Suivi complet de l'exécution avec métriques

## 🚀 Installation

### Prérequis

- Python 3.8+
- MongoDB (local ou distant)
- Google Chrome (pour le scraping web)

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration initiale

1. **Démarrer MongoDB** (si local) :
   ```bash
   mongod
   ```

2. **Vérifier la connexion MongoDB** :
   ```bash
   python utils/check_mongodb.py
   ```

3. **Configurer l'environnement** (optionnel) :
   ```bash
   cp .env.example .env
   # Éditer .env selon vos besoins
   ```

## ⚙️ Configuration

Le scraper utilise plusieurs sources de configuration par ordre de priorité :

1. **Variables d'environnement** (priorité maximale)
2. **Fichier config.json** 
3. **Valeurs par défaut**

### Configuration MongoDB

```json
{
  "database": {
    "host": "localhost",
    "port": 27017,
    "name": "stackoverflow_data",
    "collection": "questions"
  }
}
```

### Configuration API Stack Overflow

```json
{
  "api": {
    "key": "",  // Optionnel - 10k requêtes/jour sans clé
    "rate_limit": 300,
    "site": "stackoverflow"
  }
}
```

## 🎯 Utilisation

### Commande de base

```bash
python main.py
```

Cette commande :
- Extrait 300 questions (par défaut)
- Utilise le scraping web
- Stocke les données en MongoDB
- Génère une analyse complète

### Syntaxe complète

```bash
python main.py [OPTIONS]
```

## 📝 Paramètres et options

| Option | Raccourci | Type | Défaut | Description |
|--------|-----------|------|--------|-------------|
| `--max-questions` | `-n` | int | 300 | Nombre max de questions à extraire |
| `--tags` | `-t` | list | None | Tags à filtrer (ex: python javascript) |
| `--use-api` | | flag | False | Utiliser l'API au lieu du scraping |
| `--no-analysis` | | flag | False | Désactiver l'analyse des données |
| `--log-level` | | choice | INFO | Niveau de logging (DEBUG/INFO/WARNING/ERROR) |

## 💡 Exemples d'utilisation

### 1. Extraction basique (300 questions)

```bash
python main.py
```

### 2. Extraction ciblée par tags

```bash
# Questions Python et JavaScript
python main.py --tags python javascript

# Questions React seulement
python main.py -t react
```

### 3. Extraction en volume

```bash
# 1000 questions via scraping web
python main.py --max-questions 1000

# 500 questions via API (plus rapide)
python main.py -n 500 --use-api
```

### 4. Extraction sans analyse

```bash
# Extraction seule (sans analyse)
python main.py --no-analysis
```

### 5. Mode débogage

```bash
# Logs détaillés pour dépannage
python main.py --log-level DEBUG
```

### 6. Combinaisons avancées

```bash
# 2500 questions Python via API avec logs détaillés
python main.py -n 2500 -t python --use-api --log-level DEBUG

# Extraction rapide React + Vue sans analyse
python main.py -t react vue.js --use-api --no-analysis
```

## 📊 Structure des données

### Question extraite

```python
{
    "title": "How to use async/await in Python?",
    "url": "https://stackoverflow.com/questions/...",
    "summary": "I'm trying to understand async programming...",
    "tags": ["python", "async-await", "asyncio"],
    "author_name": "PythonDev",
    "author_reputation": 5420,
    "publication_date": "2025-08-06T10:30:00",
    "view_count": 1250,
    "vote_count": 15,
    "answer_count": 3,
    "question_id": 78901234
}
```

### Rapport d'analyse généré

- **Statistiques générales** : Nombre de questions, auteurs, tags
- **Analyse temporelle** : Tendances par période
- **Analyse des tags** : Tags les plus populaires
- **Analyse de sentiment** : Sentiment moyen des questions
- **Mots-clés** : Extraction TF-IDF des termes importants
- **Métriques d'exécution** : Temps, taux d'extraction, performance

## 🧪 Tests

### Lancer tous les tests

```bash
python run_tests.py
```

### Tests spécifiques

```bash
# Tests du scraper seulement
pytest tests/test_scraper.py -v

# Tests avec couverture
pytest tests/ --cov=src
```

### Rapport de tests

Les rapports de tests sont automatiquement générés dans `output/reports/` avec :
- Statistiques détaillées
- Tests échoués/réussis
- Temps d'exécution
- Recommandations

## 🔧 Dépannage

### Problèmes courants

#### 1. Erreur de connexion MongoDB

```bash
# Vérifier que MongoDB est démarré
python utils/check_mongodb.py

# Nettoyer la base si nécessaire
python utils/clear_database.py
```

#### 2. Erreur Chrome/Selenium

```bash
# Installer/mettre à jour ChromeDriver
pip install --upgrade webdriver-manager
```

#### 3. Erreur de dépendances NLP

```bash
# Installer les ressources NLTK
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

#### 4. Erreur de taux limite API

```bash
# Utiliser le mode scraping web
python main.py --max-questions 100  # sans --use-api

# Ou réduire le nombre de questions
python main.py --use-api -n 50
```

### Logs de débogage

```bash
# Logs détaillés
python main.py --log-level DEBUG

# Logs dans le fichier
tail -f logs/scraper.log
```

### Nettoyage de la base de données

```bash
# ⚠️  ATTENTION: Supprime toutes les données
python utils/clear_database.py
```

## 📁 Structure du projet

```
so-scrapper/
├── src/                    # Code source principal
│   ├── scraper.py         # Module de scraping
│   ├── database.py        # Gestion MongoDB
│   ├── analyzer.py        # Analyse des données
│   └── config.py          # Configuration
├── tests/                 # Tests unitaires
├── utils/                 # Utilitaires
├── output/               # Rapports générés
│   ├── analysis/         # Analyses de données
│   └── reports/          # Rapports de tests
├── logs/                 # Fichiers de log
├── main.py              # Point d'entrée principal
├── run_tests.py         # Script de tests
├── config.json          # Configuration
└── requirements.txt     # Dépendances
```

## 🚀 Workflow typique

1. **Extraction** → Récupération des questions Stack Overflow
2. **Stockage** → Sauvegarde en MongoDB avec gestion des doublons
3. **Analyse** → Traitement NLP et identification des tendances
4. **Rapport** → Génération automatique du rapport complet

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

**Auteur** : Pierre Mazard  
**Date** : Août 2025  
**Version** : 1.0.0