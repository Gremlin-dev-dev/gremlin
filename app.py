from flask import Flask, jsonify, request, redirect, url_for

from extensions import db, login_manager, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object("config")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api") or request.path.startswith("/chat"):
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("auth.login"))

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large."}), 413

    from auth import auth_bp
    from chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
