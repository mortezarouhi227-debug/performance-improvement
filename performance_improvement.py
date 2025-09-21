# performance_improvement.py
import gspread
import os, json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ---------- تنظیمات ----------
SPREADSHEET_ID = "1VgKCQ8EjVF2sS8rSPdqFZh2h6CuqWAeqSMR56APvwes"
ALL_DATA_SHEET = "All_Data"
OUTPUT_SHEET = "Performance_Improvement"
WARNING_SHEET = "Warning_Detail"
QUALITY_SHEET = "Task Time Header"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# ---------- اتصال ----------
if os.environ.get("GOOGLE_CREDENTIALS"):
    creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

client = gspread.authorize(creds)
ss = client.open_by_key(SPREADSHEET_ID)

all_ws = ss.worksheet(ALL_DATA_SHEET)
try:
    out_ws = ss.worksheet(OUTPUT_SHEET)
except gspread.WorksheetNotFound:
    out_ws = ss.add_worksheet(title=OUTPUT_SHEET, rows="3000", cols="200")

# ---------- خواندن تاریخ مرجع، شیفت و Done/Not Done ----------
ref_raw = out_ws.acell("B1").value
if not ref_raw:
    raise SystemExit("⚠️ خطا: سلول B1 خالی است (تاریخ مرجع).")
shift_val = (out_ws.acell("C1").value or "").strip()
done_flag = (out_ws.acell("D1").value or "").strip()

# تبدیل تاریخ
ref_date = None
for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
    try:
        ref_date = datetime.strptime(ref_raw, fmt)
        break
    except:
        continue
if ref_date is None:
    raise SystemExit(f"⚠️ خطا: مقدار '{ref_raw}' قابل تبدیل به تاریخ نیست.")

ref_date_only = ref_date.date()
start_date_only = (ref_date - timedelta(days=30)).date()

# ---------- بارگذاری All_Data ----------
vals = all_ws.get_all_values()
headers = vals[0]
rows = vals[1:]

def find_idx(name):
    target = name.strip().lower().replace(" ", "").replace("_", "")
    for i, h in enumerate(headers):
        if (h or "").strip().lower().replace(" ", "").replace("_", "") == target:
            return i
    return -1

idx_full = find_idx("full_name")
idx_task = find_idx("task_type")
idx_date = find_idx("date")
idx_hour = find_idx("hour")
idx_perf_with = find_idx("performance_with_rotation")
idx_shift = find_idx("Shift")
idx_occ = find_idx("occupied_hours")

# ---------- helper ----------
def parse_percent(x):
    if not x: return None
    s = str(x).replace("%", "").replace(",", "").strip()
    try:
        v = float(s)
        if v <= 1: v *= 100
        return v
    except:
        return None

def parse_date_str(s):
    if not s: return None
    s = str(s).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

# ---------- جمع‌آوری لاگ‌ها ----------
task_types = ["Receive", "Locate", "Pick", "Presort", "Sort", "Pack_Multi", "Pack_Single", "Stock taking"]
user_logs = {}
logs_before_window = set()

for r in rows:
    name = r[idx_full] if idx_full < len(r) else ""
    task = r[idx_task] if idx_task < len(r) else ""
    date_parsed = parse_date_str(r[idx_date]) if idx_date < len(r) else None
    if not name or not task or date_parsed is None:
        continue

    # فیلتر شیفت
    shift_str = r[idx_shift] if idx_shift != -1 and idx_shift < len(r) else ""
    if shift_val and shift_val != "" and shift_str != shift_val:
        continue

    # ---------- منطق Done / Not Done ----------
    if done_flag == "Done":
        if date_parsed < start_date_only:
            logs_before_window.add(name)
            continue
        if not (start_date_only <= date_parsed < ref_date_only):
            continue
    else:  # Not Done
        if not (start_date_only <= date_parsed < ref_date_only):
            continue

    perf = parse_percent(r[idx_perf_with]) if idx_perf_with < len(r) else None
    occ = float(r[idx_occ]) if idx_occ != -1 and r[idx_occ] else 0
    try:
        hour_val = int(float(r[idx_hour])) if idx_hour < len(r) and r[idx_hour] else None
    except:
        hour_val = None

    entry = {"date": date_parsed, "hour": hour_val, "perf": perf, "occ": occ}
    user_logs.setdefault(name, {}).setdefault(task, []).append(entry)

if done_flag == "Done":
    for n in list(user_logs.keys()):
        if n in logs_before_window:
            del user_logs[n]

# ---------- جمع‌آوری Warning و Quality ----------
def collect_counts(ws_name, name_cols, date_cols, count_cols):
    m = {}
    try:
        ws = ss.worksheet(ws_name)
    except gspread.WorksheetNotFound:
        return m
    vals = ws.get_all_values()
    if not vals or len(vals) < 2: return m
    hdr, body = vals[0], vals[1:]

    def find_any(cols):
        for c in cols:
            t = c.strip().lower().replace(" ", "").replace("_", "")
            for i,h in enumerate(hdr):
                if (h or "").strip().lower().replace(" ", "").replace("_", "") == t:
                    return i
        return -1

    idx_name, idx_date, idx_count = find_any(name_cols), find_any(date_cols), find_any(count_cols)
    if idx_name == -1 or idx_date == -1 or idx_count == -1: return m

    for r in body:
        nm = r[idx_name]
        d = parse_date_str(r[idx_date]) if idx_date < len(r) else None
        if not nm or d is None: continue
        if not (start_date_only <= d < ref_date_only): continue
        try:
            cnt = int(float(r[idx_count])) if r[idx_count] else 0
        except:
            cnt = 0
        m[nm] = m.get(nm, 0) + cnt
    return m

warn_map = collect_counts(WARNING_SHEET, ["full_name"], ["date"], ["warning_count"])
qual_map = collect_counts(QUALITY_SHEET, ["full_name"], ["date"], ["error_count"])

# ---------- محاسبات جدول ----------
main_results = []
avg_per_task = {}
status_per_task = {}

for name, task_dict in user_logs.items():
    row_out = [name]
    status_row = [name]

    for task in task_types:
        logs = task_dict.get(task, [])
        if not logs:
            row_out += [""]*6
            status_row.append("❌")
            continue

        logs_sorted = sorted(logs, key=lambda e: (e["date"], e["hour"] if e["hour"] is not None else -1))
        first = logs_sorted[0]
        first_perf_val = first["perf"]
        first_perf = f"{first_perf_val:.0f}%" if first_perf_val is not None else ""

        above_perf = ""
        diff_days = ""

        if first_perf_val is not None and first_perf_val >= 100:
            diff_days = 1  # ✅ حداقل ۱ روز
            status_row.append("✅")
        else:
            above = next((e for e in logs_sorted if e["perf"] is not None and e["perf"] >= 100), None)
            if above:
                above_perf = f"{above['perf']:.0f}%"
                diff_days = (above["date"] - first["date"]).days + 1  # ✅ همیشه حداقل ۱
                status_row.append("✅")
            else:
                status_row.append("❌")

        day_set = set(e["date"] for e in logs_sorted if e["hour"] is not None)
        day_count = len(day_set)

        perfs = [e["perf"] for e in logs_sorted if e["perf"] is not None]
        avg_perf = f"{(sum(perfs)/len(perfs)):.0f}%" if perfs else ""
        occ_sum = sum(e["occ"] for e in logs_sorted if e["occ"])

        row_out += [first_perf, above_perf, diff_days, avg_perf, occ_sum, day_count]

        if perfs:
            avg_per_task.setdefault(task, {})[name] = sum(perfs)/len(perfs)

    row_out += [warn_map.get(name, ""), qual_map.get(name, "")]
    main_results.append(row_out)
    status_per_task[name] = status_row

# ---------- پاک کردن داده‌های قبلی (فقط از ردیف ۵ به بعد) ----------
last_row = out_ws.row_count
out_ws.batch_clear([f"A5:BR{last_row}"])

# ---------- جدول اول ----------
if main_results:
    out_ws.update("A5", main_results)

# ---------- جدول وضعیت ----------
status_headers = ["full_name"] + task_types
status_results = list(status_per_task.values())
if status_results:
    out_ws.update("BA4", [status_headers])
    out_ws.update("BA5", status_results)

# ---------- جدول دوم (Threshold Table) ----------
col_map = {
    "Receive": "BK",
    "Locate": "BL",
    "Pick": "BM",
    "Presort": "BN",
    "Sort": "BO",
    "Pack_Multi": "BP",
    "Pack_Single": "BQ",
    "Stock taking": "BR"
}

for task, col in col_map.items():
    min_thr = parse_percent(out_ws.acell(f"{col}2").value)
    max_thr = parse_percent(out_ws.acell(f"{col}1").value)
    out_ws.update(f"{col}4", [[task]])

    selected = []
    for name, avg in avg_per_task.get(task, {}).items():
        if min_thr is not None and max_thr is not None:
            if min_thr <= avg <= max_thr:
                selected.append((name, avg))

    selected.sort(key=lambda x: x[1], reverse=True)
    rows_out = [[f"{n} {round(v,1)}%"] for n, v in selected]

    if rows_out:
        out_ws.update(f"{col}5", rows_out)

print("✅ سه جدول ساخته شد و داخل Performance_Improvement ذخیره گردید.")


