# app.py
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 Performance Improvement API is running"

@app.route("/run-performance-improvement", methods=["GET"])
def run_performance_improvement():
    try:
        # اینجا بعداً کد performance_improvement.py رو کپی می‌کنیم
        return jsonify({"status": "ok", "message": "✅ Script executed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
