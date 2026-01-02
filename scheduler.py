from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import json
from pathlib import Path
from typing import List, Dict
from scraper import SmartScraper
from database import DatabaseFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Gestionnaire de planification pour les collectes automatiques
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.data_dir = Path("data")
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True, parents=True)
        
    def load_config(self) -> Dict:
        """Charger la configuration"""
        config_file = self.data_dir / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def load_sites(self) -> List[Dict]:
        """Charger la liste des sites"""
        sites_file = self.data_dir / "sites.json"
        if sites_file.exists():
            with open(sites_file, 'r') as f:
                return json.load(f)
        return []
    
    def load_credentials(self, site_id: int) -> Dict:
        """Charger les identifiants d'un site"""
        cred_file = self.data_dir / "credentials" / f"{site_id}.json"
        if cred_file.exists():
            with open(cred_file, 'r') as f:
                return json.load(f)
        return {}
    
    def scrape_site(self, site: Dict) -> Dict:
        """
        Scraper un site individuel
        """
        logger.info(f"Début du scraping de {site['name']}...")
        
        start_time = datetime.now()
        result = {
            'site': site['name'],
            'url': site['url'],
            'timestamp': start_time.isoformat(),
            'status': 'success',
            'products_collected': 0,
            'errors': []
        }
        
        try:
            # Initialiser le scraper
            use_selenium = site.get('requires_auth', False)
            scraper = SmartScraper(use_selenium=use_selenium)
            
            # Authentification si nécessaire
            if site.get('requires_auth', False):
                credentials = self.load_credentials(site['id'])
                if credentials:
                    login_success = scraper.login(
                        site['url'],
                        credentials.get('username', ''),
                        credentials.get('password', '')
                    )
                    if not login_success:
                        result['status'] = 'error'
                        result['errors'].append("Échec de l'authentification")
                        return result
                else:
                    result['status'] = 'error'
                    result['errors'].append("Identifiants manquants")
                    return result
            
            # Scraper les produits
            selectors = site.get('selectors')
            products = scraper.scrape_multiple_pages(
                site['url'],
                max_pages=5,  # Limiter à 5 pages par défaut
                selectors=selectors
            )
            
            result['products_collected'] = len(products)
            
            # Sauvegarder dans la base de données
            if products:
                config = self.load_config()
                db_config = config.get('database', {})
                
                db = DatabaseFactory.create(db_config)
                if db.connect():
                    db.create_tables()
                    inserted = db.insert_products(products, site_source=site['name'])
                    result['products_inserted'] = inserted
                    db.close()
                    logger.info(f"{inserted} produits sauvegardés dans la base de données")
                else:
                    result['errors'].append("Erreur de connexion à la base de données")
            
            # Nettoyer
            scraper.close_driver()
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
            logger.error(f"Erreur lors du scraping de {site['name']}: {str(e)}")
        
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            result['duration_seconds'] = duration
            
            # Sauvegarder le log
            self.save_log(result)
            
            logger.info(f"Scraping de {site['name']} terminé en {duration:.1f}s")
        
        return result
    
    def scrape_all_sites(self):
        """
        Scraper tous les sites actifs
        """
        logger.info("========== DÉBUT DE LA COLLECTE AUTOMATIQUE ==========")
        
        sites = self.load_sites()
        active_sites = [s for s in sites if s.get('active', True)]
        
        if not active_sites:
            logger.warning("Aucun site actif à scraper")
            return
        
        logger.info(f"Scraping de {len(active_sites)} sites...")
        
        results = []
        for site in active_sites:
            result = self.scrape_site(site)
            results.append(result)
        
        # Résumé
        total_products = sum(r.get('products_collected', 0) for r in results)
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        logger.info("========== RÉSUMÉ DE LA COLLECTE ==========")
        logger.info(f"Sites scrapés: {len(results)}")
        logger.info(f"Succès: {successful}, Échecs: {failed}")
        logger.info(f"Produits collectés: {total_products}")
        logger.info("========================================")
    
    def save_log(self, log_data: Dict):
        """Sauvegarder un log de collecte"""
        log_file = self.logs_dir / f"scraping_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    
    def get_logs(self, date: str = None, limit: int = 100) -> List[Dict]:
        """Récupérer les logs de collecte"""
        if date:
            log_file = self.logs_dir / f"scraping_{date}.jsonl"
            files = [log_file] if log_file.exists() else []
        else:
            files = sorted(self.logs_dir.glob("scraping_*.jsonl"), reverse=True)
        
        logs = []
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
                        if len(logs) >= limit:
                            return logs
        
        return logs
    
    def setup_schedule(self, hour: int = 9, minute: int = 0):
        """
        Configurer la planification quotidienne
        """
        # Supprimer les jobs existants
        self.scheduler.remove_all_jobs()
        
        # Ajouter le job quotidien
        self.scheduler.add_job(
            func=self.scrape_all_sites,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_scraping',
            name='Collecte quotidienne automatique',
            replace_existing=True
        )
        
        logger.info(f"Planification configurée: tous les jours à {hour:02d}:{minute:02d}")
    
    def start(self):
        """Démarrer le scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler démarré")
    
    def stop(self):
        """Arrêter le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler arrêté")
    
    def is_running(self) -> bool:
        """Vérifier si le scheduler est actif"""
        return self.scheduler.running
    
    def get_next_run_time(self):
        """Obtenir la prochaine exécution planifiée"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            return jobs[0].next_run_time
        return None


# Instance globale du scheduler
scheduler_instance = ScraperScheduler()


def init_scheduler():
    """Initialiser le scheduler au démarrage de l'application"""
    config = scheduler_instance.load_config()
    scheduler_config = config.get('scheduler', {})
    
    if scheduler_config.get('enabled', False):
        time_str = scheduler_config.get('time', '09:00')
        hour, minute = map(int, time_str.split(':'))
        
        scheduler_instance.setup_schedule(hour=hour, minute=minute)
        scheduler_instance.start()
        
        next_run = scheduler_instance.get_next_run_time()
        if next_run:
            logger.info(f"Prochaine collecte automatique: {next_run}")
    else:
        logger.info("Planification automatique désactivée")


# Démarrer le scheduler au chargement du module
if __name__ != "__main__":
    init_scheduler()