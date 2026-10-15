#!/usr/bin/env python3
"""KOGAS 계간 가스산업 목록(boardNo=30)에서 호별 게시물을 묶어 reports.json에 등록한다.
요약 없이 제목·PDF 다운로드 링크만 게시한다. PDF 파일 자체는 내려받지 않는다."""
import json, re, sys, html, datetime, urllib.request

LIST_URL = "https://www.kogas.or.kr/site/koGas/goBoard.do?boardNo=30&Key=1040603000000"
BASE = "https://www.kogas.or.kr"
KST = datetime.timezone(datetime.timedelta(hours=9))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")

def parse(page):
    rows = re.findall(r"<tr\b.*?</tr>", page, re.S | re.I)
    out = []
    for r in rows:
        t = re.search(r"계간\s*가스산업\s*\[(\d{4})년\s*(\d+)월\s*제(\d+)권\s*제(\d+)호\]\s*_?\s*(\d+)\.\s*([^<\n]+)", r)
        if not t:
            continue
        f = re.search(r'href="([^"]*fileDownload\.do\?[^"]*)"', r)
        d = re.search(r"(\d{4}-\d{2}-\d{2})", r)
        if not f or not d:
            continue
        url = html.unescape(f.group(1))
        if url.startswith("/"):
            url = BASE + url
        y, m, vol, no, n, title = t.groups()
        out.append(dict(year=y, month=int(m), vol=vol, no=no, n=int(n),
                        title=html.unescape(title).strip(), url=url, date=d.group(1)))
    return out

def main():
    page = fetch(LIST_URL)
    posts = parse(page)
    if not posts:
        open("kogas_debug.html", "w", encoding="utf-8").write(page)
        print("목록 파싱 실패"); sys.exit(1)
    issues = {}
    for p in posts:
        issues.setdefault((p["year"], p["month"], p["vol"], p["no"]), []).append(p)
    data = json.load(open("reports.json", encoding="utf-8"))
    items = data["items"]
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    changed = False
    for (y, m, vol, no), ps in sorted(issues.items()):
        iid = "kogas-gas-%s-%02d" % (y, m)
        ps.sort(key=lambda x: x["n"])
        secs = [{"title": "%d. %s" % (p["n"], p["title"]), "url": p["url"]} for p in ps]
        old = next((i for i in items if i["id"] == iid), None)
        item = {
            "id": iid, "source": "한국가스공사(KOGAS)", "category": "리포트",
            "series": "계간 가스산업",
            "title": "계간 가스산업 %s년 %d월호 (제%s권 제%s호)" % (y, m, vol, no),
            "date": max(p["date"] for p in ps), "summary": [], "sections": secs,
            "url": LIST_URL, "link_label": "게시판 보기",
            "added": old["added"] if old else today,
        }
        if old != item:
            if old: items.remove(old)
            items.append(item); changed = True
    if changed:
        items.sort(key=lambda i: (i.get("added", ""), i.get("date", "")), reverse=True)
        data["updated"] = today
        json.dump(data, open("reports.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open("reports.json", "a").write("\n")
    print("changed" if changed else "no change", len(issues), "issues")

main()
