import concurrent.futures
import random
import time
from datetime import datetime
from typing import Dict, List, Any
from services.api_fetcher import fetch_all_data_concurrent
from services.itinerary_optimizer import plan_optimizer
from services.ai_recommendations import AIRecommendations

class PlanGenerator:
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.ai_recommender = AIRecommendations()
    
    def generate_plan_optimized(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        debut = time.time()
        destination = preferences.get('destination', 'Destination')
        
        api_results = fetch_all_data_concurrent(preferences)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futur_itinerary = executor.submit(self._generate_itinerary, preferences, api_results)
            futur_recommendations = executor.submit(
                self.ai_recommender.generate_personalized_recommendations, preferences, api_results
            )
            futur_budget = executor.submit(self._calculate_budget, preferences, api_results)
            
            itinerary = futur_itinerary.result()
            recommendations = futur_recommendations.result()
            budget_details = futur_budget.result()
        
        plan = self._assembler_plan(preferences, api_results, itinerary, recommendations, budget_details)
        
        print(f"Plan généré en {time.time()-debut:.2f}s pour {destination}")
        return plan
    
    def _generate_itinerary(self, preferences: Dict[str, Any], api_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        activites = api_results.get("activities", [])
        hotels = api_results.get("hotels", [])
        restaurants = api_results.get("restaurants", [])
        
        optimise = plan_optimizer.optimize_plan_days(preferences, activites, hotels, restaurants)
        jours_itineraire = optimise.get("itinerary", [])
        
        print(f"plan généré: {len(jours_itineraire)} jours")
        return jours_itineraire
    
    def _calculate_budget(self, preferences: Dict[str, Any], api_results: Dict[str, Any]) -> Dict[str, Any]:
        budget = float(preferences.get("budget", 0))
        vols = api_results.get("flights", [])
        hotels = api_results.get("hotels", [])
        duree = self._calculer_duree(preferences.get("depart_date"), preferences.get("return_date"))
        
        cout_vol = self._estimer_cout_vols(vols)
        cout_hotel = self._estimer_cout_hotels(hotels, duree)
        
        if budget <= 0:
            budget = (cout_vol + cout_hotel) * 1.5
        
        repartition = {
            "total": round(budget, 2),
            "flight": round(cout_vol, 2),
            "accommodation": round(cout_hotel, 2),
            "food": round(budget * 0.25, 2),
            "activities": round(budget * 0.15, 2),
            "transport": round(budget * 0.10, 2),
            "shopping": round(budget * 0.08, 2),
            "misc": round(budget * 0.07, 2),
            "daily": round(budget / max(1, duree), 2),
            "currency": "EUR"
        }
        
        return repartition
    
    def _estimer_cout_vols(self, vols: List[Dict[str, Any]]) -> float:
        if not vols:
            return random.uniform(150, 600)
        
        prix_valides = []
        for vol in vols:
            if isinstance(vol, dict):
                donnees_prix = vol.get('price', {})
                if isinstance(donnees_prix, dict):
                    prix = donnees_prix.get('total', donnees_prix.get('amount', 0))
                else:
                    prix = donnees_prix
                
                try:
                    prix_float = float(prix)
                    if prix_float > 0:
                        prix_valides.append(prix_float)
                except:
                    continue
        
        return min(prix_valides) if prix_valides else random.uniform(150, 600)
    
    def _estimer_cout_hotels(self, hotels: List[Dict[str, Any]], nuits: int) -> float:
        if not hotels or nuits <= 0:
            return random.uniform(50, 200) * max(1, nuits)
        
        prix_valides = []
        for hotel in hotels[:10]:
            if isinstance(hotel, dict):
                prix = hotel.get('price', 0)
                try:
                    prix_float = float(prix)
                    if prix_float > 0:
                        prix_valides.append(prix_float)
                except:
                    continue
        
        if prix_valides:
            return min(prix_valides) * nuits
        
        return random.uniform(50, 200) * nuits
    
    def _calculer_duree(self, date_depart: str, date_retour: str) -> int:
        try:
            if date_depart and date_retour:
                debut = datetime.strptime(date_depart, "%Y-%m-%d")
                fin = datetime.strptime(date_retour, "%Y-%m-%d")
                return max(1, (fin - debut).days)
        except:
            pass
        
        return 7
    
    def _assembler_plan(self, preferences: Dict[str, Any], api_results: Dict[str, Any], 
                       itinerary: List[Dict[str, Any]], recommendations: Dict[str, Any], 
                       budget: Dict[str, Any]) -> Dict[str, Any]:
        destination = preferences.get("destination", "Destination")
        duree = self._calculer_duree(preferences.get("depart_date"), preferences.get("return_date"))
        
        plan = {
            "destination": destination,
            "origin": preferences.get("origin", "TUN"),
            "depart_date": preferences.get("depart_date"),
            "return_date": preferences.get("return_date"),
            "duration_days": duree,
            "budget": float(preferences.get("budget", 0)),
            "flights": api_results.get("flights", []),
            "hotels": api_results.get("hotels", []),
            "restaurants": api_results.get("restaurants", []),
            "activities": api_results.get("activities", []),
            "weather": api_results.get("weather", {}),
            "itinerary": itinerary,
            "estimated_budget": budget,
            "recommendations": recommendations.get("personalized_recommendations", []),
            "packing_tips": recommendations.get("packing_tips", []),
            "travel_style": recommendations.get("travel_style", "optimisé"),
            "ai_enhanced": recommendations.get("ai_enhanced", False),
            "travel_tips": self._generer_conseils_voyage(destination, duree, budget),
            "summary": self._generer_resume(destination, duree, budget, recommendations),
            "generation_time": time.time(),
            "smart_score": recommendations.get("smart_score", 85),
            "optimization_level": "high"
        }
        
        return plan
    
    def _generer_conseils_voyage(self, destination: str, duree: int, budget: Dict[str, Any]) -> List[str]:
        conseils = [
            f"🎯 Visitez {destination} tôt le matin pour éviter les foules",
            f"💰 Budget quotidien recommandé: {budget.get('daily', 0):.0f}€",
            "📱 Téléchargez l'application de transport local avant le départ",
            "🎒 Prévoyez des chaussures confortables pour la marche",
            "🔌 N'oubliez pas votre adaptateur de prise",
            "📸 Prenez des photos aux heures dorées (lever/coucher du soleil)"
        ]
        
        if duree > 10:
            conseils.append("⏱️ Planifiez des journées de repos pour éviter la fatigue")
        
        if budget.get('total', 0) < 1000:
            conseils.append("💸 Explorez les options gratuites et les marchés locaux")
        
        return conseils[:6]
    
    def _generer_resume(self, destination: str, duree: int, budget: Dict[str, Any], 
                        recommendations: Dict[str, Any]) -> str:
        texte_ai = "avec recommandations intelligentes" if recommendations.get('ai_enhanced') else "optimisé"
        
        return f"""Voyage de {duree} jours à {destination} {texte_ai}.
Budget total estimé: {budget.get('total', 0):.0f}€ ({budget.get('daily', 0):.0f}€ par jour).
Itinéraire optimisé avec un équilibre entre visites culturelles, détente et gastronomie.
Recommandations personnalisées incluses pour une expérience mémorable."""