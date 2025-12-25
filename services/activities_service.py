# services/activities_service.py - VERSION AVEC SERPAPI
import random
from datetime import datetime
from config import Config
from .cache_service import get_cached_data, set_cached_data
from .api_fetcher import get_country_code_for_city, FIXED_ACTIVITY_IMAGE
from serpapi import GoogleSearch

ACTIVITY_IMAGES = {
    "OTHER": "https://images.unsplash.com/photo-1540541338287-41700207dee6?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80",
    "default": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"
}

def search_activities(city_name: str, max_results=12):
    cache_key = f"activities_{city_name.lower().replace(' ', '_')}"
    
    cached_data = get_cached_data(cache_key)
    if cached_data is not None:
        return cached_data
    
    activities = search_activities_api(city_name, max_results)
    return set_cached_data(cache_key, activities)

def search_activities_api(city_name, max_results=12):
    if not hasattr(Config, 'SERP_API_KEY') or not Config.SERP_API_KEY:
        return []
    
    try:
        country_code = get_country_code_for_city(city_name)
        search_strategies = [
            {"engine": "google_local", "q": "tourist attractions", "location": city_name, "hl": "fr", "gl": country_code, "type": "search", "num": max_results},
            {"engine": "google_local", "q": f"things to do in {city_name}", "location": city_name, "hl": "fr", "gl": country_code, "type": "search", "num": max_results},
            {"engine": "google_local", "q": f"sightseeing {city_name}", "location": city_name, "hl": "fr", "gl": country_code, "type": "search", "num": max_results}
        ]
        
        activities = []
        for params in search_strategies:
            if len(activities) >= max_results:
                break   
            params["api_key"] = Config.SERP_API_KEY
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                if "error" in results:
                    continue
                local_results = results.get("local_results", [])
                
                for result in local_results[:max_results]:
                    try:
                        name = result.get("title", "").strip()
                        if not name:
                            continue
                        
                        if any(act.get("name") == name for act in activities):
                            continue
                        
                        address = result.get("address", "")
                        
                        rating = result.get("rating", 0)
                        if isinstance(rating, (int, float)):
                            rating = float(rating)
                        else:
                            rating = round(random.uniform(3.8, 5.0), 1)
                        
                        reviews = result.get("reviews", 0)
                        if isinstance(reviews, (int, float)):
                            reviews = int(reviews)
                        else:
                            reviews = random.randint(10, 500)
                        
                        description = result.get("description", "")
                        
                        activity_type = determine_activity_type(name, description)
                        
                        price_data = result.get("price", {})
                        if isinstance(price_data, dict):
                            price = price_data.get('low', 0) if price_data else 0
                        else:
                            price = 0
                        
                        photos = result.get("photos", [])
                        image_url = FIXED_ACTIVITY_IMAGE
                        if photos and isinstance(photos, list) and len(photos) > 0:
                            if isinstance(photos[0], dict) and "image" in photos[0]:
                                image_url = photos[0]["image"]
                            elif isinstance(photos[0], str):
                                image_url = photos[0]
                        
                        gps_coordinates = result.get("gps_coordinates", {})
                        latitude = gps_coordinates.get("latitude", 0)
                        longitude = gps_coordinates.get("longitude", 0)
                        
                        website = result.get("website", "")
                        phone = result.get("phone", "")
                        hours = result.get("hours", "Open daily")
                        
                        duration_options = ["2h", "3h", "4h", "Journée"]
                        duration = random.choice(duration_options)
                        
                        activity_data = {
                            "id": f"serpapi_act_{len(activities)}",
                            "name": name,
                            "type": activity_type,
                            "category": _map_activity_category(activity_type),
                            "description": description if description else f"Visite de {name} à {city_name}",
                            "short_description": description[:200] + "..." if description and len(description) > 200 else f"Visite de {name}",
                            "duration": duration,
                            "price": {
                                "amount": float(price) if price else random.uniform(10, 100),
                                "currency": "EUR",
                                "original_amount": random.uniform(15, 120),
                                "discount": random.choice([0, 10, 20, 30]) if price else 0
                            },
                            "rating": rating,
                            "review_count": reviews,
                            "location": {
                                "latitude": latitude if latitude else 0,
                                "longitude": longitude if longitude else 0,
                                "address": address if address else city_name,
                                "city": city_name
                            },
                            "photos": [{"url": image_url, "caption": name, "source": "SerpAPI" if not image_url.startswith("https://images.unsplash.com") else "Unsplash"}],
                            "booking_required": price > 0,
                            "family_friendly": activity_type in ['SIGHTSEEING', 'ENTERTAINMENT', 'CULTURAL'],
                            "accessibility": random.choice(["accessible", "partiellement accessible"]),
                            "contact": {
                                "website": website ,
                                "phone": phone if phone else generate_telephone_number()
                            },
                            "opening_hours": hours,
                            "metadata": {
                                "timestamp": datetime.now().isoformat(),
                                "popularity_score": round(rating * 20, 1)
                            }
                        }
                        
                        activities.append(activity_data)
                        
                    except Exception:
                        continue
                
            except Exception:
                continue
        
        return activities
        
    except Exception:
        return []

def determine_activity_type(name, description):
    text_to_check = f"{name} {description}".lower()
    
    type_mapping = [
        (["musée", "museum", "galerie", "gallery", "exhibition", "exposition"], "CULTURAL"),
        (["château", "castle", "palais", "palace", "monument", "historic", "histoire", "historical"], "SIGHTSEEING"),
        (["restaurant", "bistro", "café", "cafe", "gastronomie", "food", "dining", "resto"], "FOOD_AND_DRINK"),
        (["parc", "park", "jardin", "garden", "nature", "natural"], "SIGHTSEEING"),
        (["shopping", "boutique", "magasin", "store", "mall", "market", "marché"], "SHOPPING"),
        (["théâtre", "theater", "cinéma", "cinema", "spectacle", "show", "concert", "music"], "ENTERTAINMENT"),
        (["sport", "stade", "stadium", "randonnée", "hiking", "ski", "golf", "tennis", "swimming", "natation"], "SPORTS"),
        (["bar", "club", "night", "soirée", "pub", "disco", "dancing"], "OTHER"),
        (["tour", "guided", "visite", "touristique", "sightseeing", "attraction"], "SIGHTSEEING")
    ]
    
    for keywords, activity_type in type_mapping:
        if any(keyword in text_to_check for keyword in keywords):
            return activity_type
    
    return "OTHER"

def _map_activity_category(activity_type):
    category_map = {
        'SIGHTSEEING': 'Visite touristique',
        'FOOD_AND_DRINK': 'Gastronomie',
        'SPORTS': 'Sports & Activité',
        'SHOPPING': 'Shopping',
        'ENTERTAINMENT': 'Divertissement',
        'CULTURAL': 'Culture',
        'OTHER': 'Activité'
    }
    return category_map.get(activity_type, 'Activité')



def generate_telephone_number():
    return f"+216 {random.randint(1, 9)}{random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"

