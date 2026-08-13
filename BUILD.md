# CrowEyes Image Viewer 1.2 빌드

## 개발 환경 실행

Windows 11의 PowerShell 또는 명령 프롬프트에서 다음 명령을 실행합니다.

```bat
py -3 -m pip install -r requirements.txt
py -3 CrowEyes_Image_Viewer_1.2.py
```

Anaconda 환경에서는 다음 명령으로 실행할 수도 있습니다.

```bat
python -m pip install -r requirements.txt
python CrowEyes_Image_Viewer_1.2.py
```

이미지나 폴더 경로를 첫 번째 인자로 전달할 수도 있습니다.

```bat
py -3 CrowEyes_Image_Viewer_1.2.py "C:\Images\sample.png"
```

`ttkbootstrap`이 설치되어 있지 않으면 프로그램이 설치 명령을 안내하는 오류 대화상자를 표시합니다.

## 제품 테마 및 대비 검사

`보기 > 테마`에서 다음 두 제품 테마를 선택할 수 있습니다.

- `CrowEyes Dark · Crow`: 완전한 검정보다 부드러운 차콜 배경과 흰색 본문 글자
- `Bright Sky Blue`: 밝은 하늘색 배경과 고대비 네이비 글자

일반 글자와 버튼 글자는 WCAG 4.5:1, 버튼 입체 경계는 3:1 이상인지 다음 명령으로 검사합니다.

```bat
python tools\check_theme_contrast.py
python tools\check_playlist_navigation.py
python tools\check_slideshow_toolbar.py
```

## 입력 및 탐색 동작

- Windows에서 연결된 그림 파일로 실행하면 CrowEyes 창과 이미지 영역이 자동 선택됩니다.
- 이미지 영역의 마우스 휠은 기본적으로 `위=이전`, `아래=다음` 이미지를 엽니다.
- `환경설정 > 마우스 휠 동작`에서 `확대 / 축소`로 변경할 수 있습니다.
- 툴바, 키보드, 마우스 휠 확대·축소는 항상 이미지 영역 중앙을 기준으로 합니다.
- `도움말 > 프로그램 정보`에서 `2026년 8월 · v1.2 · Crow Science Lab`을 확인할 수 있습니다.

## PyInstaller onedir 빌드

개발·배포 검증에는 문제 추적이 쉽고 실행 안정성이 높은 `onedir` 방식을 기본으로 사용합니다.
Windows 실행 파일 아이콘 `assets\icons\croweyes.ico`와 상단 브랜드용 투명 PNG
`assets\icons\croweyes-eye-logo.png`(약 38KB)를 포함합니다.
아이콘을 다시 만들 때는 다음 명령을 실행합니다.

```bat
py -3 tools\generate_croweyes_icon.py
```

일반 Python 환경의 빌드 명령은 다음과 같습니다.

```bat
py -3 -m pip install pyinstaller
py -3 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onedir ^
  --name CrowEyes ^
  --icon assets\icons\croweyes.ico ^
  --collect-data ttkbootstrap ^
  CrowEyes_Image_Viewer_1.2.py
```

현재 개발 PC의 Anaconda 패키지를 직접 수집하면 불필요한 과학 계산 라이브러리가 포함됩니다.
배포 전용 가상환경과 검증된 `CrowEyes.spec`을 사용하면 Pillow 이미지 코덱과 Anaconda Tk
필수 DLL만 포함한 경량 빌드를 재현할 수 있습니다.

```bat
python -m venv .publish-venv
.publish-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.16.0
.publish-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CrowEyes.spec
```

결과물은 `dist\CrowEyes\CrowEyes.exe`에 생성됩니다. 배포할 때는 `CrowEyes` 폴더 전체를
그대로 압축해 전달합니다. 실행 후 `설정 > 기본 프로그램 등록…`에서 원하는 확장자를
등록하면 Windows 기본 앱 설정 화면으로 연결됩니다. 현재 검증된 Windows x64 배포 폴더는
약 41.53MB입니다.
