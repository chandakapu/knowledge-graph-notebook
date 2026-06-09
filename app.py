import os
from flask import Flask
from routes.workspace import workspace_bp
from routes.studio import studio_bp

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Register Blueprints
app.register_blueprint(workspace_bp)
app.register_blueprint(studio_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)
