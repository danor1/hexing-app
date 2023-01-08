import os
from flask import Flask
from flask import render_template, url_for, session, redirect
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
import json


def init_app():
    """Construct core Flask application with embedded Dash app."""
    app = Flask(__name__, instance_relative_config=True)

    # load config variables from heroku
    auth_client_id = str(os.environ.get("AUTH0_CLIENT_ID", None))
    auth_client_secret = str(os.environ.get("AUTH0_CLIENT_SECRET", None))
    auth_domain = str(os.environ.get("AUTH0_DOMAIN", None))
    app.secret_key = str(os.environ.get("APP_SECRET_KEY", None))

    # if heroku config vars return None, switch to local variables (this occurs when running wsgi locally)
    if app.secret_key == "None":
        with open('AUTH0_details.json') as json_file:
            auth_details = json.load(json_file)
        auth_client_id = auth_details["AUTH0_CLIENT_ID"]
        auth_client_secret = auth_details["AUTH0_CLIENT_SECRET"]
        auth_domain = auth_details["AUTH0_DOMAIN"]
        app.secret_key = auth_details["APP_SECRET_KEY"]

    with app.app_context():
        # Import parts of our core Flask app from . import routes

        oauth = OAuth(app)

        oauth.register(
            "auth0",
            client_id=auth_client_id,
            client_secret=auth_client_secret,
            client_kwargs={
                "scope": "openid profile email",
            },
            server_metadata_url=f'https://{auth_domain}/.well-known/openid-configuration'
        )

        @app.route("/login")
        def login():
            return oauth.auth0.authorize_redirect(
                redirect_uri=url_for("callback", _external=True)
            )

        @app.route("/callback", methods=["GET", "POST"])
        def callback():
            token = oauth.auth0.authorize_access_token()
            print(token)
            session["user"] = token
            return redirect("/")

        @app.route("/logout")
        def logout():
            session.clear()
            return redirect(
                "https://" + auth_domain
                + "/v2/logout?"
                + urlencode(
                    {
                        "returnTo": url_for("home", _external=True),
                        "client_id": auth_client_id,
                    },
                    quote_via=quote_plus,
                )
            )

        @app.route("/")
        def home():
            """Landing page."""
            return render_template(
                "index.jinja2",
                session=session.get('user'),
                pretty=json.dumps(session.get('user'), indent=4),
                title="Hexing App landing page",
                description="Landing page (may be removed in future). Select hyperlink below to continue",
                template="home-template",
            )

        # Import Dash application
        from .dashboard.__init__ import init_dashboard
        app = init_dashboard(app)

        return app
