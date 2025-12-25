from extensions import db

# Importer les modèles ici pour les rendre accessibles
from .user import User
from .plan import Plan as TravelPlan

__all__ = ["User", "TravelPlan", "db"]
