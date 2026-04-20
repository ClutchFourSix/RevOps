from flask import Flask, render_template, request
from revops.services import collect_msps

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    results = None

    if request.method == "POST":
        city = request.form.get("city")
        state = request.form.get("state")

        results = collect_msps(city, state)

    return render_template("index.html", results=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
