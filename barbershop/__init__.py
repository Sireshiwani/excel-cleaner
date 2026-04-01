from flask import Flask
from .extensions import db, login_manager
from .models import User
from .views import bp
from .cli import register_cli


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        SQLALCHEMY_DATABASE_URI="sqlite:///barbershop.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(bp)
    register_cli(app)

    with app.app_context():
        db.create_all()

    return app
