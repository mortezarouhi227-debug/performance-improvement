from flask import Flask, jsonify
import subprocess
import sys

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Performance Improvement API is running!"

@app.route("/run-performance-improvement", methods=["GET"])
def run_performance_improvement():
    try:
        # اجرای اسکریپت performance_improvement.py
        result = subprocess.run(
            [sys.executable, "performance_improvement.py"],
            capture_output=True, text=True, check=True
        )
        return jsonify({
            "status": "success",
            "output": result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "error",
            "output": e.stderr
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
