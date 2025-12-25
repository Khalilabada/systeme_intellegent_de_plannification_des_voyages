// static/js/main.js

// Initialisation lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    initPlanPage();
});

function initPlanPage() {
    // Socket.io pour les mises à jour en temps réel
    const socket = io();

    // Notification quand un plan est supprimé
    socket.on('plan_deleted', data => {
        if (data.plan_id == window.currentPlanId) {
            showNotification('Plan supprimé', 'info');
            setTimeout(() => {
                window.location.href = window.dashboardUrl;
            }, 1500);
        }
    });

    // Initialisation des tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Animation d'apparition progressive des cartes
    animateCards();
    
    // Animation pour la timeline
    animateTimeline();
    
    // Gestion des onglets - sauvegarde de l'onglet actif
    initTabManagement();
}

// Suppression de plan
function deletePlan(planId) {
    if (!confirm("Voulez-vous vraiment supprimer ce plan ? Cette action est irréversible.")) {
        return;
    }

    fetch(`/plan/${planId}/delete`, { 
        method: "POST", 
        headers: {"Content-Type": "application/json"} 
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showNotification('Plan supprimé avec succès!', 'success');
            setTimeout(() => {
                window.location.href = window.dashboardUrl;
            }, 1000);
        } else {
            showNotification('Erreur: ' + (data.error || 'Erreur inconnue'), 'error');
        }
    })
    .catch(err => {
        console.error('Erreur:', err);
        showNotification('Erreur réseau lors de la suppression', 'error');
    });
}

// Fonction de notification
function showNotification(message, type = 'info') {
    // Créer une notification toast Bootstrap
    const toastContainer = document.createElement('div');
    toastContainer.innerHTML = `
        <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0 show" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    document.body.appendChild(toastContainer);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toastContainer.remove();
    }, 5000);
}

// Animation des cartes
function animateCards() {
    const cards = document.querySelectorAll('.flight-card, .hotel-card, .restaurant-card, .activity-card, .weather-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Animation de la timeline
function animateTimeline() {
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, index * 150);
    });
}

// Gestion des onglets
function initTabManagement() {
    const tabEl = document.querySelector('button[data-bs-toggle="tab"]');
    if (tabEl) {
        tabEl.addEventListener('shown.bs.tab', function (event) {
            localStorage.setItem('activeTab', event.target.getAttribute('data-bs-target'));
        });
    }

    const activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        const tabTrigger = document.querySelector(`[data-bs-target="${activeTab}"]`);
        if (tabTrigger) {
            new bootstrap.Tab(tabTrigger).show();
        }
    }
}