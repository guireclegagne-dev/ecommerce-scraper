import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="E-Commerce Scraper",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des dossiers
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "sites").mkdir(exist_ok=True)
(DATA_DIR / "logs").mkdir(exist_ok=True)
(DATA_DIR / "credentials").mkdir(exist_ok=True)

# Fichiers de configuration
CONFIG_FILE = DATA_DIR / "config.json"
SITES_FILE = DATA_DIR / "sites.json"

# Initialisation de la session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Chargement de la configuration
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "database": {
            "type": "supabase",
            "url": "",
            "key": ""
        },
        "scheduler": {
            "enabled": False,
            "time": "09:00"
        }
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_sites():
    if SITES_FILE.exists():
        with open(SITES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_sites(sites):
    with open(SITES_FILE, 'w') as f:
        json.dump(sites, f, indent=2)

# Sidebar navigation
with st.sidebar:
    st.title("🛒 E-Commerce Scraper")
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "🌐 Gestion des Sites", "⚙️ Configuration", "📋 Logs", "📤 Export"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption(f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Page Dashboard
if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    sites = load_sites()
    
    with col1:
        st.metric("Sites surveillés", len(sites))
    
    with col2:
        active_sites = sum(1 for s in sites if s.get('active', True))
        st.metric("Sites actifs", active_sites)
    
    with col3:
        st.metric("Produits collectés", "0")
    
    with col4:
        st.metric("Dernière collecte", "Jamais")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Activité récente")
        if sites:
            for site in sites[:5]:
                with st.container():
                    st.write(f"🔗 **{site['name']}**")
                    st.caption(f"URL: {site['url']}")
                    st.caption(f"Statut: {'✅ Actif' if site.get('active', True) else '❌ Inactif'}")
                    st.markdown("---")
        else:
            st.info("Aucun site configuré. Ajoutez votre premier site dans 'Gestion des Sites'.")
    
    with col2:
        st.subheader("🔔 Notifications")
        st.info("Système prêt à démarrer")
        
    st.markdown("---")
    
    if st.button("🚀 Lancer une collecte maintenant", type="primary", use_container_width=True):
        with st.spinner("Collecte en cours..."):
            st.success("Collecte terminée ! (Fonctionnalité en cours d'implémentation)")

# Page Gestion des Sites
elif page == "🌐 Gestion des Sites":
    st.title("🌐 Gestion des Sites")
    
    tab1, tab2 = st.tabs(["📋 Liste des sites", "➕ Ajouter un site"])
    
    with tab1:
        sites = load_sites()
        
        if sites:
            for idx, site in enumerate(sites):
                with st.expander(f"🔗 {site['name']} - {site['url']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**URL:** {site['url']}")
                        st.write(f"**Type:** {site.get('type', 'E-commerce')}")
                        st.write(f"**Authentification:** {'Oui' if site.get('requires_auth', False) else 'Non'}")
                        st.write(f"**Statut:** {'✅ Actif' if site.get('active', True) else '❌ Inactif'}")
                        
                        if site.get('selectors'):
                            st.write("**Sélecteurs configurés:**")
                            for key, value in site['selectors'].items():
                                st.code(f"{key}: {value}", language="css")
                    
                    with col2:
                        if st.button("🗑️ Supprimer", key=f"del_{idx}"):
                            sites.pop(idx)
                            save_sites(sites)
                            st.rerun()
                        
                        if st.button("⏸️ Désactiver" if site.get('active', True) else "▶️ Activer", key=f"toggle_{idx}"):
                            sites[idx]['active'] = not site.get('active', True)
                            save_sites(sites)
                            st.rerun()
        else:
            st.info("Aucun site configuré. Ajoutez votre premier site dans l'onglet 'Ajouter un site'.")
    
    with tab2:
        with st.form("add_site_form"):
            st.subheader("Ajouter un nouveau site")
            
            name = st.text_input("Nom du site", placeholder="Ex: Amazon France")
            url = st.text_input("URL du catalogue", placeholder="https://example.com/catalog")
            
            col1, col2 = st.columns(2)
            with col1:
                site_type = st.selectbox("Type de site", ["E-commerce", "Marketplace", "Autre"])
            with col2:
                requires_auth = st.checkbox("Nécessite une authentification")
            
            if requires_auth:
                st.warning("⚠️ Les identifiants seront configurés dans la section Configuration")
            
            st.markdown("---")
            st.subheader("Sélecteurs CSS (optionnel)")
            st.caption("Laissez vide pour une détection automatique")
            
            col1, col2 = st.columns(2)
            with col1:
                selector_brand = st.text_input("Sélecteur Marque", placeholder=".brand, [data-brand]")
                selector_model = st.text_input("Sélecteur Modèle", placeholder=".model, .product-name")
            with col2:
                selector_finish = st.text_input("Sélecteur Finitions", placeholder=".finish, .variant")
                selector_specs = st.text_input("Sélecteur Caractéristiques", placeholder=".specs, .features")
            
            submitted = st.form_submit_button("➕ Ajouter le site", type="primary", use_container_width=True)
            
            if submitted:
                if name and url:
                    sites = load_sites()
                    
                    new_site = {
                        "id": len(sites) + 1,
                        "name": name,
                        "url": url,
                        "type": site_type,
                        "requires_auth": requires_auth,
                        "active": True,
                        "created_at": datetime.now().isoformat(),
                        "selectors": {
                            "brand": selector_brand,
                            "model": selector_model,
                            "finish": selector_finish,
                            "specs": selector_specs
                        } if any([selector_brand, selector_model, selector_finish, selector_specs]) else None
                    }
                    
                    sites.append(new_site)
                    save_sites(sites)
                    
                    st.success(f"✅ Site '{name}' ajouté avec succès!")
                    st.rerun()
                else:
                    st.error("⚠️ Veuillez remplir au minimum le nom et l'URL du site")

# Page Configuration
elif page == "⚙️ Configuration":
    st.title("⚙️ Configuration")
    
    tab1, tab2, tab3 = st.tabs(["🗄️ Base de données", "🔐 Identifiants", "⏰ Planification"])
    
    config = load_config()
    
    with tab1:
        st.subheader("Configuration de la base de données")
        
        with st.form("database_config"):
            db_type = st.selectbox(
                "Type de base de données",
                ["supabase", "postgresql", "mysql", "sqlite"],
                index=0
            )
            
            if db_type == "supabase":
                st.info("📚 Supabase - Base de données en temps réel")
                url = st.text_input("URL du projet", value=config['database'].get('url', ''), 
                                   placeholder="https://xxxxx.supabase.co")
                key = st.text_input("Clé API (anon key)", value=config['database'].get('key', ''),
                                   type="password", placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
            
            elif db_type == "postgresql":
                st.info("🐘 PostgreSQL - Base de données relationnelle")
                host = st.text_input("Hôte", placeholder="localhost")
                port = st.number_input("Port", value=5432)
                database = st.text_input("Nom de la base", placeholder="scraper_db")
                user = st.text_input("Utilisateur", placeholder="postgres")
                password = st.text_input("Mot de passe", type="password")
            
            elif db_type == "mysql":
                st.info("🐬 MySQL - Base de données relationnelle")
                host = st.text_input("Hôte", placeholder="localhost")
                port = st.number_input("Port", value=3306)
                database = st.text_input("Nom de la base", placeholder="scraper_db")
                user = st.text_input("Utilisateur", placeholder="root")
                password = st.text_input("Mot de passe", type="password")
            
            else:  # sqlite
                st.info("💾 SQLite - Base de données locale")
                db_path = st.text_input("Chemin du fichier", value="data/scraper.db")
            
            submitted = st.form_submit_button("💾 Sauvegarder", type="primary")
            
            if submitted:
                if db_type == "supabase":
                    config['database'] = {
                        "type": db_type,
                        "url": url,
                        "key": key
                    }
                save_config(config)
                st.success("✅ Configuration sauvegardée!")
    
    with tab2:
        st.subheader("Gestion des identifiants")
        st.caption("Pour les sites nécessitant une authentification")
        
        sites = load_sites()
        auth_sites = [s for s in sites if s.get('requires_auth', False)]
        
        if auth_sites:
            for site in auth_sites:
                with st.expander(f"🔐 {site['name']}"):
                    with st.form(f"auth_form_{site['id']}"):
                        username = st.text_input("Nom d'utilisateur / Email", key=f"user_{site['id']}")
                        password = st.text_input("Mot de passe", type="password", key=f"pass_{site['id']}")
                        
                        if st.form_submit_button("💾 Sauvegarder les identifiants"):
                            # Sauvegarder de manière sécurisée (à améliorer avec encryption)
                            cred_file = DATA_DIR / "credentials" / f"{site['id']}.json"
                            with open(cred_file, 'w') as f:
                                json.dump({
                                    "username": username,
                                    "password": password
                                }, f)
                            st.success("✅ Identifiants sauvegardés!")
        else:
            st.info("Aucun site nécessitant une authentification configuré.")
    
    with tab3:
        st.subheader("Planification automatique")
        
        with st.form("scheduler_config"):
            enabled = st.checkbox("Activer la collecte automatique quotidienne",
                                 value=config['scheduler'].get('enabled', False))
            
            time = st.time_input("Heure de la collecte", 
                                value=datetime.strptime(config['scheduler'].get('time', '09:00'), '%H:%M').time())
            
            st.info("🤖 La collecte s'exécutera automatiquement tous les jours à l'heure configurée")
            
            if st.form_submit_button("💾 Sauvegarder la planification", type="primary"):
                config['scheduler'] = {
                    "enabled": enabled,
                    "time": time.strftime('%H:%M')
                }
                save_config(config)
                st.success("✅ Planification configurée!")

# Page Logs
elif page == "📋 Logs":
    st.title("📋 Historique des collectes")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox("Statut", ["Tous", "Succès", "Erreur", "En cours"])
    with col2:
        filter_site = st.selectbox("Site", ["Tous"] + [s['name'] for s in load_sites()])
    with col3:
        filter_date = st.date_input("Date")
    
    st.markdown("---")
    
    # Placeholder pour les logs
    st.info("📝 Aucune collecte effectuée pour le moment")
    
    # Exemple de structure de log
    with st.expander("Exemple de log"):
        st.json({
            "timestamp": "2025-01-02 10:30:15",
            "site": "Amazon France",
            "status": "success",
            "products_collected": 150,
            "duration": "45s",
            "errors": []
        })

# Page Export
elif page == "📤 Export":
    st.title("📤 Export des données")
    
    st.subheader("Exporter les données collectées")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox("Format d'export", ["CSV", "Excel (XLSX)", "JSON"])
        date_range = st.date_input("Période", value=[])
    
    with col2:
        sites = load_sites()
        selected_sites = st.multiselect("Sites à exporter", [s['name'] for s in sites], default=[s['name'] for s in sites])
    
    include_fields = st.multiselect(
        "Champs à inclure",
        ["Marque", "Modèle", "Finitions", "Caractéristiques", "Prix", "Stock", "URL", "Date de collecte"],
        default=["Marque", "Modèle", "Finitions", "Caractéristiques"]
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Exporter", type="primary", use_container_width=True):
            st.success("Export généré ! (Fonctionnalité en cours d'implémentation)")
    
    with col2:
        if st.button("📧 Envoyer par email", use_container_width=True):
            st.info("Email envoyé ! (Fonctionnalité en cours d'implémentation)")
    
    with col3:
        if st.button("☁️ Upload vers Drive", use_container_width=True):
            st.info("Upload réussi ! (Fonctionnalité en cours d'implémentation)")

# Footer
st.markdown("---")
st.caption("🛒 E-Commerce Scraper v1.0 - Développé avec ❤️")