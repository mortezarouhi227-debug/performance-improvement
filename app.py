# app.py
from flask import Flask, request, jsonify
import subprocess, sys, traceback, os

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    """برای تست سلامت سرویس"""
    return jsonify(ok=True, message="Server is healthy ✅"), 200


@app.route("/run-performance-improvement", methods=["GET", "POST"])
def run_performance_improvement():
    """
    اجرای امن فایل performance_improvement.py
    و بازگرداندن خروجی یا خطا به‌صورت JSON
    """
    try:
        # اجرای اسکریپت با timeout مناسب
        result = subprocess.run(
            [sys.executable, "performance_improvement.py"],
            capture_output=True,
            text=True,
            timeout=180  # 👈 حداکثر زمان اجرا (3 دقیقه)
        )

        # اگر با SystemExit(1) یا خطای منطقی خارج شده باشد
        if result.returncode != 0:
            # اگر پیام خطا در stderr باشد، همان را برگردان
            err_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            # اگر خطای معروف 'سلول B1 خالی' باشد، وضعیت 400 بده
            if "سلول B1 خالی" in err_msg or "تاریخ" in err_msg:
                return jsonify(ok=False, error=err_msg), 400
            else:
                return jsonify(ok=False, error=err_msg), 500

        # اگر موفق بود
        return jsonify(ok=True, stdout=result.stdout.strip()), 200

    except subprocess.TimeoutExpired:
        # اگر بیش از 3 دقیقه طول کشید
        return jsonify(ok=False, error="⏱ Timeout: اجرای اسکریپت بیش از حد مجاز طول کشید."), 504

    except Exception as e:
        # هر خطای دیگر
        tb = traceback.format_exc()
        print(tb, flush=True)
        return jsonify(ok=False, error=str(e), trace=tb), 500


# -------- برنامه اصلی --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Server started on port {port}", flush=True)
    app.run(host="0.0.0.0", port=port)
