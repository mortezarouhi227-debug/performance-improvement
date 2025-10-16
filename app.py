# app.py
from flask import Flask, request, jsonify
import subprocess, sys, traceback, os, signal, shlex

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, message="Server is healthy ✅"), 200

@app.route("/run-performance-improvement", methods=["GET", "POST"])
def run_performance_improvement():
    """
    اجرای امن performance_improvement.py و بازگشت خروجی/خطا به صورت JSON
    """
    try:
        # تنظیمات
        project_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(project_dir, "performance_improvement.py")

        # timeout قابل تنظیم با env (پیش‌فرض 540 ثانیه)
        try:
            sp_timeout = int(os.environ.get("APP_SUBPROC_TIMEOUT", "540"))
        except ValueError:
            sp_timeout = 540

        # اجرای اسکریپت
        # نکته: preexec_fn=os.setsid برای ساختن گروه فرایندی تا بتوانیم kill گروه را راحت انجام دهیم
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=sp_timeout,
            cwd=project_dir,
            check=False,
            preexec_fn=os.setsid  # فقط در لینوکس/رندر؛ در ویندوز نادیده گرفته می‌شود
        )

        stdout_txt = (result.stdout or "").strip()
        stderr_txt = (result.stderr or "").strip()

        if result.returncode != 0:
            # خطای منطقی/اجرایی
            err_msg = stderr_txt or stdout_txt or "Unknown error"
            status = 400 if ("سلول B1 خالی" in err_msg or "تاریخ" in err_msg) else 500
            return jsonify(ok=False, error=err_msg, code=result.returncode), status

        return jsonify(ok=True, stdout=stdout_txt), 200

    except subprocess.TimeoutExpired as e:
        # تلاش برای خاتمه گروه فرایندی اگر ساخته شده
        try:
            if hasattr(e, 'pid'):
                os.killpg(e.pid, signal.SIGTERM)
        except Exception:
            pass
        return jsonify(ok=False, error="⏱ Timeout: اجرای اسکریپت بیش از حد مجاز طول کشید."), 504

    except Exception as e:
        tb = traceback.format_exc()
        print(tb, flush=True)
        return jsonify(ok=False, error=str(e), trace=tb), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"🚀 Server started on port {port} (debug={debug})", flush=True)
    app.run(host="0.0.0.0", port=port, debug=debug)

