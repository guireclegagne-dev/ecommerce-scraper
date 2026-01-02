import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from typing import Dict, List, Optional
import time
import re
from urllib.parse import urljoin, urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartScraper:
    """
    Scraper intelligent capable de s'adapter à différentes structures de sites e-commerce
    """
    
    def __init__(self, use_selenium: bool = False):
        self.use_selenium = use_selenium
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def init_driver(self):
        """Initialise le driver Selenium si nécessaire"""
        if not self.driver:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
    
    def close_driver(self):
        """Ferme le driver Selenium"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def login(self, url: str, username: str, password: str, 
              username_selector: str = None, password_selector: str = None,
              submit_selector: str = None) -> bool:
        """
        Authentification sur un site
        """
        try:
            self.init_driver()
            self.driver.get(url)
            time.sleep(2)
            
            # Détection automatique des champs de login si non fournis
            if not username_selector:
                username_selector = self._detect_login_field('username')
            if not password_selector:
                password_selector = self._detect_login_field('password')
            if not submit_selector:
                submit_selector = self._detect_login_field('submit')
            
            # Remplir les champs
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            username_field.send_keys(username)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.send_keys(password)
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_button.click()
            
            time.sleep(3)
            
            logger.info("Authentification réussie")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification: {str(e)}")
            return False
    
    def _detect_login_field(self, field_type: str) -> str:
        """Détecte automatiquement les sélecteurs de champs de login"""
        selectors = {
            'username': [
                'input[type="email"]',
                'input[name*="email"]',
                'input[name*="username"]',
                'input[id*="email"]',
                'input[id*="username"]',
                '#email', '#username', '#login'
            ],
            'password': [
                'input[type="password"]',
                'input[name*="password"]',
                'input[id*="password"]',
                '#password', '#pass'
            ],
            'submit': [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:contains("Login")',
                'button:contains("Sign in")',
                'button:contains("Connexion")',
                '.login-button', '.submit-button'
            ]
        }
        
        for selector in selectors.get(field_type, []):
            try:
                if self.driver.find_element(By.CSS_SELECTOR, selector):
                    return selector
            except:
                continue
        
        return selectors[field_type][0]  # Retourne le premier par défaut
    
    def scrape_page(self, url: str, selectors: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        Scrape une page avec ou sans sélecteurs personnalisés
        """
        try:
            if self.use_selenium or self.driver:
                return self._scrape_with_selenium(url, selectors)
            else:
                return self._scrape_with_requests(url, selectors)
        except Exception as e:
            logger.error(f"Erreur lors du scraping de {url}: {str(e)}")
            return []
    
    def _scrape_with_requests(self, url: str, selectors: Optional[Dict[str, str]]) -> List[Dict]:
        """Scraping avec requests (plus rapide, sans JS)"""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._extract_products(soup, url, selectors)
    
    def _scrape_with_selenium(self, url: str, selectors: Optional[Dict[str, str]]) -> List[Dict]:
        """Scraping avec Selenium (supporte JS)"""
        self.init_driver()
        self.driver.get(url)
        
        # Attendre que la page charge
        time.sleep(3)
        
        # Scroll pour charger les produits lazy-loaded
        self._scroll_page()
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return self._extract_products(soup, url, selectors)
    
    def _scroll_page(self):
        """Scroll progressif pour charger tout le contenu"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(3):  # Maximum 3 scrolls
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def _extract_products(self, soup: BeautifulSoup, base_url: str, 
                         selectors: Optional[Dict[str, str]]) -> List[Dict]:
        """
        Extrait les produits de la page
        """
        products = []
        
        # Détection automatique des containers de produits
        product_containers = self._detect_product_containers(soup)
        
        for container in product_containers:
            try:
                product = self._extract_product_data(container, base_url, selectors)
                if product and any(product.values()):  # Ne garder que les produits avec au moins une info
                    products.append(product)
            except Exception as e:
                logger.warning(f"Erreur extraction produit: {str(e)}")
                continue
        
        logger.info(f"Nombre de produits extraits: {len(products)}")
        return products
    
    def _detect_product_containers(self, soup: BeautifulSoup) -> List:
        """
        Détecte automatiquement les containers de produits
        """
        # Patterns communs pour les containers de produits
        common_patterns = [
            {'class': re.compile(r'product-item|product-card|item-card|product_item', re.I)},
            {'class': re.compile(r'product|item', re.I)},
            {'data-testid': re.compile(r'product', re.I)},
            {'itemtype': 'https://schema.org/Product'}
        ]
        
        for pattern in common_patterns:
            containers = soup.find_all(['div', 'article', 'li'], pattern, limit=100)
            if len(containers) > 5:  # Au moins 5 produits détectés
                logger.info(f"Containers détectés avec pattern: {pattern}")
                return containers
        
        # Fallback: chercher les éléments répétitifs
        all_divs = soup.find_all('div', class_=True)
        class_counts = {}
        for div in all_divs:
            classes = ' '.join(div.get('class', []))
            class_counts[classes] = class_counts.get(classes, 0) + 1
        
        # Trouver la classe la plus fréquente (probablement les produits)
        if class_counts:
            most_common_class = max(class_counts.items(), key=lambda x: x[1])
            if most_common_class[1] >= 5:
                logger.info(f"Classe la plus fréquente: {most_common_class[0]} ({most_common_class[1]} occurrences)")
                return soup.find_all('div', class_=most_common_class[0].split())
        
        return []
    
    def _extract_product_data(self, container, base_url: str, 
                             selectors: Optional[Dict[str, str]]) -> Dict:
        """
        Extrait les données d'un produit individuel
        """
        product = {
            'marque': '',
            'modele': '',
            'finitions': '',
            'caracteristiques': '',
            'prix': '',
            'url': '',
            'image': '',
            'disponibilite': ''
        }
        
        # Si des sélecteurs personnalisés sont fournis, les utiliser
        if selectors:
            product['marque'] = self._extract_text(container, selectors.get('brand', ''))
            product['modele'] = self._extract_text(container, selectors.get('model', ''))
            product['finitions'] = self._extract_text(container, selectors.get('finish', ''))
            product['caracteristiques'] = self._extract_text(container, selectors.get('specs', ''))
        else:
            # Détection automatique
            product['marque'] = self._detect_brand(container)
            product['modele'] = self._detect_model(container)
            product['finitions'] = self._detect_finish(container)
            product['caracteristiques'] = self._detect_specs(container)
        
        # Extraire le prix
        product['prix'] = self._detect_price(container)
        
        # Extraire l'URL
        product['url'] = self._detect_url(container, base_url)
        
        # Extraire l'image
        product['image'] = self._detect_image(container, base_url)
        
        # Disponibilité
        product['disponibilite'] = self._detect_availability(container)
        
        return product
    
    def _extract_text(self, container, selector: str) -> str:
        """Extrait le texte d'un élément via sélecteur CSS"""
        if not selector:
            return ''
        try:
            element = container.select_one(selector)
            return element.get_text(strip=True) if element else ''
        except:
            return ''
    
    def _detect_brand(self, container) -> str:
        """Détecte automatiquement la marque"""
        patterns = [
            {'class': re.compile(r'brand|manufacturer|marque', re.I)},
            {'data-brand': True},
            {'itemprop': 'brand'}
        ]
        
        for pattern in patterns:
            element = container.find(['span', 'div', 'p', 'a'], pattern)
            if element:
                return element.get_text(strip=True)
        
        return ''
    
    def _detect_model(self, container) -> str:
        """Détecte automatiquement le modèle"""
        patterns = [
            {'class': re.compile(r'product-name|product-title|title|name|model', re.I)},
            {'itemprop': 'name'},
            {'data-name': True}
        ]
        
        for pattern in patterns:
            element = container.find(['h1', 'h2', 'h3', 'h4', 'a', 'span'], pattern)
            if element:
                return element.get_text(strip=True)
        
        # Fallback: premier titre trouvé
        title = container.find(['h1', 'h2', 'h3', 'h4', 'a'])
        return title.get_text(strip=True) if title else ''
    
    def _detect_finish(self, container) -> str:
        """Détecte automatiquement les finitions/variantes"""
        patterns = [
            {'class': re.compile(r'variant|finish|color|colour|size|option', re.I)},
            {'data-variant': True}
        ]
        
        finishes = []
        for pattern in patterns:
            elements = container.find_all(['span', 'div', 'li'], pattern)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) < 50:
                    finishes.append(text)
        
        return ', '.join(finishes) if finishes else ''
    
    def _detect_specs(self, container) -> str:
        """Détecte automatiquement les caractéristiques techniques"""
        patterns = [
            {'class': re.compile(r'spec|feature|characteristic|description|detail', re.I)},
            {'itemprop': 'description'}
        ]
        
        specs = []
        for pattern in patterns:
            elements = container.find_all(['ul', 'div', 'p', 'span'], pattern, limit=5)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and 10 < len(text) < 500:
                    specs.append(text)
        
        return ' | '.join(specs[:3]) if specs else ''  # Max 3 specs
    
    def _detect_price(self, container) -> str:
        """Détecte automatiquement le prix"""
        patterns = [
            {'class': re.compile(r'price|prix|cost', re.I)},
            {'itemprop': 'price'},
            {'data-price': True}
        ]
        
        for pattern in patterns:
            element = container.find(['span', 'div', 'p'], pattern)
            if element:
                text = element.get_text(strip=True)
                # Chercher un pattern de prix
                price_match = re.search(r'[\d\s]+[,.]?\d*\s*[€$£¥]', text)
                if price_match:
                    return price_match.group(0)
        
        return ''
    
    def _detect_url(self, container, base_url: str) -> str:
        """Détecte automatiquement l'URL du produit"""
        link = container.find('a', href=True)
        if link:
            return urljoin(base_url, link['href'])
        return ''
    
    def _detect_image(self, container, base_url: str) -> str:
        """Détecte automatiquement l'image du produit"""
        img = container.find('img', src=True)
        if img:
            return urljoin(base_url, img['src'])
        return ''
    
    def _detect_availability(self, container) -> str:
        """Détecte automatiquement la disponibilité"""
        patterns = [
            {'class': re.compile(r'stock|availability|disponibilit', re.I)},
            {'itemprop': 'availability'}
        ]
        
        for pattern in patterns:
            element = container.find(['span', 'div', 'p'], pattern)
            if element:
                return element.get_text(strip=True)
        
        # Chercher des mots-clés
        text = container.get_text().lower()
        if 'en stock' in text or 'available' in text or 'disponible' in text:
            return 'En stock'
        elif 'rupture' in text or 'out of stock' in text:
            return 'Rupture de stock'
        
        return 'Inconnu'
    
    def scrape_multiple_pages(self, url: str, max_pages: int = 10,
                             selectors: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        Scrape plusieurs pages d'un catalogue
        """
        all_products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping page {page}/{max_pages}...")
            
            # Modifier l'URL pour la pagination (patterns communs)
            page_url = self._generate_page_url(url, page)
            
            products = self.scrape_page(page_url, selectors)
            
            if not products:
                logger.info(f"Aucun produit sur la page {page}, arrêt du scraping")
                break
            
            all_products.extend(products)
            
            # Pause entre les pages
            time.sleep(2)
        
        return all_products
    
    def _generate_page_url(self, base_url: str, page: int) -> str:
        """Génère l'URL pour une page spécifique"""
        if page == 1:
            return base_url
        
        # Patterns communs de pagination
        if '?' in base_url:
            return f"{base_url}&page={page}"
        else:
            return f"{base_url}?page={page}"
    
    def __del__(self):
        """Nettoyage"""
        self.close_driver()