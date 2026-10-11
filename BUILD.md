# CrowEyes 빌드 안내

현행 2.0 빌드·패키징 절차는 [docs/BUILD_V2.md](docs/BUILD_V2.md)를 따릅니다.
버전 기준은 version.json입니다. 최종 로컬 배포 결과는 [docs/FINAL_RELEASE_V2.md](docs/FINAL_RELEASE_V2.md)에 기록합니다.

이전 1.9e 소스와 실행 폴더·배포 패키지는 별도로 보존합니다. 자동 업데이트 호환성은 tools/check_update_compatibility.py가 보존된 1.9e와 과거 숫자 비교기 최소 fixture로 검증합니다.
