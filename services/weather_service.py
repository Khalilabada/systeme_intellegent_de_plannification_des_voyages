# services/weather_service.py
import requests
from datetime import datetime
from config import Config
from .cache_service import get_cached_data, set_cached_data
import time


def get_weather(city, depart_date=None, return_date=None):
    cache_key = f"weather_{city}_{depart_date}_{return_date}"
    
    cached_data = get_cached_data(cache_key)
    if cached_data is not None:
        return cached_data
    
    key = Config.OPENWEATHER_API_KEY

    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={key}&units=metric"
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
       
        if "list" in data:
            for forecast in data["list"]:
                
                if "dt_txt" in forecast and "dt" not in forecast:
                    try:
                        dt_obj = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
                        forecast["dt"] = int(dt_obj.timestamp())
                    except:
                        pass
                
                # S'assurer que weather est une liste
                if "weather" in forecast and not isinstance(forecast["weather"], list):
                    forecast["weather"] = [forecast["weather"]] if forecast["weather"] else []
        
        # Structuration standardisée
        result = {
            "city": data.get("city", {"name": city, "country": "", "coord": {}}),
            "period": {
                "from": depart_date if depart_date else datetime.now().strftime("%Y-%m-%d"),
                "to": return_date if return_date else (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            },
            "list": data.get("list", []),
            "forecast": data.get("list", []),
            "cnt": data.get("cnt", 0),
            "cod": data.get("cod", "200")
        }
        
        print(f"✅ Météo récupérée pour {city}: {len(result['list'])} prévisions")
        return set_cached_data(cache_key, result, ttl=3600)
        
    except Exception as e:
        print(f"Erreur OpenWeather pour {city}: {e}")
        # Retourner une structure vide mais valide
        return {
            "city": {"name": city, "country": "", "coord": {}},
            "period": {
                "from": depart_date if depart_date else datetime.now().strftime("%Y-%m-%d"),
                "to": return_date if return_date else (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            },
            "list": [],
            "forecast": [],
            "cnt": 0,
            "cod": "500",
            "error": str(e)
        }
    