from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Performance Improvement API is running!"

@app.route("/run-performance-improvement", methods=["GET"])
def run_performance_improvement():
    try:
        # اجرای مستقیم اسکریپت performance_improvement.py
        result = subprocess.run(
            ["python", "performance_improvement.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({
            "status": "ok",
            "output": result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "error",
            "output": e.stderr
        }), 500
