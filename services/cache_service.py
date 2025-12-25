import time
import threading

# Cache en mémoire avec synchronisation
memoire_cache = {}
cache_lock = threading.RLock()  # NOUVEAU : verrou réentrant
cache_stats = {
    'succes': 0,
    'echec': 0,
    'taille': 0
}

def get_cached_data(key):
    with cache_lock:  
        if key in memoire_cache:
            cache_entry = memoire_cache[key]
            # Vérifier si le cache a expiré
            if cache_entry.get('expires_at', 0) > time.time():
                cache_stats['succes'] += 1
                return cache_entry['data']
            else:

                del memoire_cache[key]
                cache_stats['taille'] -= 1
                cache_stats['echec'] += 1
        else:
            cache_stats['echec'] += 1
    return None

def set_cached_data(key, data, ttl=3600):
    with cache_lock:
        memoire_cache[key] = {
            'data': data,
            'expires_at': time.time() + ttl,
            'cached_at': time.time()
        }
        cache_stats['taille'] += 1
    return data

def get_cache_stats():
    with cache_lock:
        return {
            'hits': cache_stats['succes'],
            'misses': cache_stats['echec'],
            'hit_ratio': cache_stats['succes'] / max(1, cache_stats['succes'] + cache_stats['echec']),
            'size': cache_stats['taille']
        }
    
def set_cached_data_without_ttl(key, data):
    return set_cached_data(key, data)