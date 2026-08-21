# CrowEyes Image Viewer

CrowEyes 1.5는 가볍고 빠른 Windows 이미지 뷰어에 파일 탐색·관리·출력을 연결한 Windows 10/11 x64용 데스크톱 프로그램입니다. 제작자는 Crow Science Lab입니다.

## 다운로드

GitHub Releases에서 용도에 맞는 파일을 받습니다.

- 설치형: `CrowEyes_Setup_1.5_Windows_x64.exe`
- 무설치형: `CrowEyes_Portable_1.5_Windows_x64.zip`
- 무결성 값: `SHA256SUMS.txt`

설치형은 관리자 권한이 필요 없는 사용자별 경로 `%LOCALAPPDATA%\Programs\CrowEyes`를 기본으로 사용하며 설치 위치를 바꿀 수 있습니다. Portable ZIP은 압축을 푼 뒤 `CrowEyes.exe`를 실행하면 되며 Python 설치가 필요하지 않습니다.

## 1.5 주요 기능

- Windows 11 파일 탐색기에서 영감을 받은 뒤로/앞으로/상위/새로고침, 클릭 가능한 Breadcrumb, 실시간 검색, 반응형 Command Bar
- PLAYLIST 파일 수·보기·정렬 상태 표시, 폴더 이동, Ctrl/Shift 다중 선택, Explorer drag-out
- Windows 파일 클립보드 복사, F2 이름 변경, 휴지통 삭제, 파일 위치 열기
- PNG/JPEG/WebP/BMP/TIFF raster 저장(JPEG 투명 영역은 흰색 합성)
- JPG, PNG, GIF, WebP, BMP, TIFF, ICO, PSD, SVG 표시와 PSD 합성 썸네일
- 실제 SVG의 px/mm/cm/pt/in/viewBox·UTF-8 BOM·UTF-16 처리와 안전한 크기 fallback
- CrowEyes 인쇄 미리보기, A4/Letter, 세로/가로, 페이지 맞춤/96 DPI 실제 크기, 원본 raster 및 SVG 재렌더 기반 고품질 Windows 인쇄
- GitHub Releases 기반 수동/24시간 자동 업데이트 확인, 진행률, SHA-256 검증
- CrowEyes Dark와 Bright Sky Blue 테마, 슬라이드쇼, 애니메이션, 확대/회전/반전/밝기/대비

AI 파일은 지원하지 않습니다. EPS는 Ghostscript가 이미 설치된 PC에서만 선택 지원하며 배포본에 Ghostscript를 포함하지 않습니다.

## 기본 앱 등록

설치 프로그램과 앱의 `더 보기 > 기본 앱 등록`은 CrowEyes를 지원 이미지의 “연결 프로그램” 후보로 등록합니다. Windows 정책상 기존 기본 앱을 강제로 변경하지 않으며, 최종 선택은 Windows 기본 앱 설정에서 사용자가 합니다. EPS는 기본 등록 대상에서 제외됩니다.

## 업데이트

`더 보기 > 업데이트 확인`을 선택합니다. 새 릴리스가 있으면 배포 형태에 맞는 Setup 또는 Portable ZIP과 `SHA256SUMS.txt`를 내려받아 SHA-256이 일치할 때만 다음 단계로 진행합니다. 설치형은 검증된 Setup을 실행하고, Portable은 실행 파일을 자동 교체하지 않고 ZIP 위치를 엽니다. 설정은 사용자 홈의 `.croweyes_image_viewer.json`에 저장되어 업그레이드 설치로 초기화되지 않습니다.

## 소스 실행과 빌드

Python 3.10 이상에서 다음을 실행합니다.

```bat
python -m pip install -r requirements.txt
python CrowEyes_Image_Viewer_1.5.py
```

검사·PyInstaller·Inno Setup 빌드 방법은 [BUILD.md](BUILD.md)를 참고하십시오.

## 저작권

Copyright 2026 Crow Science Lab. All rights reserved. 별도의 오픈 소스 라이선스는 부여되지 않습니다.
