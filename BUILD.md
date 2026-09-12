# CrowEyes Image Viewer 1.9 빌드 및 릴리스

## 1. Clean venv

Windows x64 Python 3.10 이상에서 배포 전용 환경을 만듭니다. Anaconda 전체 패키지를 수집하지 않습니다.

```bat
py -3 -m venv .publish-venv
.publish-venv\Scripts\python.exe -m pip install --upgrade pip
.publish-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.22.0
```

의존성은 Pillow, ttkbootstrap, tkinterdnd2, `resvg_py==0.4.0`, Send2Trash, NumPy와 ONNX Runtime CPU입니다. ONNX Runtime DLL, 모델, 투명 WebP, 아이콘과 라이선스 파일을 PyInstaller 결과에서 확인합니다. Ghostscript는 EPS 선택 지원용 외부 프로그램이며 번들하지 않습니다.

## 2. 검사

```bat
.publish-venv\Scripts\python.exe -m py_compile CrowEyes_Image_Viewer_1.9.py croweyes_safety.py
.publish-venv\Scripts\python.exe tools\check_theme_contrast.py
.publish-venv\Scripts\python.exe tools\check_playlist_navigation.py
.publish-venv\Scripts\python.exe tools\check_slideshow_toolbar.py
.publish-venv\Scripts\python.exe tools\check_extended_formats.py
.publish-venv\Scripts\python.exe tools\check_v19.py
```

`check_v19.py`는 새 아이콘, C2PA 표시, 테마, 문구, 버전 및 패키징 계약을 검사합니다. 기존 안전 정책·비동기 로딩 검사는 이전 버전 검사와 Windows GUI smoke test에서 함께 확인합니다.

## 3. PyInstaller onedir 및 Portable

```bat
.publish-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CrowEyes.spec
```

`dist\CrowEyes\_internal\c2pa\libs\c2pa_c.dll` 포함 여부를 확인하고, `CrowEyes.exe --c2pa-self-test test-assets\CrowEyes_C2PA_50pct_sample.jpg`를 실행해 종료 코드 0을 확인합니다. 이후 이미지 경로 인자와 빈 실행, 안전 필터 OFF/ON 방식으로 smoke test합니다. 그 후 `dist\CrowEyes`의 내용이 ZIP 최상위에서 바로 보이도록 `CrowEyes_Portable_1.9_Windows_x64.zip`을 만듭니다.

## 4. Inno Setup

Inno Setup 6의 `ISCC.exe installer\CrowEyes.iss`를 실행하면 `release\CrowEyes_Setup_1.9_Windows_x64.exe`가 생성됩니다. 설치는 관리자 권한이 필요 없는 `%LOCALAPPDATA%\Programs\CrowEyes`가 기본이며 사용자가 경로를 바꿀 수 있습니다. 동일 AppId로 기존 설치를 감지해 업그레이드하고, 시작 메뉴·선택적 바탕 화면 바로가기·제거 프로그램·Open With 후보 등록을 제공합니다. 사용자 설정 파일은 설치 폴더 밖에 있어 업그레이드/제거 시 보존됩니다.

설치/사용자 지정 경로/업그레이드/제거/재설치 후 실행과 설정 보존을 Windows 10/11 x64에서 확인합니다.

## 5. SHA-256 및 릴리스

Setup과 Portable ZIP에 대해 SHA-256을 계산해 다음 형식의 `release\SHA256SUMS.txt`를 만듭니다.

```text
<64자리 hash>  CrowEyes_Setup_1.9_Windows_x64.exe
<64자리 hash>  CrowEyes_Portable_1.9_Windows_x64.zip
```

사용자 검토가 끝난 뒤 GitHub 공개 릴리스 `v1.9` / `CrowEyes Image Viewer 1.9`에 세 파일을 모두 올립니다. 앱 업데이트 기능은 GitHub latest release를 background thread에서 읽고 numeric version 비교 후 선택한 asset을 임시 폴더에 다운로드합니다. `SHA256SUMS.txt`와 일치하지 않으면 Setup을 실행하지 않습니다. Portable은 자체 교체하지 않고 검증된 ZIP 위치만 엽니다.

## 6. 코드 서명

현재 인증서가 없어 `CrowEyes.exe`와 Setup EXE는 unsigned 상태입니다. 따라서 Windows SmartScreen 경고 또는 Smart App Control 차단이 발생할 수 있습니다. 무료 배포 방침에서는 이 사실과 공식 다운로드·SHA-256 검증 절차를 `WINDOWS_SECURITY.md`와 앱 내부에 명확히 안내합니다. Smart App Control을 끄도록 자동 유도하거나 Windows 보안 설정을 변경하지 않습니다.
