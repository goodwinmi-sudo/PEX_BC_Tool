from flask import Blueprint

def init_app(app):
    from routes.api import api_bp
    from routes.views import views_bp
    from routes.tasks import tasks_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(tasks_bp)
