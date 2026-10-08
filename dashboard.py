"""Local web dashboard for the latest counting session."""

from flask import Flask, jsonify, render_template

from storage import dashboard_state, initialize

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    return jsonify(dashboard_state())


if __name__ == "__main__":
    initialize()
    app.run(host="127.0.0.1", port=5000, debug=False)
