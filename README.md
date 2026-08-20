# CrowEyes Image Viewer

CrowEyes는 Windows용 데스크톱 이미지 뷰어입니다. 이미지 감상과 폴더 탐색에 필요한 기능을
빠르고 간결한 인터페이스로 제공합니다.

- 현재 버전: 1.3
- 최신 GitHub 릴리스: 1.3
- 제작: Crow Science Lab
- 릴리스: 2026년 8월
- 지원 운영체제: Windows 10/11 x64

## 주요 기능

- JPG, PNG, GIF, WebP, BMP, TIFF, ICO, PSD, SVG 지원
- Ghostscript가 설치된 PC에서 EPS 선택 지원(AI 파일은 지원하지 않음)
- Windows 기본 프린터 선택 창을 이용한 고품질 이미지 인쇄(`Ctrl+P`)
- SVG 확대 시 필요한 해상도로 단계형 재렌더링하여 선명도 유지
- 폴더의 이전·다음 이미지를 키보드와 마우스 휠로 탐색
- 목록·상세·아이콘 격자 보기와 이름/날짜/크기/형식별 오름차순·내림차순 정렬
- 플레이리스트의 `.. 상위 폴더`·하위 폴더 더블클릭 이동
- 플레이리스트 Ctrl/Shift 다중 선택 유지와 Windows 탐색기로 파일 끌어 놓기 복사
- `+`, `-` 확대·축소, 화면 맞춤, 원본 크기, 회전, 좌우·상하 반전
- 이미지 우클릭으로 원본 크기·보이는 크기·선택 영역을 클립보드에 복사
- GIF/WebP 애니메이션과 슬라이드쇼
- F5·상단 버튼 슬라이드쇼 재생/일시정지와 파일명에 영향받지 않는 고정 툴바
- 상단의 중복 파일명과 하단 확대 제어를 정리한 고정 폭 전체 경로 표시줄
- 고정된 앱 제목과 `Pixel (x, y) #RRGGBB · 크기 % · 전체 경로` 순서의 하단 정보 표시
- 까마귀 눈 로고와 CrowEyes 이름 뒤로 12개 명령이 연속되는 반응형 상단 툴바 및 통일된 벡터형 아이콘
- 전문 그래픽 기반의 투명 까마귀 눈 로고, 큰 CrowEyes 워드마크, 이름·단축키 툴팁
- `CrowEyes Dark · Crow`, `Bright Sky Blue` 제품 테마
- Windows 기본 이미지 프로그램 등록 도우미
- 파일 연결로 실행할 때 자동 창 선택 및 키보드 포커스

## 일반 사용자

GitHub의 **Releases** 페이지에서 `CrowEyes_Image_Viewer_1.3_Windows_x64.zip`을 내려받습니다.
ZIP 압축을 푼 뒤 `CrowEyes.exe`를 실행하면 Python 설치 없이 사용할 수 있습니다.

기본 이미지 뷰어로 사용하려면 CrowEyes에서 다음 메뉴를 선택합니다.

1. `설정 > 기본 프로그램 등록…`
2. 사용할 이미지 확장자 선택
3. `자동 등록`을 눌러 아직 기본 앱이 정해지지 않은 형식에 CrowEyes 적용

Windows가 보호하는 기존 사용자 선택은 CrowEyes가 임의로 바꾸지 않습니다. 이미 다른 기본 앱이
지정된 형식은 `등록 후 Windows 설정 열기`에서 사용자가 직접 CrowEyes를 선택할 수 있습니다.

## 소스 실행

Python 3.10 이상에서 다음 명령을 실행합니다.

```bat
python -m pip install -r requirements.txt
python CrowEyes_Image_Viewer_1.3.py
```

## 검사와 빌드

```bat
python tools\check_theme_contrast.py
python tools\check_extended_formats.py
python -m PyInstaller --noconfirm --clean CrowEyes.spec
```

자세한 빌드 방법은 [BUILD.md](BUILD.md)를 참고하십시오.

## 저작권

Copyright 2026 Crow Science Lab. All rights reserved.

소스가 공개되어 있더라도 별도의 오픈 소스 라이선스는 부여되지 않습니다.
