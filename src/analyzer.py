"""
Data Analyzer Module
===================

Module pour l'analyse des données extraites de Stack Overflow.
Utilise des techniques de NLP et d'analyse statistique pour identifier les tendances.

Classes:
    DataAnalyzer: Analyseur principal des données
    TrendAnalyzer: Analyseur de tendances spécialisé
    NLPProcessor: Processeur de traitement du langage naturel
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter, defaultdict
import json
import re

import pandas as pd
import numpy as np
from textblob import TextBlob
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .database import DatabaseManager


class NLPProcessor:
    """Processeur de traitement du langage naturel pour l'analyse de texte."""
    
    def __init__(self):
        """Initialise le processeur NLP."""
        self.logger = logging.getLogger(__name__)
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Télécharger les ressources NLTK nécessaires
        self._download_nltk_resources()
    
    def _download_nltk_resources(self):
        """Télécharge les ressources NLTK nécessaires."""
        resources = ['punkt', 'stopwords', 'wordnet', 'vader_lexicon']
        for resource in resources:
            try:
                nltk.data.find(f'tokenizers/{resource}')
            except LookupError:
                nltk.download(resource, quiet=True)
    
    def preprocess_text(self, text: str) -> str:
        """
        Prétraite un texte pour l'analyse NLP.
        
        Args:
            text: Texte à prétraiter
            
        Returns:
            Texte prétraité
        """
        if not text:
            return ""
        
        # Nettoyage de base
        text = text.lower()
        text = re.sub(r'<[^>]+>', '', text)  # Supprimer HTML
        text = re.sub(r'http\S+|www\S+', '', text)  # Supprimer URLs
        text = re.sub(r'[^a-zA-Z\s]', '', text)  # Garder seulement lettres et espaces
        
        # Tokenisation et lemmatisation
        tokens = word_tokenize(text)
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                 if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def extract_keywords(self, texts: List[str], max_features: int = 100) -> List[Tuple[str, float]]:
        """
        Extrait les mots-clés les plus importants d'une collection de textes.
        
        Args:
            texts: Liste des textes à analyser
            max_features: Nombre maximum de mots-clés à extraire
            
        Returns:
            Liste des mots-clés avec leurs scores TF-IDF
        """
        if not texts:
            return []
        
        # Prétraitement
        processed_texts = [self.preprocess_text(text) for text in texts]
        processed_texts = [text for text in processed_texts if text.strip()]
        
        if not processed_texts:
            return []
        
        # Adaptation des paramètres selon le nombre de documents
        num_docs = len(processed_texts)
        
        # min_df adaptatif : minimum 1, mais pas plus de 10% des documents
        adaptive_min_df = max(1, min(2, int(num_docs * 0.1)))
        
        # max_df adaptatif : entre 0.7 et 0.95 selon le nombre de documents
        if num_docs <= 5:
            adaptive_max_df = 0.95
        elif num_docs <= 10:
            adaptive_max_df = 0.9
        else:
            adaptive_max_df = 0.8
        
        # TF-IDF avec paramètres adaptatifs
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            min_df=adaptive_min_df,
            max_df=adaptive_max_df
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calcul des scores moyens
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # Création de la liste des mots-clés avec scores
            keywords = list(zip(feature_names, mean_scores))
            keywords.sort(key=lambda x: x[1], reverse=True)
            
            return keywords
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de mots-clés: {e}")
            return []
    
    def analyze_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyse le sentiment d'une collection de textes.
        
        Args:
            texts: Liste des textes à analyser
            
        Returns:
            Statistiques de sentiment
        """
        if not texts:
            return {"positive": 0, "negative": 0, "neutral": 0, "average": 0}
        
        sentiments = []
        
        for text in texts:
            if text and text.strip():
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                sentiments.append(polarity)
        
        if not sentiments:
            return {"positive": 0, "negative": 0, "neutral": 0, "average": 0}
        
        # Classification des sentiments
        positive = sum(1 for s in sentiments if s > 0.1)
        negative = sum(1 for s in sentiments if s < -0.1)
        neutral = len(sentiments) - positive - negative
        
        return {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "average": np.mean(sentiments),
            "total": len(sentiments)
        }


class TrendAnalyzer:
    """Analyseur de tendances pour les données Stack Overflow."""
    
    def __init__(self):
        """Initialise l'analyseur de tendances."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_tag_trends(self, questions: List[Dict]) -> Dict[str, Any]:
        """
        Analyse les tendances des tags.
        
        Args:
            questions: Liste des questions
            
        Returns:
            Analyse des tendances des tags
        """
        if not questions:
            return {}
        
        # Extraction des tags avec dates
        tag_timeline = defaultdict(list)
        
        for question in questions:
            date = question.get('publication_date')
            tags = question.get('tags', [])
            
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                except:
                    continue
            
            for tag in tags:
                tag_timeline[tag].append(date)
        
        # Analyse par période
        trends = {}
        current_date = datetime.now()
        periods = {
            'last_week': current_date - timedelta(days=7),
            'last_month': current_date - timedelta(days=30),
            'last_quarter': current_date - timedelta(days=90),
            'last_year': current_date - timedelta(days=365)
        }
        
        for tag, dates in tag_timeline.items():
            if len(dates) < 5:  # Ignorer les tags avec peu de données
                continue
            
            tag_trend = {'tag': tag, 'total_questions': len(dates)}
            
            for period_name, period_start in periods.items():
                count = sum(1 for date in dates if date >= period_start)
                tag_trend[period_name] = count
            
            # Calcul de la tendance (croissance récente vs ancienne)
            recent_count = tag_trend['last_month']
            older_count = len([d for d in dates 
                              if current_date - timedelta(days=60) <= d < current_date - timedelta(days=30)])
            
            if older_count > 0:
                growth_rate = (recent_count - older_count) / older_count * 100
            else:
                growth_rate = 100 if recent_count > 0 else 0
            
            tag_trend['growth_rate'] = growth_rate
            trends[tag] = tag_trend
        
        # Tri par popularité et croissance
        trending_tags = sorted(
            trends.values(),
            key=lambda x: (x['growth_rate'], x['last_month']),
            reverse=True
        )
        
        return {
            'trending_tags': trending_tags[:20],
            'top_tags': sorted(trends.values(), key=lambda x: x['total_questions'], reverse=True)[:20],
            'analysis_date': current_date.isoformat()
        }
    
    def analyze_temporal_patterns(self, questions: List[Dict]) -> Dict[str, Any]:
        """
        Analyse les patterns temporels des questions.
        
        Args:
            questions: Liste des questions
            
        Returns:
            Analyse des patterns temporels
        """
        if not questions:
            return {}
        
        # Conversion en DataFrame pour faciliter l'analyse
        df_data = []
        for question in questions:
            date = question.get('publication_date')
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                except:
                    continue
            
            if date:
                df_data.append({
                    'date': date,
                    'hour': date.hour,
                    'day_of_week': date.weekday(),
                    'month': date.month,
                    'votes': question.get('vote_count', 0),
                    'views': question.get('view_count', 0),
                    'answers': question.get('answer_count', 0)
                })
        
        if not df_data:
            return {}
        
        df = pd.DataFrame(df_data)
        
        # Analyse par heure
        hourly_stats = df.groupby('hour').agg({
            'votes': ['count', 'mean'],
            'views': 'mean',
            'answers': 'mean'
        }).round(2)
        
        # Analyse par jour de la semaine
        daily_stats = df.groupby('day_of_week').agg({
            'votes': ['count', 'mean'],
            'views': 'mean',
            'answers': 'mean'
        }).round(2)
        
        # Analyse par mois
        monthly_stats = df.groupby('month').agg({
            'votes': ['count', 'mean'],
            'views': 'mean',
            'answers': 'mean'
        }).round(2)
        
        return {
            'hourly_patterns': hourly_stats.to_dict(),
            'daily_patterns': daily_stats.to_dict(),
            'monthly_patterns': monthly_stats.to_dict(),
            'peak_hour': int(df.groupby('hour').size().idxmax()),
            'peak_day': int(df.groupby('day_of_week').size().idxmax()),
            'total_questions_analyzed': len(df)
        }


class DataAnalyzer:
    """
    Analyseur principal des données Stack Overflow.
    
    Coordonne les différents types d'analyses et génère des rapports complets.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialise l'analyseur de données.
        
        Args:
            database_manager: Gestionnaire de base de données
        """
        self.db_manager = database_manager
        self.logger = logging.getLogger(__name__)
        self.nlp_processor = NLPProcessor()
        self.trend_analyzer = TrendAnalyzer()
    
    async def analyze_trends(self) -> Dict[str, Any]:
        """
        Effectue une analyse complète des tendances.
        
        Returns:
            Résultats d'analyse complets
        """
        self.logger.info("[ANALYZE] Début de l'analyse des tendances")
        start_time = datetime.now()
        
        try:
            # Récupération des données
            self.logger.info("Questions extraites: Récupération des données depuis la base...")
            questions = await self.db_manager.get_questions(limit=5000)
            
            if not questions:
                self.logger.warning("⚠️ Aucune question trouvée pour l'analyse")
                return {"error": "Aucune donnée disponible"}
            
            self.logger.info(f"[OK] {len(questions)} questions récupérées pour l'analyse")
            
            # Analyses principales
            results = {
                'analysis_metadata': {
                    'analysis_date': datetime.now().isoformat(),
                    'total_questions': len(questions),
                    'date_range': self._get_date_range(questions)
                }
            }
            
            # 1. Analyse des tags et tendances
            self.logger.info("[TAGS]  Étape 1/5: Analyse des tendances des tags...")
            results['tag_trends'] = self.trend_analyzer.analyze_tag_trends(questions)
            self.logger.info("[OK] Analyse des tags terminée")
            
            # 2. Analyse temporelle
            self.logger.info("[TIME] Étape 2/5: Analyse des patterns temporels...")
            results['temporal_patterns'] = self.trend_analyzer.analyze_temporal_patterns(questions)
            self.logger.info("[OK] Analyse temporelle terminée")
            
            # 3. Analyse NLP des titres et résumés
            self.logger.info("[NLP] Étape 3/5: Analyse NLP des contenus...")
            results['content_analysis'] = await self._analyze_content(questions)
            self.logger.info("[OK] Analyse NLP terminée")
            
            # 4. Analyse des auteurs
            self.logger.info("[AUTHORS] Étape 4/5: Analyse des auteurs...")
            results['author_analysis'] = await self._analyze_authors()
            self.logger.info("[OK] Analyse des auteurs terminée")
            
            # 5. Statistiques générales
            self.logger.info("[STATS] Étape 5/5: Calcul des statistiques générales...")
            results['general_stats'] = await self._calculate_general_stats(questions)
            self.logger.info("[OK] Statistiques générales calculées")
            
            # Temps d'exécution
            end_time = datetime.now()
            results['analysis_metadata']['duration'] = (end_time - start_time).total_seconds()
            
            self.logger.info("🎉 ANALYSE COMPLÈTE TERMINÉE!")
            self.logger.info(f"Temps total:  Durée totale: {results['analysis_metadata']['duration']:.2f} secondes")
            self.logger.info(f"Questions extraites: Questions analysées: {len(questions)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}")
            raise
    
    def _get_date_range(self, questions: List[Dict]) -> Dict[str, str]:
        """Calcule la plage de dates des questions."""
        dates = []
        for question in questions:
            date = question.get('publication_date')
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    dates.append(date)
                except:
                    continue
            elif isinstance(date, datetime):
                dates.append(date)
        
        if dates:
            return {
                'start': min(dates).isoformat(),
                'end': max(dates).isoformat()
            }
        return {'start': None, 'end': None}
    
    async def _analyze_content(self, questions: List[Dict]) -> Dict[str, Any]:
        """Analyse le contenu textuel des questions."""
        # Extraction des textes
        titles = [q.get('title', '') for q in questions]
        summaries = [q.get('summary', '') for q in questions]
        
        # Mots-clés des titres
        title_keywords = self.nlp_processor.extract_keywords(titles, max_features=50)
        
        # Mots-clés des résumés
        summary_keywords = self.nlp_processor.extract_keywords(summaries, max_features=50)
        
        # Analyse de sentiment
        title_sentiment = self.nlp_processor.analyze_sentiment(titles)
        summary_sentiment = self.nlp_processor.analyze_sentiment(summaries)
        
        return {
            'title_keywords': title_keywords[:20],
            'summary_keywords': summary_keywords[:20],
            'title_sentiment': title_sentiment,
            'summary_sentiment': summary_sentiment,
            'average_title_length': np.mean([len(title) for title in titles if title]),
            'average_summary_length': np.mean([len(summary) for summary in summaries if summary])
        }
    
    async def _analyze_authors(self) -> Dict[str, Any]:
        """Analyse les données des auteurs."""
        authors = await self.db_manager.get_top_authors(limit=100)
        
        if not authors:
            return {}
        
        # Statistiques de réputation
        reputations = [author.get('reputation', 0) for author in authors]
        question_counts = [author.get('question_count', 0) for author in authors]
        
        return {
            'top_authors': authors[:10],
            'reputation_stats': {
                'mean': np.mean(reputations),
                'median': np.median(reputations),
                'max': max(reputations),
                'min': min(reputations)
            },
            'activity_stats': {
                'mean_questions_per_author': np.mean(question_counts),
                'median_questions_per_author': np.median(question_counts),
                'most_active_author': max(authors, key=lambda x: x.get('question_count', 0))
            },
            'total_authors': len(authors)
        }
    
    async def _calculate_general_stats(self, questions: List[Dict]) -> Dict[str, Any]:
        """Calcule les statistiques générales."""
        if not questions:
            return {}
        
        # Statistiques numériques
        votes = [q.get('vote_count', 0) for q in questions]
        views = [q.get('view_count', 0) for q in questions]
        answers = [q.get('answer_count', 0) for q in questions]
        
        # Statistiques des tags
        all_tags = []
        for q in questions:
            all_tags.extend(q.get('tags', []))
        
        tag_counter = Counter(all_tags)
        
        return {
            'vote_stats': {
                'mean': np.mean(votes),
                'median': np.median(votes),
                'max': max(votes),
                'std': np.std(votes)
            },
            'view_stats': {
                'mean': np.mean(views),
                'median': np.median(views),
                'max': max(views),
                'std': np.std(views)
            },
            'answer_stats': {
                'mean': np.mean(answers),
                'median': np.median(answers),
                'max': max(answers),
                'unanswered_rate': sum(1 for a in answers if a == 0) / len(answers) * 100
            },
            'tag_stats': {
                'total_unique_tags': len(tag_counter),
                'most_common_tags': tag_counter.most_common(20),
                'average_tags_per_question': len(all_tags) / len(questions)
            }
        }
    
    def _clean_for_mongodb(self, data):
        """
        Nettoie les données pour qu'elles soient compatibles avec MongoDB.
        Convertit les tuples en chaînes, les types numpy en types Python natifs, etc.
        
        Args:
            data: Données à nettoyer
            
        Returns:
            Données nettoyées compatibles avec MongoDB
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Convertir les clés tuples en chaînes
                if isinstance(key, tuple):
                    key_str = "_".join(str(k) for k in key)
                else:
                    key_str = str(key)
                
                # Nettoyer récursivement la valeur
                cleaned[key_str] = self._clean_for_mongodb(value)
            return cleaned
        
        elif isinstance(data, list):
            return [self._clean_for_mongodb(item) for item in data]
        
        elif isinstance(data, tuple):
            return list(data)
        
        elif isinstance(data, np.integer):
            return int(data)
        
        elif isinstance(data, np.floating):
            if np.isnan(data):
                return None
            return float(data)
        
        elif isinstance(data, np.ndarray):
            return data.tolist()
        
        elif hasattr(data, 'item'):  # numpy scalars
            return data.item()
        
        else:
            return data

    async def save_results(self, results: Dict[str, Any]) -> None:
        """
        Sauvegarde les résultats d'analyse.
        
        Args:
            results: Résultats à sauvegarder
        """
        # Nettoyer les données pour MongoDB
        cleaned_results = self._clean_for_mongodb(results)
        
        # Sauvegarde en base de données
        await self.db_manager.store_analysis_results(
            analysis_type="comprehensive_trend_analysis",
            results=cleaned_results
        )
        
        # Créer les dossiers output s'ils n'existent pas
        from pathlib import Path
        analysis_dir = Path("output/analysis")
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        reports_dir = Path("output/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp pour les fichiers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarde en fichier JSON
        json_file = analysis_dir / f"analysis_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_results, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Résultats JSON sauvegardés dans {json_file}")
        
        # Génération des rapports
        await self._generate_reports(results, reports_dir, timestamp)
    
    async def generate_visualizations(self, results: Dict[str, Any]) -> None:
        """
        Génère des visualisations des résultats d'analyse.
        
        Args:
            results: Résultats d'analyse
        """
        try:
            # Créer le dossier output/visualizations s'il n'existe pas
            from pathlib import Path
            output_dir = Path("output/visualizations")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Timestamp pour les fichiers
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Configuration du style
            plt.style.use('seaborn-v0_8')
            
            # 1. Graphique des tags tendances
            if 'tag_trends' in results and 'trending_tags' in results['tag_trends']:
                self._plot_trending_tags(results['tag_trends']['trending_tags'], output_dir, timestamp)
            
            # 2. Patterns temporels
            if 'temporal_patterns' in results:
                self._plot_temporal_patterns(results['temporal_patterns'], output_dir, timestamp)
            
            # 3. Statistiques générales
            if 'general_stats' in results:
                self._plot_general_stats(results['general_stats'], output_dir, timestamp)
            
            self.logger.info(f"Visualisations générées avec succès dans {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des visualisations: {e}")
    
    def _plot_trending_tags(self, trending_tags: List[Dict], output_dir, timestamp: str) -> None:
        """Génère un graphique des tags en tendance."""
        if not trending_tags:
            return
        
        tags = [tag['tag'] for tag in trending_tags[:15]]
        growth_rates = [tag['growth_rate'] for tag in trending_tags[:15]]
        
        plt.figure(figsize=(12, 8))
        bars = plt.barh(tags, growth_rates)
        plt.xlabel('Taux de croissance (%)')
        plt.title('Tags en tendance (croissance mensuelle)')
        plt.tight_layout()
        
        # Couleurs conditionnelles
        for i, bar in enumerate(bars):
            if growth_rates[i] > 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        # Sauvegarde dans le dossier output/visualizations
        output_file = output_dir / f'trending_tags_{timestamp}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        self.logger.info(f"Graphique des tags tendances sauvegardé: {output_file}")
    
    def _plot_temporal_patterns(self, temporal_data: Dict, output_dir, timestamp: str) -> None:
        """Génère des graphiques des patterns temporels."""
        if 'hourly_patterns' in temporal_data:
            # Graphique par heure
            hourly_counts = temporal_data['hourly_patterns'].get(('votes', 'count'), {})
            if hourly_counts:
                hours = list(hourly_counts.keys())
                counts = list(hourly_counts.values())
                
                plt.figure(figsize=(12, 6))
                plt.plot(hours, counts, marker='o')
                plt.xlabel('Heure de la journée')
                plt.ylabel('Nombre de questions')
                plt.title('Distribution des questions par heure')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Sauvegarde dans le dossier output/visualizations
                output_file = output_dir / f'temporal_patterns_{timestamp}.png'
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                self.logger.info(f"Graphique des patterns temporels sauvegardé: {output_file}")
    
    def _plot_general_stats(self, stats: Dict, output_dir, timestamp: str) -> None:
        """Génère des graphiques des statistiques générales."""
        if 'tag_stats' in stats and 'most_common_tags' in stats['tag_stats']:
            most_common = stats['tag_stats']['most_common_tags'][:15]
            tags = [tag[0] for tag in most_common]
            counts = [tag[1] for tag in most_common]
            
            plt.figure(figsize=(12, 8))
            plt.barh(tags, counts)
            plt.xlabel('Nombre de questions')
            plt.title('Tags les plus populaires')
            plt.tight_layout()
            
            # Sauvegarde dans le dossier output/visualizations
            output_file = output_dir / f'general_stats_{timestamp}.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            self.logger.info(f"Graphique des statistiques générales sauvegardé: {output_file}")
    
    async def _generate_reports(self, results: Dict[str, Any], reports_dir, timestamp: str) -> None:
        """Génère des rapports textuels des résultats d'analyse."""
        try:
            # Rapport de synthèse (format texte)
            summary_file = reports_dir / f"summary_report_{timestamp}.txt"
            await self._generate_summary_report(results, summary_file)
            
            # Rapport détaillé (format Markdown)
            detailed_file = reports_dir / f"detailed_analysis_{timestamp}.md"
            await self._generate_detailed_report(results, detailed_file)
            
            self.logger.info(f"Rapports générés dans {reports_dir}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des rapports: {e}")
    
    async def _generate_summary_report(self, results: Dict[str, Any], output_file) -> None:
        """Génère un rapport de synthèse."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("RAPPORT DE SYNTHÈSE - ANALYSE STACK OVERFLOW\n")
            f.write("=" * 50 + "\n\n")
            
            # Métadonnées
            if 'analysis_metadata' in results:
                meta = results['analysis_metadata']
                f.write(f"Date d'analyse: {meta.get('analysis_date', 'N/A')}\n")
                f.write(f"Questions analysées: {meta.get('total_questions', 0)}\n")
                f.write(f"Durée de l'analyse: {meta.get('duration', 0):.2f} secondes\n\n")
            
            # Tags tendances
            if 'tag_trends' in results and 'trending_tags' in results['tag_trends']:
                f.write("TOP 10 TAGS EN TENDANCE:\n")
                f.write("-" * 25 + "\n")
                for i, tag in enumerate(results['tag_trends']['trending_tags'][:10], 1):
                    f.write(f"{i:2d}. {tag['tag']} (croissance: {tag['growth_rate']:.1f}%)\n")
                f.write("\n")
            
            # Statistiques générales
            if 'general_stats' in results:
                stats = results['general_stats']
                f.write("STATISTIQUES GÉNÉRALES:\n")
                f.write("-" * 20 + "\n")
                if 'vote_stats' in stats:
                    f.write(f"Score moyen: {stats['vote_stats'].get('mean', 0):.1f}\n")
                if 'view_stats' in stats:
                    f.write(f"Vues moyennes: {stats['view_stats'].get('mean', 0):.0f}\n")
                if 'answer_stats' in stats:
                    f.write(f"Taux sans réponse: {stats['answer_stats'].get('unanswered_rate', 0):.1f}%\n")
                f.write("\n")
            
            # Analyse de sentiment
            if 'content_analysis' in results:
                content = results['content_analysis']
                f.write("ANALYSE DE SENTIMENT:\n")
                f.write("-" * 20 + "\n")
                if 'title_sentiment' in content:
                    sent = content['title_sentiment']
                    f.write(f"Sentiment des titres - Positif: {sent.get('positive', 0)}, ")
                    f.write(f"Neutre: {sent.get('neutral', 0)}, Négatif: {sent.get('negative', 0)}\n")
                f.write("\n")
        
        self.logger.info(f"Rapport de synthèse sauvegardé: {output_file}")
    
    async def _generate_detailed_report(self, results: Dict[str, Any], output_file) -> None:
        """Génère un rapport détaillé en Markdown."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 📊 Rapport d'Analyse Détaillé - Stack Overflow\n\n")
            
            # Métadonnées
            if 'analysis_metadata' in results:
                meta = results['analysis_metadata']
                f.write("## 📋 Informations Générales\n\n")
                f.write(f"- **Date d'analyse**: {meta.get('analysis_date', 'N/A')}\n")
                f.write(f"- **Questions analysées**: {meta.get('total_questions', 0)}\n")
                f.write(f"- **Durée de l'analyse**: {meta.get('duration', 0):.2f} secondes\n")
                if 'date_range' in meta and meta['date_range']['start']:
                    f.write(f"- **Période couverte**: {meta['date_range']['start']} à {meta['date_range']['end']}\n")
                f.write("\n")
            
            # Analyse des tags
            if 'tag_trends' in results:
                f.write("## 🏷️ Analyse des Tags\n\n")
                if 'trending_tags' in results['tag_trends']:
                    f.write("### Tags en Tendance\n\n")
                    f.write("| Rang | Tag | Croissance (%) | Questions Totales |\n")
                    f.write("|------|-----|----------------|-------------------|\n")
                    for i, tag in enumerate(results['tag_trends']['trending_tags'][:15], 1):
                        f.write(f"| {i} | {tag['tag']} | {tag['growth_rate']:.1f}% | {tag['total_questions']} |\n")
                    f.write("\n")
            
            # Patterns temporels
            if 'temporal_patterns' in results:
                f.write("## ⏰ Patterns Temporels\n\n")
                temporal = results['temporal_patterns']
                if 'peak_hour' in temporal:
                    f.write(f"- **Heure de pic**: {temporal['peak_hour']}h\n")
                if 'peak_day' in temporal:
                    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                    day_name = days[temporal['peak_day']] if temporal['peak_day'] < 7 else f"Jour {temporal['peak_day']}"
                    f.write(f"- **Jour de pic**: {day_name}\n")
                f.write("\n")
            
            # Analyse de contenu
            if 'content_analysis' in results:
                f.write("## 📝 Analyse de Contenu\n\n")
                content = results['content_analysis']
                
                if 'title_keywords' in content:
                    f.write("### Mots-clés des Titres\n\n")
                    for i, (keyword, score) in enumerate(content['title_keywords'][:10], 1):
                        f.write(f"{i}. **{keyword}** (score: {score:.3f})\n")
                    f.write("\n")
                
                if 'title_sentiment' in content:
                    f.write("### Analyse de Sentiment\n\n")
                    sent = content['title_sentiment']
                    total = sent.get('total', 1)
                    f.write(f"- **Positif**: {sent.get('positive', 0)} ({sent.get('positive', 0)/total*100:.1f}%)\n")
                    f.write(f"- **Neutre**: {sent.get('neutral', 0)} ({sent.get('neutral', 0)/total*100:.1f}%)\n")
                    f.write(f"- **Négatif**: {sent.get('negative', 0)} ({sent.get('negative', 0)/total*100:.1f}%)\n")
                    f.write(f"- **Score moyen**: {sent.get('average', 0):.3f}\n\n")
            
            # Analyse des auteurs
            if 'author_analysis' in results and 'top_authors' in results['author_analysis']:
                f.write("## 👥 Top Auteurs\n\n")
                f.write("| Rang | Auteur | Réputation | Questions |\n")
                f.write("|------|--------|------------|----------|\n")
                for i, author in enumerate(results['author_analysis']['top_authors'][:10], 1):
                    f.write(f"| {i} | {author.get('name', 'N/A')} | {author.get('reputation', 0):,} | {author.get('question_count', 0)} |\n")
                f.write("\n")
            
            f.write("---\n")
            f.write(f"*Rapport généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}*\n")
        
        self.logger.info(f"Rapport détaillé sauvegardé: {output_file}")
