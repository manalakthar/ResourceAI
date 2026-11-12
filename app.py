import json
from flask import Flask, render_template, request, jsonify
from modules.resource_analysis import load_data, calculate_balance
from modules.redistribution import recommend_transfers

app = Flask(__name__)

COLS = ["location", "lat", "lng", "category", "unit", "available_quantity",
        "required_quantity", "balance", "coverage", "status", "risk", "date", "source"]


def records(df):
    return json.loads(df[COLS].to_json(orient="records"))


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard")
def api_dashboard():
    rtype = request.args.get("type", "water")
    if rtype not in ("food", "water"):
        rtype = "water"
    df = calculate_balance(load_data())
    df = df[df["resource_type"] == rtype]
    transfers, unmet = recommend_transfers(df, rtype)
    return jsonify({
        "type": rtype,
        "locations": records(df),
        "transfers": transfers,
        "unmet": unmet,
        "sources": sorted(df["source"].unique().tolist()),
        "date": str(df["date"].max()) if len(df) else None,
    })


@app.route("/resource-data")
def resource_data():
    rtype = request.args.get("type", "all")
    df = calculate_balance(load_data())
    if rtype in ("food", "water"):
        df = df[df["resource_type"] == rtype]
    rows = json.loads(df.drop(columns=["lat", "lng"]).to_json(orient="records"))
    return render_template("resource_data.html", rows=rows, selected=rtype)


if __name__ == "__main__":
    app.run(debug=True)
