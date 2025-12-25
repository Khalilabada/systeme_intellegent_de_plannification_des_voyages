# services/itinerary_optimizer.py - VERSION OPTIMISÉE ET CORRIGÉE
import re
from typing import Dict, List
from datetime import datetime

class OptimizedPlanOptimizer:
    def optimize_plan_days(self, preferences: Dict, activities_data: List, hotels_data: List, restaurants_data: List) -> Dict:
        destination = preferences.get("destination", "Destination")
        duration = self.calculate_duration_fast(preferences)
        activities_list = self.activities_simple(activities_data)
        selected_hotel = self.select_meilleur_hotel(hotels_data, preferences)
        selected_restaurants = self.select_restaurants(restaurants_data, duration)
        plan_days = self.generate_plan_days(
            duration, destination, activities_list, selected_hotel, selected_restaurants
        )
        
        return {
            "itinerary": plan_days,
            "hotel": selected_hotel,
            "total_days": duration,
            "optimized": True,
        }
    
    def generate_plan_days(self, duration: int, destination: str,
                                activities: List, hotel: Dict, restaurants: List) -> List:
        plan_days = []
        
        for day in range(1, duration + 1):
            plan_days.append(self.create_day_plan(
                day, duration, destination, activities, hotel, restaurants
            ))
        
        return plan_days
    
    def create_day_plan(self, day: int, total_days: int, destination: str,activities: List, hotel: Dict, restaurants: List) -> Dict:
        selected_activities = self.select_activities_for_day(activities, day)
        restaurant = self.get_restaurant_for_day(restaurants, day)
        morning_acts = selected_activities[:min(2, len(selected_activities))]
        afternoon_acts = selected_activities[2:4] if len(selected_activities) > 2 else []
        estimated_cost = self.estimate_budget_day(len(selected_activities), hotel.get("price", 100.0))
        
        # Thème
        if day == 1:
            theme = "Arrivée"
        elif day == total_days:
            theme = "Départ"
        else:
            theme = f"Jour {day}"
        
        return {
            "day": day,
            "theme": theme,
            "accommodation": hotel.get("name", ""),
            "hotel_rating": f"⭐{hotel.get('rating', 4.0):.1f}",
            "morning": morning_acts,
            "afternoon": afternoon_acts,
            "evening": [f"Dîner au {restaurant}"],
            "estimated_cost": estimated_cost,
            "activity_count": len(selected_activities)
        }
    
    def activities_simple(self, activities: List) -> List[str]:
        activity_names = []
        seen = set()
        
        for activity in activities[:15]: 
            if isinstance(activity, dict):
                name = str(activity.get("name", "")).strip()
                if name and name not in seen:
                    activity_names.append(name)
                    seen.add(name)
        
        return activity_names
    
    def select_activities_for_day(self, activities: List, day: int) -> List[str]:
        activities_per_day = min(4, len(activities))
        selected = []
        
        for i in range(activities_per_day):
            idx = ((day - 1) * 2 + i) % len(activities)
            if idx < len(activities):
                selected.append(activities[idx])
        
        return selected
    
    def select_meilleur_hotel(self, hotels: List, preferences: Dict) -> Dict:

        duration = self.calculate_duration_fast(preferences)
        budget = float(preferences.get("budget", 0))
        
        prix_par_night = 150
        if budget > 0 and duration > 0:
            hotel_budget = budget * 0.3  # 30% du budget pour l'hôtel
            prix_par_night = hotel_budget / duration
        

        best_hotel = None
        best_score = -1
        
        for hotel in hotels[:10]:
            if not isinstance(hotel, dict):
                continue
                
            name = hotel.get("name", "Hôtel")
            price = self.safe_parse_price(hotel.get("price"))
            rating = self.safe_parse_rating(hotel.get("rating"))
            price_score = max(0, 100 - (price / prix_par_night * 50)) if prix_par_night > 0 else 50
            rating_score = rating * 15
            total_score = price_score + rating_score
            
            if total_score > best_score:
                best_score = total_score
                best_hotel = {
                    "name": name,
                    "price": price,
                    "rating": rating,
                    "address": hotel.get("address", ""),
                    "photo": hotel.get("photo", ""),
                    "in_budget": price <= prix_par_night * 1.2
                }
        
        return best_hotel 
    
    
    
    def safe_parse_price(self, price_value) -> float:
       
        try:
            price_str = str(price_value)
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', price_str.replace(',', '.'))
            if match:
                price = float(match.group(1))
                if 0 < price < 10000:
                    return price
        except:
            pass
        
        return 100.0
    
    def safe_parse_rating(self, rating_value) -> float:
        
        if isinstance(rating_value, (int, float)):
            return min(max(float(rating_value), 0), 5)
        
        try:
            rating_str = str(rating_value)
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', rating_str)
            if match:
                rating = float(match.group(1))
                return min(max(rating, 0), 5)
        except:
            pass
        
        return 4.0
    
    def get_restaurant_for_day(self, restaurants: List, day: int) -> str:

        index = (day - 1) % min(5, len(restaurants))
        restaurant = restaurants[index]
        
        if isinstance(restaurant, dict):
            return restaurant.get("name", "restaurant local")
        return "restaurant local"
    
    def select_restaurants(self, restaurants: List, duration: int) -> List:
        max_restaurants = min(10,len(restaurants), duration * 2)
        if len(restaurants) > 1:
            try:
                sorted_restaurants = sorted(
                    restaurants[:10],
                    key=lambda r: self.safe_parse_rating(r.get("rating", 0)),
                    reverse=True
                )
                return sorted_restaurants[:max_restaurants]
            except:
                return restaurants[:max_restaurants]
        
        return restaurants[:max_restaurants]
    
    def estimate_budget_day(self, activity_count: int, hotel_price: float) -> float:
        activity_budget = activity_count * 15
        hotel_budget = hotel_price
        food_budget = 40 
        transport_budget = 10
        
        return round(activity_budget + hotel_budget + food_budget + transport_budget, 2)
    
    def calculate_duration_fast(self, preferences: Dict) -> int:
        try:
            start_str = preferences.get("depart_date")
            end_str = preferences.get("return_date")
            
            if start_str and end_str:
                start = datetime.strptime(start_str, "%Y-%m-%d")
                end = datetime.strptime(end_str, "%Y-%m-%d")
                days = (end - start).days
                return max(1, days)
        except:
            pass
        return 1


plan_optimizer = OptimizedPlanOptimizer()