#!/usr/bin/env python3
"""
週次決算レポート生成スクリプト
GitHub Actions から毎週日曜 10:00 JST に実行
earnings.json を読み込んで HTML + テキストメールを生成する
"""
import json
import os
import datetime
from pathlib import Path

# ============================================================
# 重点銘柄マスター
# ============================================================
PRIORITY = {
    6331: {"name": "三菱化工機",   "eval": "1",  "sector": "機械",   "order": True,  "order_note": "受注残あり"},
    6777: {"name": "santec",      "eval": "1",  "sector": "電子機器","order": False, "order_note": ""},
    1950: {"name": "日本電設",    "eval": "1",  "sector": "建設",   "order": False, "order_note": ""},
    6366: {"name": "千代田化工",  "eval": "1",  "sector": "機械",   "order": False, "order_note": ""},
    1942: {"name": "関電工",      "eval": "1",  "sector": "建設",   "order": False, "order_note": ""},
    3627: {"name": "ネオス",      "eval": "A",  "sector": "IT",     "order": False, "order_note": ""},
    3658: {"name": "イーブック",  "eval": "A",  "sector": "電子書籍","order": False, "order_note": ""},
    6161: {"name": "エスティック","eval": "A",  "sector": "機械",   "order": False, "order_note": ""},
    3682: {"name": "エンカレッジ","eval": "A",  "sector": "IT",     "order": False, "order_note": ""},
    4722: {"name": "フューチャー","eval": "〇", "sector": "IT",     "order": False, "order_note": ""},
    6255: {"name": "NPC",         "eval": "〇", "sector": "機械",   "order": True,  "order_note": "受注残〇 149億"},
    2471: {"name": "エスプール",  "eval": "",   "sector": "人材",   "order": False, "order_note": ""},
    6961: {"name": "エンプラス",  "eval": "1",  "sector": "電子部品","order": False, "order_note": ""},
    6941: {"name": "山一電機",    "eval": "1",  "sector": "電子部品","order": False, "order_note": ""},
    6501: {"name": "日立",        "eval": "1",  "sector": "電気機器","order": False, "order_note": ""},
    5208: {"name": "有沢製作所",  "eval": "1",  "sector": "化学",   "order": False, "order_note": ""},
    1980: {"name": "ダイダン",    "eval": "1",  "sector": "建設",   "order": False, "order_note": ""},
    1944: {"name": "きんでん",    "eval": "1",  "sector": "建設",   "order": False, "order_note": ""},
    6855: {"name": "日本電子材料","eval": "1",  "sector": "半導体", "order": False, "order_note": ""},
    2802: {"name": "味の素",      "eval": "1",  "sector": "食品",   "order": False, "order_note": ""},
}

HOLIDAYS = {
    "2026-01-01","2026-01-12","2026-02-11","2026-02-23",
    "2026-03-20","2026-04-29","2026-05-03","2026-05-04",
    "2026-05-05","2026-05-06","2026-07-20","2026-08-11",
    "2026-09-21","2026-09-23","2026-10-12","2026-11-03","2026-11-23",
}

def business_days_between(from_date: datetime.date, to_date: datetime.date) -> int:
    count = 0
    d = from_date + datetime.timedelta(days=1)
    while d < to_date:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            count += 1
        d += datetime.timedelta(days=1)
    return count

def format_date_jp(date_str: str) -> str:
    d = datetime.date.fromisoformat(date_str)
    days = ["月","火","水","木","金","土","日"]
    return f"{d.month}/{d.day}({days[d.weekday()]})"

def load_earnings() -> list[dict]:
    """earnings.json を読み込む（GitHub Actions 実行ディレクトリ想定）"""
    path = Path("docs/earnings.json")
    if not path.exists():
        # フォールバック: スクリプトと同じ階層
        path = Path(__file__).parent.parent.parent / "docs/earnings.json"
    if not path.exists():
        print(f"[WARN] earnings.json が見つかりません: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("earnings", [])

def generate_report():
    today = datetime.date.today()
    jst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    two_weeks_later = today + datetime.timedelta(days=14)

    earnings = load_earnings()

    # 2週間以内のデータに絞る
    upcoming = [
        e for e in earnings
        if today <= datetime.date.fromisoformat(e["date"]) <= two_weeks_later
    ]
    upcoming.sort(key=lambda x: x["date"])

    # 重点銘柄のみ抽出
    priority_upcoming = [e for e in upcoming if e["code"] in PRIORITY]

    # アラート銘柄（10営業日以内）
    alert_stocks = [
        e for e in priority_upcoming
        if 0 <= business_days_between(today, datetime.date.fromisoformat(e["date"])) <= 10
    ]

    # ============================================================
    # HTML メール生成
    # ============================================================
    rows_all = ""
    rows_priority = ""

    for e in upcoming:
        p = PRIORITY.get(e["code"])
        is_priority = p is not None
        d = datetime.date.fromisoformat(e["date"])
        biz_days = business_days_between(today, d)
        is_alert = is_priority and 0 <= biz_days <= 10

        bg = "#fff8e6" if is_priority and is_alert else ("#fffdf4" if is_priority else "#ffffff")
        name_style = "font-weight:bold;" if is_priority else ""
        star = "【★】" if is_priority else "　　"

        eval_badge = ""
        if p and p["eval"]:
            color = "#e6a817" if p["eval"] == "1" else "#4a90d9" if p["eval"] == "A" else "#3ba55d"
            eval_badge = f'<span style="background:{color};color:#fff;padding:1px 5px;border-radius:3px;font-size:11px;font-weight:bold;">評価{p["eval"]}</span>'
        order_badge = ""
        if p and p["order"]:
            order_badge = f'<span style="background:#2dd4bf;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px;font-weight:bold;">受注残</span>'
        alert_badge = ""
        if is_alert:
            alert_badge = f'<span style="background:#ef4444;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px;font-weight:bold;">残{biz_days}営業日</span>'

        row = f"""
        <tr style="background:{bg};border-bottom:1px solid #eee;">
          <td style="padding:6px 8px;font-family:monospace;font-size:13px;color:#888;">{format_date_jp(e["date"])}</td>
          <td style="padding:6px 8px;font-family:monospace;font-size:13px;color:#444;">{e["code"]}</td>
          <td style="padding:6px 8px;font-size:13px;{name_style}">{star}{e["name"]}</td>
          <td style="padding:6px 8px;font-size:12px;color:#666;">{e.get("sector","")}</td>
          <td style="padding:6px 8px;font-size:12px;color:#888;">{e.get("q","")}</td>
          <td style="padding:6px 4px;">{eval_badge} {order_badge} {alert_badge}</td>
        </tr>"""
        rows_all += row
        if is_priority:
            rows_priority += row

    # アラートセクション
    alert_html = ""
    if alert_stocks:
        items = ""
        for e in alert_stocks:
            d = datetime.date.fromisoformat(e["date"])
            biz = business_days_between(today, d)
            items += f'<li><strong>{e["code"]} {e["name"]}</strong> — {format_date_jp(e["date"])}（残{biz}営業日）</li>'
        alert_html = f"""
        <div style="background:#fff1f0;border:2px solid #ef4444;border-radius:6px;padding:12px 16px;margin-bottom:20px;">
          <h3 style="color:#ef4444;margin:0 0 8px;">🚨 10営業日アラート</h3>
          <ul style="margin:0;padding-left:20px;">{items}</ul>
        </div>"""

    html_body = f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><title>週次決算レポート</title></head>
<body style="font-family:'Noto Sans JP',sans-serif;background:#f5f5f5;margin:0;padding:20px;">
<div style="max-width:800px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

  <!-- ヘッダー -->
  <div style="background:#0d1117;padding:20px 24px;">
    <h1 style="color:#f59e0b;margin:0;font-size:20px;">📊 決算監視 PRO — 週次レポート</h1>
    <p style="color:#94a3b8;margin:4px 0 0;font-size:13px;">
      {jst_now.strftime("%Y年%m月%d日 %H:%M")} JST 生成 | 対象期間: {today.strftime("%m/%d")}〜{two_weeks_later.strftime("%m/%d")}
    </p>
  </div>

  <div style="padding:20px 24px;">

    <!-- サマリー -->
    <div style="display:flex;gap:16px;margin-bottom:20px;">
      <div style="flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 16px;text-align:center;">
        <div style="font-size:24px;font-weight:bold;color:#0d1117;">{len(upcoming)}</div>
        <div style="font-size:12px;color:#64748b;">全決算件数</div>
      </div>
      <div style="flex:1;background:#fffdf4;border:1px solid #f59e0b;border-radius:6px;padding:12px 16px;text-align:center;">
        <div style="font-size:24px;font-weight:bold;color:#d97706;">{len(priority_upcoming)}</div>
        <div style="font-size:12px;color:#64748b;">★重点銘柄</div>
      </div>
      <div style="flex:1;background:#fff1f0;border:1px solid #ef4444;border-radius:6px;padding:12px 16px;text-align:center;">
        <div style="font-size:24px;font-weight:bold;color:#ef4444;">{len(alert_stocks)}</div>
        <div style="font-size:12px;color:#64748b;">🚨 10日内アラート</div>
      </div>
    </div>

    {alert_html}

    <!-- ★重点銘柄テーブル -->
    <h2 style="font-size:15px;border-bottom:2px solid #f59e0b;padding-bottom:6px;margin-bottom:12px;">
      ★ 重点監視銘柄スケジュール
    </h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">日付</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">コード</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">銘柄名</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">業種</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">決算期</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">ステータス</th>
        </tr>
      </thead>
      <tbody>{rows_priority if rows_priority else '<tr><td colspan="6" style="padding:16px;text-align:center;color:#999;">重点銘柄の決算予定なし</td></tr>'}</tbody>
    </table>

    <!-- 全銘柄テーブル -->
    <h2 style="font-size:15px;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-bottom:12px;">
      全決算スケジュール（2週間）
    </h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">日付</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">コード</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">銘柄名</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">業種</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">決算期</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#64748b;">ステータス</th>
        </tr>
      </thead>
      <tbody>{rows_all if rows_all else '<tr><td colspan="6" style="padding:16px;text-align:center;color:#999;">データなし</td></tr>'}</tbody>
    </table>

  </div>

  <!-- フッター -->
  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:12px 24px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#94a3b8;">
      決算監視PRO | データソース: kabuyoho.jp | 自動生成レポート
    </p>
  </div>
</div>
</body></html>"""

    # ============================================================
    # テキストメール生成
    # ============================================================
    txt_lines = [
        f"【決算監視PRO】週次レポート {jst_now.strftime('%Y年%m月%d日')}",
        f"対象期間: {today.strftime('%m/%d')}〜{two_weeks_later.strftime('%m/%d')}",
        "=" * 50,
        f"全決算件数: {len(upcoming)}件",
        f"★重点銘柄: {len(priority_upcoming)}件",
        f"🚨アラート: {len(alert_stocks)}件",
        "",
    ]
    if alert_stocks:
        txt_lines.append("■ 10営業日アラート")
        for e in alert_stocks:
            d = datetime.date.fromisoformat(e["date"])
            biz = business_days_between(today, d)
            txt_lines.append(f"  {e['code']} {e['name']} {format_date_jp(e['date'])} 残{biz}日")
        txt_lines.append("")

    txt_lines.append("■ ★重点銘柄スケジュール")
    for e in priority_upcoming:
        p = PRIORITY[e["code"]]
        order = "【受注残】" if p["order"] else ""
        eval_s = f"評価{p['eval']}" if p["eval"] else ""
        txt_lines.append(f"  {format_date_jp(e['date'])} {e['code']} {e['name']} {eval_s} {order}")

    txt_lines += ["", "■ 全決算スケジュール"]
    prev_date = ""
    for e in upcoming:
        if e["date"] != prev_date:
            txt_lines.append(f"\n  [{format_date_jp(e['date'])}]")
            prev_date = e["date"]
        star = "★" if e["code"] in PRIORITY else "　"
        txt_lines.append(f"    {star} {e['code']} {e['name']}")

    text_body = "\n".join(txt_lines)

    # ファイル出力
    Path("report_output.html").write_text(html_body, encoding="utf-8")
    Path("report_output.txt").write_text(text_body, encoding="utf-8")

    # GitHub Actions の環境変数にタイトルをセット
    title = f"{today.strftime('%Y/%m/%d')} ★重点{len(priority_upcoming)}件 🚨アラート{len(alert_stocks)}件"
    env_file = os.environ.get("GITHUB_ENV", "")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"REPORT_TITLE={title}\n")

    print(f"✅ レポート生成完了")
    print(f"   全件: {len(upcoming)} / 重点: {len(priority_upcoming)} / アラート: {len(alert_stocks)}")

if __name__ == "__main__":
    generate_report()
