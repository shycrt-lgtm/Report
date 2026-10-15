#!/usr/bin/env python3
"""민간LNG산업협회 LNG통계 게시판(statistics)에서 2026-10-01 이후 새 글의 제목·링크를 reports.json에 등록한다.
요약 없이 제목과 링크만 게시하며, 첨부파일 자체는 내려받지 않는다."""
import json, re, html, sys, datetime, urllib.request

START = "2026-10-01"
LIST_URL = "http://www.lngkorea.or.kr/bbs/board.php?bo_table=statistics"
KST = datetime.timezone(datetime.timedelta(hours=9))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")

def parse(page):
    out = []
    for r in re.findall(r"<tr\b.*?</tr>", page, re.S | re.I):
        m = re.search(r'<a href="([^"]*wr_id=(\d+)[^"]*)"[^>]*>\s*(.*?)\s*</a>', r, re.S)
        n = re.search(r'td_num2">\s*(\d+)', r)
        d = re.search(r"(\d{4}-\d{2}-\d{2})", r)
        if not (m and d):
            continue
        out.append(dict(url=html.unescape(m.group(1)), wr_id=m.group(2),
                        title=re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(3)))).strip(),
                        no=n.group(1) if n else "", date=d.group(1)))
    return out

def attach_url(detail_url):
    try:
        page = fetch(detail_url)
    except Exception:
        return None
    m = re.search(r'href="([^"]*download\.php[^"]*)"', page)
    if not m:
        return None
    u = html.unescape(m.group(1))
    return u if u.startswith("http") else "http://www.lngkorea.or.kr" + u

def main():
    posts = parse(fetch(LIST_URL))
    if not posts:
        print("목록 파싱 실패"); sys.exit(1)
    data = json.load(open("reports.json", encoding="utf-8"))
    items = data["items"]
    have = {i["id"] for i in items}
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    added = 0
    for p in sorted(posts, key=lambda x: x["date"]):
        iid = "lng-stat-" + p["wr_id"]
        if p["date"] < START or iid in have:
            continue
        dl = attach_url(p["url"])
        items.append({
            "id": iid, "source": "민간LNG산업협회", "category": "가스산업",
            "series": "LNG통계", "title": p["title"], "date": p["date"], "summary": [],
            "url": dl or p["url"], "detail_url": p["url"] if dl else "",
            "link_label": "첨부파일 열기" if dl else "게시글 보기", "added": today})
        added += 1
    if added:
        items.sort(key=lambda i: (i.get("added", ""), i.get("date", "")), reverse=True)
        data["updated"] = today
        json.dump(data, open("reports.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open("reports.json", "a").write("\n")
    print("added", added, "of", len(posts), "posts")

main()
