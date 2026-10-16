/*
 * 에너지 리포트 NEW 배지
 * - 각 사이트의 메뉴에서 data-report-link 속성이 붙은 링크를 찾아, 자료실(reports.json)의
 *   최신 게시물을 아직 확인하지 않았으면 NEW 배지를 붙인다.
 * - 링크를 누르거나 자료실 화면을 열면 "확인함"으로 기록되어 배지가 사라진다.
 * - 게시물 등록일(added)로부터 EXPIRE_DAYS일이 지나면 확인하지 않았어도 배지를 내린다.
 * - 같은 도메인(shycrt-lgtm.github.io)의 모든 사이트가 localStorage를 공유한다.
 */
(function () {
  var DATA_URL = "https://shycrt-lgtm.github.io/Report/reports.json";
  var KEY = "energyReport.seen";
  var EXPIRE_DAYS = 1;

  function getSeen() {
    try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; }
  }
  function setSeen(id) {
    try { localStorage.setItem(KEY, id); } catch (e) { /* 저장 불가 시 무시 */ }
  }

  function addStyle() {
    if (document.getElementById("report-badge-style")) return;
    var s = document.createElement("style");
    s.id = "report-badge-style";
    s.textContent =
      "a[data-report-link]{position:relative}" +
      ".report-new{position:absolute;top:-7px;right:-4px;background:#dc2626;color:#fff;" +
      "font-size:10px;font-weight:900;line-height:1;padding:3px 5px;border-radius:2px;" +
      "letter-spacing:.02em;pointer-events:none;font-family:inherit}" +
      "@media (max-width:640px){.report-new{top:-6px;right:-2px;font-size:9px;padding:2px 4px}}";
    document.head.appendChild(s);
  }

  function latestOf(items) {
    var best = null;
    (items || []).forEach(function (it) {
      var k = (it.added || it.date || "") + "|" + (it.date || "");
      if (!best || k > best.k) best = { k: k, it: it };
    });
    return best ? best.it : null;
  }

  function isFresh(it) {
    var d = it.added || it.date;
    if (!d) return true;
    var t = Date.parse(d + "T00:00:00+09:00");
    if (isNaN(t)) return true;
    return (Date.now() - t) / 86400000 <= EXPIRE_DAYS;
  }

  function run() {
    var links = document.querySelectorAll("a[data-report-link]");
    if (!links.length) return;

    fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var all = (data.items || []).slice();
        if (data.internal_notice) all.push(data.internal_notice); // 자체자료 신규 알림(제목 없음)
        var latest = latestOf(all);
        if (!latest || !latest.id) return;
        Array.prototype.forEach.call(links, function (a) {
          a.addEventListener("click", function () { setSeen(latest.id); });
        });
        if (getSeen() === latest.id || !isFresh(latest)) return;
        addStyle();
        Array.prototype.forEach.call(links, function (a) {
          if (a.querySelector(".report-new")) return;
          var b = document.createElement("span");
          b.className = "report-new";
          b.textContent = "NEW";
          b.setAttribute("aria-label", "새 자료");
          a.appendChild(b);
        });
      })
      .catch(function () { /* 배지는 부가 기능이므로 실패해도 화면에 영향 없음 */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
