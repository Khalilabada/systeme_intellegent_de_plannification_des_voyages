# services/ai_recommendations.py - VERSION SIMPLIFIÉE ET CORRIGÉE
import json
from typing import Dict, List
from datetime import datetime
from openai import OpenAI
from config import Config

class AIRecommendations:
    def __init__(self):
        self.client = None
        self._initialize_ai_client()
    
    def _initialize_ai_client(self):
        try:
            
            if hasattr(Config, 'OPENROUTER_API_KEY') and Config.OPENROUTER_API_KEY:
                self.client = OpenAI(
                    api_key=Config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
        except ImportError:
            self.client = None
        except Exception:
            self.client = None
    
    def generate_personalized_recommendations(self, preferences: Dict, travel_data: Dict) -> Dict:
        
        if self.client:
            try:
                return self._generate_with_ai(preferences, travel_data)
            except Exception:
                pass
    def _generate_with_ai(self, preferences: Dict, travel_data: Dict) -> Dict:
        destination = preferences.get('destination', 'Destination')
        duration = self._calculate_duration(
            preferences.get('depart_date'),
            preferences.get('return_date')
        )
        budget = preferences.get('budget', 0)
        
        activities_count = len(travel_data.get('activities', []))
        hotels_count = len(travel_data.get('hotels', []))
        restaurants_count = len(travel_data.get('restaurants', []))
        
        prompt = f"""
        Recommandations pour un voyage à {destination}.
        
        Infos:
        - Durée: {duration} jours
        - Budget: {budget}€
        - Activités: {activities_count}
        - Hôtels: {hotels_count}
        - Restaurants: {restaurants_count}
        
        Format JSON:
        {{
            "personalized_recommendations": [
                "Recommandation 2 pour {destination}",
                "Recommandation 2 budget",
                "Recommandation 3 activités",
                "Recommandation 4 gastronomie"
            ],
            "packing_tips": [
                "Conseil 1 {destination}",
                "Conseil 2 saison",
                "Conseil 3 essentiel",
                "Conseil 4 pratique"
            ],
            "travel_style": "Style de voyage"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            ai_data = json.loads(content)
            
            return {
                "personalized_recommendations": ai_data.get("personalized_recommendations", []),
                "packing_tips": ai_data.get("packing_tips", []),
                "travel_style": ai_data.get("travel_style", ""),
                "ai_enhanced": True,
                "model": "gpt-3.5-turbo",
                "smart_score": 95
            }
        except Exception:
            print("Erreur lors de la génération AI")
           
    def _calculate_duration(self, depart_date: str, return_date: str) -> int:
        try:
            if depart_date and return_date:
                start = datetime.strptime(depart_date, "%Y-%m-%d")
                end = datetime.strptime(return_date, "%Y-%m-%d")
                return max(1, (end - start).days)
        except:
            pass
        return 0
   
