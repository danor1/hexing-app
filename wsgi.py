"""Application entry point."""
from plotly_flask_dir import init_app


# initialise Flask app
app = init_app()


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
