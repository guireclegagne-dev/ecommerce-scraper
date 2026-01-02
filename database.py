from typing import List, Dict, Optional
import logging
from datetime import datetime
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseInterface(ABC):
    """Interface abstraite pour les différentes bases de données"""
    
    @abstractmethod
    def connect(self):
        """Établir la connexion à la base de données"""
        pass
    
    @abstractmethod
    def create_tables(self):
        """Créer les tables nécessaires"""
        pass
    
    @abstractmethod
    def insert_products(self, products: List[Dict]) -> int:
        """Insérer des produits dans la base"""
        pass
    
    @abstractmethod
    def get_products(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Récupérer des produits"""
        pass
    
    @abstractmethod
    def update_product(self, product_id: int, data: Dict) -> bool:
        """Mettre à jour un produit"""
        pass
    
    @abstractmethod
    def delete_product(self, product_id: int) -> bool:
        """Supprimer un produit"""
        pass
    
    @abstractmethod
    def close(self):
        """Fermer la connexion"""
        pass


class SupabaseDB(DatabaseInterface):
    """Gestionnaire de base de données Supabase"""
    
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client = None
        self.table_name = "produits"
    
    def connect(self):
        """Établir la connexion à Supabase"""
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(self.url, self.key)
            logger.info("Connexion à Supabase établie")
            return True
        except ImportError:
            logger.error("Module supabase non installé. Installez-le avec: pip install supabase")
            return False
        except Exception as e:
            logger.error(f"Erreur de connexion à Supabase: {str(e)}")
            return False
    
    def create_tables(self):
        """
        Créer la table produits dans Supabase
        Note: En Supabase, il est préférable de créer les tables via l'interface SQL
        """
        # Cette fonction fournit le SQL à exécuter manuellement dans Supabase
        sql_schema = """
        CREATE TABLE IF NOT EXISTS produits (
            id BIGSERIAL PRIMARY KEY,
            marque TEXT,
            modele TEXT NOT NULL,
            finitions TEXT,
            caracteristiques TEXT,
            prix TEXT,
            url TEXT,
            image TEXT,
            disponibilite TEXT,
            site_source TEXT,
            date_collecte TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Index pour améliorer les performances
        CREATE INDEX IF NOT EXISTS idx_produits_marque ON produits(marque);
        CREATE INDEX IF NOT EXISTS idx_produits_modele ON produits(modele);
        CREATE INDEX IF NOT EXISTS idx_produits_site ON produits(site_source);
        CREATE INDEX IF NOT EXISTS idx_produits_date ON produits(date_collecte);
        
        -- Trigger pour mettre à jour updated_at automatiquement
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        CREATE TRIGGER update_produits_updated_at BEFORE UPDATE ON produits
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        logger.info("Schéma SQL pour Supabase:")
        logger.info(sql_schema)
        return sql_schema
    
    def insert_products(self, products: List[Dict], site_source: str = "") -> int:
        """Insérer des produits dans Supabase"""
        if not self.client:
            logger.error("Client Supabase non connecté")
            return 0
        
        try:
            # Préparer les données
            products_data = []
            for product in products:
                products_data.append({
                    'marque': product.get('marque', ''),
                    'modele': product.get('modele', ''),
                    'finitions': product.get('finitions', ''),
                    'caracteristiques': product.get('caracteristiques', ''),
                    'prix': product.get('prix', ''),
                    'url': product.get('url', ''),
                    'image': product.get('image', ''),
                    'disponibilite': product.get('disponibilite', ''),
                    'site_source': site_source,
                    'date_collecte': datetime.now().isoformat()
                })
            
            # Insérer dans Supabase
            response = self.client.table(self.table_name).insert(products_data).execute()
            
            logger.info(f"{len(products_data)} produits insérés dans Supabase")
            return len(products_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion dans Supabase: {str(e)}")
            return 0
    
    def get_products(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """Récupérer des produits depuis Supabase"""
        if not self.client:
            logger.error("Client Supabase non connecté")
            return []
        
        try:
            query = self.client.table(self.table_name).select("*")
            
            # Appliquer les filtres
            if filters:
                for key, value in filters.items():
                    if value:
                        query = query.eq(key, value)
            
            response = query.limit(limit).execute()
            return response.data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération depuis Supabase: {str(e)}")
            return []
    
    def update_product(self, product_id: int, data: Dict) -> bool:
        """Mettre à jour un produit dans Supabase"""
        if not self.client:
            logger.error("Client Supabase non connecté")
            return False
        
        try:
            response = self.client.table(self.table_name).update(data).eq('id', product_id).execute()
            logger.info(f"Produit {product_id} mis à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {str(e)}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Supprimer un produit de Supabase"""
        if not self.client:
            logger.error("Client Supabase non connecté")
            return False
        
        try:
            response = self.client.table(self.table_name).delete().eq('id', product_id).execute()
            logger.info(f"Produit {product_id} supprimé")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            return False
    
    def close(self):
        """Fermer la connexion (pas nécessaire avec Supabase)"""
        logger.info("Connexion Supabase fermée")


class SQLiteDB(DatabaseInterface):
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, db_path: str = "data/scraper.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établir la connexion à SQLite"""
        try:
            import sqlite3
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Connexion à SQLite établie: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion à SQLite: {str(e)}")
            return False
    
    def create_tables(self):
        """Créer les tables SQLite"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS produits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marque TEXT,
                    modele TEXT NOT NULL,
                    finitions TEXT,
                    caracteristiques TEXT,
                    prix TEXT,
                    url TEXT,
                    image TEXT,
                    disponibilite TEXT,
                    site_source TEXT,
                    date_collecte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Créer des index
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_marque ON produits(marque)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_modele ON produits(modele)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_site ON produits(site_source)")
            
            self.conn.commit()
            logger.info("Tables SQLite créées")
            return True
        except Exception as e:
            logger.error(f"Erreur création tables SQLite: {str(e)}")
            return False
    
    def insert_products(self, products: List[Dict], site_source: str = "") -> int:
        """Insérer des produits dans SQLite"""
        try:
            count = 0
            for product in products:
                self.cursor.execute("""
                    INSERT INTO produits (
                        marque, modele, finitions, caracteristiques, 
                        prix, url, image, disponibilite, site_source, date_collecte
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product.get('marque', ''),
                    product.get('modele', ''),
                    product.get('finitions', ''),
                    product.get('caracteristiques', ''),
                    product.get('prix', ''),
                    product.get('url', ''),
                    product.get('image', ''),
                    product.get('disponibilite', ''),
                    site_source,
                    datetime.now().isoformat()
                ))
                count += 1
            
            self.conn.commit()
            logger.info(f"{count} produits insérés dans SQLite")
            return count
        except Exception as e:
            logger.error(f"Erreur insertion SQLite: {str(e)}")
            self.conn.rollback()
            return 0
    
    def get_products(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """Récupérer des produits depuis SQLite"""
        try:
            query = "SELECT * FROM produits WHERE 1=1"
            params = []
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query += f" AND {key} = ?"
                        params.append(value)
            
            query += f" LIMIT {limit}"
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération SQLite: {str(e)}")
            return []
    
    def update_product(self, product_id: int, data: Dict) -> bool:
        """Mettre à jour un produit dans SQLite"""
        try:
            set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
            values = list(data.values()) + [product_id]
            
            self.cursor.execute(
                f"UPDATE produits SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            self.conn.commit()
            logger.info(f"Produit {product_id} mis à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour SQLite: {str(e)}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Supprimer un produit de SQLite"""
        try:
            self.cursor.execute("DELETE FROM produits WHERE id = ?", (product_id,))
            self.conn.commit()
            logger.info(f"Produit {product_id} supprimé")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression SQLite: {str(e)}")
            return False
    
    def close(self):
        """Fermer la connexion SQLite"""
        if self.conn:
            self.conn.close()
            logger.info("Connexion SQLite fermée")


class PostgreSQLDB(DatabaseInterface):
    """Gestionnaire de base de données PostgreSQL"""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établir la connexion à PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connexion à PostgreSQL établie")
            return True
        except ImportError:
            logger.error("Module psycopg2 non installé. Installez-le avec: pip install psycopg2-binary")
            return False
        except Exception as e:
            logger.error(f"Erreur de connexion à PostgreSQL: {str(e)}")
            return False
    
    def create_tables(self):
        """Créer les tables PostgreSQL"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS produits (
                    id SERIAL PRIMARY KEY,
                    marque TEXT,
                    modele TEXT NOT NULL,
                    finitions TEXT,
                    caracteristiques TEXT,
                    prix TEXT,
                    url TEXT,
                    image TEXT,
                    disponibilite TEXT,
                    site_source TEXT,
                    date_collecte TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Créer des index
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_marque ON produits(marque)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_modele ON produits(modele)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_site ON produits(site_source)")
            
            self.conn.commit()
            logger.info("Tables PostgreSQL créées")
            return True
        except Exception as e:
            logger.error(f"Erreur création tables PostgreSQL: {str(e)}")
            return False
    
    def insert_products(self, products: List[Dict], site_source: str = "") -> int:
        """Insérer des produits dans PostgreSQL"""
        try:
            count = 0
            for product in products:
                self.cursor.execute("""
                    INSERT INTO produits (
                        marque, modele, finitions, caracteristiques, 
                        prix, url, image, disponibilite, site_source, date_collecte
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product.get('marque', ''),
                    product.get('modele', ''),
                    product.get('finitions', ''),
                    product.get('caracteristiques', ''),
                    product.get('prix', ''),
                    product.get('url', ''),
                    product.get('image', ''),
                    product.get('disponibilite', ''),
                    site_source,
                    datetime.now()
                ))
                count += 1
            
            self.conn.commit()
            logger.info(f"{count} produits insérés dans PostgreSQL")
            return count
        except Exception as e:
            logger.error(f"Erreur insertion PostgreSQL: {str(e)}")
            self.conn.rollback()
            return 0
    
    def get_products(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """Récupérer des produits depuis PostgreSQL"""
        try:
            query = "SELECT * FROM produits WHERE 1=1"
            params = []
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query += f" AND {key} = %s"
                        params.append(value)
            
            query += f" LIMIT {limit}"
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur récupération PostgreSQL: {str(e)}")
            return []
    
    def update_product(self, product_id: int, data: Dict) -> bool:
        """Mettre à jour un produit dans PostgreSQL"""
        try:
            set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
            values = list(data.values()) + [product_id]
            
            self.cursor.execute(
                f"UPDATE produits SET {set_clause}, updated_at = NOW() WHERE id = %s",
                values
            )
            self.conn.commit()
            logger.info(f"Produit {product_id} mis à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour PostgreSQL: {str(e)}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Supprimer un produit de PostgreSQL"""
        try:
            self.cursor.execute("DELETE FROM produits WHERE id = %s", (product_id,))
            self.conn.commit()
            logger.info(f"Produit {product_id} supprimé")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression PostgreSQL: {str(e)}")
            return False
    
    def close(self):
        """Fermer la connexion PostgreSQL"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Connexion PostgreSQL fermée")


class DatabaseFactory:
    """Factory pour créer la bonne instance de base de données"""
    
    @staticmethod
    def create(config: Dict) -> DatabaseInterface:
        """Créer une instance de base de données selon la configuration"""
        db_type = config.get('type', 'sqlite').lower()
        
        if db_type == 'supabase':
            return SupabaseDB(
                url=config.get('url', ''),
                key=config.get('key', '')
            )
        
        elif db_type == 'postgresql':
            return PostgreSQLDB(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5432),
                database=config.get('database', 'scraper_db'),
                user=config.get('user', 'postgres'),
                password=config.get('password', '')
            )
        
        elif db_type == 'sqlite':
            return SQLiteDB(
                db_path=config.get('path', 'data/scraper.db')
            )
        
        else:
            logger.warning(f"Type de base de données non supporté: {db_type}, utilisation de SQLite par défaut")
            return SQLiteDB()