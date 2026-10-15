#!/usr/bin/env python3
"""행정안전부 관보 인사(공공데이터포털) 수집 -> reports.json 의 '기후부 [인사발령]' 으로 추가.

- API: https://apis.data.go.kr/1741000/ApiPersonnelService/getApiPersonnelList
- 인증키는 환경변수 DATA_GO_KR_KEY(GitHub Secret)로 받는다. 코드·로그·결과 파일에 적지 않는다.
- 발행기관이 기후에너지환경부인 건만 게시한다(국가공무원 5급 이상 인사).
- 첫 실행에서 응답 구조를 확인할 수 있도록 gwanbo_debug.json 에 진단 정보를 남긴다.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://apis.data.go.kr/1741000/ApiPersonnelService/getApiPersonnelList"
GWANBO_HOME = "https://gwanbo.go.kr/"
INSTITUTION = "기후에너지환경부"
SINCE = "2026-10-01"
PAGE_SIZE = 100
MAX_PAGES = 20
HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))


def today():
    return datetime.datetime.now(KST).date()


def load_json(name, default=None):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def encode_key(key):
    """디코딩 키·인코딩 키 어느 쪽을 넣어도 한 번만 인코딩되도록 맞춘다."""
    return urllib.parse.quote(urllib.parse.unquote(key), safe="")


def fetch(key, params):
    q = "serviceKey=" + encode_key(key)
    for k, v in params.items():
        q += "&%s=%s" % (k, urllib.parse.quote(str(v), safe=""))
    req = urllib.request.Request(ENDPOINT + "?" + q, headers={"User-Agent": "Mozilla/5.0 (report-collector)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def mask(text, key):
    for k in {key, urllib.parse.unquote(key), encode_key(key)}:
        if k:
            text = text.replace(k, "***")
    return text


def parse_response(body):
    """(resultCode, resultMsg, totalCount, items) 를 돌려준다. 응답이 한 겹 감싸져 있어도 처리."""
    data = json.loads(body)
    node = data
    for _ in range(3):
        if isinstance(node, dict) and "resultCode" not in node and len(node) == 1:
            node = next(iter(node.values()))
    if isinstance(node, dict) and "response" in node and "resultCode" not in node:
        node = node["response"]
    code = str(node.get("resultCode", ""))
    msg = str(node.get("resultMsg", ""))
    total = node.get("totalCount", 0)
    items = node.get("items") or []
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    try:
        total = int(total)
    except (TypeError, ValueError):
        total = 0
    return code, msg, total, [i for i in items if isinstance(i, dict)]


def norm_date(s):
    d = re.sub(r"\D", "", s or "")
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) >= 8 else ""


def link_of(it):
    p = (it.get("pdfFilePath") or "").strip()
    if p.startswith("http"):
        return p
    if p.startswith("//"):
        return "https:" + p
    if p.startswith("/"):
        return "https://gwanbo.go.kr" + p
    return GWANBO_HOME


def to_report(it):
    return {
        "id": "gb-" + str(it.get("cntntSeqNo", "")).strip(),
        "source": INSTITUTION,
        "category": "기후부",
        "prefix": "인사발령",
        "series": (it.get("ofcttBookNm") or "").strip(),
        "title": (it.get("cntntSj") or "").strip(),
        "date": norm_date(it.get("hopePblictDt", "")),
        "added": today().isoformat(),
        "summary": [],
        "url": link_of(it),
        "link_label": "관보 원문 보기",
    }


def select(items):
    keep = []
    for it in items:
        d = norm_date(it.get("hopePblictDt", ""))
        if d and d < SINCE:
            continue
        if INSTITUTION not in (it.get("pblcnInstNm") or ""):
            continue
        if not str(it.get("cntntSeqNo", "")).strip():
            continue
        keep.append(it)
    return keep


def merge(reports, new_items):
    have = {x.get("id") for x in reports["items"]}
    added = []
    for it in new_items:
        r = to_report(it)
        if r["id"] not in have:
            reports["items"].append(r)
            have.add(r["id"])
            added.append(r)
    if added:
        reports["updated"] = today().isoformat()
    return added


def pull(key, extra, debug, label):
    """날짜 형식(YYYYMMDD → YYYY-MM-DD)을 바꿔가며 모든 페이지를 받는다."""
    since = datetime.date.fromisoformat(SINCE)
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        base = {"pageSize": PAGE_SIZE, "type": "json",
                "reqFrom": since.strftime(fmt), "reqTo": today().strftime(fmt)}
        base.update(extra)
        items, bad_param = [], False
        for page in range(1, MAX_PAGES + 1):
            rec = {"step": label, "fmt": fmt, "page": page}
            try:
                status, body = fetch(key, dict(base, pageNo=page))
                code, msg, total, got = parse_response(body)
            except (urllib.error.URLError, ValueError, OSError) as e:
                rec["error"] = mask(str(e), key)
                debug["requests"].append(rec)
                return items, True
            rec.update(status=status, resultCode=code, resultMsg=msg, totalCount=total, items=len(got))
            if page == 1 and got:
                rec["sample"] = got[0]
            if page == 1 and not got:
                rec["head"] = mask(body[:600], key)
            debug["requests"].append(rec)
            if code == "303":
                bad_param = True
                break
            if code not in ("00", "10", "0", ""):
                return items, True
            items += got
            if not got or len(items) >= total:
                break
        if not bad_param:
            return items, False
    return [], True


def main():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_KEY 가 설정되지 않았습니다.")
        return 1
    debug = {"run_at": datetime.datetime.now(KST).isoformat(timespec="seconds"), "requests": []}

    items, failed = pull(key, {"pblcnSearch": INSTITUTION}, debug, "기관 검색")
    if not items and not failed:
        # 기관명 표기가 다른지 확인하기 위해 전체 기관을 받아 이름만 모은다
        allitems, failed = pull(key, {}, debug, "기관 조건 없음(진단)")
        debug["institutions_seen"] = sorted({(i.get("pblcnInstNm") or "") for i in allitems})
        items = allitems

    keep = select(items)
    debug.update(fetched=len(items), matched=[{"id": i.get("cntntSeqNo"), "title": i.get("cntntSj"),
                                               "date": norm_date(i.get("hopePblictDt", ""))} for i in keep])
    reports = load_json("reports.json", {"updated": "", "items": []})
    added = merge(reports, keep)
    if added:
        save_json("reports.json", reports)
    save_json("gwanbo_debug.json", debug)
    print("조회 %d건 / 게시 대상 %d건 / 신규 추가 %d건" % (len(items), len(keep), len(added)))
    return 1 if (failed and not items) else 0


if __name__ == "__main__":
    sys.exit(main())
