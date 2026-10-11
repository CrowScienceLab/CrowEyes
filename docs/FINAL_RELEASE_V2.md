# CrowEyes 2.0 최종 로컬 배포 준비 · 2026-10-12

상태: UI 수정, 실행 검증, Setup/Portable/MSIX 생성 완료. GitHub 및 Microsoft Store 업로드는 수행하지 않았습니다.

## 최종 변경

Blue/Pink 상단 프레임·아이콘·경로 텍스트 배경의 실제 Tk 스타일을 재적용하여 테두리형 셀과 폴더 뒤 검은 여백을 제거했습니다. 브랜드는 20pt 굵은 글씨와 얇은 외곽선으로 만들고 옆 까마귀 아이콘 높이를 폰트 줄 높이와 맞췄습니다.

편집은 복원 / 회전·반전 / 크기·영역 / 주석·형광펜·모자이크·편집 전후 비교로 그룹화했습니다. 정리는 검색·색인 / 이름·변환 / 중복 검색 / 파일 작업 / 정렬 그룹으로 분리했습니다.

첫 실행은 지원 이미지 29종을 연결 프로그램 후보로 등록하고 미지정 확장자만 자동 연결합니다. Windows 보호 UserChoice와 기존 기본 앱 선택은 유지합니다. 완료 플래그로 반복 등록을 막습니다. 새 설치 자동 업데이트 확인 기본값은 켜짐이며 기존 명시적 설정은 보존합니다. 업그레이드는 사용자 동의와 다운로드 SHA-256 검증을 거칩니다.

## 공통 버전과 산출물

앱/Setup/Portable: 2.0.0, PE FileVersion/ProductVersion: 2.0.0.
GitHub: v2.0.0, Microsoft Store: 2.0.0.0.
기존 Inno AppId, Store identity 170231F2.CrowEyes와 publisher를 유지합니다.

파일 위치: release/review-v2.0.0. SHA256SUMS.txt 포함.

| 파일 | 크기 | SHA-256 |
| --- | ---: | --- |
| CrowEyes_2.0.0.0_x64.msix | 73.00 MiB | 99ac71907cc179e232bb77a13deea65949203a9d7139baa2b4378165d0dc29e6 |
| CrowEyes_Portable_2.0.0_Windows_x64.zip | 69.98 MiB | 77bb8b52bbf184e3d3554079f04b7d015f8eb08557d547851c1d3d2c67c0e788 |
| CrowEyes_Setup_2.0.0_Windows_x64.exe | 48.73 MiB | 5266664810c0bade0f90321b12c4df6e14999a6fe57ee6bb71900f595950bdc1 |

압축을 푼 실행 폴더: 2.0 170.06 MiB, 보존한 1.9e 181.62 MiB. 기본 포함 런타임은 C2PA·ONNX 성인 필터·rawpy이며 사용자 요청 시 로드합니다. CLIP/AI 내용검색 모델은 포함하지 않습니다.

## 검증

- 18개 창 크기·테마·모드 조합에서 경계/글자/배치 확인, Blue/Pink/Black 상단 실제 스타일·경로 배경 검사.
- 실행 파일의 뷰어/편집, 공통 파일목록, 모드 전환, 주석/형광펜 실행 취소, 메뉴, 선택·스크롤, OCR 커서, 인쇄 아이콘 검사.
- 실제 기본 포함 성인 필터 On/Off 시 창 닫힘, Off 시 원본 썸네일 즉시 복원, 늦게 도착한 판정 무시 검사.
- 업데이트 숫자 비교: 이전 1.9·1.9e에서 v2.0.0 감지, 동일 버전 반복 알림 방지.
- 첫 실행 등록과 완료 플래그는 등록 함수를 대체한 격리 테스트로 검사.
- 실제 파일 내보내기·덮어쓰기 충돌·취소·EXIF/ICC·색인·중복·C2PA 서명 fixture·실행 취소/재실행 검사.
- 54MP 미리보기 제한, 내보내기 EXIF 방향/치수, 확장 ZIP 경로 탈출 및 잘못된 해시 거부 검사.
- 최종 실행 파일에서 Windows OCR 런타임, C2PA 무기록 처리, ONNX 실제 추론, RAW 라이브러리 로드 통과. OCR은 무문자 이미지로 런타임 호출을 확인했으며 모든 사진에서의 인식 정확도를 평가한 것은 아닙니다.
- 시작 시 c2pa/numpy/onnxruntime/tokenizers 미로드 확인.
- Inno Setup 빌드 성공, MakeAppx manifest 검증 및 패키지 생성 성공.
- Portable/MSIX ZIP CRC 검사, 포함 실행 파일 해시 동일, 모든 기본 포함 런타임 원본 해시 동일, 29개 확장자 앱/Setup/Store 일치 검사.

실제 기존 설치의 교체·설치/제거 및 Store 인증은 수행하지 않았습니다. 실행 파일·Setup은 무서명이며 Store MSIX는 제출용 무서명 패키지입니다. 서명·Store 심사는 로컬 검증과 별도입니다. RAW는 내장 미리보기이며 HEIC/HEIF는 Windows 코덱에 의존합니다.

## 정리

정리 결과는 아래에 추가합니다. 기존 사용자 설정·색인·캐시는 삭제하지 않습니다. 재빌드에 필요한 숨김 의존성 폴더와 Git 이력, 1.9e/2.0 소스·배포 결과는 보존합니다.

복구용 백업을 중복 제거 ZIP 하나로 만들고 CRC와 모든 고유 파일 SHA-256을 검증한 뒤 원본을 정리했습니다.

- 정리 대상: 73개 파일/폴더, 내부 파일 59,745개.
- 원본 합계: 7.38 GiB.
- 복구 ZIP: 1.95 GiB.
- 순 회수 공간: 5.43 GiB (파일 논리 크기 기준).
- 복구 위치: D:\App coding\_archive\CrowEyes-before-final-2.0-cleanup-20261012.zip. manifest.json에서 원래 위치와 blobs/<SHA-256>를 대응시켜 선택 복원할 수 있습니다.
- 활성 소스/배포 폴더에는 이전 1.9e와 최종 2.0.0만 남았습니다. 오래된 미리보기, 중복 Store layout, 빌드 캐시, 테스트 tmp, 구버전 검사/노트는 제거했습니다.
- 재빌드 의존성, Git 이력, 서명 검증 fixture, 사용자 설정·색인·캐시는 유지했습니다.
- 모든 제거 성공, 잠김/권한 오류 없음.

상세 검사 로그와 JSON은 D:/App coding/Segyo-On/docs/maintenance/2026-10-12-croweyes-2.0-final에 보존했습니다.
