# CrowEyes 2.3 배포 후보 검토

2026-11-23 · Windows x64 · 앱 2.3.0 · Store 패키지 2.3.0.0

CrowFlow UI와 이미지 디코딩 수정이 포함된 로컬 배포 후보다. 빌드는 Python 3.12.16, Pillow 13.0.0, PyInstaller 6.22.3, Inno Setup, Windows SDK MakeAppx로 진행했다. 배포본의 Python DLL 해시는 검증한 3.12.16 런타임과 일치한다.

## 패키지

파일과 체크섬은 `release/review-v2.3.0/`에 있다.

| 파일 | 크기(바이트) | SHA-256 |
| --- | ---: | --- |
| `CrowEyes_Setup_2.3.0_Windows_x64.exe` | 51,472,205 | `f499d8f11486358296425e211bf16035009eddfbb710235f769030f14cba6f66` |
| `CrowEyes_Portable_2.3.0_Windows_x64.zip` | 73,612,370 | `550be300c507c615eff59ea842e4053f0e4cae7d8fa17157e474f46b2e911a43` |
| `CrowEyes_2.3.0.0_x64.msix` | 76,754,972 | `a4cfbcb916424713dcdc61a43de53bd5bb7fc1c63fe57a6cc1c0f6b955562c64` |

## 확인한 항목

- `tools/validate_release.py` 통과. 버전 및 파일 연결 29종을 대조했다. Portable ZIP과 MSIX에 있는 앱 파일 각 2,292개의 SHA-256이 PyInstaller 배포 폴더와 일치했다. Store 앱 ID, 게시자, x64 아키텍처가 2.2 MSIX와 일치했다.
- `CrowEyes.exe --v20-self-test`와 `--workspace-self-test` 통과. 무거운 모듈 지연 로드, C2PA, 콘텐츠 필터 추론, RAW 바인딩, 4열 목록과 공통 캔버스를 확인했다. Portable ZIP을 새 폴더에 푼 뒤 해당 EXE의 핵심 검사를 다시 실행했다.
- 업데이트 호환성, 이미지 경계, 2.3 소스 UI, 인쇄 설정과 Microsoft Print to PDF 2장·4장 검사 통과. 로컬 2.2 배포 파일은 기존 체크섬과 일치했다.

ICC JPEG 빈 화면과 설치 출처별 업데이트 확인을 수정한 뒤 세 패키지를 다시 빌드했다. `tmp/review-v2.3.0/update-routing/`의 `package-validation.json`, `payload-parity.json`, `frozen-v20.json`, `frozen-workspace.json`, `portable-self-test.json`이 위 체크섬의 빌드에 해당한다. 같은 폴더의 `v22_logic.log`와 `v22_ui.log`에서 채널별 조회, 동시 요청 합치기, 오류 및 시간 초과를 확인할 수 있다. Store 회귀 검사는 모의 API를 사용했다. `tmp/review-v2.3.0/icc-fix-tests/`에는 JPEG 수정 검증이 있다. PDF 출력은 `tmp/v22-print-pdf/2b5e0fc424844c91bd84d5ad00b272ef/`에 있다.

## 게시 전 확인

Setup과 MSIX는 서명이 없는 로컬 후보다. 별도 Windows 환경에서 Setup 설치·2.2 업그레이드, 서명된 Store 환경에서 최초 실행·업데이트 서비스, AGY의 실제 카메라 파일·고 DPI 화면 검증이 남아 있다. Store 공개 버전 피드는 실제 게시 확인 후 갱신한다.

[2.3 릴리스 노트](../RELEASE_NOTES_v2.3.0.md) · [Store 한국어·영어 문안](../store/listing-2.3.json)
