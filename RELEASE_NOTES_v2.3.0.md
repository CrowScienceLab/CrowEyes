# CrowEyes 2.3 — CrowFlow 화면과 대용량 이미지 개선

CrowEyes는 Windows 10/11 x64용 이미지 뷰어입니다. 앱·설치형·Portable 버전은 **2.3.0**이며, Microsoft Store 패키지 버전은 **2.3.0.0**입니다.

## 2.3에서 달라진 점

- 뷰어·편집 도구 모음을 작업별로 그룹화했습니다. 파일목록의 제목과 정렬·보기 메뉴를 두 줄로 나누고, 이미지 오른쪽 아래에 확대·축소·100%·화면 맞춤을 배치했습니다.
- 보기 메뉴에서 테마와 하단 상태 바를 선택할 수 있습니다. 설정 메뉴에는 Windows 기본 앱 설정과 두 열로 정리한 단축키 안내가 있습니다.
- 대용량 JPEG와 다중 프레임 MPO 사진의 미리보기를 개선했습니다. ICC 프로파일이 포함된 JPEG를 축소할 때 이미지와 썸네일이 빈 화면으로 표시되는 문제를 수정했습니다. 끝부분이 일부 잘린 JPEG는 복구를 시도하며, 읽을 수 없는 ICC 프로파일은 기본 색상 변환으로 처리합니다.
- 모드 스위치의 키 입력과 이미지 이동·재생을 분리했습니다. 좁은 창에서 인쇄 설정과 단축키 안내가 잘리는 문제를 수정했습니다.
- 이미지 읽기 경로의 크기 제한을 정리하고 Pillow와 Python 런타임에 보안 수정판을 적용했습니다.
- 자동·수동 업데이트 확인을 설치 경로별로 분리했습니다. GitHub의 Setup·Portable은 GitHub에서, Microsoft Store 설치형은 Microsoft Store에서 업데이트를 확인합니다.

뷰어와 편집은 공통 파일목록과 이미지 화면을 사용합니다. C2PA, 로컬 콘텐츠 필터, RAW 내장 미리보기는 필요할 때만 로드합니다. 인쇄 배율·여백·2장/4장 분할 출력, OCR 색인·검색, 일괄 정리 도구도 사용할 수 있습니다.

## 설치

Setup은 일반 설치와 기존 GitHub 설치형 업데이트에 사용하세요. Portable은 ZIP 전체를 새 폴더에 풀고 CrowEyes.exe를 실행하세요. Store 설치형은 Store에서 업데이트합니다. 각 파일의 SHA-256은 배포 파일과 함께 제공됩니다.

RAW는 내장 미리보기를 사용합니다. HEIC/HEIF는 Windows 코덱이, EPS는 별도 Ghostscript가 필요합니다. 고해상도 뷰어 편집·저장은 표시 미리보기 픽셀을 사용합니다. [현재 공개 릴리스](https://github.com/CrowScienceLab/CrowEyes/releases/latest) · [Microsoft Store](https://apps.microsoft.com/detail/9NNHX36VPSQZ)

## English

CrowEyes 2.3 groups viewer and editor actions, adds a two-row file-list header and places zoom controls on the image. It improves previews for large JPEG and MPO photos, recovers some JPEGs with a missing file ending and displays images with unreadable ICC profiles using a fallback conversion. Keyboard controls for the mode switch, shortcut help and print layout have been refined. Setup and Portable check GitHub for updates, and Store installs check Microsoft Store. This build also includes updated Pillow and Python runtimes with security fixes. C2PA, local content filtering and embedded RAW previews load on demand.
