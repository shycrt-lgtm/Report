#!/usr/bin/env python3
"""에너지경제연구원(KEEI) '국제유가 및 시장 동향'(주간) 새 호를 reports.json에 등록한다.
게시판 목록에서 새 호를 찾고, 원문 PDF 첫 쪽의 요약 항목을 뽑아 summary로 넣는다.
PROBE=1 환경변수로 실행하면 등록하지 않고 목록·PDF 구조만 출력한다(점검용)."""
import io, json, os, re, html, sys, datetime, urllib.request

LIST_URL = "https://www.keei.re.kr/board.es?mid=a10102020000&bid=0002"
BASE = "https://www.keei.re.kr"
SERIES = "국제유가 및 시장 동향"
MIN_NO = 1114                       # 이 호수 이상만 자동 등록 (1113호까지는 수동 등록분)
KST = datetime.timezone(datetime.timedelta(hours=9))
PROBE = os.environ.get("PROBE") == "1"

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": LIST_URL})
    b = urllib.request.urlopen(req, timeout=60).read()
    return b if binary else b.decode("utf-8", "ignore")

def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def parse_list(page):
    """목록에서 (list_no, 제목, 날짜) 추출. 표(tr) 또는 목록(li) 구조 모두 시도."""
    out, seen = [], set()
    blocks = re.findall(r"<tr\b.*?</tr>", page, re.S | re.I) or re.findall(r"<li\b.*?</li>", page, re.S | re.I)
    for b in blocks:
        m = re.search(r'href="([^"]*list_no=(\d+)[^"]*)"[^>]*>(.*?)</a>', b, re.S)
        if not m:
            continue
        title = strip(m.group(3)) or strip(b)
        if SERIES.replace(" ", "") not in title.replace(" ", ""):
            continue
        ln = m.group(2)
        if ln in seen:
            continue
        seen.add(ln)
        d = re.search(r"(\d{4})[-.](\d{2})[-.](\d{2})", strip(b))
        out.append(dict(list_no=ln, title=title, date="-".join(d.groups()) if d else "",
                        detail=BASE + html.unescape(m.group(1)) if m.group(1).startswith("/") else html.unescape(m.group(1))))
    return out

def pdf_text(list_no):
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    for seq in (1, 2, 0):
        url = f"{BASE}/pdfOpen.es?bid=0002&list_no={list_no}&seq={seq}"
        try:
            b = fetch(url, binary=True)
        except Exception as e:
            print("  PDF 실패", seq, type(e).__name__); continue
        if not b.startswith(b"%PDF"):
            continue
        try:
            r = PdfReader(io.BytesIO(b))
            return url, "\n".join((r.pages[i].extract_text() or "") for i in range(min(2, len(r.pages))))
        except Exception as e:
            print("  PDF 해석 실패", type(e).__name__)
    return None, ""

def summarize(text):
    """첫 쪽의 요약 항목(□·○·ㅇ·◦·- 로 시작하는 줄)을 최대 12개 추출."""
    items = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r"^[□■○◦ㅇ●•▪\-]\s*\S", s) and len(s) > 8:
            s = re.sub(r"^[□■○◦ㅇ●•▪\-]\s*", "", s)
            items.append(s)
        elif items and s and not re.match(r"^[□■○◦ㅇ●•▪\-]", s) and len(items[-1]) < 120 and not re.match(r"^\d+$", s):
            items[-1] += " " + s           # 줄바꿈으로 끊긴 문장 이어 붙이기
        if len(items) >= 12:
            break
    return [re.sub(r"\s+", " ", i).strip() for i in items]

def main():
    page = fetch(LIST_URL)
    posts = parse_list(page)
    if PROBE:
        print("목록 길이", len(page), "tr", len(re.findall(r"<tr\b", page)), "li", len(re.findall(r"<li\b", page)))
        for m in re.finditer(r"list_no=\d+", page):
            print("  ", strip(page[max(0, m.start()-300):m.end()+300])[:400]); break
        print("국제유가 글", posts[:5])
        if posts:
            u, t = pdf_text(posts[0]["list_no"])
            print("PDF", u); print(t[:3000]); print("요약", summarize(t))
        return
    if not posts:
        print("목록 파싱 실패"); sys.exit(1)
    data = json.load(open("reports.json", encoding="utf-8"))
    items = data["items"]
    have = {i["id"] for i in items}
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    added = 0
    for p in sorted(posts, key=lambda x: int(x["list_no"])):
        no = re.search(r"(\d{3,5})\s*호", p["title"])
        no = no.group(1) if no else ""
        if not no or int(no) < MIN_NO:
            continue
        iid = "keei-oil-" + no
        if iid in have:
            continue
        url, text = pdf_text(p["list_no"])
        period = re.search(r"(\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?\s*[~∼]\s*\d{1,2}\.\s*\d{1,2})", text or "")
        date = p["date"] or today
        title = p["title"] if re.search(r"\d{4}\.\d{1,2}\.\d{1,2}", p["title"]) else f"{SERIES} ({no}호, {date.replace('-', '.')})"
        items.append({
            "id": iid, "source": "에너지경제연구원(KEEI)", "category": "국제유가", "series": SERIES,
            "title": title, "date": date, "period": re.sub(r"\s+", " ", period.group(1)) if period else "",
            "summary": summarize(text), "url": url or p["detail"], "detail_url": p["detail"],
            "link_label": "원문 PDF 열기" if url else "게시글 보기", "added": today})
        added += 1
        print("등록", iid, title)
    if added:
        items.sort(key=lambda i: (i.get("added", ""), i.get("date", "")), reverse=True)
        data["updated"] = today
        json.dump(data, open("reports.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open("reports.json", "a").write("\n")
    print("added", added, "of", len(posts), "posts")

main()
