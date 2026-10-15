#!/usr/bin/env python3
"""법제처 입법예고(기후에너지환경부) 수집 -> reports.json 의 '입법예고' 분류로 추가.

- 법제처 정보공개 API(목록 조회): https://www.lawmaking.go.kr/rest/ogLmPp.xml?OC=...
- 인증값은 환경변수 LAWMAKING_OC(GitHub Secret)로 받는다. 코드·로그·결과 파일에 적지 않는다.
- 첫 실행에서 응답 구조를 확인할 수 있도록 lawmaking_debug.json 에 진단 정보를 남긴다.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://www.lawmaking.go.kr/rest/ogLmPp.xml"
WEB_DETAIL = "https://opinion.lawmaking.go.kr/gcom/ogLmPp/{seq}"
HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
FIELDS = ["ogLmPpSeq", "lsNm", "lsClsNm", "asndOfiNm", "pntcNo", "pntcDt", "stYd", "edYd",
          "FileName", "FileDownLink", "mappingLbicId", "announceType"]


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


def mask(text, oc):
    return text.replace(oc, "***") if oc else text


def fetch(oc, params):
    q = "OC=" + oc + "".join("&%s=%s" % (k, v) for k, v in params.items())
    req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": "Mozilla/5.0 (report-collector)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def parse_items(xml_text):
    """ogLmPpSeq 를 자식으로 가진 요소를 한 건으로 본다(응답 구조가 달라도 동작)."""
    root = ET.fromstring(xml_text)
    out = []
    for el in root.iter():
        if el.find("ogLmPpSeq") is not None:
            out.append({f: (el.findtext(f) or "").strip() for f in FIELDS})
    return out


def norm_date(s):
    d = re.sub(r"\D", "", s or "")
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) >= 8 else ""


def norm_name(s):
    return re.sub(r"[\sㆍ·•・,.()「」『』<>\[\]]", "", s or "")


def is_energy_law(title, keywords):
    n = norm_name(title)
    return any(norm_name(k) in n for k in keywords)


def to_report(it):
    st, ed = norm_date(it["stYd"]), norm_date(it["edYd"])
    return {
        "id": "lm-" + it["ogLmPpSeq"],
        "source": "기후에너지환경부",
        "category": "입법예고",
        "series": it["lsClsNm"],
        "title": it["lsNm"],
        "date": norm_date(it["pntcDt"]) or st,
        "added": datetime.datetime.now(KST).date().isoformat(),
        "period": ("%s ~ %s" % (st.replace("-", "."), ed.replace("-", "."))) if st and ed else "",
        "period_label": "입법예고 기간",
        "summary": [],
        "url": WEB_DETAIL.format(seq=it["ogLmPpSeq"]),
        "link_label": "원문 보기",
    }


def select(items, cfg):
    since = cfg["since"]
    keep, unmatched, other_ministry = [], [], []
    for it in items:
        d = norm_date(it["pntcDt"]) or norm_date(it["stYd"])
        if d and d < since:
            continue
        if not any(m in it["asndOfiNm"] for m in cfg["ministry_names"]):
            other_ministry.append(it)
            continue
        (keep if is_energy_law(it["lsNm"], cfg["law_keywords"]) else unmatched).append(it)
    return keep, unmatched, other_ministry


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
        reports["updated"] = datetime.datetime.now(KST).date().isoformat()
    return added


def main():
    oc = os.environ.get("LAWMAKING_OC", "").strip()
    if not oc:
        print("LAWMAKING_OC 가 설정되지 않았습니다.")
        return 1
    cfg = load_json("lawmaking_filter.json")
    debug = {"run_at": datetime.datetime.now(KST).isoformat(timespec="seconds"), "requests": []}
    items, seen = [], set()
    failed = False

    for diff in ("0", "1"):  # 0: 진행, 1: 종료
        for page in range(1, 11):
            params = {"cptOfiOrgCd": cfg["ministry_code"], "diff": diff, "page": str(page)}
            rec = {"diff": diff, "page": page}
            try:
                status, body = fetch(oc, params)
                rec.update(status=status, length=len(body), head=mask(body[:1200], oc))
                got = parse_items(body)
            except (urllib.error.URLError, ET.ParseError, OSError) as e:
                rec["error"] = mask(str(e), oc)
                debug["requests"].append(rec)
                failed = True
                break
            new = [g for g in got if g["ogLmPpSeq"] not in seen]
            rec.update(items=len(got), new=len(new))
            debug["requests"].append(rec)
            for g in new:
                seen.add(g["ogLmPpSeq"])
                items.append(g)
            if not new:
                break

    keep, unmatched, other = select(items, cfg)
    debug.update(
        total_fetched=len(items),
        ministries=sorted({i["asndOfiNm"] for i in items}),
        matched=[i["lsNm"] for i in keep],
        unmatched=[{"title": i["lsNm"], "date": norm_date(i["pntcDt"])} for i in unmatched],
        other_ministry=len(other),
    )

    reports = load_json("reports.json", {"updated": "", "items": []})
    added = merge(reports, keep)
    if added:
        save_json("reports.json", reports)
    save_json("lawmaking_debug.json", debug)
    print("조회 %d건 / 게시 대상 %d건 / 신규 추가 %d건 / 미분류 %d건 / 타 부처 %d건"
          % (len(items), len(keep), len(added), len(unmatched), len(other)))
    return 1 if (failed and not items) else 0


if __name__ == "__main__":
    sys.exit(main())
