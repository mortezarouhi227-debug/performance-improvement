from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "🎉 Performance Improvement API is running on Render!"

@app.route("/run", methods=["GET"])
def run_script():
    try:
        result = subprocess.run(
            ["python", "performance_improvement.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return f"[OK] performance_improvement executed ✅\n{result.stdout}", 200
    except subprocess.CalledProcessError as e:
        return f"[ERROR]\n{e.stderr}", 500
