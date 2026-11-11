# CrowEyes 빌드 안내

현행 2.2 빌드·패키징 절차는 [docs/BUILD_V2.md](docs/BUILD_V2.md)를 따릅니다.
버전 기준은 version.json입니다. 최종 로컬 배포 결과는 [docs/FINAL_RELEASE_V2.md](docs/FINAL_RELEASE_V2.md)에 기록합니다.

사용자 요청으로 2.0 미만 전용 소스·실행 폴더·배포 패키지는 삭제합니다. 자동 업데이트 호환성은 tools/check_update_compatibility.py가 과거 비교기 최소 fixture와 현행 비교기로 검증합니다. 개발 Git 이력을 재작성하지 않습니다.
