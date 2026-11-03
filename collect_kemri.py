#!/usr/bin/env python3
"""한전 경영연구원(KEMRI) 'KEMRI Review' 게시판에서 2026-01-01 이후 새 글을 reports.json에 등록한다.
게시글 본문의 목차(Issue Paper·Research Activities)를 요약란에 넣고, 원문 PDF는 다운로드 링크만 건다.
PDF 파일 자체는 내려받지 않는다."""
import json, re, sys, html, datetime, urllib.request, urllib.parse

START = "2026-01-01"
BASE = "https://www.kepco.co.kr"
LIST_URL = BASE + "/kemri/report/kemri-review/boardList.do"
VIEW_URL = BASE + "/kemri/report/kemri-review/boardView.do?boardMngNo=131&boardNo=%s"
FILE_URL = BASE + "/c2r/FileDownload.do?fileNo=%s&fileSeq=%s"
KST = datetime.timezone(datetime.timedelta(hours=9))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_list(page):
    out = []
    for blk in re.split(r'<div class="media-list-item', page)[1:]:
        b = re.search(r"fn_Detail\('\d+'\s*,\s*'(\d+)'\)", blk)
        t = re.search(r'<strong class="tit">(.*?)</strong>', blk, re.S)
        d = re.search(r'class="date">\s*(\d{4})\.(\d{2})\.(\d{2})', blk)
        n = re.search(r'class="num">\s*No\.(\d+)', blk)
        f = re.search(r"downloadFile\('([^']+)'\s*,\s*'([^']+)'\)", blk)
        if not (b and t and d):
            continue
        out.append(dict(board=b.group(1), title=text(t.group(1)), date="-".join(d.groups()),
                        no=n.group(1) if n else "", file=f.groups() if f else None))
    return out


def parse_view(page):
    """본문 목차 → 요약 줄, 첨부파일명, 다운로드 키"""
    body = re.search(r'<div class="detail-content">(.*?)<div class="detail-tag', page, re.S)
    lines, head = [], ""
    if body:
        raw = re.sub(r"<br\s*/?>|</p>", "\n", body.group(1), flags=re.I)
        for ln in (text(x) for x in raw.split("\n")):
            if not ln or ln.startswith("※"):
                continue
            if ln.startswith("▶"):
                head = "이슈페이퍼" if "issue" in ln.lower() else "연구동향" if "research" in ln.lower() else ln.lstrip("▶ ").strip()
                continue
            lines.append("[%s] %s" % (head, ln.lstrip("-· ").strip()) if head else ln)
    fn = re.search(r'class="file-name">\s*(.*?)\s*</span>', page, re.S)
    f = re.search(r"downloadFile\('([^']+)'\s*,\s*'([^']+)'\)", page)
    return lines, text(fn.group(1)) if fn else "", f.groups() if f else None


def series_of(fname):
    m = re.search(r"Vol\.?\s*(\d+)\].*?(\d{4})년.*?(\d{1,2})월호", fname)
    return "KEMRI 전력경제 REVIEW %s년 %s월호 (Vol.%s)" % (m.group(2), m.group(3), m.group(1)) if m else "KEMRI 전력경제 REVIEW"


def make_item(p, lines, fname, fkey, added):
    fkey = fkey or p["file"]
    detail = VIEW_URL % p["board"]
    url = FILE_URL % tuple(urllib.parse.quote(k, safe="") for k in fkey) if fkey else detail
    return {
        "id": "kemri-review-" + p["board"], "source": "한전 경영연구원(KEMRI)", "category": "KEMRI",
        "series": series_of(fname), "title": p["title"], "date": p["date"], "summary": lines,
        "url": url, "detail_url": detail if fkey else "",
        "link_label": "원문 PDF 다운로드" if fkey else "게시글 보기", "added": added,
    }


def main():
    posts = parse_list(fetch(LIST_URL))
    if not posts:
        print("목록 파싱 실패"); sys.exit(1)
    data = json.load(open("reports.json", encoding="utf-8"))
    items = data["items"]
    have = {i["id"] for i in items}
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    added = 0
    for p in sorted(posts, key=lambda x: x["date"]):
        if p["date"] < START or "kemri-review-" + p["board"] in have:
            continue
        try:
            lines, fname, fkey = parse_view(fetch(VIEW_URL % p["board"]))
        except Exception:
            lines, fname, fkey = [], "", None
        items.append(make_item(p, lines, fname, fkey, today))
        added += 1
    if added:
        items.sort(key=lambda i: (i.get("added", ""), i.get("date", "")), reverse=True)
        data["updated"] = today
        json.dump(data, open("reports.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open("reports.json", "a").write("\n")
    print("added", added, "of", len(posts), "posts")


if __name__ == "__main__":
    main()
