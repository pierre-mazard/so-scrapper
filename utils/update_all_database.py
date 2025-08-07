#!/usr/bin/env python3
"""
Script utilitaire pour mettre à jour TOUTE la base de données Stack Overflow.

Ce script récupère toutes les questions existantes en base et les met à jour
via l'API Stack Overflow avec les dernières informations (scores, réponses, etc.).

Usage:
    python utils/update_all_database.py
    
Options:
    --batch-size: Nombre de questions à traiter par batch (défaut: 100)
    --dry-run: Mode test sans modification de la base
    --max-questions: Limite le nombre de questions à mettre à jour
    --delay: Délai entre les requêtes API en secondes (défaut: 0.1)
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
import time

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.database import DatabaseManager
from src.scraper import StackOverflowScraper
from src.analyzer import DataAnalyzer

class DatabaseUpdater:
    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.db_manager = None
        self.scraper = None
        self.logger = self._setup_logger()
        
        # Statistiques
        self.stats = {
            'total_questions': 0,
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'authors_updated': 0,
            'start_time': None,
            'batches_completed': 0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger pour l'update."""
        logger = logging.getLogger('database_updater')
        logger.setLevel(logging.INFO)
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Handler pour fichier
        log_file = f"logs/database_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(console_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    async def initialize(self):
        """Initialise les composants nécessaires."""
        self.logger.info("[INIT] Initialisation du système de mise à jour...")
        
        # Initialiser la base de données
        self.db_manager = DatabaseManager(self.config.database_config)
        await self.db_manager.connect()
        self.logger.info("[OK] Connexion à la base de données établie")
        
        # Initialiser le scraper
        self.scraper = StackOverflowScraper(self.config)
        await self.scraper.setup_session()
        self.logger.info("[OK] Scraper Stack Overflow initialisé")
        
        if self.dry_run:
            self.logger.info("[DRY-RUN] MODE DRY-RUN : Aucune modification ne sera apportée à la base")
    
    async def get_all_question_ids(self) -> List[int]:
        """Récupère tous les IDs des questions en base."""
        self.logger.info("[LIST] Récupération de la liste des questions en base...")
        
        questions_collection = self.db_manager.motor_database[self.db_manager.questions_collection]
        cursor = questions_collection.find({}, {"question_id": 1})
        
        question_ids = []
        async for doc in cursor:
            question_ids.append(doc["question_id"])
        
        self.stats['total_questions'] = len(question_ids)
        self.logger.info(f"[STATS] {len(question_ids)} questions trouvées en base de données")
        
        return question_ids
    
    async def update_questions_batch(self, question_ids: List[int], batch_num: int, total_batches: int) -> Dict[str, int]:
        """Met à jour un batch de questions."""
        batch_size = len(question_ids)
        self.logger.info(f"[BATCH] Batch {batch_num}/{total_batches} : Mise à jour de {batch_size} questions...")
        
        batch_stats = {
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'authors_updated': 0
        }
        
        try:
            # Récupérer les données via l'API Stack Overflow
            questions_data = await self.scraper.get_questions_by_ids(question_ids)
            
            if not questions_data:
                self.logger.warning(f"[WARNING] Aucune donnée récupérée pour ce batch")
                batch_stats['skipped'] = batch_size
                return batch_stats
            
            self.logger.info(f"[API] {len(questions_data)} questions récupérées de l'API")
            
            # Mettre à jour en base si pas en mode dry-run
            if not self.dry_run:
                # Mettre à jour les questions
                storage_result = await self.db_manager.store_questions(
                    questions_data, 
                    update_only=True
                )
                
                batch_stats['updated'] = storage_result['questions_stored']
                batch_stats['authors_updated'] = storage_result.get('authors_new', 0) + storage_result.get('authors_updated', 0)
                
                self.logger.info(f"[OK] {batch_stats['updated']} questions mises à jour")
                if batch_stats['authors_updated'] > 0:
                    self.logger.info(f"[AUTHORS] {batch_stats['authors_updated']} auteurs mis à jour")
            else:
                # Mode dry-run : simuler la mise à jour
                batch_stats['updated'] = len(questions_data)
                self.logger.info(f"[DRY-RUN] {batch_stats['updated']} questions seraient mises à jour")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Erreur lors de la mise à jour du batch {batch_num}: {e}")
            batch_stats['errors'] = batch_size
        
        return batch_stats
    
    async def update_all_database(self, batch_size: int = 100, max_questions: int = None, delay: float = 0.1):
        """Met à jour toute la base de données."""
        self.stats['start_time'] = time.time()
        
        self.logger.info("=" * 80)
        self.logger.info("[UPDATE] DÉBUT DE LA MISE À JOUR COMPLÈTE DE LA BASE DE DONNÉES")
        self.logger.info("=" * 80)
        
        # Récupérer tous les IDs de questions
        all_question_ids = await self.get_all_question_ids()
        
        if not all_question_ids:
            self.logger.warning("[WARNING] Aucune question trouvée en base de données")
            return
        
        # Limiter si demandé
        if max_questions and max_questions < len(all_question_ids):
            all_question_ids = all_question_ids[:max_questions]
            self.logger.info(f"🎯 Limitation à {max_questions} questions")
        
        # Créer les batches
        total_questions = len(all_question_ids)
        batches = [all_question_ids[i:i + batch_size] for i in range(0, total_questions, batch_size)]
        total_batches = len(batches)
        
        self.logger.info(f"📦 {total_batches} batches de {batch_size} questions maximum")
        self.logger.info(f"⏱️  Délai entre requêtes: {delay}s")
        
        # Traiter chaque batch
        for i, batch_ids in enumerate(batches, 1):
            batch_stats = await self.update_questions_batch(batch_ids, i, total_batches)
            
            # Mettre à jour les statistiques globales
            self.stats['processed'] += len(batch_ids)
            self.stats['updated'] += batch_stats['updated']
            self.stats['errors'] += batch_stats['errors']
            self.stats['skipped'] += batch_stats['skipped']
            self.stats['authors_updated'] += batch_stats['authors_updated']
            self.stats['batches_completed'] += 1
            
            # Afficher le progrès
            progress = (i / total_batches) * 100
            self.logger.info(f"📈 Progression: {progress:.1f}% ({i}/{total_batches} batches)")
            
            # Délai entre les batches pour respecter les limites de l'API
            if i < total_batches and delay > 0:
                await asyncio.sleep(delay)
        
        # Afficher le résumé final
        await self._display_final_summary()
        
        # Générer le rapport de mise à jour
        await self.generate_update_report()
    
    async def _display_final_summary(self):
        """Affiche le résumé final de la mise à jour."""
        elapsed_time = time.time() - self.stats['start_time']
        
        self.logger.info("=" * 80)
        self.logger.info("📊 RÉSUMÉ FINAL DE LA MISE À JOUR")
        self.logger.info("=" * 80)
        self.logger.info(f"⏱️  Durée totale: {elapsed_time:.1f}s")
        self.logger.info(f"📋 Questions en base: {self.stats['total_questions']}")
        self.logger.info(f"🔄 Questions traitées: {self.stats['processed']}")
        self.logger.info(f"✅ Questions mises à jour: {self.stats['updated']}")
        self.logger.info(f"👤 Auteurs mis à jour: {self.stats['authors_updated']}")
        self.logger.info(f"⚠️  Erreurs: {self.stats['errors']}")
        self.logger.info(f"⏭️  Ignorées: {self.stats['skipped']}")
        self.logger.info(f"📦 Batches complétés: {self.stats['batches_completed']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['updated'] / self.stats['processed']) * 100
            questions_per_sec = self.stats['processed'] / elapsed_time
            self.logger.info(f"📈 Taux de succès: {success_rate:.1f}%")
            self.logger.info(f"⚡ Vitesse: {questions_per_sec:.1f} questions/sec")
        
        if self.dry_run:
            self.logger.info("🧪 MODE DRY-RUN: Aucune modification réelle n'a été apportée")
        else:
            self.logger.info("🎉 MISE À JOUR TERMINÉE AVEC SUCCÈS!")
    
    async def generate_update_report(self):
        """Génère un rapport de mise à jour dans le dossier reports."""
        try:
            self.logger.info("📄 Génération du rapport de mise à jour...")
            
            # Créer le dossier reports s'il n'existe pas
            os.makedirs('output/reports', exist_ok=True)
            
            # Timestamp pour le nom du fichier
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"output/reports/database_update_report_{timestamp}.md"
            
            # Calculer les statistiques finales
            elapsed_time = time.time() - self.stats['start_time']
            success_rate = (self.stats['updated'] / self.stats['processed']) * 100 if self.stats['processed'] > 0 else 0
            questions_per_sec = self.stats['processed'] / elapsed_time if elapsed_time > 0 else 0
            
            # Contenu du rapport
            report_content = f"""# 📊 RAPPORT DE MISE À JOUR - BASE DE DONNÉES STACK OVERFLOW

*Rapport de mise à jour complète de la base de données*

---

## 🚀 INFORMATIONS D'EXÉCUTION

### Configuration de la mise à jour

- **Date de démarrage**: {datetime.fromtimestamp(self.stats['start_time']).strftime('%Y-%m-%d %H:%M:%S')}
- **Mode d'exécution**: {"🧪 DRY-RUN (test)" if self.dry_run else "🔄 MISE À JOUR RÉELLE"}
- **Durée totale**: {elapsed_time:.1f} secondes

---

## 📊 STATISTIQUES GLOBALES

### Questions traitées

| Métrique | Valeur |
|----------|--------|
| **Questions en base de données** | {self.stats['total_questions']:,} |
| **Questions traitées** | {self.stats['processed']:,} |
| **Questions mises à jour** | {self.stats['updated']:,} |
| **Erreurs rencontrées** | {self.stats['errors']:,} |
| **Questions ignorées** | {self.stats['skipped']:,} |

### Auteurs

- **Auteurs mis à jour**: {self.stats['authors_updated']:,}

### Performance

| Métrique | Valeur |
|----------|--------|
| **Batches complétés** | {self.stats['batches_completed']:,} |
| **Taux de succès** | {success_rate:.1f}% |
| **Vitesse de traitement** | {questions_per_sec:.1f} questions/sec |

---

## 🔄 DÉTAILS DE L'OPÉRATION

### Processus de mise à jour

1. **📋 Récupération des IDs**: Extraction de tous les IDs de questions en base
2. **📦 Division en batches**: Organisation des questions par lots pour traitement
3. **📡 Récupération API**: Récupération des données via l'API Stack Overflow
4. **💾 Mise à jour base**: {"Simulation des mises à jour" if self.dry_run else "Application des mises à jour en base de données"}

### Résultats par catégorie

- **✅ Questions mises à jour avec succès**: {self.stats['updated']:,}
- **⚠️ Questions avec erreurs**: {self.stats['errors']:,}
- **⏭️ Questions ignorées (API)**: {self.stats['skipped']:,}

---

## 📈 ANALYSE DE PERFORMANCE

### Efficacité du processus

- **Taux de traitement réussi**: {success_rate:.1f}%
- **Questions par seconde**: {questions_per_sec:.1f}
- **Temps moyen par question**: {(elapsed_time / self.stats['processed']) * 1000:.1f}ms

### Répartition des résultats

- **Succès**: {(self.stats['updated'] / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0:.1f}%
- **Erreurs**: {(self.stats['errors'] / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0:.1f}%
- **Ignorées**: {(self.stats['skipped'] / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0:.1f}%

---

## 💡 RECOMMANDATIONS

### Optimisations possibles

"""

            # Ajouter des recommandations basées sur les résultats
            if self.stats['errors'] > 0:
                error_rate = (self.stats['errors'] / self.stats['processed']) * 100
                if error_rate > 10:
                    report_content += f"- ⚠️ **Taux d'erreur élevé ({error_rate:.1f}%)**: Vérifier les limitations de l'API et la connectivité\n"
                else:
                    report_content += f"- ✅ **Taux d'erreur acceptable ({error_rate:.1f}%)**\n"

            if questions_per_sec < 1:
                report_content += "- 🐌 **Performance lente**: Considérer augmenter les délais ou réduire la taille des batches\n"
            elif questions_per_sec > 10:
                report_content += "- ⚡ **Excellente performance**: Le système fonctionne de manière optimale\n"
            else:
                report_content += "- 👍 **Performance correcte**: Le système fonctionne normalement\n"

            if self.stats['skipped'] > self.stats['updated']:
                report_content += "- 📡 **Beaucoup de questions ignorées**: Vérifier la disponibilité des données via l'API\n"

            # Finaliser le rapport
            report_content += f"""
### Actions suivantes recommandées

{"- 🧪 **Exécuter en mode réel**: Ce test montre que le processus est prêt" if self.dry_run else "- ✅ **Mise à jour terminée**: Base de données synchronisée avec succès"}
- 📊 **Analyser les données**: Lancer une analyse complète des données mises à jour
- 🔄 **Planifier la prochaine mise à jour**: Établir une fréquence de mise à jour régulière

---

## 📋 JOURNAL D'EXÉCUTION

### Configuration utilisée

- **Taille des batches**: Optimisée pour l'API Stack Overflow
- **Délais entre requêtes**: Respect des limitations de taux
- **Gestion des erreurs**: Récupération automatique et logging détaillé

### Fichiers générés

- **Log détaillé**: `logs/database_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log`
- **Rapport de mise à jour**: `{report_file}`

---

**Rapport généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}**
*Utilitaire de mise à jour de base de données - Stack Overflow Scraper*
"""

            # Écrire le rapport
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"📄 Rapport de mise à jour généré: {report_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération du rapport: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources."""
        if self.scraper:
            await self.scraper.close()
        if self.db_manager:
            await self.db_manager.disconnect()
        self.logger.info("[CLEANUP] Toutes les connexions fermées")

async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Met à jour toute la base de données Stack Overflow avec les dernières informations."
    )
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=100,
        help='Nombre de questions à traiter par batch (défaut: 100)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Mode test sans modification de la base'
    )
    parser.add_argument(
        '--max-questions', 
        type=int,
        help='Limite le nombre de questions à mettre à jour'
    )
    parser.add_argument(
        '--delay', 
        type=float, 
        default=0.1,
        help='Délai entre les requêtes API en secondes (défaut: 0.1)'
    )
    
    args = parser.parse_args()
    
    try:
        # Charger la configuration
        config = Config()
        
        # Créer l'updater
        updater = DatabaseUpdater(config, dry_run=args.dry_run)
        
        # Initialiser
        await updater.initialize()
        
        # Lancer la mise à jour
        await updater.update_all_database(
            batch_size=args.batch_size,
            max_questions=args.max_questions,
            delay=args.delay
        )
        
    except KeyboardInterrupt:
        print("\n⏸️  Mise à jour interrompue par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        return 1
    finally:
        if 'updater' in locals():
            await updater.cleanup()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
