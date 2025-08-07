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
    
    def analyze_content_quality(self, titles: List[str], summaries: List[str]) -> Dict[str, Any]:
        """
        Analyse la qualité du contenu basée sur les titres et résumés.
        
        Args:
            titles: Liste des titres
            summaries: Liste des résumés
            
        Returns:
            Métriques de qualité du contenu
        """
        quality_metrics = {
            'summary_completeness': 0,
            'content_richness': {},
            'technical_depth': 0,
            'question_clarity': {}
        }
        
        if not titles or not summaries:
            return quality_metrics
        
        # 1. Complétude des résumés (% de questions avec résumé substantiel)
        substantial_summaries = sum(1 for summary in summaries if len(summary.strip()) > 50)
        quality_metrics['summary_completeness'] = substantial_summaries / len(summaries) * 100
        
        # 2. Richesse du contenu (ratio mots techniques vs mots communs)
        technical_terms = {'function', 'class', 'method', 'variable', 'algorithm', 'library', 
                          'framework', 'api', 'database', 'server', 'client', 'code', 'syntax',
                          'error', 'exception', 'debug', 'compile', 'runtime', 'async', 'await'}
        
        combined_texts = [f"{title} {summary}".lower() for title, summary in zip(titles, summaries)]
        total_words = sum(len(text.split()) for text in combined_texts)
        technical_word_count = sum(sum(1 for word in text.split() if word in technical_terms) 
                                 for text in combined_texts)
        
        quality_metrics['content_richness'] = {
            'technical_word_ratio': technical_word_count / max(total_words, 1) * 100,
            'avg_words_per_question': total_words / len(combined_texts),
            'technical_term_count': technical_word_count
        }
        
        # 3. Profondeur technique (présence de mots-clés avancés)
        advanced_terms = {'performance', 'optimization', 'architecture', 'design pattern',
                         'security', 'scalability', 'microservices', 'deployment', 'testing',
                         'refactoring', 'best practices', 'clean code'}
        
        advanced_count = sum(sum(1 for term in advanced_terms if term in text.lower()) 
                           for text in combined_texts)
        quality_metrics['technical_depth'] = advanced_count / len(combined_texts) * 100
        
        # 4. Clarté des questions (présence de mots interrogatifs et structure)
        question_indicators = ['how', 'what', 'why', 'when', 'where', 'which', 'can', 'should', 
                             'is', 'are', 'does', 'do', 'will', 'would', '?']
        
        clear_questions = 0
        for title, summary in zip(titles, summaries):
            text = f"{title} {summary}".lower()
            has_question_words = any(indicator in text for indicator in question_indicators)
            has_code_context = any(keyword in text for keyword in ['code', 'function', 'method', 'class'])
            
            if has_question_words and has_code_context:
                clear_questions += 1
        
        quality_metrics['question_clarity'] = {
            'clear_questions_ratio': clear_questions / len(titles) * 100,
            'questions_with_context': clear_questions
        }
        
        return quality_metrics


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
            if len(dates) < 1:  # Analyser tous les tags qui apparaissent au moins une fois
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
            elif recent_count > 0:
                # Si pas de données anciennes mais des récentes, afficher comme "nouveau" plutôt que 100%
                growth_rate = 0  # Marquer comme nouveau tag plutôt que croissance infinie
            else:
                growth_rate = 0
            
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
        self.execution_metadata = {}
    
    def set_execution_metadata(self, scraping_info: Dict[str, Any]) -> None:
        """
        Configure les métadonnées d'exécution du scraping.
        
        Args:
            scraping_info: Informations sur l'exécution du scraping
        """
        self.execution_metadata = scraping_info
    
    async def analyze_trends(self, question_ids: List[int] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète des tendances.
        
        Args:
            question_ids: Liste des IDs de questions à analyser. Si None, analyse toutes les questions.
        
        Returns:
            Résultats d'analyse complets
        """
        self.logger.info("[ANALYZE] Début de l'analyse des tendances")
        start_time = datetime.now()
        
        try:
            # Récupération des données
            if question_ids is not None:
                self.logger.info(f"Questions extraites: Récupération de {len(question_ids)} questions spécifiques...")
                questions = await self.db_manager.get_questions_by_ids(question_ids)
            else:
                self.logger.info("Questions extraites: Récupération des données depuis la base...")
                questions = await self.db_manager.get_questions(limit=None)  # Toutes les questions
            
            if not questions:
                self.logger.warning("⚠️ Aucune question trouvée pour l'analyse")
                return {"error": "Aucune donnée disponible"}
            
            scope_info = f"spécifiques ({len(question_ids)} IDs)" if question_ids else "toutes disponibles"
            self.logger.info(f"[OK] {len(questions)} questions récupérées pour l'analyse ({scope_info})")
            
            # Analyses principales
            results = {
                'execution_info': self.execution_metadata,
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
            results['author_analysis'] = await self._analyze_authors(question_ids)
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
        
        # Texte combiné (titre + résumé) pour analyse globale
        combined_texts = [f"{title} {summary}".strip() for title, summary in zip(titles, summaries)]
        
        # Mots-clés séparés
        title_keywords = self.nlp_processor.extract_keywords(titles, max_features=50)
        summary_keywords = self.nlp_processor.extract_keywords(summaries, max_features=50)
        
        # Mots-clés du contenu combiné (pour une vision globale)
        combined_keywords = self.nlp_processor.extract_keywords(combined_texts, max_features=100)
        
        # Analyse de sentiment
        title_sentiment = self.nlp_processor.analyze_sentiment(titles)
        summary_sentiment = self.nlp_processor.analyze_sentiment(summaries)
        combined_sentiment = self.nlp_processor.analyze_sentiment(combined_texts)
        
        # Nouvelle analyse de qualité du contenu
        content_quality = self.nlp_processor.analyze_content_quality(titles, summaries)
        
        # Statistiques de longueur
        title_lengths = [len(title) for title in titles if title]
        summary_lengths = [len(summary) for summary in summaries if summary]
        
        return {
            'title_keywords': title_keywords[:20],
            'summary_keywords': summary_keywords[:20],
            'combined_keywords': combined_keywords[:30],  # Plus de mots-clés pour le contenu complet
            'title_sentiment': title_sentiment,
            'summary_sentiment': summary_sentiment,
            'combined_sentiment': combined_sentiment,
            'content_quality': content_quality,  # Nouvelle métrique de qualité
            'length_stats': {
                'average_title_length': np.mean(title_lengths) if title_lengths else 0,
                'average_summary_length': np.mean(summary_lengths) if summary_lengths else 0,
                'title_word_count': np.mean([len(title.split()) for title in titles if title]) if titles else 0,
                'summary_word_count': np.mean([len(summary.split()) for summary in summaries if summary]) if summaries else 0
            }
        }
    
    async def _analyze_authors(self, question_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Analyse les données des auteurs.
        
        Args:
            question_ids: Si fourni, analyse uniquement les auteurs de ces questions
        """
        if question_ids:
            # Analyser uniquement les auteurs des questions spécifiées
            authors = await self.db_manager.get_authors_by_question_ids(question_ids)
        else:
            # Analyser tous les auteurs (sans limite)
            authors = await self.db_manager.get_top_authors(limit=None)
        
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
        
        # Génération du rapport complet unique
        await self._generate_complete_report(results, reports_dir, timestamp)
    
    
    async def _generate_complete_report(self, results: Dict[str, Any], reports_dir, timestamp: str) -> None:
        """
        Génère un rapport complet incluant toutes les informations d'exécution et d'analyse.
        
        Args:
            results: Résultats d'analyse complets
            reports_dir: Répertoire de sauvegarde des rapports
            timestamp: Timestamp pour nommer le fichier
        """
        try:
            # Rapport complet unique (format Markdown)
            complete_file = reports_dir / f"rapport_complet_{timestamp}.md"
            
            with open(complete_file, 'w', encoding='utf-8') as f:
                # En-tête du rapport
                f.write("# 📊 RAPPORT COMPLET - STACK OVERFLOW SCRAPER & ANALYZER\n\n")
                f.write("*Rapport d'exécution complète du processus de scraping et d'analyse*\n\n")
                f.write("---\n\n")
                
                # 1. INFORMATIONS D'EXÉCUTION GÉNÉRALE
                self._write_execution_info(f, results)
                
                # 2. PHASE SCRAPING
                self._write_scraping_info(f, results)
                
                # 3. PHASE STOCKAGE
                self._write_storage_info(f, results)
                
                # 4. PHASE ANALYSE
                self._write_analysis_info(f, results)
                
                # 5. RÉSULTATS D'ANALYSE DÉTAILLÉS
                self._write_detailed_analysis_results(f, results)
                
                # 6. PERFORMANCE ET STATISTIQUES
                self._write_performance_stats(f, results)
                
                # 7. FOOTER
                f.write("\n---\n")
                f.write(f"**Rapport généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}**\n")
                f.write("*Stack Overflow Scraper & Analyzer - Version complète*\n")
            
            self.logger.info(f"📄 Rapport complet généré: {complete_file}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du rapport complet: {e}")
    
    
    def _write_execution_info(self, f, results: Dict[str, Any]) -> None:
        """Écrit les informations d'exécution générale."""
        f.write("## 🚀 INFORMATIONS D'EXÉCUTION GÉNÉRALE\n\n")
        
        # Informations de base
        if 'execution_info' in results:
            exec_info = results['execution_info']
            f.write("### Configuration d'exécution\n\n")
            f.write(f"- **Date de démarrage**: {exec_info.get('start_time', 'N/A')}\n")
            f.write(f"- **Questions demandées**: {exec_info.get('max_questions', 'N/A')}\n")
            f.write(f"- **Tags ciblés**: {', '.join(exec_info.get('target_tags', [])) if exec_info.get('target_tags') else 'Tous les tags'}\n")
            f.write(f"- **Mode d'extraction**: {exec_info.get('extraction_mode', 'N/A')}\n")
            f.write(f"- **Mode de stockage**: {exec_info.get('storage_mode', 'N/A')}\n")
            analysis_scope = exec_info.get('analysis_scope', 'N/A')
            if analysis_scope == 'disabled':
                f.write(f"- **Mode d'analyse**: ❌ Désactivé\n")
            else:
                f.write(f"- **Mode d'analyse**: {analysis_scope}\n")
            
            # Affichage des options d'exécution détaillées
            f.write("\n### Options d'exécution utilisées\n\n")
            options = []
            
            # Reconstruction de la commande équivalente
            if exec_info.get('max_questions'):
                options.append(f"--max-questions {exec_info['max_questions']}")
            
            if exec_info.get('target_tags'):
                tags_str = ' '.join(exec_info['target_tags'])
                options.append(f"--tags {tags_str}")
            
            if exec_info.get('extraction_mode') == 'API Stack Overflow':
                options.append("--use-api")
            
            if exec_info.get('storage_mode') == 'append-only':
                options.append("--mode append-only")
            elif exec_info.get('storage_mode') == 'update':
                options.append("--mode update")
            elif exec_info.get('storage_mode') == 'upsert':
                # upsert est maintenant le défaut, on ne l'affiche que si explicitement spécifié
                pass  # Mode par défaut, pas besoin de l'ajouter
            
            if exec_info.get('analysis_scope') == 'new-only':
                options.append("--analysis-scope new-only")
            elif exec_info.get('analysis_scope') == 'all':
                options.append("--analysis-scope all (défaut)")
            elif exec_info.get('analysis_scope') == 'disabled':
                options.append("--no-analysis")
            
            if options:
                f.write(f"**Commande équivalente :** `python main.py {' '.join(options)}`\n\n")
            else:
                f.write("**Commande équivalente :** `python main.py` (paramètres par défaut)\n\n")
            
            if 'total_duration' in exec_info:
                f.write(f"- **⏱️ Temps total d'exécution**: {exec_info['total_duration']:.2f} secondes\n")
            f.write("\n")
        
        # Résumé des phases
        f.write("### Résumé des phases d'exécution\n\n")
        if 'execution_info' in results:
            exec_info = results['execution_info']
            f.write("| Phase | Durée (s) | Status |\n")
            f.write("|-------|-----------|--------|\n")
            phases = [
                ('scraping', '🔍 Extraction'),
                ('storage', '💾 Stockage'),
                ('analysis', '📊 Analyse')
            ]
            
            for phase_key, phase_name in phases:
                duration = exec_info.get(f'{phase_key}_duration', 'N/A')
                status = exec_info.get(f'{phase_key}_status', '✅ Terminé')
                if isinstance(duration, (int, float)):
                    f.write(f"| {phase_name} | {duration:.2f} | {status} |\n")
                else:
                    f.write(f"| {phase_name} | {duration} | {status} |\n")
            f.write("\n")
    
    def _write_scraping_info(self, f, results: Dict[str, Any]) -> None:
        """Écrit les informations de la phase de scraping."""
        f.write("## 🔍 PHASE 1: EXTRACTION DES DONNÉES\n\n")
        
        if 'execution_info' in results:
            exec_info = results['execution_info']
            f.write("### Résultats de l'extraction\n\n")
            f.write(f"- **Questions extraites**: {exec_info.get('questions_extracted', 'N/A')}\n")
            f.write(f"- **Auteurs uniques**: {exec_info.get('unique_authors', 'N/A')}\n")
            f.write(f"- **Tags uniques**: {exec_info.get('unique_tags', 'N/A')}\n")
            if 'extraction_rate' in exec_info:
                f.write(f"- **Taux d'extraction**: {exec_info['extraction_rate']:.1f} questions/sec\n")
            f.write("\n")
            
            # Erreurs et problèmes
            if exec_info.get('extraction_errors', 0) > 0:
                f.write("### ⚠️ Erreurs d'extraction\n\n")
                f.write(f"- **Erreurs rencontrées**: {exec_info['extraction_errors']}\n")
                f.write(f"- **Taux d'erreur**: {exec_info.get('error_rate', 0):.1f}%\n\n")
    
    def _write_storage_info(self, f, results: Dict[str, Any]) -> None:
        """Écrit les informations de la phase de stockage."""
        f.write("## 💾 PHASE 2: STOCKAGE EN BASE DE DONNÉES\n\n")
        
        if 'execution_info' in results:
            exec_info = results['execution_info']
            storage_mode = exec_info.get('storage_mode', 'N/A')
            
            f.write("### Opérations de stockage\n\n")
            
            # Informations détaillées sur les questions selon le mode
            questions_attempted = exec_info.get('questions_attempted', 0)
            questions_stored = exec_info.get('questions_stored', 0)
            new_questions_count = exec_info.get('new_questions_count', 0)
            
            f.write(f"- **Mode de stockage utilisé**: {storage_mode}\n")
            f.write(f"- **Questions extraites**: {questions_attempted}\n")
            f.write(f"- **Questions stockées**: {questions_stored}\n")
            
            # Détails spécifiques selon le mode de stockage
            if storage_mode == 'upsert':
                f.write(f"- **Questions nouvelles/mises à jour**: {questions_stored} (insertion + mise à jour)\n")
            elif storage_mode == 'update':
                questions_ignored = questions_attempted - questions_stored
                f.write(f"- **Questions mises à jour**: {questions_stored}\n")
                f.write(f"- **Questions nouvelles ignorées**: {questions_ignored}\n")
            elif storage_mode == 'append-only':
                questions_ignored = questions_attempted - questions_stored
                f.write(f"- **Questions nouvelles ajoutées**: {questions_stored}\n")
                f.write(f"- **Questions doublons ignorées**: {questions_ignored}\n")
            
            # Statistiques détaillées des auteurs
            authors_new = exec_info.get('authors_new', 0)
            authors_updated = exec_info.get('authors_updated', 0)
            
            f.write("\n#### Gestion des auteurs\n\n")
            if authors_new > 0 or authors_updated > 0:
                f.write(f"- **Nouveaux auteurs**: {authors_new}\n")
                f.write(f"- **Auteurs mis à jour**: {authors_updated}\n")
                f.write(f"- **Total auteurs affectés**: {authors_new + authors_updated}\n")
            else:
                f.write("- **Auteurs**: Aucun changement\n")
            
            # Métriques de performance
            f.write("\n#### Performance de stockage\n\n")
            if 'storage_rate' in exec_info:
                f.write(f"- **Taux de stockage**: {exec_info['storage_rate']:.1f} opérations/sec\n")
            if 'storage_duration' in exec_info:
                f.write(f"- **Durée de stockage**: {exec_info['storage_duration']:.2f} secondes\n")
            
            # Efficacité du stockage
            if questions_attempted > 0:
                efficiency = (questions_stored / questions_attempted) * 100
                f.write(f"- **Efficacité**: {efficiency:.1f}% des questions extraites stockées\n")
            
            f.write("\n")
    
    def _write_analysis_info(self, f, results: Dict[str, Any]) -> None:
        """Écrit les informations de la phase d'analyse."""
        f.write("## 📊 PHASE 3: ANALYSE DES DONNÉES\n\n")
        
        # Vérifier si l'analyse a été annulée ou désactivée
        if results.get('analysis_skipped') or results.get('analysis_disabled'):
            f.write("### ⚠️ Analyse non effectuée\n\n")
            skip_reason = results.get('skip_reason', 'Raison inconnue')
            
            if results.get('analysis_skipped'):
                f.write(f"**Statut**: Analyse annulée automatiquement\n\n")
                f.write(f"**Raison**: {skip_reason}\n\n")
                f.write("💡 *L'analyse a été intelligemment annulée pour optimiser les performances. ")
                f.write("Utilisez `--analysis-scope all` pour forcer l'analyse de toutes les questions.*\n\n")
            elif results.get('analysis_disabled'):
                f.write(f"**Statut**: Analyse désactivée par l'utilisateur\n\n")
                f.write(f"**Raison**: {skip_reason}\n\n")
                f.write("💡 *Pour activer l'analyse, retirez l'option `--no-analysis` de votre commande.*\n\n")
            
            return
        
        # Analyse normale
        if 'analysis_metadata' in results:
            meta = results['analysis_metadata']
            f.write("### Configuration de l'analyse\n\n")
            f.write(f"- **Date d'analyse**: {meta.get('analysis_date', 'N/A')}\n")
            f.write(f"- **Questions analysées**: {meta.get('total_questions', 0)}\n")
            f.write(f"- **Durée de l'analyse**: {meta.get('duration', 0):.2f} secondes\n")
            if 'date_range' in meta and meta['date_range']['start']:
                f.write(f"- **Période couverte**: {meta['date_range']['start']} à {meta['date_range']['end']}\n")
            f.write("\n")
    
    def _write_detailed_analysis_results(self, f, results: Dict[str, Any]) -> None:
        """Écrit les résultats détaillés de l'analyse."""
        # Vérifier si l'analyse a été annulée ou désactivée
        if results.get('analysis_skipped') or results.get('analysis_disabled'):
            # Ne pas afficher la section des résultats détaillés si pas d'analyse
            return
        
        f.write("## 📈 RÉSULTATS D'ANALYSE DÉTAILLÉS\n\n")
        
        # Tags tendances
        if 'tag_trends' in results:
            f.write("### 🏷️ Analyse des Tags\n\n")
            if 'trending_tags' in results['tag_trends']:
                f.write("#### Tags en Tendance\n\n")
                f.write("| Rang | Tag | Croissance (%) | Questions Totales | Dernière Semaine | Dernier Mois |\n")
                f.write("|------|-----|----------------|-------------------|------------------|---------------|\n")
                for i, tag in enumerate(results['tag_trends']['trending_tags'][:15], 1):
                    f.write(f"| {i} | `{tag['tag']}` | {tag['growth_rate']:.1f}% | {tag['total_questions']} | {tag.get('last_week', 'N/A')} | {tag.get('last_month', 'N/A')} |\n")
                f.write("\n")
        
        # Patterns temporels
        if 'temporal_patterns' in results:
            f.write("### ⏰ Patterns Temporels\n\n")
            temporal = results['temporal_patterns']
            f.write("#### Activité par période\n\n")
            if 'peak_hour' in temporal:
                f.write(f"- **🕐 Heure de pic d'activité**: {temporal['peak_hour']}h\n")
            if 'peak_day' in temporal:
                days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                day_name = days[temporal['peak_day']] if temporal['peak_day'] < 7 else f"Jour {temporal['peak_day']}"
                f.write(f"- **📅 Jour de pic d'activité**: {day_name}\n")
            f.write(f"- **📊 Questions analysées**: {temporal.get('total_questions_analyzed', 0)}\n")
            f.write("\n")
        
        # Analyse de contenu NLP
        if 'content_analysis' in results:
            f.write("### 📝 Analyse de Contenu (NLP)\n\n")
            content = results['content_analysis']
            
            # Mots-clés des titres
            if 'title_keywords' in content and content['title_keywords']:
                f.write("#### 🔤 Mots-clés des Titres (TF-IDF)\n\n")
                f.write("| Rang | Mot-clé | Score TF-IDF | Signification |\n")
                f.write("|------|---------|--------------|---------------|\n")
                for i, (keyword, score) in enumerate(content['title_keywords'][:15], 1):
                    significance = "Très important" if score > 0.5 else "Important" if score > 0.2 else "Modéré" if score > 0.1 else "Faible"
                    f.write(f"| {i} | `{keyword}` | {score:.3f} | {significance} |\n")
                f.write("\n")
            
            # Mots-clés des résumés (nouveau) - toujours afficher la section
            f.write("#### 📄 Mots-clés des Résumés (TF-IDF)\n\n")
            if 'summary_keywords' in content and content['summary_keywords']:
                f.write("| Rang | Mot-clé | Score TF-IDF | Signification |\n")
                f.write("|------|---------|--------------|---------------|\n")
                for i, (keyword, score) in enumerate(content['summary_keywords'][:15], 1):
                    significance = "Très important" if score > 0.5 else "Important" if score > 0.2 else "Modéré" if score > 0.1 else "Faible"
                    f.write(f"| {i} | `{keyword}` | {score:.3f} | {significance} |\n")
                f.write("\n")
            else:
                f.write("❌ **Pas de mots-clés extraits des résumés**\n\n")
                f.write("💡 **Raison possible** : Les questions analysées ne contiennent pas de résumés substantiels (>50 caractères), ou les résumés sont trop similaires pour générer des mots-clés distinctifs.\n\n")
            
            # Mots-clés du contenu combiné (nouveau)
            if 'combined_keywords' in content and content['combined_keywords']:
                f.write("#### 🔄 Mots-clés du Contenu Complet (Titres + Résumés)\n\n")
                f.write("| Rang | Mot-clé | Score TF-IDF | Signification |\n")
                f.write("|------|---------|--------------|---------------|\n")
                for i, (keyword, score) in enumerate(content['combined_keywords'][:20], 1):
                    significance = "Très important" if score > 0.5 else "Important" if score > 0.2 else "Modéré" if score > 0.1 else "Faible"
                    f.write(f"| {i} | `{keyword}` | {score:.3f} | {significance} |\n")
                f.write("\n")
                
                # Explication des scores TF-IDF
                f.write("💡 **Note**: Les scores TF-IDF mesurent l'importance statistique des mots dans le corpus. Un score plus élevé indique un terme plus significatif et distinctif.\n\n")
            
            # Analyse de sentiment des titres
            if 'title_sentiment' in content:
                f.write("#### 😊 Analyse de Sentiment des Titres\n\n")
                sent = content['title_sentiment']
                total = sent.get('total', 1)
                if total > 0:
                    pos_pct = (sent.get('positive', 0) / total) * 100
                    neu_pct = (sent.get('neutral', 0) / total) * 100
                    neg_pct = (sent.get('negative', 0) / total) * 100
                    
                    f.write("| Sentiment | Nombre | Pourcentage |\n")
                    f.write("|-----------|--------|--------------|\n")
                    f.write(f"| 😊 **Positif** | {sent.get('positive', 0)} | {pos_pct:.1f}% |\n")
                    f.write(f"| 😐 **Neutre** | {sent.get('neutral', 0)} | {neu_pct:.1f}% |\n")
                    f.write(f"| 😞 **Négatif** | {sent.get('negative', 0)} | {neg_pct:.1f}% |\n")
                    f.write(f"| 📊 **Score moyen** | - | {sent.get('average', 0):.3f} |\n")
                    f.write("\n")
            
            # Analyse de sentiment des résumés (nouveau) - toujours afficher la section
            f.write("#### 📄 Analyse de Sentiment des Résumés\n\n")
            if 'summary_sentiment' in content and content['summary_sentiment'].get('total', 0) > 0:
                sent = content['summary_sentiment']
                total = sent.get('total', 1)
                if total > 0:
                    pos_pct = (sent.get('positive', 0) / total) * 100
                    neu_pct = (sent.get('neutral', 0) / total) * 100
                    neg_pct = (sent.get('negative', 0) / total) * 100
                    
                    f.write("| Sentiment | Nombre | Pourcentage |\n")
                    f.write("|-----------|--------|--------------|\n")
                    f.write(f"| 😊 **Positif** | {sent.get('positive', 0)} | {pos_pct:.1f}% |\n")
                    f.write(f"| 😐 **Neutre** | {sent.get('neutral', 0)} | {neu_pct:.1f}% |\n")
                    f.write(f"| 😞 **Négatif** | {sent.get('negative', 0)} | {neg_pct:.1f}% |\n")
                    f.write(f"| 📊 **Score moyen** | - | {sent.get('average', 0):.3f} |\n")
                    f.write("\n")
            else:
                f.write("❌ **Pas d'analyse de sentiment disponible pour les résumés**\n\n")
                f.write("💡 **Raison possible** : Les questions analysées ne contiennent pas de résumés substantiels pour effectuer une analyse de sentiment fiable.\n\n")
            
            # Analyse de sentiment combinée (nouveau)
            if 'combined_sentiment' in content and content['combined_sentiment'].get('total', 0) > 0:
                f.write("#### 🔄 Analyse de Sentiment du Contenu Complet\n\n")
                sent = content['combined_sentiment']
                total = sent.get('total', 1)
                if total > 0:
                    pos_pct = (sent.get('positive', 0) / total) * 100
                    neu_pct = (sent.get('neutral', 0) / total) * 100
                    neg_pct = (sent.get('negative', 0) / total) * 100
                    
                    f.write("| Sentiment | Nombre | Pourcentage |\n")
                    f.write("|-----------|--------|--------------|\n")
                    f.write(f"| 😊 **Positif** | {sent.get('positive', 0)} | {pos_pct:.1f}% |\n")
                    f.write(f"| 😐 **Neutre** | {sent.get('neutral', 0)} | {neu_pct:.1f}% |\n")
                    f.write(f"| 😞 **Négatif** | {sent.get('negative', 0)} | {neg_pct:.1f}% |\n")
                    f.write(f"| 📊 **Score moyen** | - | {sent.get('average', 0):.3f} |\n")
                    f.write("\n")
                    
                    # Explication du score de sentiment
                    f.write("💡 **Note**: Le score de sentiment varie de -1 (très négatif) à +1 (très positif). Un score proche de 0 indique un contenu neutre/technique.\n\n")
            
            # Analyse de qualité du contenu (nouveau)
            if 'content_quality' in content:
                f.write("#### 🎯 Analyse de Qualité du Contenu\n\n")
                quality = content['content_quality']
                
                f.write("**📊 Métriques de qualité globales :**\n\n")
                f.write("| Métrique | Valeur | Interprétation |\n")
                f.write("|----------|--------|----------------|\n")
                
                # Complétude des résumés
                completeness = quality.get('summary_completeness', 0)
                completeness_desc = "Excellent" if completeness > 80 else "Bon" if completeness > 60 else "Modéré" if completeness > 40 else "Faible"
                f.write(f"| 📝 **Complétude des résumés** | {completeness:.1f}% | {completeness_desc} |\n")
                
                # Richesse technique
                if 'content_richness' in quality:
                    richness = quality['content_richness']
                    tech_ratio = richness.get('technical_word_ratio', 0)
                    tech_desc = "Très technique" if tech_ratio > 30 else "Technique" if tech_ratio > 20 else "Modérément technique" if tech_ratio > 10 else "Peu technique"
                    f.write(f"| 🔧 **Richesse technique** | {tech_ratio:.1f}% | {tech_desc} |\n")
                    
                    avg_words = richness.get('avg_words_per_question', 0)
                    word_desc = "Très détaillé" if avg_words > 100 else "Détaillé" if avg_words > 50 else "Standard" if avg_words > 30 else "Concis"
                    f.write(f"| 📊 **Mots par question** | {avg_words:.1f} | {word_desc} |\n")
                
                # Profondeur technique
                depth = quality.get('technical_depth', 0)
                depth_desc = "Très avancé" if depth > 20 else "Avancé" if depth > 10 else "Intermédiaire" if depth > 5 else "Basique"
                f.write(f"| 🎓 **Profondeur technique** | {depth:.1f}% | {depth_desc} |\n")
                
                # Clarté des questions
                if 'question_clarity' in quality:
                    clarity = quality['question_clarity']
                    clear_ratio = clarity.get('clear_questions_ratio', 0)
                    clear_desc = "Excellent" if clear_ratio > 80 else "Bon" if clear_ratio > 60 else "Modéré" if clear_ratio > 40 else "Améliorable"
                    f.write(f"| 💡 **Clarté des questions** | {clear_ratio:.1f}% | {clear_desc} |\n")
                
                f.write("\n")
            
            # Statistiques de longueur (améliorées)
            if 'length_stats' in content:
                length_stats = content['length_stats']
                f.write("#### 📏 Statistiques de Longueur du Contenu\n\n")
                f.write("| Type de contenu | Longueur moyenne | Mots moyens |\n")
                f.write("|-----------------|------------------|-------------|\n")
                
                if length_stats.get('average_title_length', 0) > 0:
                    f.write(f"| 🏷️ **Titres** | {length_stats['average_title_length']:.1f} caractères | {length_stats.get('title_word_count', 0):.1f} mots |\n")
                
                if length_stats.get('average_summary_length', 0) > 0:
                    f.write(f"| 📄 **Résumés** | {length_stats['average_summary_length']:.1f} caractères | {length_stats.get('summary_word_count', 0):.1f} mots |\n")
                
                f.write("\n")
        
        # Analyse des auteurs
        if 'author_analysis' in results and 'top_authors' in results['author_analysis']:
            f.write("### 👥 Analyse des Auteurs\n\n")
            f.write("#### Top Contributeurs\n\n")
            f.write("| Rang | Auteur | Réputation | Questions | Activité |\n")
            f.write("|------|--------|------------|-----------|----------|\n")
            for i, author in enumerate(results['author_analysis']['top_authors'][:10], 1):
                author_name = author.get('author_name', author.get('name', 'N/A'))
                reputation = author.get('reputation', 0)
                questions = author.get('question_count', 0)
                activity = "🔥 Très actif" if questions >= 10 else "⚡ Actif" if questions >= 5 else "📝 Contributeur"
                f.write(f"| {i} | **{author_name}** | {reputation:,} | {questions} | {activity} |\n")
            f.write("\n")
            
            # Statistiques des auteurs
            if 'reputation_stats' in results['author_analysis']:
                rep_stats = results['author_analysis']['reputation_stats']
                f.write("#### 📊 Statistiques de Réputation\n\n")
                f.write(f"- **Réputation moyenne**: {rep_stats.get('mean', 0):.0f} points\n")
                f.write(f"- **Réputation médiane**: {rep_stats.get('median', 0):.0f} points\n")
                f.write(f"- **Réputation maximale**: {rep_stats.get('max', 0):,} points\n")
                f.write(f"- **Réputation minimale**: {rep_stats.get('min', 0):,} points\n")
                f.write("\n")
    
    def _write_performance_stats(self, f, results: Dict[str, Any]) -> None:
        """Écrit les statistiques de performance et générales."""
        f.write("## 📊 STATISTIQUES GÉNÉRALES ET PERFORMANCE\n\n")
        
        if 'general_stats' in results:
            stats = results['general_stats']
            
            # Statistiques des questions
            f.write("### 📋 Statistiques des Questions\n\n")
            if 'vote_stats' in stats:
                vote_stats = stats['vote_stats']
                f.write("#### 👍 Votes et Scores\n")
                f.write(f"- **Score moyen**: {vote_stats.get('mean', 0):.2f}\n")
                f.write(f"- **Score médian**: {vote_stats.get('median', 0):.2f}\n")
                f.write(f"- **Score maximum**: {vote_stats.get('max', 0)}\n")
                f.write(f"- **Écart-type**: {vote_stats.get('std', 0):.2f}\n\n")
            
            if 'view_stats' in stats:
                view_stats = stats['view_stats']
                f.write("#### 👀 Vues et Visibilité\n")
                f.write(f"- **Vues moyennes**: {view_stats.get('mean', 0):.0f}\n")
                f.write(f"- **Vues médianes**: {view_stats.get('median', 0):.0f}\n")
                f.write(f"- **Vues maximum**: {view_stats.get('max', 0):,}\n")
                f.write(f"- **Écart-type**: {view_stats.get('std', 0):.0f}\n\n")
            
            if 'answer_stats' in stats:
                answer_stats = stats['answer_stats']
                f.write("#### 💬 Réponses et Engagement\n")
                f.write(f"- **Réponses moyennes**: {answer_stats.get('mean', 0):.2f}\n")
                f.write(f"- **Réponses médianes**: {answer_stats.get('median', 0):.2f}\n")
                f.write(f"- **Réponses maximum**: {answer_stats.get('max', 0)}\n")
                f.write(f"- **Taux sans réponse**: {answer_stats.get('unanswered_rate', 0):.1f}%\n\n")
            
            # Statistiques des tags
            if 'tag_stats' in stats:
                tag_stats = stats['tag_stats']
                f.write("### 🏷️ Statistiques des Tags\n\n")
                f.write(f"- **Tags uniques**: {tag_stats.get('total_unique_tags', 0)}\n")
                f.write(f"- **Tags par question (moyenne)**: {tag_stats.get('average_tags_per_question', 0):.2f}\n\n")
                
                if 'most_common_tags' in tag_stats:
                    f.write("#### Top Tags par Popularité\n\n")
                    f.write("| Rang | Tag | Questions |\n")
                    f.write("|------|-----|----------|\n")
                    for i, (tag, count) in enumerate(tag_stats['most_common_tags'][:15], 1):
                        f.write(f"| {i} | `{tag}` | {count} |\n")
                    f.write("\n")
        
        # Performance système
        if 'execution_info' in results:
            exec_info = results['execution_info']
            f.write("### ⚡ Performance du Système\n\n")
            if 'total_duration' in exec_info:
                total_time = exec_info['total_duration']
                questions = exec_info.get('questions_extracted', 0)
                if questions > 0:
                    f.write(f"- **Efficacité globale**: {questions/total_time:.1f} questions/seconde\n")
                f.write(f"- **Temps total d'exécution**: {total_time:.2f} secondes\n")
                
                # Répartition du temps par phase
                phases = ['scraping', 'storage', 'analysis']
                f.write("\n#### Répartition du temps par phase\n\n")
                f.write("| Phase | Temps (s) | Pourcentage |\n")
                f.write("|-------|-----------|-------------|\n")
                for phase in phases:
                    duration = exec_info.get(f'{phase}_duration', 0)
                    if isinstance(duration, (int, float)) and total_time > 0:
                        percentage = (duration / total_time) * 100
                        phase_name = {'scraping': '🔍 Extraction', 'storage': '💾 Stockage', 'analysis': '📊 Analyse'}.get(phase, phase)
                        f.write(f"| {phase_name} | {duration:.2f} | {percentage:.1f}% |\n")
                f.write("\n")
                f.write("| Rang | Auteur | Réputation | Questions |\n")
                f.write("|------|--------|------------|----------|\n")
