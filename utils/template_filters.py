# utils/template_filters.py
import json
from datetime import datetime

def register_filters(app):
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%d/%m/%Y'):
        try:
            if isinstance(value, str):
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%d/%m/%y']:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime(format)
                    except:
                        continue
            return str(value)
        except:
            return str(value)
    
    @app.template_filter('fromjson')
    def fromjson(value):
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except:
            return {}
    
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)