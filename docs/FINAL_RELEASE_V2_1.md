# CrowEyes 2.1 배포 기록 — 2026-10-24

사용자 검토 승인 후 제목줄 아이콘을 추가하고 Setup/Portable/MSIX를 생성했다. 앱 버전 2.1.0, Store 2.1.0.0. 실제 실행 창에서 까마귀 제목줄 아이콘을 확인했다. 현행 창에 ICO를 직접 지정하고 테마 변경 때 재적용한다. Tk의 iconbitmap() 조회 문자열은 Windows에서 빈 문자열을 반환할 수 있어 회귀 검사는 실제 WM_GETICON 핸들로 확인한다.

`tools/check_title_icon.py` 통과. 정렬·숨김·OCR·작업 모드 등 기존 2.1 검사 기록은 REVIEW_V2_1.md를 참조한다. 최종 산출물은 release/review-v2.1.0이며 tools/validate_release.py가 ZIP CRC, 포함 EXE/런타임 원본 해시, 공통 버전과 확장자 29종 일치를 확인했다. package-published.json이 최종 해시이며 이전 검토본 package-review.json과 구분한다.

실제 최신 2.1 실행 화면은 store/screenshots-v2.1에 보존한다. 기존 공개 2.0과 1.9e 패키지는 유지했다. GitHub/Store 결과는 아래에 추가한다.
