"""
Scraper générique pour tous les sites PrestaShop
Réutilisable pour n'importe quel site utilisant PrestaShop
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from datetime import datetime

class PrestaShopScraper:
    """Scraper universel pour sites PrestaShop"""
    
    def __init__(self):
        self.driver = None
        self.urls_vues = set()
        
    def init_driver(self):
        """Initialiser Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def close_driver(self):
        """Fermer Selenium"""
        if self.driver:
            self.driver.quit()
    
    def scraper_catalogue(self, url_catalogue, nom_site, max_pages=5, sauvegarder=True):
        """
        Scraper un catalogue PrestaShop
        
        Args:
            url_catalogue: URL de la catégorie à scraper
            nom_site: Nom pour identifier dans la BDD
            max_pages: Nombre de pages à parcourir
            sauvegarder: Sauvegarder automatiquement ou non
        
        Returns:
            Liste des produits collectés
        """
        print("=" * 70)
        print(f"🛒 SCRAPING PRESTASHOP - {nom_site.upper()}")
        print("=" * 70)
        print(f"📍 URL: {url_catalogue}")
        print(f"📄 Pages: {max_pages}")
        print("=" * 70)
        
        self.init_driver()
        tous_les_produits = []
        
        for page in range(1, max_pages + 1):
            print(f"\n📄 Page {page}/{max_pages}")
            
            # Construction URL avec pagination
            if page == 1:
                url = url_catalogue
            else:
                separator = '&' if '?' in url_catalogue else '?'
                url = f"{url_catalogue}{separator}page={page}"
            
            print(f"   🔗 {url[:60]}...")
            
            # Charger la page
            self.driver.get(url)
            time.sleep(3)
            
            # Scroll pour lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Parser avec BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Trouver les produits (structure PrestaShop standard)
            produits = soup.find_all('article', class_='product-miniature')
            
            if not produits:
                print(f"   ⚠️  Aucun produit trouvé sur cette page")
                break
            
            print(f"   🔍 {len(produits)} produits détectés")
            
            produits_page = 0
            
            for produit in produits:
                try:
                    produit_data = self._extraire_produit(produit)
                    
                    if produit_data and produit_data['url'] not in self.urls_vues:
                        self.urls_vues.add(produit_data['url'])
                        tous_les_produits.append(produit_data)
                        produits_page += 1
                
                except Exception as e:
                    continue
            
            print(f"   ✅ {produits_page} produits uniques collectés")
            print(f"   📊 Total: {len(tous_les_produits)} produits")
            
            time.sleep(2)  # Pause entre pages
        
        self.close_driver()
        
        # Afficher résumé
        print(f"\n" + "=" * 70)
        print(f"📊 RÉSULTATS: {len(tous_les_produits)} produits uniques collectés")
        print("=" * 70)
        
        if tous_les_produits:
            self._afficher_echantillon(tous_les_produits)
            
            if sauvegarder:
                self._sauvegarder_produits(tous_les_produits, nom_site)
        
        return tous_les_produits
    
    def _extraire_produit(self, produit):
        """Extraire les données d'un produit PrestaShop"""
        
        # URL
        lien = produit.find('a', class_='product-thumbnail')
        if not lien or not lien.get('href'):
            return None
        url_produit = lien['href']
        
        # Titre
        titre_elem = produit.find('h3', class_='h3')
        if not titre_elem:
            titre_elem = produit.find('h2', class_='h3')
        if not titre_elem:
            titre_elem = produit.find('a', class_='product-title')
        
        titre = titre_elem.get_text(strip=True) if titre_elem else ''
        if not titre or len(titre) < 3:
            return None
        
        # Prix
        prix_elem = produit.find('span', class_='price')
        prix = prix_elem.get_text(strip=True) if prix_elem else ''
        
        # Image
        img = produit.find('img')
        image_url = ''
        if img:
            image_url = img.get('data-src', img.get('src', ''))
        
        # Marque (extraite du titre)
        marque = ''
        mots = titre.split()
        if len(mots) > 0:
            premier_mot = mots[0]
            if premier_mot.isupper() or len(premier_mot) < 15:
                marque = premier_mot
        
        # Description courte
        desc = produit.find('div', class_='product-description-short')
        caracteristiques = desc.get_text(strip=True) if desc else ''
        
        return {
            'modele': titre,
            'marque': marque,
            'prix': prix,
            'url': url_produit,
            'image': image_url,
            'disponibilite': 'En stock',
            'finitions': '',
            'caracteristiques': caracteristiques[:200]  # Limiter la taille
        }
    
    def _afficher_echantillon(self, produits, nb=10):
        """Afficher un échantillon de produits"""
        print(f"\n📦 Échantillon ({min(nb, len(produits))} premiers produits):")
        print("-" * 70)
        
        for i, p in enumerate(produits[:nb], 1):
            print(f"\n{i}. {p['modele'][:60]}")
            print(f"   💰 {p['prix']}")
            print(f"   🏷️  {p['marque'] if p['marque'] else 'N/A'}")
    
    def _sauvegarder_produits(self, produits, nom_site):
        """Sauvegarder les produits dans la base"""
        print("\n" + "-" * 70)
        save = input(f"\n💾 Sauvegarder ces {len(produits)} produits ? (o/n): ").lower()
        
        if save == 'o':
            # Charger la configuration pour utiliser la bonne base de données
            import json
            from pathlib import Path
            
            config_file = Path("data/config.json")
            db = None
            
            # Lire la config si elle existe
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    db_type = config.get('database', {}).get('type', 'sqlite')
                    
                    if db_type == 'supabase':
                        print(f"   📊 Utilisation de Supabase...")
                        from database import SupabaseDB
                        db = SupabaseDB(
                            config['database']['url'],
                            config['database']['key']
                        )
                    else:
                        print(f"   📊 Utilisation de SQLite...")
                        from database import SQLiteDB
                        db = SQLiteDB(db_path="data/scraper.db")
                except Exception as e:
                    print(f"   ⚠️ Erreur lecture config: {e}")
                    print(f"   📊 Utilisation de SQLite par défaut...")
                    from database import SQLiteDB
                    db = SQLiteDB(db_path="data/scraper.db")
            else:
                # Pas de config, utiliser SQLite par défaut
                print(f"   📊 Pas de config trouvée, utilisation de SQLite...")
                from database import SQLiteDB
                db = SQLiteDB(db_path="data/scraper.db")
            
            # Sauvegarder
            if db and db.connect():
                db.create_tables()
                count = db.insert_products(produits, site_source=nom_site)
                
                all_products = db.get_products()
                print(f"\n✅ {count} produits sauvegardés!")
                print(f"📊 Total en base: {len(all_products)} produits")
                db.close()
                
                # Proposer export
                export = input("\n📤 Exporter en Excel maintenant ? (o/n): ").lower()
                if export == 'o':
                    self._exporter_excel(produits, nom_site)
    
    def _exporter_excel(self, produits, nom_site):
        """Exporter en Excel"""
        from exporter import DataExporter
        
        exporter = DataExporter()
        nom_fichier = f"{nom_site.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        fichier = exporter.export_to_excel(produits, filename=nom_fichier)
        
        if fichier:
            print(f"\n✅ Export réussi: {fichier}")
            print(f"📂 Dossier: data/exports/")


# Fonction simple pour utilisation directe
def scraper_prestashop_simple(url, nom_site, max_pages=5):
    """
    Fonction simple pour scraper un site PrestaShop
    
    Exemple:
        scraper_prestashop_simple(
            "https://example.com/category",
            "Mon Fournisseur",
            max_pages=3
        )
    """
    scraper = PrestaShopScraper()
    return scraper.scraper_catalogue(url, nom_site, max_pages)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🛒 SCRAPER PRESTASHOP GÉNÉRIQUE")
    print("=" * 70)
    
    url = input("\n📍 URL du catalogue PrestaShop: ").strip()
    nom = input("🏷️  Nom du site: ").strip()
    
    try:
        pages = int(input("📄 Nombre de pages (défaut=5): ").strip() or 5)
    except:
        pages = 5
    
    if url and nom:
        scraper_prestashop_simple(url, nom, pages)
    else:
        print("\n❌ URL et nom requis")