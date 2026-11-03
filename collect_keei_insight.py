#!/usr/bin/env python3
"""에너지경제연구원(KEEI) '세계 에너지시장 인사이트'(격주간) 2026-01-01 이후 새 호를 reports.json에 등록한다.
게시글 본문의 목차(현안분석·포커스·해외기관 보고서·주요 단신)를 요약란에 넣고, 원문 PDF는 링크만 건다.
PDF 파일 자체는 내려받지 않는다."""
import json, re, sys, html, datetime, urllib.request

START = "2026-01-01"
BASE = "https://www.keei.re.kr"
LIST_URL = BASE + "/board.es?mid=a10103010000&bid=0003"
VIEW_URL = BASE + "/board.es?mid=a10103010000&bid=0003&act=view&list_no=%s"
PDF_URL = BASE + "/pdfOpen.es?bid=0003&list_no=%s&seq=1"
CATEGORY = "에너지시장 인사이트"
SERIES = "세계 에너지시장 인사이트(격주간)"
KST = datetime.timezone(datetime.timedelta(hours=9))
HEADS = {"현안분석": "현안분석", "포커스": "포커스", "해외기관보고서": "해외기관 보고서", "주요단신": "주요 단신"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": LIST_URL})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")


def text(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = s.replace("\U00010a50", "·").replace("­", "-")      # 원문의 특수 구분자 정리
    return re.sub(r"\s+", " ", s).strip()


def parse_list(page):
    out, seen = [], set()
    for li in re.findall(r"<li\b.*?</li>", page, re.S | re.I):
        m = re.search(r'href="[^"]*act=view[^"]*list_no=(\d+)[^"]*"[^>]*>(.*?)</a>', li, re.S)
        if not m or "인사이트" not in text(m.group(2)) or m.group(1) in seen:
            continue
        d = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", text(li))
        no = re.search(r"제\s*(\d+-\d+)\s*호", text(m.group(2)))
        seen.add(m.group(1))
        out.append(dict(list_no=m.group(1), title=text(m.group(2)), date="-".join(d.groups()) if d else "",
                        no=no.group(1) if no else ""))
    return out


def toc_lines(page):
    """본문 목차 → ['[현안분석] …', '[주요 단신] …']"""
    body = re.search(r'<div class="detail">\s*<div class="cont">(.*?)</div>', page, re.S)
    if not body:
        return []
    raw = re.sub(r"<br\s*/?>|</p>|</li>", "\n", body.group(1), flags=re.I)
    lines, head = [], ""
    for ln in (text(x) for x in raw.split("\n")):
        if not ln:
            continue
        if ln.startswith("□"):
            k = ln.lstrip("□ ").replace(" ", "")
            head = HEADS.get(k, ln.lstrip("□ ").strip())
            continue
        ln = ln.lstrip("▪•·- ").strip()
        if ln:
            lines.append("[%s] %s" % (head, ln) if head else ln)
    return lines


def make_item(p, lines, added):
    return {
        "id": "keei-insight-" + p["list_no"], "source": "에너지경제연구원(KEEI)", "category": CATEGORY,
        "series": SERIES, "title": "세계 에너지시장 인사이트(제%s호)" % p["no"] if p["no"] else p["title"],
        "date": p["date"], "summary": lines,
        "url": PDF_URL % p["list_no"], "detail_url": VIEW_URL % p["list_no"],
        "link_label": "원문 PDF 열기", "added": added,
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
        if p["date"] < START or "keei-insight-" + p["list_no"] in have:
            continue
        try:
            lines = toc_lines(fetch(VIEW_URL % p["list_no"]))
        except Exception:
            lines = []
        items.append(make_item(p, lines, today))
        added += 1
    if added:
        items.sort(key=lambda i: (i.get("added", ""), i.get("date", "")), reverse=True)
        data["updated"] = today
        json.dump(data, open("reports.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open("reports.json", "a").write("\n")
    print("added", added, "of", len(posts), "posts")


if __name__ == "__main__":
    main()
