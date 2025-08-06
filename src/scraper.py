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
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.driver = None
        
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
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.config.user_agent}
        )
        
        # Configuration du driver Selenium
        chrome_options = Options()
        if self.config.headless:
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
        
        # Enrichir les données des questions
        enriched_questions = []
        for question in questions[:max_questions]:
            try:
                enriched_question = await self._enrich_question_data(question)
                enriched_questions.append(enriched_question)
                
                # Délai plus long entre les enrichissements
                delay = random.uniform(2, 4)
                await asyncio.sleep(delay)
                
            except ConnectionResetError as e:
                self.logger.error(f"Connexion fermée lors de l'enrichissement de {question.url}: {e}")
                self.logger.info("Utilisation des données de base sans enrichissement")
                enriched_questions.append(question)
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'enrichissement de la question {question.url}: {e}")
                enriched_questions.append(question)
        
        self.logger.info(f"Scraping terminé: {len(enriched_questions)} questions extraites")
        return enriched_questions
    
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
                vote_element = stats.find('div', class_='s-post-summary--stats-item-number')
                if vote_element:
                    vote_count = int(vote_element.get_text(strip=True) or 0)
                
                answer_elements = stats.find_all('div', class_='s-post-summary--stats-item-number')
                if len(answer_elements) > 1:
                    answer_count = int(answer_elements[1].get_text(strip=True) or 0)
            
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
            
            # Date (à enrichir plus tard)
            publication_date = datetime.now()  # Sera mise à jour lors de l'enrichissement
            
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
    
    async def _enrich_question_data(self, question: QuestionData) -> QuestionData:
        """Enrichit les données d'une question en visitant sa page détaillée."""
        try:
            self.driver.get(question.url)
            await asyncio.sleep(random.uniform(1, 2))
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Date de publication
            time_element = soup.find('time', {'itemprop': 'dateCreated'})
            if time_element:
                date_str = time_element.get('datetime')
                if date_str:
                    question.publication_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Nombre de vues
            view_element = soup.find('div', {'title': lambda x: x and 'viewed' in x.lower()})
            if view_element:
                view_text = view_element.get('title', '')
                # Extraire le nombre de vues du texte
                import re
                view_match = re.search(r'(\d{1,3}(?:,\d{3})*)', view_text)
                if view_match:
                    view_count_str = view_match.group(1).replace(',', '')
                    question.view_count = int(view_count_str)
            
            # Réputation de l'auteur
            rep_element = soup.find('div', class_='reputation-score')
            if rep_element:
                rep_text = rep_element.get_text(strip=True)
                # Convertir k, m en nombres
                if 'k' in rep_text.lower():
                    question.author_reputation = int(float(rep_text.lower().replace('k', '')) * 1000)
                elif 'm' in rep_text.lower():
                    question.author_reputation = int(float(rep_text.lower().replace('m', '')) * 1000000)
                else:
                    question.author_reputation = int(rep_text.replace(',', ''))
            
            return question
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enrichissement de {question.url}: {e}")
            return question
    
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
        
        return QuestionData(
            title=api_question.get('title', ''),
            url=api_question.get('link', ''),
            summary=api_question.get('body_markdown', '')[:500] + '...' if len(api_question.get('body_markdown', '')) > 500 else api_question.get('body_markdown', ''),
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
