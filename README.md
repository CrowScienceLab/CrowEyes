# CrowEyes Image Viewer

CrowEyes는 Windows용 데스크톱 이미지 뷰어입니다. 이미지 감상과 폴더 탐색에 필요한 기능을
빠르고 간결한 인터페이스로 제공합니다.

- 버전: 1.0
- 제작: Crow Science Lab
- 릴리스: 2026년 8월
- 지원 운영체제: Windows 10/11 x64

## 주요 기능

- JPG, PNG, GIF, WebP, BMP, TIFF, ICO 등 주요 이미지 형식 지원
- 폴더의 이전·다음 이미지를 키보드와 마우스 휠로 탐색
- 확대·축소, 화면 맞춤, 원본 크기, 회전, 좌우·상하 반전
- GIF/WebP 애니메이션과 슬라이드쇼
- `CrowEyes Dark · Crow`, `Bright Sky Blue` 제품 테마
- Windows 기본 이미지 프로그램 등록 도우미
- 파일 연결로 실행할 때 자동 창 선택 및 키보드 포커스

## 일반 사용자

GitHub의 **Releases** 페이지에서 `CrowEyes_Image_Viewer_1.0_Windows_x64.zip`을 내려받습니다.
ZIP 압축을 푼 뒤 `CrowEyes.exe`를 실행하면 Python 설치 없이 사용할 수 있습니다.

기본 이미지 뷰어로 사용하려면 CrowEyes에서 다음 메뉴를 선택합니다.

1. `설정 > 기본 프로그램 등록…`
2. 사용할 이미지 확장자 선택
3. Windows 기본 앱 설정에서 CrowEyes 선택

## 소스 실행

Python 3.10 이상에서 다음 명령을 실행합니다.

```bat
python -m pip install -r requirements.txt
python CrowEyes_Image_Viewer_1.0.py
```

## 검사와 빌드

```bat
python tools\check_theme_contrast.py
python -m PyInstaller --noconfirm --clean CrowEyes.spec
```

자세한 빌드 방법은 [BUILD.md](BUILD.md)를 참고하십시오.

## 저작권

Copyright 2026 Crow Science Lab. All rights reserved.

현재 저장소는 비공개 배포 준비용이며, 별도의 오픈 소스 라이선스를 부여하지 않습니다.
