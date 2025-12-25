// static/js/dashboard.js
// ==================== VARIABLES GLOBALES ====================
let socket = null;
let batchCourantId = null;
let debutBatch = null;
let timerBatch = null;
let isSocketConnecte = false;
let graphiqueBatchActuel = null;

// ==================== FONCTIONS D'INITIALISATION ====================
function chargerChartJS() {
    const script = document.createElement('script');
    script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
    script.integrity = "sha384-btiaFVq6voOj7MmywIHJj0aD0a7wT3lQjMS7gQeKkC84v9Fg9xJ5tH0f0K0C8BmF";
    script.crossOrigin = "anonymous";
    script.onload = () => {
        console.log('✅ Chart.js chargé');
    };
    script.onerror = () => {
        console.error('❌ Impossible de charger Chart.js');
        afficherNotification('Graphique', 'Impossible de charger Chart.js', 'warning');
    };
    document.head.appendChild(script);
}

// ==================== FONCTIONS UTILITAIRES ====================
function estimerTempsSequentiel(nombrePlans) {
    const tempsMoyenParPlan = 25; // secondes
    let tempsTotal = nombrePlans * tempsMoyenParPlan;
    
    if (nombrePlans > 5) tempsTotal *= 1.1;
    if (nombrePlans > 10) tempsTotal *= 1.2;
    if (nombrePlans > 20) tempsTotal *= 1.3;
    
    return {
        secondes: Math.round(tempsTotal),
        formatHumain: formaterTempsHumain(tempsTotal)
    };
}

function formaterTempsHumain(secondes) {
    const heures = Math.floor(secondes / 3600);
    const minutes = Math.floor((secondes % 3600) / 60);
    const secs = Math.floor(secondes % 60);
    
    let result = [];
    if (heures > 0) result.push(`${heures}h`);
    if (minutes > 0) result.push(`${minutes}min`);
    if (secs > 0 || result.length === 0) result.push(`${secs}s`);
    
    return result.join(' ');
}

// ==================== GESTION DES FORMULAIRES ====================
function ajouterPlan() {
    const conteneur = document.getElementById('conteneurPlans');
    const nombre = conteneur.children.length + 1;
    
    const aujourdhui = new Date();
    const dateDepart = new Date(aujourdhui);
    dateDepart.setDate(aujourdhui.getDate() + 7 * nombre);
    const dateRetour = new Date(dateDepart);
    dateRetour.setDate(dateDepart.getDate() + 7);
    
    const formulaire = document.createElement('div');
    formulaire.className = 'formulaire-plan mb-3 p-3 border rounded bg-light';
    formulaire.innerHTML = `
        <div class="row g-2">
            <div class="col-md-2">
                <label class="form-label small">Origine</label>
                <input class="form-control form-control-sm champ-origine" placeholder="TUN" value="TUN" required />
            </div>
            <div class="col-md-3">
                <label class="form-label small">Destination*</label>
                <input class="form-control form-control-sm champ-destination" placeholder="Paris" required />
            </div>
            <div class="col-md-2">
                <label class="form-label small">Date départ</label>
                <input class="form-control form-control-sm champ-date-depart" type="date" 
                       value="${dateDepart.toISOString().split('T')[0]}" required />
            </div>
            <div class="col-md-2">
                <label class="form-label small">Date retour</label>
                <input class="form-control form-control-sm champ-date-retour" type="date" 
                       value="${dateRetour.toISOString().split('T')[0]}" required />
            </div>
            <div class="col-md-2">
                <label class="form-label small">Budget (€)</label>
                <input class="form-control form-control-sm champ-budget" type="number" 
                       min="0" placeholder="1000" value="${800 + (nombre * 200)}" required />
            </div>
            <div class="col-md-1">
                <label class="form-label small">&nbsp;</label>
                <button type="button" class="btn btn-sm btn-danger w-100" onclick="supprimerPlan(this)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    conteneur.appendChild(formulaire);
    actualiserCompteurPlans();
}

function supprimerPlan(bouton) {
    const conteneur = document.getElementById('conteneurPlans');
    const formulaire = bouton.closest('.formulaire-plan');
    
    if (conteneur.children.length > 1) {
        formulaire.remove();
        actualiserCompteurPlans();
    }
}

function actualiserCompteurPlans() {
    const nombre = document.querySelectorAll('.formulaire-plan').length;
    const badge = document.getElementById('badge-nombre-plans');
    
    if (badge) {
        badge.textContent = `${nombre} itinéraire${nombre > 1 ? 's' : ''}`;
        badge.className = 'badge fs-6 ';
        if (nombre === 1) badge.classList.add('bg-success');
        else if (nombre <= 3) badge.classList.add('bg-warning');
        else badge.classList.add('bg-danger');
    }
}

// ==================== LANCEMENT BATCH ====================
async function lancerBatch() {
    const formulaires = document.querySelectorAll('.formulaire-plan');
    const plans = [];
    
    let valide = true;
    formulaires.forEach((formulaire, index) => {
        const destination = formulaire.querySelector('.champ-destination').value.trim();
        const depart = formulaire.querySelector('.champ-date-depart').value;
        const retour = formulaire.querySelector('.champ-date-retour').value;
        
        if (!destination || !depart || !retour) {
            valide = false;
            formulaire.classList.add('border-danger');
            afficherNotification('Erreur', `Plan ${index + 1}: champs manquants`, 'danger');
        } else {
            formulaire.classList.remove('border-danger');
        }
    });
    
    if (!valide) return;
    
    formulaires.forEach(formulaire => {
        const planData = {
            preferences: {
                origin: formulaire.querySelector('.champ-origine').value.trim() || 'TUN',
                destination: formulaire.querySelector('.champ-destination').value.trim(),
                depart_date: formulaire.querySelector('.champ-date-depart').value,
                return_date: formulaire.querySelector('.champ-date-retour').value,
                budget: parseFloat(formulaire.querySelector('.champ-budget').value) || 1000
            }
        };
        plans.push(planData);
    });
    
    console.log(`📤 Lancement batch: ${plans.length} plans`);
    
    const bouton = document.getElementById('bouton-lancer');
    const texteOriginal = bouton.innerHTML;
    bouton.disabled = true;
    bouton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Démarrage...';
    
    try {
        const response = await fetch('/creer_batch_plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                plans: plans
            })
        });
        
        const resultat = await response.json();
        
        if (response.ok) {
            afficherNotification('Batch démarré!', `${plans.length} plans en traitement`, 'success');
            batchCourantId = resultat.batch_id;
            initialiserInterfaceBatch();
            
            if (socket && socket.connected) {
                socket.emit('rejoindre_batch', { batch_id: batchCourantId });
            }
        } else {
            afficherNotification('Erreur', resultat.erreur || 'Erreur inconnue', 'danger');
            bouton.disabled = false;
            bouton.innerHTML = texteOriginal;
        }
    } catch (erreur) {
        console.error('❌ Erreur réseau:', erreur);
        afficherNotification('Erreur réseau', 'Impossible de démarrer le batch', 'danger');
        bouton.disabled = false;
        bouton.innerHTML = texteOriginal;
    }
}

// ==================== GESTION PROGRESSION BATCH ====================
function initialiserInterfaceBatch() {
    const section = document.getElementById('progression-batch');
    const barre = document.getElementById('barre-progression');
    const resultats = document.getElementById('resultats-batch');
    
    section.classList.remove('d-none');
    resultats.classList.add('d-none');
    
    barre.style.width = '0%';
    barre.className = 'progress-bar progress-bar-striped progress-bar-animated bg-warning';
    document.getElementById('texte-progression').textContent = '0%';
    
    document.getElementById('statut-batch').textContent = 'Préparation...';
    document.getElementById('plan-courant').textContent = '-';
    document.getElementById('compteur-batch').textContent = '0/0';
    document.getElementById('plans-reussis').textContent = '0';
    document.getElementById('temps-ecoule').textContent = '0s';
    document.getElementById('speedup-batch').textContent = '-';
    
    debutBatch = Date.now();
    demarrerTimer();
}

function mettreAJourProgression(data) {
    const barre = document.getElementById('barre-progression');
    const texte = document.getElementById('texte-progression');
    const statut = document.getElementById('statut-batch');
    const compteur = document.getElementById('compteur-batch');
    const planCourant = document.getElementById('plan-courant');
    const plansReussis = document.getElementById('plans-reussis');
    
    const progression = data.total > 0 ? (data.completed / data.total) * 100 : 0;
    barre.style.width = `${progression}%`;
    texte.textContent = `${Math.round(progression)}%`;
    
    if (data.status === 'starting') {
        statut.textContent = 'Initialisation...';
        statut.className = 'badge bg-warning ms-2';
    } else if (progression < 30) {
        statut.textContent = 'Récupération données...';
        statut.className = 'badge bg-info ms-2';
    } else if (progression < 70) {
        statut.textContent = 'Génération en cours...';
        statut.className = 'badge bg-warning ms-2';
        barre.classList.remove('bg-info');
        barre.classList.add('bg-warning');
    } else {
        statut.textContent = 'Finalisation...';
        statut.className = 'badge bg-success ms-2';
        barre.classList.remove('bg-warning');
        barre.classList.add('bg-success');
    }
    
    planCourant.textContent = data.current_plan || 'Traitement...';
    compteur.textContent = `${data.completed}/${data.total}`;
    plansReussis.textContent = data.successful || 0;
    
    if (data.speedup) {
        document.getElementById('speedup-batch').textContent = `${data.speedup.toFixed(2)}x`;
    }
}

function terminerBatch(data) {
    console.log('✅ Terminaison batch:', data);
    
    const barre = document.getElementById('barre-progression');
    const texte = document.getElementById('texte-progression');
    const statut = document.getElementById('statut-batch');
    const resultats = document.getElementById('resultats-batch');
    const details = document.getElementById('details-resultats');
    const bouton = document.getElementById('bouton-lancer');
    
    barre.style.width = '100%';
    texte.textContent = '100%';
    barre.classList.remove('progress-bar-animated', 'progress-bar-striped');
    barre.classList.add('bg-success');
    statut.textContent = 'Terminé ✓';
    statut.className = 'badge bg-success ms-2';
    
    arreterTimer();
    
    const tauxReussite = data.resultat.total_plans > 0 
        ? (data.resultat.plans_reussis / data.resultat.total_plans * 100) 
        : 0;
    
    details.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6><i class="bi bi-check-circle"></i> Résultats</h6>
                <ul class="mb-0">
                    <li>Total: <strong>${data.resultat.total_plans}</strong> plans</li>
                    <li>Réussis: <strong class="text-success">${data.resultat.plans_reussis}</strong></li>
                    <li>Échecs: <strong class="text-danger">${data.resultat.plans_echoues}</strong></li>
                    <li>Taux de réussite: <strong>${tauxReussite.toFixed(1)}%</strong></li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6><i class="bi bi-graph-up"></i> Performance</h6>
                <ul class="mb-0">
                    <li>Temps total: <strong>${data.resultat.temps_total_batch}s</strong></li>
                    <li>Speedup: <strong class="text-primary">${data.resultat.speedup_batch}x</strong></li>
                    <li>Gain de temps: <strong class="text-success">${data.resultat.gain_temps}s</strong></li>
                    <li>Temps/plan: <strong>${data.resultat.temps_moyen_par_plan}s</strong></li>
                </ul>
            </div>
        </div>
    `;
    
    resultats.classList.remove('d-none');
    bouton.disabled = false;
    bouton.innerHTML = '<i class="bi bi-magic"></i> Générer mes plans';
    
    afficherNotification('Batch terminé!', `${data.resultat.plans_reussis} plans générés`, 'success');
    
    // Afficher le graphique comparatif
    afficherGraphiqueBatch(data);
    
    setTimeout(() => {
        actualiserMetriques();
        actualiserHistorique();
    }, 2000);
    
    batchCourantId = null;
}

function erreurBatch(data) {
    console.log('❌ Erreur batch:', data);
    
    const barre = document.getElementById('barre-progression');
    const statut = document.getElementById('statut-batch');
    const bouton = document.getElementById('bouton-lancer');
    
    barre.className = 'progress-bar bg-danger';
    statut.textContent = 'Erreur ✗';
    statut.className = 'badge bg-danger ms-2';
    
    arreterTimer();
    
    bouton.disabled = false;
    bouton.innerHTML = '<i class="bi bi-magic"></i> Générer mes plans';
    
    afficherNotification('Erreur batch', data.erreur || 'Erreur inconnue', 'danger');
    batchCourantId = null;
}

function demarrerTimer() {
    arreterTimer();
    timerBatch = setInterval(() => {
        if (debutBatch) {
            const ecoule = Math.floor((Date.now() - debutBatch) / 1000);
            const minutes = Math.floor(ecoule / 60);
            const secondes = ecoule % 60;
            document.getElementById('temps-ecoule').textContent = 
                minutes > 0 ? `${minutes}m ${secondes}s` : `${secondes}s`;
        }
    }, 1000);
}

function arreterTimer() {
    if (timerBatch) {
        clearInterval(timerBatch);
        timerBatch = null;
    }
}

// ==================== GRAPHIQUE COMPARATIF SIMPLIFIÉ ====================
function afficherGraphiqueBatch(data) {
    // Afficher la section
    const section = document.getElementById('section-graphique-post-generation');
    section.classList.remove('d-none');
    
    // Mettre à jour le badge
    document.getElementById('badge-batch-courant').textContent = 
        `Batch ${data.batch_id.substring(0, 8)}...`;
    
    // Calculer les données comparatives
    const totalPlans = data.resultat.total_plans;
    const tempsParalleleReel = data.resultat.temps_total_batch;
    const tempsSequentielTheorique = estimerTempsSequentiel(totalPlans).secondes;
    const speedup = data.resultat.speedup_batch;
    const gainSecondes = tempsSequentielTheorique - tempsParalleleReel;
    const gainPourcentage = (gainSecondes / tempsSequentielTheorique * 100).toFixed(1);
    
    // Préparer les données pour le graphique
    const labels = ['Séquentiel', 'Parallèle'];
    const tempsData = [tempsSequentielTheorique, tempsParalleleReel];
    
    // Créer le graphique comparatif
    creerGraphiqueComparatif(labels, tempsData, speedup);
    
    // Afficher l'analyse de performance
    afficherAnalysePerformance({
        totalPlans: totalPlans,
        tempsSequentiel: tempsSequentielTheorique,
        tempsParalleleReel: tempsParalleleReel,
        speedup: speedup,
        gainSecondes: gainSecondes,
        gainPourcentage: gainPourcentage
    });
    
    // Afficher les détails du batch
    afficherDetailsBatch(data);
    
    // Faire défiler jusqu'au graphique
    setTimeout(() => {
        section.scrollIntoView({ behavior: 'smooth' });
    }, 500);
}

function creerGraphiqueComparatif(labels, tempsData, speedup) {
    const ctx = document.getElementById('graphiqueBatchActuel').getContext('2d');
    
    // Détruire le graphique existant
    if (graphiqueBatchActuel) {
        graphiqueBatchActuel.destroy();
    }
    
    graphiqueBatchActuel = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temps de Génération (secondes)',
                    data: tempsData,
                    backgroundColor: [
                        'rgba(220, 53, 69, 0.8)',  // Rouge pour séquentiel
                        'rgba(25, 135, 84, 0.8)'   // Vert pour parallèle
                    ],
                    borderColor: [
                        'rgb(220, 53, 69)',
                        'rgb(25, 135, 84)'
                    ],
                    borderWidth: 2,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 12
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            const secondes = context.parsed.y;
                            if (secondes >= 60) {
                                const minutes = Math.floor(secondes / 60);
                                const secs = secondes % 60;
                                label += secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
                            } else {
                                label += secondes + 's';
                            }
                            
                            // Ajouter le speedup pour le parallèle
                            if (context.dataIndex === 1 && speedup) {
                                label += ` (Speedup: ${speedup.toFixed(2)}x)`;
                            }
                            
                            return label;
                        },
                        afterLabel: function(context) {
                            if (context.dataIndex === 1) {
                                // Pour le parallèle, montrer le gain
                                const tempsSequentiel = context.chart.data.datasets[0].data[0];
                                const reduction = ((tempsSequentiel - context.parsed.y) / tempsSequentiel * 100).toFixed(1);
                                return `Gain: ${reduction}%`;
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Mode d\'exécution',
                        color: '#666',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temps (secondes)',
                        color: '#666',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    min: 0,
                    ticks: {
                        callback: function(value) {
                            if (value >= 60) {
                                const minutes = Math.floor(value / 60);
                                const secondes = value % 60;
                                return secondes > 0 ? `${minutes}m ${secondes}s` : `${minutes}m`;
                            }
                            return value + 's';
                        }
                    }
                }
            }
        }
    });
}

function afficherAnalysePerformance(metriques) {
    const container = document.getElementById('analyse-performance-batch');
    
    let classSpeedup = 'badge ';
    if (metriques.speedup >= 2.0) classSpeedup += 'bg-success';
    else if (metriques.speedup >= 1.5) classSpeedup += 'bg-warning';
    else classSpeedup += 'bg-danger';
    
    container.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>Speedup:</span>
                <span class="${classSpeedup}">${metriques.speedup.toFixed(2)}x</span>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>Gain temps:</span>
                <span class="badge bg-success">${formaterTempsHumain(metriques.gainSecondes)}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>Réduction:</span>
                <span class="badge bg-success">${metriques.gainPourcentage}%</span>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <span>Plans/min:</span>
                <span class="badge bg-info">
                    ${((metriques.totalPlans / metriques.tempsParalleleReel) * 60).toFixed(1)}
                </span>
            </div>
        </div>
        
        <div class="progress mb-3" style="height: 10px;">
            <div class="progress-bar bg-success" style="width: ${metriques.gainPourcentage}%"></div>
        </div>
        
        <div class="small text-muted">
            <p><i class="bi bi-info-circle"></i> 
            ${metriques.speedup >= 2.0 ? 'Excellent accélération' : 
              metriques.speedup >= 1.5 ? 'Bonne accélération' : 
              'Accélération modérée'}
            </p>
        </div>
    `;
    
    // Tableau des métriques
    const tableau = document.getElementById('tableau-metriques-batch');
    tableau.innerHTML = `
        <table class="table table-sm small">
            <tr>
                <td>Nombre de plans:</td>
                <td class="text-end">${metriques.totalPlans}</td>
            </tr>
            <tr>
                <td>Temps séquentiel:</td>
                <td class="text-end">${formaterTempsHumain(metriques.tempsSequentiel)}</td>
            </tr>
            <tr>
                <td>Temps parallèle:</td>
                <td class="text-end">${formaterTempsHumain(metriques.tempsParalleleReel)}</td>
            </tr>
            <tr>
                <td>Accélération:</td>
                <td class="text-end text-success">${metriques.speedup.toFixed(2)}x</td>
            </tr>
        </table>
    `;
}

function afficherDetailsBatch(data) {
    const container = document.getElementById('details-batch-actuel');
    
    let plansListe = '';
    if (data.resultat.plans_details) {
        data.resultat.plans_details.forEach((plan, index) => {
            const statutBadge = plan.statut === 'reussi' ? 'bg-success' : 
                              plan.statut === 'erreur' ? 'bg-danger' : 'bg-warning';
            plansListe += `
                <div class="col-md-6 mb-2">
                    <div class="d-flex justify-content-between small">
                        <span>${plan.destination || `Plan ${index + 1}`}</span>
                        <span>
                            <span class="badge ${statutBadge}">${plan.statut}</span>
                            <span class="badge bg-secondary ms-1">${plan.temps_generation || 0}s</span>
                        </span>
                    </div>
                </div>
            `;
        });
    }
    
    container.innerHTML = `
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Informations Générales</h6>
                    <ul class="mb-0 small">
                        <li>Batch ID: <code>${data.batch_id.substring(0, 12)}...</code></li>
                        <li>Date: ${new Date().toLocaleString()}</li>
                        <li>CPUs disponibles: {{cpus}}</li>
                        <li>Concurrence max: {{plans_simultanes}}</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Performance</h6>
                    <ul class="mb-0 small">
                        <li>Temps total: <strong>${data.resultat.temps_total_batch}s</strong></li>
                        <li>Temps moyen/plan: <strong>${data.resultat.temps_moyen_par_plan}s</strong></li>
                        <li>Plans/min: <strong>${((data.resultat.plans_reussis / data.resultat.temps_total_batch) * 60).toFixed(1)}</strong></li>
                        <li>CPU utilisation: <strong>${Math.min(100, (data.resultat.total_plans / {{cpus}}) * 100).toFixed(0)}%</strong></li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Plans Générés</h6>
                    <div class="row">
                        ${plansListe || '<div class="col-12 text-muted">Aucun détail disponible</div>'}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function exporterGraphiqueBatch() {
    if (!graphiqueBatchActuel) {
        afficherNotification('Erreur', 'Aucun graphique à exporter', 'warning');
        return;
    }
    
    // Créer un canvas temporaire pour l'export
    const canvas = document.getElementById('graphiqueBatchActuel');
    const image = canvas.toDataURL('image/png');
    
    // Créer un lien de téléchargement
    const link = document.createElement('a');
    link.href = image;
    link.download = `comparatif_batch_${batchCourantId || 'actuel'}_${new Date().toISOString().slice(0, 10)}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    afficherNotification('Export', 'Graphique exporté en PNG', 'success');
}

// ==================== FONCTIONS EXISTANTES ====================
async function voirDetailsBatch(batchId) {
    try {
        const response = await fetch(`/api/batch/${batchId}/metriques`);
        const data = await response.json();
        
        if (data.success) {
            const metriques = data.metriques;
            
            let html = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>Informations Générales</h6>
                        <table class="table table-sm">
                            <tr><td>Batch ID:</td><td><code>${metriques.batch_id}</code></td></tr>
                            <tr><td>Statut:</td><td><span class="badge ${metriques.statut === 'termine' ? 'bg-success' : 'bg-warning'}">${metriques.statut}</span></td></tr>
                            <tr><td>Plans totaux:</td><td>${metriques.total_plans}</td></tr>
                            <tr><td>Plans réussis:</td><td>${metriques.plans_reussis}</td></tr>
                            <tr><td>Plans terminés:</td><td>${metriques.plans_termines}</td></tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6>Performance</h6>
                        <table class="table table-sm">
            `;
            
            if (metriques.speedup > 0) {
                html += `
                    <tr>
                        <td>Speedup:</td>
                        <td>
                            <span class="badge ${metriques.speedup >= 2.0 ? 'bg-success' : metriques.speedup >= 1.2 ? 'bg-warning' : 'bg-danger'}">
                                ${metriques.speedup.toFixed(2)}x
                            </span>
                        </td>
                    </tr>
                    <tr><td>Temps séquentiel estimé:</td><td>${metriques.temps_sequentiel_estime}s</td></tr>
                    <tr><td>Temps réel:</td><td>${metriques.temps_total}s</td></tr>
                    <tr><td>Gain de temps:</td><td><strong class="text-success">${metriques.gain_temps}s</strong></td></tr>
                `;
            }
            
            html += `
                        </table>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Temps d'exécution</h6>
                        <table class="table table-sm">
                            <tr><td>Temps écoulé:</td><td>${metriques.temps_ecoule}s</td></tr>
                            <tr><td>Temps moyen/plan:</td><td>${metriques.temps_moyen_plan}s</td></tr>
                            <tr><td>Temps minimum:</td><td>${metriques.temps_min_plan}s</td></tr>
                            <tr><td>Temps maximum:</td><td>${metriques.temps_max_plan}s</td></tr>
                        </table>
                    </div>
                </div>
            `;
            
            document.getElementById('contenu-details-batch').innerHTML = html;
            
            const modal = new bootstrap.Modal(document.getElementById('modalDetailsBatch'));
            modal.show();
        } else {
            afficherNotification('Erreur', data.erreur || 'Batch non trouvé', 'danger');
        }
    } catch (error) {
        console.error('Erreur détails batch:', error);
        afficherNotification('Erreur', 'Impossible de récupérer les détails', 'danger');
    }
}

function afficherGraphiqueHistorique(batchId) {
    fetch(`/api/batch/${batchId}/metriques`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const batchData = {
                    batch_id: batchId,
                    resultat: {
                        total_plans: data.metriques.total_plans,
                        plans_reussis: data.metriques.plans_reussis,
                        temps_total_batch: data.metriques.temps_total,
                        speedup_batch: data.metriques.speedup,
                        gain_temps: data.metriques.gain_temps,
                        temps_moyen_par_plan: data.metriques.temps_moyen_plan
                    }
                };
                
                afficherGraphiqueBatch(batchData);
                afficherNotification('Historique', `Graphique du batch ${batchId.substring(0, 8)} chargé`, 'info');
            }
        })
        .catch(error => {
            console.error('Erreur chargement historique:', error);
            afficherNotification('Erreur', 'Impossible de charger le graphique historique', 'danger');
        });
}

async function supprimerPlanIndividuel(planId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce plan ?')) return;
    
    try {
        const response = await fetch(`/plan/${planId}/supprimer`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const element = document.getElementById(`plan-${planId}`);
            if (element) {
                element.remove();
                afficherNotification('Suppression', 'Plan supprimé avec succès', 'success');
            }
            actualiserMetriques();
        } else {
            const erreur = await response.json();
            afficherNotification('Erreur', erreur.erreur || 'Erreur lors de la suppression', 'danger');
        }
    } catch (error) {
        afficherNotification('Erreur', 'Impossible de supprimer le plan', 'danger');
    }
}

async function actualiserMetriques() {
    try {
        const response = await fetch('/api/metriques/detaillees');
        if (response.ok) {
            const data = await response.json();
            
            if (data.success) {
                if (data.global) {
                    const speedupMoyen = document.getElementById('speedup-moyen');
                    const tempsMoyenPlan = document.getElementById('temps-moyen-plan');
                    const plansGeneres = document.getElementById('plans-generes');
                    
                    if (speedupMoyen) {
                        speedupMoyen.textContent = 
                            data.global.speedup_moyen ? data.global.speedup_moyen.toFixed(2) + 'x' : '0.00x';
                    }
                    
                    if (tempsMoyenPlan) {
                        tempsMoyenPlan.textContent = 
                            data.global.temps_moyen_par_plan ? data.global.temps_moyen_par_plan + 's' : '0.0s';
                    }
                    
                    if (plansGeneres) {
                        plansGeneres.textContent = 
                            data.utilisateur.plans_termines || 0;
                    }
                }
                
                const nombreBatchsTermines = document.getElementById('nombre-batchs-termines');
                if (nombreBatchsTermines && data.batchs_termines) {
                    nombreBatchsTermines.textContent = Object.keys(data.batchs_termines).length;
                }
            }
        }
    } catch (error) {
        console.error('Erreur actualisation métriques:', error);
    }
}

function actualiserHistorique() {
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function afficherNotification(titre, message, type = 'info') {
    if (typeof bootstrap === 'undefined' || !bootstrap.Toast) {
        console.log(`[${type}] ${titre}: ${message}`);
        return;
    }
    
    const toastId = 'toast-' + Date.now();
    const html = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">${titre}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    let conteneur = document.getElementById('conteneur-notifications');
    if (!conteneur) {
        conteneur = document.createElement('div');
        conteneur.id = 'conteneur-notifications';
        conteneur.className = 'position-fixed top-0 end-0 p-3';
        conteneur.style.zIndex = '9999';
        document.body.appendChild(conteneur);
    }
    
    conteneur.insertAdjacentHTML('beforeend', html);
    
    const element = document.getElementById(toastId);
    const toast = new bootstrap.Toast(element, { delay: 3000 });
    toast.show();
    
    element.addEventListener('hidden.bs.toast', () => {
        element.remove();
    });
}

// ==================== INITIALISATION ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard chargé avec graphique comparatif simplifié');
    
    // Charger Chart.js
    chargerChartJS();
    
    // Configurer les dates par défaut
    const aujourdhui = new Date();
    const semaineProchaine = new Date(aujourdhui);
    semaineProchaine.setDate(aujourdhui.getDate() + 7);
    const deuxSemaines = new Date(semaineProchaine);
    deuxSemaines.setDate(semaineProchaine.getDate() + 7);
    
    const premierFormulaire = document.querySelector('.formulaire-plan');
    if (premierFormulaire) {
        const champDepart = premierFormulaire.querySelector('.champ-date-depart');
        const champRetour = premierFormulaire.querySelector('.champ-date-retour');
        
        if (champDepart) {
            champDepart.value = semaineProchaine.toISOString().split('T')[0];
        }
        
        if (champRetour) {
            champRetour.value = deuxSemaines.toISOString().split('T')[0];
        }
        
        const boutonSuppression = premierFormulaire.querySelector('.btn-danger');
        if (boutonSuppression && document.querySelectorAll('.formulaire-plan').length > 1) {
            boutonSuppression.disabled = false;
        }
    }
    
    actualiserCompteurPlans();
    
    // Écouter les changements dans les formulaires
    document.getElementById('conteneurPlans').addEventListener('DOMNodeInserted', () => {
        setTimeout(() => {
            actualiserCompteurPlans();
        }, 100);
    });
    
    document.getElementById('conteneurPlans').addEventListener('DOMNodeRemoved', () => {
        setTimeout(() => {
            actualiserCompteurPlans();
        }, 100);
    });
    
    setInterval(actualiserMetriques, 30000);
    actualiserMetriques();
});