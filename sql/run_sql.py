"""SQLファイルをDatabricks SQL Statement Execution APIで逐次実行する簡易ドライバ."""
import json
import subprocess
import sys
import time
import urllib.request

PROFILE = "Azure-ytcy-east2"
HOST = "https://adb-7405605463330453.13.azuredatabricks.net"
WAREHOUSE = "9c8fac7a0b250221"


def token():
    out = subprocess.run(["/opt/homebrew/bin/databricks", "auth", "token", "-p", PROFILE],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["access_token"]


TOKEN = token()


def api(method, path, body=None):
    req = urllib.request.Request(
        HOST + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def run_statement(sql):
    res = api("POST", "/api/2.0/sql/statements/", {
        "warehouse_id": WAREHOUSE, "statement": sql,
        "catalog": "ytcy_azure_east2classic_stable", "schema": "digital_thread",
        "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    sid = res["statement_id"]
    while res["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = api("GET", f"/api/2.0/sql/statements/{sid}")
    return res


def split_statements(text):
    stmts, cur, in_str = [], [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        cur.append(line)
        if stripped.endswith(";"):
            stmts.append("\n".join(cur).rstrip(";"))
            cur = []
    if cur:
        stmts.append("\n".join(cur))
    return stmts


if __name__ == "__main__":
    text = open(sys.argv[1]).read()
    ok = fail = 0
    for i, stmt in enumerate(split_statements(text)):
        head = " ".join(stmt.split()[:6])
        res = run_statement(stmt)
        state = res["status"]["state"]
        if state == "SUCCEEDED":
            ok += 1
            print(f"[{i+1:02d}] OK   {head}")
        else:
            fail += 1
            err = res["status"].get("error", {}).get("message", "")[:300]
            print(f"[{i+1:02d}] FAIL {head}\n     {err}")
    print(f"done: {ok} ok, {fail} failed")
    sys.exit(1 if fail else 0)
