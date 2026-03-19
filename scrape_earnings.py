#!/usr/bin/env python3
"""
決算発表スケジュール スクレイパー
kabuyoho.jp から2週間分の決算データを取得し earnings.json に出力する
GitHub Actions から実行される
"""
import json
import time
import datetime
import re
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "lxml"], check=True)
    import requests
    from bs4 import BeautifulSoup

# ============================================================
# 祝日リスト (2026年)
# ============================================================
HOLIDAYS = {
    "2026-01-01", "2026-01-12", "2026-02-11", "2026-02-23",
    "2026-03-20", "2026-04-29", "2026-05-03", "2026-05-04",
    "2026-05-05", "2026-05-06", "2026-07-20", "2026-08-11",
    "2026-09-21", "2026-09-23", "2026-10-12", "2026-11-03",
    "2026-11-23",
    # 2025年分（念のため）
    "2025-01-01", "2025-01-13", "2025-02-11", "2025-02-23",
    "2025-02-24", "2025-03-20", "2025-04-29", "2025-05-03",
    "2025-05-04", "2025-05-05", "2025-05-06", "2025-07-21",
    "2025-08-11", "2025-09-15", "2025-09-23", "2025-10-13",
    "2025-11-03", "2025-11-23", "2025-11-24",
}

def is_business_day(d: datetime.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS

def get_target_dates(days_ahead: int = 14) -> list[str]:
    today = datetime.date.today()
    dates = []
    d = today
    while len(dates) < days_ahead * 2:  # 週末を含む余裕を持たせる
        dates.append(d.isoformat())
        d += datetime.timedelta(days=1)
        if len([x for x in dates if datetime.date.fromisoformat(x).weekday() < 5]) >= days_ahead:
            break
    return dates

# ============================================================
# kabuyoho スクレイパー
# ============================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://kabuyoho.jp/",
}

def scrape_kabuyoho_date(date_str: str, session: requests.Session) -> list[dict]:
    """kabuyoho.jp の決算カレンダーを1日分スクレイプする"""
    url = f"https://kabuyoho.jp/calender?report_date={date_str.replace('-', '')}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"  [WARN] {date_str}: fetch failed - {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    # kabuyoho のテーブル構造を解析
    # メインテーブルを探す
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            row_text = row.get_text(" ", strip=True)

            # 証券コード (4〜5桁) を探す
            code_match = re.search(r'\b(\d{4,5})\b', row_text)
            if not code_match:
                continue
            code = int(code_match.group(1))
            if not (1000 <= code <= 99999):
                continue

            # 銘柄名
            name = ""
            for col in cols:
                text = col.get_text(strip=True)
                # 数字だけじゃない・短すぎない・コードじゃない
                if text and not re.match(r'^\d+$', text) and len(text) >= 2:
                    if text != code_match.group(1):
                        name = text[:30]
                        break

            if not name:
                continue

            # 業種・市場・時間などを抽出
            sector = ""
            market = ""
            timing = "本引後"
            for col in cols[2:]:
                t = col.get_text(strip=True)
                if "東P" in t or "東S" in t or "東G" in t or "名証" in t:
                    market = t[:10]
                elif any(kw in t for kw in ["本引後", "引前", "引後"]):
                    timing = t[:10]

            results.append({
                "date": date_str,
                "code": code,
                "name": name,
                "market": market or "東証",
                "q": "",
                "time": timing,
                "sector": sector,
            })

    # リンクからも試みる（kabuyohoは銘柄リンクが /reportTop?bcode=XXXX 形式）
    if not results:
        links = soup.find_all("a", href=re.compile(r'bcode=(\d{4,5})'))
        seen = set()
        for a in links:
            m = re.search(r'bcode=(\d{4,5})', a["href"])
            if not m:
                continue
            code = int(m.group(1))
            if code in seen:
                continue
            seen.add(code)
            name = a.get_text(strip=True)[:30]
            if not name:
                continue
            results.append({
                "date": date_str,
                "code": code,
                "name": name,
                "market": "東証",
                "q": "",
                "time": "本引後",
                "sector": "",
            })

    # 重複除去
    seen_codes = set()
    unique = []
    for r in results:
        if r["code"] not in seen_codes:
            seen_codes.add(r["code"])
            unique.append(r)

    print(f"  {date_str}: {len(unique)}件取得")
    return unique


# ============================================================
# フォールバック: 重点銘柄のハードコードスケジュール
# ============================================================
PRIORITY_SCHEDULE_FALLBACK = [
    {"date": "2026-03-19", "code": 6777,  "name": "santec",      "market": "東P", "q": "9月2Q", "time": "本引後", "sector": "電子機器"},
    {"date": "2026-03-23", "code": 3627,  "name": "ネオス",       "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "IT"},
    {"date": "2026-03-24", "code": 6255,  "name": "NPC",          "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "機械"},
    {"date": "2026-03-24", "code": 4722,  "name": "フューチャー",  "market": "東P", "q": "12月本決算", "time": "本引後", "sector": "IT"},
    {"date": "2026-03-24", "code": 3658,  "name": "イーブック",    "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "電子書籍"},
    {"date": "2026-03-25", "code": 2471,  "name": "エスプール",    "market": "東P", "q": "11月1Q", "time": "本引後", "sector": "人材"},
    {"date": "2026-03-25", "code": 3682,  "name": "エンカレッジ",  "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "IT"},
    {"date": "2026-03-26", "code": 6161,  "name": "エスティック",  "market": "東S", "q": "9月2Q", "time": "本引後", "sector": "機械"},
    {"date": "2026-03-26", "code": 6331,  "name": "三菱化工機",   "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "機械"},
    {"date": "2026-03-27", "code": 1942,  "name": "関電工",       "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "建設"},
    {"date": "2026-03-27", "code": 1950,  "name": "日本電設",      "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "建設"},
    {"date": "2026-03-30", "code": 6366,  "name": "千代田化工",   "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "機械"},
    {"date": "2026-03-30", "code": 1944,  "name": "きんでん",     "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "建設"},
    {"date": "2026-03-30", "code": 6941,  "name": "山一電機",     "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "電子部品"},
    {"date": "2026-03-30", "code": 5208,  "name": "有沢製作所",   "market": "東S", "q": "3月3Q", "time": "本引後", "sector": "化学"},
    {"date": "2026-03-31", "code": 1980,  "name": "ダイダン",     "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "建設"},
    {"date": "2026-03-31", "code": 6961,  "name": "エンプラス",   "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "電子部品"},
    {"date": "2026-03-31", "code": 6855,  "name": "日本電子材料", "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "半導体"},
    {"date": "2026-03-31", "code": 6501,  "name": "日立",        "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "電気機器"},
    {"date": "2026-04-01", "code": 2802,  "name": "味の素",      "market": "東P", "q": "3月3Q", "time": "本引後", "sector": "食品"},
    {"date": "2026-04-01", "code": 6941,  "name": "山一電機",    "market": "東S", "q": "3月本決算", "time": "本引後", "sector": "電子部品"},
]

# ============================================================
# メイン
# ============================================================
def main():
    print("=== 決算スケジュール取得開始 ===")
    today = datetime.date.today()
    target_dates = []
    d = today
    for _ in range(21):  # 3週間分のカレンダー日付を試みる
        target_dates.append(d.isoformat())
        d += datetime.timedelta(days=1)

    session = requests.Session()
    all_earnings = []
    success_count = 0

    for date_str in target_dates:
        d = datetime.date.fromisoformat(date_str)
        if not is_business_day(d):
            continue
        items = scrape_kabuyoho_date(date_str, session)
        if items:
            success_count += 1
            all_earnings.extend(items)
        time.sleep(1.5)  # 礼儀正しいクロール間隔

    # スクレイプ失敗 or 件数が少ない場合は重点銘柄フォールバックをマージ
    scraped_keys = {(e["date"], e["code"]) for e in all_earnings}
    for fb in PRIORITY_SCHEDULE_FALLBACK:
        fb_date = datetime.date.fromisoformat(fb["date"])
        if fb_date >= today and (fb["date"], fb["code"]) not in scraped_keys:
            all_earnings.append(fb)

    # 日付順ソート
    all_earnings.sort(key=lambda x: (x["date"], x["code"]))

    # 重複コード×日付を除去
    seen = set()
    unique = []
    for e in all_earnings:
        key = (e["date"], e["code"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "source": "kabuyoho.jp" if success_count > 0 else "fallback",
        "success_dates": success_count,
        "total": len(unique),
        "earnings": unique,
    }

    out_path = Path("docs/earnings.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 完了: {len(unique)}件 → {out_path}")
    print(f"   スクレイプ成功日数: {success_count}/{len(target_dates)}")


if __name__ == "__main__":
    main()
