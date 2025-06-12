# route_external_admin_settings.py:

from config import *
from functions_authentication import *
from functions_settings import *
from functions_group import *
from functions_documents import *

def register_route_external_admin_settings(app):
    @app.route('/external/applicationsettings/set', methods=['POST'])
    @accesstoken_required
    def external_update_application_settings():
        return jsonify("Method not available yet."), 200

    
    @app.route('/external/applicationsettings/get', methods=['GET'])
    @accesstoken_required
    def external_get_application_settings():
        settings = get_settings()
        return settings, 200
