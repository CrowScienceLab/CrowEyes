# CrowEyes Image Viewer

CrowEyes 1.7은 가볍고 빠른 Windows 이미지 뷰어에 파일 탐색·관리·출력을 연결한 Windows 10/11 x64용 데스크톱 프로그램입니다. 제작자는 Crow Science Lab입니다.

## 다운로드

GitHub Releases에서 용도에 맞는 파일을 받습니다.

- 설치형: `CrowEyes_Setup_1.7_Windows_x64.exe`
- 무설치형: `CrowEyes_Portable_1.7_Windows_x64.zip`
- 무결성 값: `SHA256SUMS.txt`

설치형은 관리자 권한이 필요 없는 사용자별 경로 `%LOCALAPPDATA%\Programs\CrowEyes`를 기본으로 사용하며 설치 위치를 바꿀 수 있습니다. Portable ZIP은 압축을 푼 뒤 `CrowEyes.exe`를 실행하면 되며 Python 설치가 필요하지 않습니다.

## 1.7 주요 기능

- 상단 CrowEyes Command Bar와 `내 컴퓨터 > 드라이브 > 폴더` 전체가 클릭되는 Breadcrumb, 새로고침, 실시간 검색
- 이미지 화면 좌우의 이전·다음 버튼과 3초 기본 간격의 재생/정지가 확실한 슬라이드쇼
- 플레이리스트에서 드라이브·바탕 화면·문서·사진·다운로드 등 Windows 사용자 폴더로 직접 이동
- 모든 플레이리스트 보기 방식에서 폴더·드라이브 한 번 클릭 이동, 패널 닫기 버튼과 간결한 헤더
- 크기가 변하지 않는 고정형 아이콘 호버 글로우와 검정 기본 테마
- PLAYLIST 파일 수·보기·정렬 상태 표시, 폴더 이동, Ctrl/Shift 다중 선택, Explorer drag-out
- Windows 파일 클립보드 복사, F2 이름 변경, 휴지통 삭제, 파일 위치 열기
- PNG/JPEG/WebP/BMP/TIFF raster 저장(JPEG 투명 영역은 흰색 합성)
- JPG, PNG, GIF, WebP, BMP, TIFF, ICO, PSD, SVG 표시와 실제 PSD 합성 썸네일
- 실제 SVG의 px/mm/cm/pt/in/viewBox·UTF-8 BOM·UTF-16 처리와 안전한 크기 fallback
- CrowEyes 인쇄 미리보기 안에서 프린터·방향·용지·매수·파일 출력을 설정하고 중복 Windows 미리보기 없이 직접 인쇄
- GitHub Releases 기반 수동/24시간 자동 업데이트 확인, 진행률, SHA-256 검증
- CrowEyes Dark와 Bright Sky Blue 테마, 슬라이드쇼, 애니메이션, 확대/회전/반전/밝기/대비

### 알려진 문제

- 플레이리스트의 `파일명으로만 보기`에서는 파일명을 클릭해도 표시 이미지가 바뀌지 않을 수 있습니다. 다음 업데이트의 우선 수정 항목이며, 그전에는 `작은 아이콘` 또는 `아이콘 격자` 보기를 이용해 주세요.

AI 파일은 지원하지 않습니다. EPS는 Ghostscript가 이미 설치된 PC에서만 선택 지원하며 배포본에 Ghostscript를 포함하지 않습니다.

## Windows 실행 차단 안내

CrowEyes는 무료로 배포되는 무서명 프로그램입니다. 일부 Windows 11 PC에서는 Smart App Control 또는 Microsoft Defender SmartScreen이 실행을 막을 수 있습니다.

- 반드시 [CrowEyes 공식 GitHub Releases](https://github.com/CrowScienceLab/CrowEyes/releases)에서 내려받고 `SHA256SUMS.txt`로 파일을 확인하십시오.
- SmartScreen에서 `추가 정보 → 실행`이 제공되는 경우에는 출처와 SHA-256을 확인한 사용자가 직접 실행 여부를 판단합니다.
- Smart App Control은 특정 앱만 예외 처리할 수 없습니다. 삭제 후 재설치해도 해결되지 않으며 PC 전체 보안 기능을 끄는 방법은 권장하지 않습니다.
- 회사·학교 관리 PC에서는 보안 설정을 변경하지 말고 관리자에게 문의하십시오.

자세한 내용은 [WINDOWS_SECURITY.md](WINDOWS_SECURITY.md)와 [Microsoft Smart App Control FAQ](https://support.microsoft.com/en-us/Windows/Security/threat-malware-protection/smart-app-control-frequently-asked-questions)를 참고하십시오.

## 기본 앱 등록

설치 프로그램과 앱의 `더 보기 > 기본 앱 등록`은 CrowEyes를 지원 이미지의 “연결 프로그램” 후보로 등록합니다. Windows 정책상 기존 기본 앱을 강제로 변경하지 않으며, 최종 선택은 Windows 기본 앱 설정에서 사용자가 합니다. EPS는 기본 등록 대상에서 제외됩니다.

## 업데이트

`더 보기 > 업데이트 확인`을 선택합니다. 새 릴리스가 있으면 배포 형태에 맞는 Setup 또는 Portable ZIP과 `SHA256SUMS.txt`를 내려받아 SHA-256이 일치할 때만 다음 단계로 진행합니다. 설치형은 검증된 Setup을 실행하고, Portable은 실행 파일을 자동 교체하지 않고 ZIP 위치를 엽니다. 설정은 사용자 홈의 `.croweyes_image_viewer.json`에 저장되어 업그레이드 설치로 초기화되지 않습니다.

## 소스 실행과 빌드

Python 3.10 이상에서 다음을 실행합니다.

```bat
python -m pip install -r requirements.txt
python CrowEyes_Image_Viewer_1.7.py
```

검사·PyInstaller·Inno Setup 빌드 방법은 [BUILD.md](BUILD.md)를 참고하십시오.

## 저작권

Copyright 2026 Crow Science Lab. All rights reserved. 별도의 오픈 소스 라이선스는 부여되지 않습니다.
