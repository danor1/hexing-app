"""Routes for parent Flask app."""
from flask import current_app as app
from flask import render_template, url_for, session, redirect
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
import json


with open('AUTH0_details.json') as json_file:
    auth_details = json.load(json_file)

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=auth_details["AUTH0_CLIENT_ID"],
    client_secret=auth_details["AUTH0_CLIENT_SECRET"],
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{auth_details["AUTH0_DOMAIN"]}/.well-known/openid-configuration'
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
        "https://" + auth_details["AUTH0_DOMAIN"]
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": auth_details["AUTH0_CLIENT_ID"],
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
        title="Plotly Dash Flask Tutorial",
        description="Embed Plotly Dash into your Flask applications.",
        template="home-template",
        body="This is a homepage served with Flask."
    )
