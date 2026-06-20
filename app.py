# -*- coding: utf-8 -*-
"""
giant_news_log アプリ
「巨人企業×国内銘柄」提携・協業ニュースを記録するための独立Renderアプリ。

【構成】
- GET  /                index.html を返す（入力フォーム + 一覧表示）
- GET  /api/logs         記録済みログを全件JSONで返す
- POST /api/logs         1件のログを追記する
- GET  /api/logs/csv     CSV形式でダウンロード（giant_news_bt.py のEVENTS作成用）

【保存方式】
data/log.jsonl に1行1レコードのJSON Linesで保存する。
Render free planは再起動でディスクが揮発する可能性があるため、
フロントエンド側(index.html)でlocalStorageにもキャッシュ・再送する設計と組み合わせて使う。
定期的にこのファイルをGitHubにコミットしておくとより安全（手動でも可）。
"""

import os
import json
import csv
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOG_PATH = os.path.join(DATA_DIR, "log.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(LOG_PATH):
    open(LOG_PATH, "w", encoding="utf-8").close()

REQUIRED_FIELDS = ["announce_date", "giant", "japan_company", "ticker"]


def read_all_logs():
    logs = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return logs


def append_log(record):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": read_all_logs()})


@app.route("/api/logs", methods=["POST"])
def post_log():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "invalid JSON body"}), 400

    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    record = {
        "announce_date": payload.get("announce_date", ""),
        "giant": payload.get("giant", ""),
        "japan_company": payload.get("japan_company", ""),
        "ticker": payload.get("ticker", ""),
        "status": payload.get("status", "要レビュー"),
        "headline": payload.get("headline", ""),
        "source_url": payload.get("source_url", ""),
        "recorded_at": datetime.utcnow().isoformat() + "Z",
    }
    append_log(record)
    return jsonify({"ok": True, "record": record}), 201


@app.route("/api/logs/csv", methods=["GET"])
def get_logs_csv():
    logs = read_all_logs()
    output = io.StringIO()
    fieldnames = [
        "announce_date", "giant", "japan_company", "ticker",
        "status", "headline", "source_url", "recorded_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in logs:
        writer.writerow({k: row.get(k, "") for k in fieldnames})

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=giant_news_log.csv"
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
