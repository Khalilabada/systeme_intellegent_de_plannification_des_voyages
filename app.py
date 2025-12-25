from flask import Flask, render_template, request, jsonify, send_file
from flask_login import LoginManager, login_required, current_user
from extensions import db, socketio
from models.plan import Plan
from models.user import User
from services.batch_generator import BatchGenerator
import threading, json, io, time, uuid, multiprocessing as mp
from datetime import datetime
from utils.pdf_export import generer_pdf
import sys

app = Flask(__name__)
app.config.from_object("config.Config")
app.config['MAX_PLANS_SIMULTANES'] = mp.cpu_count()

db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*", async_mode='threading',logger=False,engineio_logger=False)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

batch_generator = BatchGenerator(app, db, socketio)

from auth.routes import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

@login_manager.user_loader
def charger_utilisateur(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def injecter_utilisateur():
    return dict(utilisateur_courant=current_user)

@app.template_filter('formatdate')
def formatdate(valeur, format='%d/%m/%Y'):
    try:
        if isinstance(valeur, str):
            formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']
            for fmt in formats:
                try:
                    dt = datetime.strptime(valeur, fmt)
                    return dt.strftime(format)
                except:
                    continue
        elif isinstance(valeur, datetime):
            return valeur.strftime(format)
        elif isinstance(valeur, (int, float)):
            dt = datetime.fromtimestamp(valeur)
            return dt.strftime(format)
    except:
        pass
    
    return str(valeur)

@app.template_filter('datetimeformat')
def datetimeformat(valeur, format='%d/%m/%Y'):
    return formatdate(valeur, format)

@app.template_filter('jsonversobjet')
def jsonversobjet(valeur):
    try:
        if isinstance(valeur, str):
            return json.loads(valeur)
        return valeur
    except:
        return {}

@app.template_filter('fromjson')
def fromjson(valeur):
    return jsonversobjet(valeur)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    plans = Plan.query.filter_by(user_id=current_user.id).order_by(Plan.created_at.desc()).limit(20).all()
    
    plans_termines = Plan.query.filter_by(user_id=current_user.id,status='pret').count()
    
    metriques = batch_generator.obtenir_metriques_globales()
    
    return render_template('dashboard.html', plans=plans,plans_termines=plans_termines, plans_simultanes=app.config['MAX_PLANS_SIMULTANES'],cpus=mp.cpu_count(), metriques=metriques)

@app.route('/creer_batch_plans', methods=['POST'])
@login_required
def creer_batch_plans():
    try:
        donnees = request.json
        plans_creer = donnees.get('plans', [])
        
        if not plans_creer:
            return jsonify({"erreur": "Aucun plan fourni"}), 400
        
        for i, plan in enumerate(plans_creer):
            prefs = plan.get('preferences', {})
            if not prefs.get('destination'):
                return jsonify({"erreur": f"Destination manquante pour le plan {i+1}"}), 400
        
        batch_id = str(uuid.uuid4())[:8]
        
        app.logger.info(f"Nouveau batch {batch_id}: {len(plans_creer)} plans")
        
        threading.Thread(
            target=batch_generator.lancer_generation_batch,args=(batch_id, plans_creer, current_user.id),daemon=True
        ).start()
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "message": f"Génération démarrée pour {len(plans_creer)} plans",
            "cpus": mp.cpu_count(),
        })
        
    except Exception as e:
        app.logger.error(f"Erreur creer_batch_plans: {e}")
        return jsonify({"erreur": str(e)}), 500

@app.route('/api/batch/<batch_id>/metriques')
@login_required
def obtenir_metriques_batch(batch_id):
    try:
        metriques = batch_generator.obtenir_metriques_batch(batch_id)
        
        if metriques:
            return jsonify({
                'success': True,
                'batch_id': batch_id,
                'metriques': metriques
            })
        else:
            return jsonify({
                'success': False,
                'erreur': 'Batch non trouvé'
            }), 404
            
    except Exception as e:
        return jsonify({"success": False, "erreur": str(e)}), 500

@app.route('/api/batchs/historique')
@login_required
def obtenir_historique_batchs():
    try:
        batchs_termines = batch_generator.obtenir_batchs_termines()
        
        return jsonify({
            'success': True,
            'batchs': batchs_termines,
            'total': len(batchs_termines)
        })
        
    except Exception as e:
        return jsonify({"success": False, "erreur": str(e)}), 500

@app.route('/plan/<int:plan_id>')
@login_required
def voir_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    
    if plan.user_id != current_user.id:
        return "Accès non autorisé", 403
    
    contenu = {}
    if plan.contenu:
        try:
            contenu = json.loads(plan.contenu)
        except:
            contenu = {"erreur": "Format invalide"}
    
    valeurs_par_defaut = {
        "flights": [], "hotels": [], "restaurants": [], 
        "activities": [], "itinerary": [], "recommendations": [],
        "packing_tips": [], "travel_tips": [], "weather": {},
        "depart_date": "", "return_date": "", "destination": "Destination",
        "estimated_budget": {}, "duration_days": 7
    }
    
    for cle, valeur in valeurs_par_defaut.items():
        if cle not in contenu:
            contenu[cle] = valeur
    
    return render_template('plan_view.html', plan=plan, contenu=contenu)

@app.route('/plan/<int:plan_id>/exporter_pdf')
@login_required
def exporter_pdf(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    
    if plan.user_id != current_user.id:
        return "Accès non autorisé", 403
    
    if not plan.contenu:
        return "Plan vide", 404
    
    try:
        donnees_plan = json.loads(plan.contenu)
        buffer = generer_pdf(donnees_plan)
        
        nom_fichier = f"voyage_{donnees_plan.get('destination', 'plan')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nom_fichier
        )
    except Exception as e:
        return f"Erreur PDF: {str(e)}", 500

@app.route('/plan/<int:plan_id>/supprimer', methods=['POST'])
@login_required
def supprimer_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    
    if plan.user_id != current_user.id:
        return jsonify({"success": False, "erreur": "Accès refusé"}), 403
    
    try:
        db.session.delete(plan)
        db.session.commit()
        
        socketio.emit('plan_supprime', {"plan_id": plan_id})
        return jsonify({"success": True, "message": "Plan supprimé"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "erreur": str(e)}), 500

@app.route('/api/statistiques')
@login_required
def obtenir_statistiques():
    try:
        plans_termines = Plan.query.filter_by(
            user_id=current_user.id,
            status='pret'
        ).count()
        
        metriques = batch_generator.obtenir_metriques_globales()
        
        try:
            import psutil
            infos_systeme = {
                'cpu_pourcent': psutil.cpu_percent(),
                'memoire_pourcent': psutil.virtual_memory().percent,
                'threads_actifs': threading.active_count(),
            }
        except:
            infos_systeme = {}
        
        return jsonify({
            "utilisateur_id": current_user.id,
            "plans_termines": plans_termines,
            "plans_simultanes_max": app.config['MAX_PLANS_SIMULTANES'],
            "cpus": mp.cpu_count(),
            "metriques": metriques,
            "systeme": infos_systeme
        })
        
    except Exception as e:
        app.logger.error(f"Erreur statistiques: {e}")
        return jsonify({"erreur": str(e)}), 500

@app.route('/api/metriques/detaillees')
@login_required
def obtenir_metriques_detaillees():
    try:
        metriques_globales = batch_generator.obtenir_metriques_globales()
        
        stats_utilisateur = {
            'plans_total': Plan.query.filter_by(user_id=current_user.id).count(),
            'plans_termines': Plan.query.filter_by(user_id=current_user.id, status='pret').count(),
            'plans_en_cours': Plan.query.filter_by(user_id=current_user.id, status='en_cours').count(),
        }
        
        try:
            import psutil
            systeme = {
                'cpu': psutil.cpu_percent(),
                'memoire': psutil.virtual_memory().percent,
                'threads': threading.active_count(),
            }
        except:
            systeme = {}
        
        return jsonify({
            'success': True,
            'global': metriques_globales['global'] if 'global' in metriques_globales else {},
            'utilisateur': stats_utilisateur,
            'systeme': systeme,
            'batchs_actifs': metriques_globales.get('batchs_actifs', {}),
            'batchs_termines': metriques_globales.get('batchs_termines', {}),
            'timestamp': time.time(),
            'timestamp_lisible': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({"success": False, "erreur": str(e)}), 500


@socketio.on('connect')
def gestion_connexion():
    app.logger.info(f'Client connecté: {request.sid}')

@socketio.on('disconnect')
def gestion_deconnexion():
    app.logger.info(f'Client déconnecté: {request.sid}')

@socketio.on('rejoindre_batch')
def rejoindre_batch(donnees):
    batch_id = donnees.get('batch_id')
    app.logger.info(f'Client {request.sid} rejoint le batch {batch_id}')
    
    batchs_actifs = batch_generator.obtenir_batchs_actifs()
    if batch_id in batchs_actifs:
        socketio.emit('statut_batch', {
            'batch_id': batch_id,
            'statut': 'actif',
            'progression': f"{batchs_actifs[batch_id].get('plans_termines', 0)}/{batchs_actifs[batch_id].get('total_plans', 0)}"
        })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True,log_output=False)