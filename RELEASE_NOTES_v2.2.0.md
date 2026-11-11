# CrowEyes 2.2 — 더 편리한 인쇄와 통합 업데이트 확인

CrowEyes는 Windows 10/11 x64용 이미지 뷰어입니다. 빠르게 사진을 열고 탐색하면서 필요한 순간에 편집, 글자 인식과 사진 정리 도구를 사용할 수 있습니다. 앱·설치형·Portable 버전은 **2.2.0**, Microsoft Store 패키지 버전은 **2.2.0.0**입니다.

## 2.2에서 달라진 점

### 인쇄 창을 더 편하게

인쇄 설정을 **기본 / 크기·여백 / 분할 출력** 탭으로 정리했습니다. 창 크기를 조절할 수 있고 앱 중앙에서 열리며, 인쇄·닫기 버튼을 하단 별도 영역에 배치해 설정 내용 때문에 가려지지 않도록 했습니다. 뷰어와 편집 화면의 상단 도구 모음에서 모두 인쇄할 수 있습니다.

- **인쇄 배율 1~1000%**: 원본 크기, 전체 용지에 맞춤 또는 직접 입력한 배율을 선택합니다.
- **상하좌우 여백(mm)**: 원하는 여백을 각각 지정합니다. 프린터의 인쇄 불가능 영역도 반영합니다.
- **실제 인쇄 크기 안내**: 용지와 이미지의 mm 크기, 총 출력 장수를 미리 확인합니다. 원본 DPI 정보와 미리보기 축소율을 반영하며 DPI도 조절할 수 있습니다.
- **잘림 경고**: 지정한 크기가 전체 출력 영역을 넘으면 경고하고 출력 전 확인합니다.

### 큰 이미지를 A4 여러 장에 나누어 출력

**2장 또는 4장 분할 출력**을 추가했습니다. 2장은 이미지 비율에 맞춰 배치를 선택하고, 4장은 2×2로 배치합니다. 미리보기의 페이지 번호와 점선으로 각 장에 인쇄될 부분을 확인하세요. 점선은 안내용으로 실제 출력물에는 인쇄하지 않습니다.

A2 포스터를 A4 4장으로 출력하려면 A4 용지와 4장 분할을 선택한 뒤 원본 크기 또는 사용자 배율을 지정합니다. 프린터 여백 때문에 원본 전체가 들어가지 않으면 경고가 표시됩니다. 전체를 담으려면 전체 용지에 맞춤을 선택하거나 무테 지원 프린터를 사용하세요. 출력 후 여백을 잘라 순서대로 이어 붙이는 방식이며, 겹침·재단 마크 옵션은 포함하지 않습니다.

### GitHub와 Microsoft Store를 함께 확인

두 배포 경로를 확인하고, 같은 최신 버전이 있으면 **Microsoft Store를 우선**합니다. 버전이 다르면 더 최신 버전을 안내하며, 한쪽 확인에 실패하면 최신이라고 단정하지 않습니다. Store 설치형은 Store를 통해 업데이트합니다. 일반 설치형은 Store 공개 상품 페이지와 게시 확인 정보를 사용하고, Store 설치형은 공식 Store 업데이트 API도 조회합니다. 심사·게시 처리 때문에 공개 시점은 다를 수 있습니다.

### 첫 실행 안내와 UI 개선

Store 설치 후 첫 실행에 **바탕화면 바로가기 추가 여부**를 묻고 연결 프로그램 등록과 Windows 기본 앱 선택 방법을 안내합니다. MSIX는 설치 중 사용자 정의 질문을 띄우지 않으므로 첫 실행에 표시합니다. 기존 기본 앱 선택은 유지하며, 기본 앱 지정은 사용자가 Windows 설정에서 선택합니다. 좌상단 CrowEyes 글자는 Normal로 변경했습니다.

## CrowEyes의 주요 기능

- **보기와 탐색**: 폴더별 파일목록, 정사각형 썸네일, 자연스러운 숫자 이름 정렬, 정렬·보기 메뉴, 클릭 가능한 폴더 경로, 확대·축소·100%·화면 맞춤, 슬라이드쇼와 이미지 비교.
- **파일 선택과 관리**: Ctrl/Shift/드래그 다중 선택, Windows 숨김·해제와 숨김 파일 표시, 일괄 이름 변경·변환, 정확·유사 중복 검색. 숨김은 암호화가 아닙니다.
- **편집**: 선택 영역 저장·클립보드 복사, 크기·비율 변경, 회전·반전·밝기·대비, 주석·형광펜·모자이크, 실행 취소·재실행, 품질·목표 용량을 지정한 저장.
- **OCR와 검색**: 영역 글자 인식, 촬영일·OCR 정보 색인과 파일(OCR) 찾기. 색인은 클립보드가 아닌 로컬 데이터베이스에 저장하며 삭제 메뉴를 제공합니다.
- **정보와 출처**: EXIF/GPS·ICC, 포인터 픽셀 색상, C2PA 출처·AI 생성 선언 확인. C2PA 기록이 없다는 이유만으로 AI 여부를 판정하지 않습니다.
- **기본 포함 도구**: C2PA, 기기 내 성인 콘텐츠 필터와 RAW 미리보기를 포함하고 사용할 때 로드합니다. 성인 필터는 기본 꺼짐이며 오탐·미탐이 있을 수 있습니다. 이미지와 필터 판정 결과를 외부로 전송하지 않습니다.

RAW는 내장 미리보기용이며 현상 도구가 아닙니다. HEIC/HEIF는 Windows 코덱, EPS는 별도 Ghostscript가 필요합니다. 고해상도 뷰어 편집·저장은 표시 미리보기 픽셀 기준이며 원본 픽셀 변환은 일괄 변환을 사용하세요. AI 내용검색·별점·태그·즐겨찾기는 포함하지 않습니다.

## 다운로드와 사용

- [Setup 설치 파일](https://github.com/CrowScienceLab/CrowEyes/releases/download/v2.2.0/CrowEyes_Setup_2.2.0_Windows_x64.exe): 일반 설치와 기존 GitHub 설치형 업그레이드.
- [Portable ZIP](https://github.com/CrowScienceLab/CrowEyes/releases/download/v2.2.0/CrowEyes_Portable_2.2.0_Windows_x64.zip): 전체를 새 폴더에 풀고 CrowEyes.exe 실행. EXE만 따로 옮기지 마세요.
- [SHA256SUMS.txt](https://github.com/CrowScienceLab/CrowEyes/releases/download/v2.2.0/SHA256SUMS.txt): 다운로드 파일 무결성 확인.
- [Microsoft Store](https://apps.microsoft.com/detail/9NNHX36VPSQZ): Store 설치·업데이트. 새 버전은 Microsoft 심사와 게시 완료 후 표시됩니다.

소스·실행 파일 회귀 검사와 패키지 검증을 수행했습니다. 실제 Windows 인쇄 경로로 PDF에 출력한 뒤 2장·4장 페이지 수, 이미지 순서와 여백을 확인했습니다. GitHub 배포 파일은 서명하지 않았으며 로컬 패키지 검증이 Microsoft Store 인증 완료를 의미하지는 않습니다.

---

**English:** CrowEyes 2.2 adds print scaling (1–1000%), individual margins, physical-size guidance, clipping warnings and two-/four-sheet poster printing with numbered previews and dashed boundaries. The resizable print dialog keeps Print/Close visible; the editor also gains a print icon. GitHub and Store checks run together; Store wins equal-version ties. Store first launch asks about a desktop shortcut and explains default-app selection. Viewing, editing, region copy/export, OCR indexing/search, comparison, batch tools, Windows Hidden attributes, on-demand C2PA, local adult filtering and embedded RAW previews remain available. Existing Windows default choices are preserved. Codec requirements and preview-pixel editing limits still apply.
