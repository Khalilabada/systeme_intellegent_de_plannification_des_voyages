# services/batch_generator.py - VERSION SIMPLIFIÉE SANS USE_AI
import time
import uuid
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import threading
import os

def generate_plan_de_voyage(preferences):
    print(f"🔍 Début génération plan pour {preferences.get('destination', 'Inconnu')}")
    
    try:
        from services.plan_generator import PlanGenerator
        
        debut_plan = time.time()
        generator = PlanGenerator()
        plan_data = generator.generate_plan_optimized(preferences)
        
        temps_execution = time.time() - debut_plan
        
        destination = preferences.get('destination', 'Inconnu')
        
        print(f"✅ Plan généré pour {destination} en {temps_execution:.2f}s")
        
        return {
            'success': True,
            'data': plan_data,
            'preferences': preferences,
            'worker_pid': os.getpid(),
            'temps_execution': round(temps_execution, 2),
            'destination': destination
        }
        
    except Exception as e:
        print(f"❌ ERREUR génération plan: {e}")
        import traceback
        traceback.print_exc()  # Affiche la stack trace complète
        
        return {
            'success': False,
            'error': str(e),
            'preferences': preferences,
            'worker_pid': os.getpid(),
            'destination': preferences.get('destination', 'Inconnu')
        }

class BatchGenerator:
    
    def __init__(self, app, db, socketio):
        self.app = app
        self.db = db
        self.socketio = socketio
        self.batches_actifs = {}
        self.v = threading.RLock()
        self.metriques_globales = {
            'plans_generes_total': 0,
            'batchs_termines_total': 0,
            'temps_total_execution': 0,
            'speedup_moyen': 0,
            'workers_max_utilises': 0
        }
    
    def lancer_generation_batch(self, batch_id, plans_data, user_id):
        try:
            total_plans = len(plans_data)
            
            if total_plans == 0:
                self.socketio.emit('erreur_batch', {
                    'batch_id': batch_id,
                    'erreur': 'Aucun plan à générer'
                })
                return
            
            temps_sequentiel = total_plans * 30
            
            with self.v:
                self.batches_actifs[batch_id] = {
                    'total': total_plans,
                    'debut': time.time(),
                    'termines': 0,
                    'reussis': 0,
                    'temps_plans': [],
                    'temps_total_batch': 0,
                    'speedup_batch': 0,
                    'statut': 'en_cours',
                    'user_id': user_id,
                    'temps_sequentiel': temps_sequentiel
                }
            
            self.socketio.emit('progression_batch', {
                'batch_id': batch_id,
                'message': f'Démarrage batch: {total_plans} plans',
                'progression': 0,
                'statut': 'debut',
                'temps_sequentiel': temps_sequentiel
            })
            
            taches = [plan.get('preferences', {}) for plan in plans_data]
            
            cpus = mp.cpu_count()
            workers_optimaux = min(cpus, total_plans)
            
            debut_batch = time.time()
            resultats = []
            
            self.app.logger.info(f"Batch {batch_id}: {total_plans} plans avec {workers_optimaux} workers")
            
            with ProcessPoolExecutor(max_workers=workers_optimaux) as executor:
                futures = {executor.submit(generate_plan_de_voyage, tache): i 
                          for i, tache in enumerate(taches)}
                
                termines = 0
                
                for future in as_completed(futures):
                    termines += 1
                    numero_plan = futures[future] + 1
                    
                    try:
                        resultat = future.result(timeout=180)
                        resultat['numero'] = numero_plan
                        resultats.append(resultat)
                        
                        if resultat.get('success'):
                            with self.v:
                                if batch_id in self.batches_actifs:
                                    self.batches_actifs[batch_id]['termines'] = termines
                                    self.batches_actifs[batch_id]['reussis'] += 1
                                    
                                    if 'temps_execution' in resultat:
                                        temps_plan = resultat['temps_execution']
                                        self.batches_actifs[batch_id]['temps_plans'].append(temps_plan)
                        
                        progression = int((termines / total_plans) * 100)
                        
                        self.socketio.emit('progression_batch', {
                            'batch_id': batch_id,
                            'plan_courant': resultat.get('destination', 'Inconnu'),
                            'progression': progression,
                            'termines': termines,
                            'reussis': self.batches_actifs.get(batch_id, {}).get('reussis', 0),
                            'numero_plan': numero_plan,
                            'statut': 'en_cours'
                        })
                        
                    except Exception as e:
                        self.app.logger.error(f"❌ Plan {numero_plan} échoué: {e}")
                        resultats.append({
                            'success': False,
                            'numero': numero_plan,
                            'error': str(e),
                            'destination': 'Erreur'
                        })
            
            temps_total_batch = time.time() - debut_batch
            plans_reussis = len([r for r in resultats if r.get('success')])
            
            speedup_batch = 0
            if temps_total_batch > 0:
                speedup_batch = round(temps_sequentiel / temps_total_batch, 2)
            
            temps_liste = []
            if batch_id in self.batches_actifs:
                temps_liste = self.batches_actifs[batch_id].get('temps_plans', [])
            
            temps_moyen_plan = 0
            temps_min_plan = 0
            temps_max_plan = 0
            
            if temps_liste:
                temps_moyen_plan = round(sum(temps_liste) / len(temps_liste), 2)
                temps_min_plan = round(min(temps_liste), 2)
                temps_max_plan = round(max(temps_liste), 2)
            
            with self.v:
                if batch_id in self.batches_actifs:
                    self.batches_actifs[batch_id].update({
                        'temps_total_batch': round(temps_total_batch, 2),
                        'speedup_batch': speedup_batch,
                        'temps_moyen_plan': temps_moyen_plan,
                        'temps_min_plan': temps_min_plan,
                        'temps_max_plan': temps_max_plan,
                        'statut': 'termine'
                    })
            
            with self.v:
                self.metriques_globales['plans_generes_total'] += plans_reussis
                self.metriques_globales['batchs_termines_total'] += 1
                self.metriques_globales['temps_total_execution'] += temps_total_batch
                self.metriques_globales['workers_max_utilises'] = max(
                    self.metriques_globales['workers_max_utilises'], 
                    workers_optimaux
                )
                
                if plans_reussis > 0:
                    poids = plans_reussis / self.metriques_globales['plans_generes_total']
                    ancien_speedup = self.metriques_globales['speedup_moyen']
                    self.metriques_globales['speedup_moyen'] = (
                        ancien_speedup * (1 - poids) + speedup_batch * poids
                    )
            
            if plans_reussis > 0:
                self._sauvegarder_plans([r for r in resultats if r.get('success')], user_id)
            
            self.socketio.emit('batch_termine', {
                'batch_id': batch_id,
                'resultat': {
                    'total_plans': total_plans,
                    'plans_reussis': plans_reussis,
                    'plans_echoues': total_plans - plans_reussis,
                    
                    'temps_total_batch': round(temps_total_batch, 2),
                    'temps_sequentiel_estime': temps_sequentiel,
                    'gain_temps': round(temps_sequentiel - temps_total_batch, 2),
                    
                    'temps_moyen_par_plan': temps_moyen_plan,
                    'temps_min_par_plan': temps_min_plan,
                    'temps_max_par_plan': temps_max_plan,
                    
                    'speedup_batch': speedup_batch,
                    'workers_utilises': workers_optimaux,
                    'efficacite': round((speedup_batch / workers_optimaux * 100) if workers_optimaux > 0 else 0, 1),
                    
                    'vitesse_plans_minute': round((plans_reussis / temps_total_batch * 60) if temps_total_batch > 0 else 0, 2),
                    'vitesse_plans_seconde': round(plans_reussis / temps_total_batch if temps_total_batch > 0 else 0, 2),
                },
                'statut': 'termine',
                'message': f'Batch terminé: {plans_reussis}/{total_plans} plans générés'
            })
            
            self.app.logger.info(
                f"Batch {batch_id}: {plans_reussis}/{total_plans} plans "
                f"en {temps_total_batch:.1f}s (speedup: {speedup_batch:.2f}x)"
            )
            
            threading.Timer(300, self._supprimer_batch, args=[batch_id]).start()
            
        except Exception as e:
            self.app.logger.error(f"❌ Erreur critique batch {batch_id}: {e}")
            
            self.socketio.emit('erreur_batch', {
                'batch_id': batch_id,
                'erreur': str(e),
                'statut': 'erreur'
            })
            
            with self.v:
                if batch_id in self.batches_actifs:
                    del self.batches_actifs[batch_id]
    
    def _sauvegarder_plans(self, resultats, user_id):
        from models.plan import Plan
        
        with self.app.app_context():
            try:
                for resultat in resultats:
                    if resultat.get('success'):
                        plan = Plan(
                            user_id=user_id,
                            preferences=json.dumps(resultat['preferences'], ensure_ascii=False),
                            contenu=json.dumps(resultat['data'], ensure_ascii=False),
                            status='pret'
                        )
                        self.db.session.add(plan)
                
                self.db.session.commit()
                self.app.logger.info(f"💾 {len(resultats)} plans sauvegardés")
                
            except Exception as e:
                self.app.logger.error(f"❌ Erreur sauvegarde: {e}")
                self.db.session.rollback()
    
    def _supprimer_batch(self, batch_id):
        with self.v:
            if batch_id in self.batches_actifs:
                del self.batches_actifs[batch_id]
    
    def obtenir_batchs_actifs(self):
        with self.v:
            batchs = {}
            
            for batch_id, infos in self.batches_actifs.items():
                if infos.get('statut') == 'en_cours':
                    temps_ecoule = time.time() - infos['debut']
                    progression = (infos['termines'] / infos['total']) * 100
                    
                    batchs[batch_id] = {
                        'total_plans': infos['total'],
                        'plans_termines': infos['termines'],
                        'plans_reussis': infos.get('reussis', 0),
                        'progression': round(progression, 1),
                        'temps_ecoule': round(temps_ecoule, 2),
                        'statut': 'en_cours'
                    }
            
            return batchs
    
    def obtenir_batchs_termines(self):
        with self.v:
            batchs = {}
            maintenant = time.time()
            
            for batch_id, infos in self.batches_actifs.items():
                if infos.get('statut') == 'termine':
                    if maintenant - infos['debut'] < 3600:
                        batchs[batch_id] = {
                            'total_plans': infos['total'],
                            'plans_reussis': infos.get('reussis', 0),
                            'temps_total': infos.get('temps_total_batch', 0),
                            'speedup': infos.get('speedup_batch', 0),
                            'temps_moyen_plan': infos.get('temps_moyen_plan', 0),
                            'temps_sequentiel_estime': infos.get('temps_sequentiel', 0),
                            'date_debut': time.strftime('%H:%M:%S', time.localtime(infos['debut'])),
                            'statut': 'termine'
                        }
            
            return batchs
    
    def obtenir_metriques_batch(self, batch_id):
        with self.v:
            if batch_id in self.batches_actifs:
                infos = self.batches_actifs[batch_id]
                
                return {
                    'batch_id': batch_id,
                    'total_plans': infos.get('total', 0),
                    'plans_termines': infos.get('termines', 0),
                    'plans_reussis': infos.get('reussis', 0),
                    'temps_total': infos.get('temps_total_batch', 0),
                    'temps_moyen_plan': infos.get('temps_moyen_plan', 0),
                    'temps_min_plan': infos.get('temps_min_plan', 0),
                    'temps_max_plan': infos.get('temps_max_plan', 0),
                    'speedup': infos.get('speedup_batch', 0),
                    'temps_sequentiel_estime': infos.get('temps_sequentiel', 0),
                    'gain_temps': round(infos.get('temps_sequentiel', 0) - infos.get('temps_total_batch', 0), 2),
                    'statut': infos.get('statut', 'inconnu'),
                    'temps_ecoule': round(time.time() - infos.get('debut', 0), 2) if infos.get('debut') else 0
                }
            
            return None
    
    def obtenir_metriques_globales(self):
        with self.v:
            batchs_actifs = self.obtenir_batchs_actifs()
            batchs_termines = self.obtenir_batchs_termines()
            
            temps_moyen_plan_global = 0
            if self.metriques_globales['plans_generes_total'] > 0:
                temps_moyen_plan_global = round(
                    self.metriques_globales['temps_total_execution'] / self.metriques_globales['plans_generes_total'], 
                    2
                )
            
            vitesse_moyenne = 0
            if self.metriques_globales['temps_total_execution'] > 0:
                plans_par_seconde = self.metriques_globales['plans_generes_total'] / self.metriques_globales['temps_total_execution']
                vitesse_moyenne = round(plans_par_seconde * 60, 2)
            
            return {
                'global': {
                    'plans_generes': self.metriques_globales['plans_generes_total'],
                    'batchs_termines': self.metriques_globales['batchs_termines_total'],
                    'temps_total': round(self.metriques_globales['temps_total_execution'], 2),
                    'speedup_moyen': round(self.metriques_globales['speedup_moyen'], 2),
                    'workers_max_utilises': self.metriques_globales['workers_max_utilises'],
                    'temps_moyen_par_plan': temps_moyen_plan_global,
                    'vitesse_moyenne': vitesse_moyenne
                },
                'systeme': {
                    'cpu_disponibles': mp.cpu_count(),
                    'batchs_actifs': len(batchs_actifs),
                    'batchs_termines_recents': len(batchs_termines)
                },
                'batchs_actifs': batchs_actifs,
                'batchs_termines': batchs_termines
            }