#!/usr/bin/env python3
import json, os, datetime
from pathlib import Path

PRIORITY = {
    6331:{"name":"三菱化工機","eval":"1","order":True,"order_note":"受注残あり"},
    6777:{"name":"santec","eval":"1","order":False,"order_note":""},
    1950:{"name":"日本電設","eval":"1","order":False,"order_note":""},
    6366:{"name":"千代田化工","eval":"1","order":False,"order_note":""},
    1942:{"name":"関電工","eval":"1","order":False,"order_note":""},
    3627:{"name":"ネオス","eval":"A","order":False,"order_note":""},
    3658:{"name":"イーブック","eval":"A","order":False,"order_note":""},
    6161:{"name":"エスティック","eval":"A","order":False,"order_note":""},
    3682:{"name":"エンカレッジ","eval":"A","order":False,"order_note":""},
    4722:{"name":"フューチャー","eval":"〇","order":False,"order_note":""},
    6255:{"name":"NPC","eval":"〇","order":True,"order_note":"受注残〇 149億"},
    2471:{"name":"エスプール","eval":"","order":False,"order_note":""},
    6961:{"name":"エンプラス","eval":"1","order":False,"order_note":""},
    6941:{"name":"山一電機","eval":"1","order":False,"order_note":""},
    6501:{"name":"日立","eval":"1","order":False,"order_note":""},
    5208:{"name":"有沢製作所","eval":"1","order":False,"order_note":""},
    1980:{"name":"ダイダン","eval":"1","order":False,"order_note":""},
    1944:{"name":"きんでん","eval":"1","order":False,"order_note":""},
    6855:{"name":"日本電子材料","eval":"1","order":False,"order_note":""},
    2802:{"name":"味の素","eval":"1","order":False,"order_note":""},
}

HOLIDAYS = {"2026-01-01","2026-01-12","2026-02-11","2026-02-23","2026-03-20",
    "2026-04-29","2026-05-03","2026-05-04","2026-05-05","2026-05-06",
    "2026-07-20","2026-08-11","2026-09-21","2026-09-23","2026-10-12",
    "2026-11-03","2026-11-23"}

def biz_between(from_d, to_d):
    c=0; d=from_d+datetime.timedelta(days=1)
    while d<to_d:
        if d.weekday()<5 and d.isoformat() not in HOLIDAYS: c+=1
        d+=datetime.timedelta(days=1)
    return c

def fmt(ds):
    d=datetime.date.fromisoformat(ds)
    return f"{d.month}/{d.day}({'月火水木金土日'[d.weekday()]})"

def main():
    today=datetime.date.today()
    jst=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    two_weeks=today+datetime.timedelta(days=14)

    path=Path("docs/earnings.json")
    earnings=json.loads(path.read_text(encoding="utf-8"))["earnings"] if path.exists() else []
    upcoming=[e for e in earnings if today<=datetime.date.fromisoformat(e["date"])<=two_weeks]
    upcoming.sort(key=lambda x:x["date"])
    pri=[e for e in upcoming if e["code"] in PRIORITY]
    alerts=[e for e in pri if 0<=biz_between(today,datetime.date.fromisoformat(e["date"]))<=10]

    rows_pri=""
    for e in pri:
        p=PRIORITY[e["code"]]
        biz=biz_between(today,datetime.date.fromisoformat(e["date"]))
        is_alr=0<=biz<=10
        bg="#fff8e6" if is_alr else "#fffdf4"
        ev=f'<span style="background:#e6a817;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px">評価{p["eval"]}</span>' if p["eval"] else ""
        ord_b='<span style="background:#2dd4bf;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px">受注残</span>' if p["order"] else ""
        alr_b=f'<span style="background:#ef4444;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px">残{biz}営業日</span>' if is_alr else ""
        rows_pri+=f'<tr style="background:{bg};border-bottom:1px solid #eee"><td style="padding:6px 8px;font-size:13px">{fmt(e["date"])}</td><td style="padding:6px 8px;font-family:monospace">{e["code"]}</td><td style="padding:6px 8px;font-weight:bold">【★】{e["name"]}</td><td style="padding:6px 4px">{ev} {ord_b} {alr_b}</td></tr>'

    alert_html=""
    if alerts:
        items="".join(f'<li><strong>{e["code"]} {e["name"]}</strong> — {fmt(e["date"])}（残{biz_between(today,datetime.date.fromisoformat(e["date"]))}営業日）</li>' for e in alerts)
        alert_html=f'<div style="background:#fff1f0;border:2px solid #ef4444;border-radius:6px;padding:12px 16px;margin-bottom:20px"><h3 style="color:#ef4444;margin:0 0 8px">🚨 10営業日アラート</h3><ul style="margin:0;padding-left:20px">{items}</ul></div>'

    html=f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f5f5f5;padding:20px">
<div style="max-width:800px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">
<div style="background:#0d1117;padding:20px 24px">
<h1 style="color:#f59e0b;margin:0;font-size:20px">📊 決算監視PRO — 週次レポート</h1>
<p style="color:#94a3b8;margin:4px 0 0;font-size:13px">{jst.strftime("%Y年%m月%d日 %H:%M")} JST | {today.strftime("%m/%d")}〜{two_weeks.strftime("%m/%d")}</p>
</div>
<div style="padding:20px 24px">
<div style="display:flex;gap:16px;margin-bottom:20px">
<div style="flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:bold">{len(upcoming)}</div><div style="font-size:12px;color:#64748b">全決算件数</div></div>
<div style="flex:1;background:#fffdf4;border:1px solid #f59e0b;border-radius:6px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:bold;color:#d97706">{len(pri)}</div><div style="font-size:12px;color:#64748b">★重点銘柄</div></div>
<div style="flex:1;background:#fff1f0;border:1px solid #ef4444;border-radius:6px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:bold;color:#ef4444">{len(alerts)}</div><div style="font-size:12px;color:#64748b">🚨アラート</div></div>
</div>
{alert_html}
<h2 style="font-size:15px;border-bottom:2px solid #f59e0b;padding-bottom:6px;margin-bottom:12px">★ 重点監視銘柄</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:24px">
<thead><tr style="background:#f8fafc"><th style="padding:8px;text-align:left;font-size:12px;color:#64748b">日付</th><th style="padding:8px;text-align:left;font-size:12px;color:#64748b">コード</th><th style="padding:8px;text-align:left;font-size:12px;color:#64748b">銘柄名</th><th style="padding:8px;text-align:left;font-size:12px;color:#64748b">ステータス</th></tr></thead>
<tbody>{rows_pri or "<tr><td colspan='4' style='padding:16px;text-align:center;color:#999'>重点銘柄の決算予定なし</td></tr>"}</tbody>
</table>
</div>
<div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:12px 24px;text-align:center">
<p style="margin:0;font-size:11px;color:#94a3b8">決算監視PRO | 自動生成レポート</p>
</div></div></body></html>"""

    Path("report_output.html").write_text(html, encoding="utf-8")
    txt=f"【決算監視PRO】週次レポート {jst.strftime('%Y年%m月%d日')}\n全件:{len(upcoming)} 重点:{len(pri)} アラート:{len(alerts)}\n\n"
    for e in pri:
        txt+=f"  {fmt(e['date'])} {e['code']} {e['name']}\n"
    Path("report_output.txt").write_text(txt, encoding="utf-8")
    title=f"{today.strftime('%Y/%m/%d')} ★重点{len(pri)}件 🚨アラート{len(alerts)}件"
    env=os.environ.get("GITHUB_ENV","")
    if env:
        open(env,"a").write(f"REPORT_TITLE={title}\n")
    print(f"完了: 全{len(upcoming)}件 重点{len(pri)}件 アラート{len(alerts)}件")

if __name__=="__main__":
    main()
