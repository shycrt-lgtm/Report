# 에너지 법령·규칙 동향 (law/)

에너지 자료실 > 자체자료 > "법령·규칙 동향" 버튼으로 여는 페이지. 주소: https://shycrt-lgtm.github.io/Report/law/

- 수집: `.github/workflows/collect_law.yml`이 매일 07·12·18시(KST) `law/scripts/collect.mjs` 실행
- 대상: 국회 법률안(열린국회정보 API) · 정부 입법예고·행정예고(국민참여입법센터) · 부처 게시판 · 전력거래소 규칙 · 전기위원회 결과
- AI 요약·당사 사업 영향 분석: Gemini (`GEMINI_API_KEY`)

## 저장소 Secrets (Settings → Secrets and variables → Actions)
| 이름 | 용도 |
|---|---|
| ASSEMBLY_API_KEY | 열린국회정보 API — 없으면 국회 법률안 수집만 건너뜀 |
| GEMINI_API_KEY | AI 요약·사업 영향 분석·주간 브리핑 |

## 파일
- `index.html` 화면 / `data/*.json` 수집 결과 / `feed.xml` RSS
- `scripts/keywords.json` 수집 분야 키워드, `scripts/boards.json` 부처 게시판 목록
- `scripts/profile.txt` 당사 사업 설명, `scripts/relevance.txt` 관련도 기준, `scripts/core_laws.txt` 항상 표시할 당사 핵심 법령
- 사업 구분 8개는 `scripts/collect.mjs`의 BIZ와 `index.html`의 BIZ를 같이 수정

원본: gemma-uxt/Energy-law-watch를 가져와 화면·분석 기준을 당사 기준으로 변경
