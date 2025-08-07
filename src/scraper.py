"""
Stack Overflow Scraper Module
============================

Module principal pour le scraping des données Stack Overflow.
Utilise Selenium et BeautifulSoup pour extraire les informations des questions.

Classes:
    StackOverflowScraper: Classe principale pour le scraping
    QuestionData: Modèle de données pour une question
"""

import asyncio
import aiohttp
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from bs4 import BeautifulSoup
import time
import random


@dataclass
class QuestionData:
    """Modèle de données pour une question Stack Overflow."""
    title: str
    url: str
    summary: str
    tags: List[str]
    author_name: str
    author_reputation: int
    author_profile_url: str
    publication_date: datetime
    view_count: int
    vote_count: int
    answer_count: int
    question_id: int


class StackOverflowScraper:
    """
    Scraper pour extraire les données de Stack Overflow.
    
    Utilise Selenium pour la navigation et BeautifulSoup pour le parsing HTML.
    Supporte également l'API officielle Stack Overflow.
    """
    
    BASE_URL = "https://stackoverflow.com"
    API_BASE_URL = "https://api.stackexchange.com/2.3"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le scraper avec la configuration fournie.
        
        Args:
            config: Configuration contenant les paramètres du scraper
        """
        self.config = config
        
        # Gérer les deux types de configuration possibles
        if hasattr(config, 'api_config'):
            # Objet Config complet
            self.api_config = config.api_config
            self.scraper_config = config.scraper_config
        elif hasattr(config, 'get'):
            # Dictionnaire
            self.api_config = config.get('api', {})
            self.scraper_config = config
        else:
            # ScraperConfig seul - pas d'API config disponible
            from .config import APIConfig
            self.api_config = APIConfig()
            self.scraper_config = config
            
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.driver = None
        
    def _get_config_value(self, key: str, default=None):
        """
        Méthode helper pour accéder aux valeurs de configuration.
        
        Args:
            key: Clé de configuration
            default: Valeur par défaut
            
        Returns:
            Valeur de configuration
        """
        if hasattr(self.scraper_config, 'get'):
            # Configuration dictionnaire
            return self.scraper_config.get(key, default)
        else:
            # Configuration dataclass
            return getattr(self.scraper_config, key, default)
        
    async def __aenter__(self):
        """Context manager entry."""
        await self.setup_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.cleanup()
    
    async def setup_session(self) -> None:
        """Configure la session HTTP et le driver Selenium."""
        # Configuration de la session aiohttp
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self._get_config_value('timeout', 30))
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self._get_config_value('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')}
        )
        
        # Configuration du driver Selenium
        chrome_options = Options()
        if self._get_config_value('headless', True):
            chrome_options.add_argument('--headless')
        
        # Options de base pour la stabilité
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Options pour supprimer les erreurs GPU et DevTools
        chrome_options.add_argument('--disable-gpu-sandbox')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--use-gl=swiftshader')  # Force software rendering
        chrome_options.add_argument('--disable-angle')      # Disable ANGLE OpenGL backend
        chrome_options.add_argument('--disable-3d-apis')    # Disable WebGL and other 3D APIs
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--log-level=3')  # Supprime les logs INFO, WARNING, ERROR
        chrome_options.add_argument('--remote-debugging-port=0')  # Supprime le message DevTools
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    async def cleanup(self) -> None:
        """Nettoie les ressources."""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()
    
    async def close(self) -> None:
        """Alias pour cleanup() - ferme toutes les ressources."""
        await self.cleanup()
    
    async def scrape_questions(
        self,
        max_questions: int = 100,
        tags: Optional[List[str]] = None,
        sort_by: str = "newest"
    ) -> List[QuestionData]:
        """
        Scrape les questions Stack Overflow.
        
        Args:
            max_questions: Nombre maximum de questions à extraire
            tags: Liste des tags à filtrer
            sort_by: Critère de tri ('newest', 'active', 'votes')
            
        Returns:
            Liste des données de questions extraites
        """
        self.logger.info(f"Début du scraping de {max_questions} questions")
        
        questions = []
        page = 1
        questions_per_page = 50
        
        while len(questions) < max_questions:
            # Construction de l'URL
            url = self._build_search_url(page, tags, sort_by)
            
            try:
                # Navigation vers la page
                self.driver.get(url)
                await asyncio.sleep(random.uniform(1, 3))  # Délai aléatoire
                
                # Attendre que la page se charge
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "s-post-summary"))
                )
                
                # Parser la page
                page_questions = await self._parse_questions_page()
                
                if not page_questions:
                    self.logger.warning(f"Aucune question trouvée sur la page {page}")
                    break
                
                questions.extend(page_questions)
                self.logger.info(f"Page {page}: {len(page_questions)} questions extraites")
                
                page += 1
                
                # Respecter les limites de taux avec délai plus long
                delay = random.uniform(3, 8)  # Délai plus long entre les pages
                self.logger.info(f"Attente de {delay:.1f} secondes avant la page suivante...")
                await asyncio.sleep(delay)
                
            except TimeoutException:
                self.logger.error(f"Timeout lors du chargement de la page {page}")
                # Attendre plus longtemps en cas d'erreur
                await asyncio.sleep(10)
                break
            except ConnectionResetError as e:
                self.logger.error(f"Connexion fermée par Stack Overflow sur la page {page}: {e}")
                self.logger.info("Attente de 30 secondes avant de continuer...")
                await asyncio.sleep(30)
                break
            except Exception as e:
                self.logger.error(f"Erreur lors du scraping de la page {page}: {e}")
                # Attendre avant de continuer
                await asyncio.sleep(5)
                break
        
        # Retourner les questions extraites (toutes les données sont récupérées dès l'extraction initiale)
        final_questions = questions[:max_questions]
        self.logger.info(f"Scraping terminé: {len(final_questions)} questions extraites")
        return final_questions
    
    def _build_search_url(
        self,
        page: int,
        tags: Optional[List[str]] = None,
        sort_by: str = "newest"
    ) -> str:
        """Construit l'URL de recherche Stack Overflow."""
        if tags:
            tag_string = "+".join([f"[{tag}]" for tag in tags])
            return f"{self.BASE_URL}/questions/tagged/{tag_string}?tab={sort_by}&page={page}"
        else:
            return f"{self.BASE_URL}/questions?tab={sort_by}&page={page}"
    
    async def _parse_questions_page(self) -> List[QuestionData]:
        """Parse une page de questions Stack Overflow."""
        questions = []
        
        # Obtenir le HTML de la page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Trouver tous les éléments de question
        question_elements = soup.find_all('div', class_='s-post-summary')
        
        for element in question_elements:
            try:
                question_data = self._extract_question_basic_data(element)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'extraction d'une question: {e}")
                continue
        
        return questions
    
    def _extract_question_basic_data(self, element) -> Optional[QuestionData]:
        """Extrait les données de base d'une question depuis un élément HTML."""
        try:
            # Titre et URL
            title_element = element.find('h3', class_='s-post-summary--content-title')
            title_link = title_element.find('a') if title_element else None
            
            if not title_link:
                return None
                
            title = title_link.get_text(strip=True)
            relative_url = title_link.get('href')
            url = urljoin(self.BASE_URL, relative_url)
            question_id = int(relative_url.split('/')[2])
            
            # Debug pour vérifier les titres
            self.logger.debug(f"🔍 Titre extrait: '{title}' | URL: {relative_url}")
            
            # Résumé/extrait
            summary_element = element.find('div', class_='s-post-summary--content-excerpt')
            summary = summary_element.get_text(strip=True) if summary_element else ""
            
            # Tags
            tags_container = element.find('div', class_='s-post-summary--meta-tags')
            tags = []
            if tags_container:
                tag_elements = tags_container.find_all('a', class_='post-tag')
                tags = [tag.get_text(strip=True) for tag in tag_elements]
            
            # Statistiques
            stats = element.find('div', class_='s-post-summary--stats')
            vote_count = 0
            answer_count = 0
            view_count = 0
            
            if stats:
                # Chercher tous les éléments de statistiques
                stat_items = stats.find_all('div', class_='s-post-summary--stats-item')
                
                for stat_item in stat_items:
                    stat_title = stat_item.get('title', '').lower()  # Renommé pour éviter la collision
                    number_element = stat_item.find('span', class_='s-post-summary--stats-item-number')
                    
                    if number_element:
                        try:
                            value = int(number_element.get_text(strip=True) or 0)
                            
                            if 'score' in stat_title or 'votes' in stat_title:
                                vote_count = value
                            elif 'answer' in stat_title:
                                answer_count = value
                            elif 'view' in stat_title:
                                view_count = value
                        except (ValueError, TypeError):
                            continue
            
            # Informations de l'auteur (basiques)
            author_element = element.find('div', class_='s-user-card--link')
            author_name = "Unknown"
            author_profile_url = ""
            author_reputation = 0
            
            if author_element:
                author_link = author_element.find('a')
                if author_link:
                    author_name = author_link.get_text(strip=True)
                    author_profile_url = urljoin(self.BASE_URL, author_link.get('href', ''))
            
            # Récupération de la réputation depuis la page de liste
            user_card = element.find('div', class_='s-user-card')
            if user_card:
                # Essayer plusieurs sélecteurs pour la réputation
                rep_element = user_card.find('span', title=lambda x: x and 'reputation' in x.lower())
                if not rep_element:
                    rep_element = user_card.find('span', class_='todo-no-class-here')
                
                if rep_element:
                    rep_text = rep_element.get_text(strip=True)
                    try:
                        # Convertir k, m en nombres
                        if 'k' in rep_text.lower():
                            author_reputation = int(float(rep_text.lower().replace('k', '')) * 1000)
                        elif 'm' in rep_text.lower():
                            author_reputation = int(float(rep_text.lower().replace('m', '')) * 1000000)
                        else:
                            author_reputation = int(rep_text.replace(',', ''))
                    except (ValueError, TypeError):
                        author_reputation = 0
            
            # Date depuis la page de liste (plus précise que datetime.now())
            publication_date = datetime.now()  # Valeur par défaut
            time_element = element.find('span', class_='relativetime')
            if time_element and time_element.get('title'):
                try:
                    # Format: '2025-08-06 10:39:52Z'
                    date_str = time_element.get('title')
                    if date_str.endswith('Z'):
                        date_str = date_str[:-1] + '+00:00'
                    publication_date = datetime.fromisoformat(date_str)
                except (ValueError, AttributeError):
                    pass  # Garder la valeur par défaut
            
            return QuestionData(
                title=title,
                url=url,
                summary=summary,
                tags=tags,
                author_name=author_name,
                author_reputation=author_reputation,
                author_profile_url=author_profile_url,
                publication_date=publication_date,
                view_count=view_count,
                vote_count=vote_count,
                answer_count=answer_count,
                question_id=question_id
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des données de base: {e}")
            return None
    
    async def fetch_via_api(
        self,
        max_questions: int = 100,
        tags: Optional[List[str]] = None,
        sort_by: str = "creation"
    ) -> List[QuestionData]:
        """
        Utilise l'API officielle Stack Overflow pour récupérer les données.
        
        Args:
            max_questions: Nombre maximum de questions
            tags: Tags à filtrer
            sort_by: Critère de tri ('creation', 'activity', 'votes')
            
        Returns:
            Liste des questions extraites via l'API
        """
        self.logger.info(f"Récupération via API de {max_questions} questions")
        
        questions = []
        page = 1
        page_size = min(100, max_questions)  # API limite à 100 par page
        
        while len(questions) < max_questions:
            try:
                # Construction des paramètres
                params = {
                    'order': 'desc',
                    'sort': sort_by,
                    'site': 'stackoverflow',
                    'page': page,
                    'pagesize': page_size,
                    'filter': 'withbody'  # Inclut le corps de la question
                }
                
                # Ajouter l'API key si disponible
                if hasattr(self.api_config, 'key') and self.api_config.key:
                    params['key'] = self.api_config.key
                    self.logger.info("Utilisation de l'API key pour des quotas étendus")
                elif hasattr(self.api_config, 'get') and self.api_config.get('key'):
                    params['key'] = self.api_config['key']
                    self.logger.info("Utilisation de l'API key pour des quotas étendus")
                
                if tags:
                    params['tagged'] = ';'.join(tags)
                
                # Requête API
                async with self.session.get(
                    f"{self.API_BASE_URL}/questions",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        api_questions = data.get('items', [])
                        
                        if not api_questions:
                            break
                        
                        # Conversion des données API vers notre modèle
                        for api_question in api_questions:
                            question_data = self._convert_api_to_question_data(api_question)
                            questions.append(question_data)
                        
                        self.logger.info(f"Page {page}: {len(api_questions)} questions récupérées")
                        page += 1
                        
                        # Respecter les limites de l'API (30 requêtes par seconde max)
                        await asyncio.sleep(0.1)
                        
                    else:
                        self.logger.error(f"Erreur API: {response.status}")
                        break
                        
            except Exception as e:
                self.logger.error(f"Erreur lors de la requête API: {e}")
                break
        
        return questions[:max_questions]
    
    def _convert_api_to_question_data(self, api_question: Dict) -> QuestionData:
        """Convertit une réponse de l'API en QuestionData."""
        owner = api_question.get('owner', {})
        
        # Récupérer le contenu - l'API retourne 'body' (HTML) avec le filtre 'withbody'
        body_content = api_question.get('body', '')
        # Limiter la taille du résumé et nettoyer le HTML basique
        if body_content:
            # Nettoyage basique du HTML (enlever les balises les plus communes)
            import re
            # Enlever les balises HTML courantes tout en gardant le contenu
            clean_content = re.sub(r'<[^>]+>', '', body_content)
            # Nettoyer les entités HTML
            clean_content = clean_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            # Limiter à 500 caractères
            summary = clean_content[:500] + '...' if len(clean_content) > 500 else clean_content
        else:
            summary = ''
        
        return QuestionData(
            title=api_question.get('title', ''),
            url=api_question.get('link', ''),
            summary=summary,
            tags=api_question.get('tags', []),
            author_name=owner.get('display_name', 'Unknown'),
            author_reputation=owner.get('reputation', 0),
            author_profile_url=owner.get('link', ''),
            publication_date=datetime.fromtimestamp(api_question.get('creation_date', 0)),
            view_count=api_question.get('view_count', 0),
            vote_count=api_question.get('score', 0),
            answer_count=api_question.get('answer_count', 0),
            question_id=api_question.get('question_id', 0)
        )
