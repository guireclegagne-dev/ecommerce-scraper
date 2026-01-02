# 🛒 E-Commerce Scraper - Guide d'Installation et d'Utilisation

## 📋 Table des matières
1. [Installation](#installation)
2. [Configuration initiale](#configuration-initiale)
3. [Utilisation](#utilisation)
4. [Configuration avancée](#configuration-avancée)
5. [Résolution des problèmes](#résolution-des-problèmes)

---

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de packages Python)
- Chrome ou Chromium (pour Selenium)

### Étape 1 : Installation des dépendances

```bash
# Installer toutes les dépendances
pip install -r requirements.txt

# OU installer manuellement
pip install streamlit requests beautifulsoup4 selenium APScheduler supabase pandas openpyxl
```

### Étape 2 : Installation du driver Chrome (pour Selenium)

```bash
# Le driver sera installé automatiquement au premier lancement
# Ou installez-le manuellement :
pip install webdriver-manager
```

### Étape 3 : Lancer l'application

```bash
streamlit run app.py
```

L'application sera accessible à l'adresse : **http://localhost:8501**

---

## ⚙️ Configuration initiale

### 1️⃣ Configuration de Supabase

#### Option A : Via l'interface web
1. Allez dans **Configuration > Base de données**
2. Sélectionnez "supabase"
3. Entrez votre **URL du projet** (https://xxxxx.supabase.co)
4. Entrez votre **clé API** (anon key)
5. Cliquez sur **Sauvegarder**

#### Option B : Créer les tables dans Supabase
1. Connectez-vous à votre projet Supabase
2. Allez dans **SQL Editor**
3. Exécutez le script suivant :

```sql
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
```

### 2️⃣ Ajouter votre premier site

1. Allez dans **Gestion des Sites > Ajouter un site**
2. Remplissez les informations :
   - **Nom du site** : Ex: "Amazon France"
   - **URL du catalogue** : L'URL de la page produits
   - **Type** : E-commerce / Marketplace
   - **Authentification** : Cochez si le site nécessite un login
3. Cliquez sur **Ajouter le site**

### 3️⃣ Configurer l'authentification (si nécessaire)

Si un site nécessite une authentification :

1. Allez dans **Configuration > Identifiants**
2. Sélectionnez le site
3. Entrez vos identifiants
4. Sauvegardez

⚠️ **Important** : Les identifiants sont stockés localement dans `data/credentials/`. Assurez-vous de protéger ce dossier.

### 4️⃣ Activer la collecte automatique

1. Allez dans **Configuration > Planification**
2. Cochez **Activer la collecte automatique quotidienne**
3. Choisissez l'heure (par défaut 09:00)
4. Sauvegardez

---

## 📖 Utilisation

### Dashboard
Le dashboard affiche :
- Nombre de sites surveillés
- Sites actifs
- Produits collectés
- Dernière collecte
- Activité récente

### Lancer une collecte manuelle
1. Depuis le **Dashboard**
2. Cliquez sur **🚀 Lancer une collecte maintenant**
3. Attendez la fin du processus

### Gérer les sites

#### Ajouter un site
- **Gestion des Sites > Ajouter un site**
- Remplissez le formulaire
- Les sélecteurs CSS sont optionnels (détection automatique)

#### Modifier un site
- **Gestion des Sites > Liste des sites**
- Développez le site à modifier
- Ajustez les paramètres

#### Désactiver/Supprimer un site
- **Gestion des Sites > Liste des sites**
- Cliquez sur **Désactiver** ou **Supprimer**

### Exporter les données

1. Allez dans **Export**
2. Choisissez le format (CSV, Excel, JSON)
3. Sélectionnez les sites et champs
4. Cliquez sur **Exporter**

Les fichiers sont sauvegardés dans `data/exports/`

### Consulter les logs

1. Allez dans **Logs**
2. Filtrez par date, site ou statut
3. Consultez les détails de chaque collecte

---

## 🔧 Configuration avancée

### Sélecteurs CSS personnalisés

Pour une meilleure précision, vous pouvez définir des sélecteurs CSS :

```
Marque : .product-brand, [data-brand]
Modèle : .product-title, h2.name
Finitions : .variant-selector, .color-option
Caractéristiques : .specs ul, .features
```

**Astuce** : Utilisez les outils de développement de votre navigateur (F12) pour identifier les sélecteurs.

### Utiliser une autre base de données

#### SQLite (local)
```python
# Dans Configuration > Base de données
Type : sqlite
Chemin : data/scraper.db
```

#### PostgreSQL
```python
# Dans Configuration > Base de données
Type : postgresql
Hôte : localhost
Port : 5432
Base : scraper_db
Utilisateur : postgres
Mot de passe : ****
```

### Ajuster le nombre de pages scrapées

Éditez `scheduler.py` ligne 67 :
```python
products = scraper.scrape_multiple_pages(
    site['url'],
    max_pages=10,  # Changez cette valeur
    selectors=selectors
)
```

### Mode headless (sans interface Chrome)

Le mode headless est activé par défaut. Pour le désactiver :

Éditez `scraper.py` ligne 34 :
```python
chrome_options.add_argument('--headless')  # Commentez cette ligne
```

---

## 🐛 Résolution des problèmes

### Erreur : "Module not found"
```bash
# Réinstallez les dépendances
pip install -r requirements.txt --force-reinstall
```

### Erreur : "Chrome driver not found"
```bash
# Installez le gestionnaire de driver
pip install webdriver-manager
```

### Erreur de connexion Supabase
- Vérifiez votre URL et clé API
- Vérifiez que les tables sont créées
- Vérifiez votre connexion internet

### Aucun produit collecté
1. Vérifiez l'URL du site (doit pointer vers une page de catalogue)
2. Le site utilise peut-être du JavaScript → Activez Selenium
3. Ajoutez des sélecteurs CSS personnalisés
4. Consultez les logs pour plus de détails

### Authentification échoue
1. Vérifiez les identifiants
2. Le site utilise peut-être un CAPTCHA
3. Essayez d'augmenter les temps d'attente dans `scraper.py`

### La collecte automatique ne se lance pas
1. Vérifiez que la planification est activée
2. Vérifiez l'heure configurée
3. Redémarrez l'application

---

## 📁 Structure des fichiers

```
projet/
├── app.py                 # Application principale Streamlit
├── scraper.py            # Module de scraping
├── database.py           # Gestion des bases de données
├── scheduler.py          # Planification automatique
├── exporter.py           # Export des données
├── requirements.txt      # Dépendances
├── README.md            # Ce fichier
└── data/                # Données de l'application
    ├── config.json      # Configuration
    ├── sites.json       # Liste des sites
    ├── credentials/     # Identifiants (sécurisés)
    ├── logs/           # Logs des collectes
    └── exports/        # Fichiers exportés
```

---

## 🔐 Sécurité

⚠️ **Recommandations importantes** :

1. **Ne partagez jamais vos identifiants** stockés dans `data/credentials/`
2. **Protégez votre clé API Supabase** (ne la commitez pas dans Git)
3. **Utilisez un fichier .env** pour les variables sensibles
4. **Respectez les robots.txt** des sites scrapés
5. **Ajoutez des délais** entre les requêtes pour ne pas surcharger les serveurs

---

## 📊 Performances

### Optimisations
- **Mode requests** : Plus rapide, sans JavaScript (par défaut)
- **Mode Selenium** : Plus lent, avec JavaScript (pour sites complexes)
- **Pagination** : Limitée à 5 pages par défaut (configurable)
- **Délais** : 2 secondes entre chaque page

### Capacités
- **Sites surveillés** : Illimité
- **Produits** : Des milliers par collecte
- **Fréquence** : Quotidienne recommandée

---

## 🆘 Support

Pour toute question ou problème :
1. Consultez les logs dans l'application
2. Vérifiez la documentation de chaque module
3. Testez avec un seul site d'abord

---

## 📝 Notes importantes

### Légalité du scraping
- Respectez les conditions d'utilisation des sites
- Consultez les fichiers robots.txt
- N'utilisez pas cet outil à des fins commerciales sans autorisation
- Respectez les limites de taux (rate limits)

### Bonnes pratiques
- Testez toujours sur un petit échantillon d'abord
- Surveillez les logs pour détecter les erreurs
- Mettez à jour les sélecteurs si les sites changent
- Faites des sauvegardes régulières de votre base de données

---

## 🎯 Fonctionnalités futures

Améliorations possibles :
- ✅ Export automatique vers Google Drive
- ✅ Notifications par email
- ✅ Détection automatique des changements de prix
- ✅ Interface de comparaison de prix
- ✅ API REST pour accès externe
- ✅ Dashboard de visualisation avancé

---

**Version** : 1.0
**Date** : Janvier 2025
