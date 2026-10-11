# CrowEyes Image Viewer

CrowEyes 2.0.0은 빠른 이미지 보기와 요청 시 실행하는 편집·사진 관리 기능을 제공합니다. 제작자는 Crow Science Lab입니다. 최종 패키지 생성과 로컬 검증을 완료했으며 GitHub 2.0 정식 릴리스로 배포합니다. Microsoft Store 게시는 별도 진행합니다.

## 2.0 화면과 기능

뷰어·편집은 같은 파일목록과 이미지 화면을 공유합니다. 상단 컬러 아이콘과 모드 스위치, 클릭 가능한 컴퓨터·드라이브·폴더 경로, 이전·다음·상위·새로고침, 정사각형 썸네일, Ctrl/Shift/드래그 선택을 제공합니다. Blue/Pink 테마의 상단 배경을 통일하고 메뉴의 관련 기능을 구분선으로 묶었습니다. 주석·형광펜·모자이크·비교는 편집 메뉴에서 별도 그룹입니다.

영역 저장·클립보드 복사, 크기·비율 변경, 회전·반전·밝기·대비, 실행 취소·재실행, 일괄 변환·이름 변경, 이미지 비교, 인쇄, 품질·목표 용량 저장, EXIF/GPS·ICC, 정확/유사 중복 검색을 지원합니다. 영역 OCR과 촬영일·OCR 정보 색인/검색은 앱 내부 보조 창에서 실행합니다. 색인은 로컬 catalog.sqlite3에 저장하며 색인 삭제 메뉴를 제공합니다.

C2PA 출처·성인 콘텐츠 필터·RAW 미리보기는 기본 포함하되 사용 시에만 라이브러리와 모델을 로드합니다. 성인 필터는 기본 꺼짐이며 이미지/판정 결과를 외부로 전송하지 않습니다. C2PA 기록 없음은 AI 여부를 판별할 수 없다는 뜻입니다. AI 내용검색·별점·태그·즐겨찾기는 포함하지 않습니다.

## 공통 버전과 패키지

version.json을 기준으로 앱/설치형/Portable 2.0.0, GitHub 태그 v2.0.0, Microsoft Store 2.0.0.0을 사용합니다. 다음 패치는 2.0.1 / v2.0.1 / 2.0.1.0으로 함께 변경합니다. 문자 접미사를 사용하지 않습니다.

release/review-v2.0.0에 Setup EXE, Portable ZIP, Store MSIX와 SHA256SUMS.txt가 있습니다. 이전 1.9e는 release/v1.9e 및 dist/v1.9e에 보존합니다. [최종 검증 및 정리](docs/FINAL_RELEASE_V2.md), [빌드 안내](docs/BUILD_V2.md), [변경 내역](RELEASE_NOTES_v2.0.0.md)를 참조하십시오.

게시 이후 [GitHub 최신 릴리스](https://github.com/CrowScienceLab/CrowEyes/releases/latest)와 [Microsoft Store](https://apps.microsoft.com/detail/9NNHX36VPSQZ)에서 배포합니다. GitHub 2.0 릴리스의 [자세한 기능·사용 안내](RELEASE_NOTES_v2.0.0.md)를 확인하세요. Microsoft Store 반영 시점은 GitHub와 다를 수 있습니다.

## 첫 실행과 업데이트

새 설치는 시작 시 백그라운드로 최신 버전을 확인합니다. 기존 설정에서 끈 경우는 선택을 유지합니다. 새 버전 설치는 사용자 동의와 SHA-256 확인을 거치며 Store 설치형은 Store 업데이트로 연결합니다. 숫자 버전 비교로 이전 1.9·1.9e도 v2.0.0을 새 버전으로 인식합니다.

첫 실행 때 지원 이미지 29종을 연결 프로그램 후보로 등록하고, 기본 앱이 없는 확장자는 자동 연결합니다. Windows 보호 UserChoice와 기존 기본 앱 선택은 변경하지 않습니다. EPS는 외부 Ghostscript가 필요하며 자동 연결에서 제외합니다. 첫 등록 완료를 설정에 기록해 반복 등록을 방지합니다.

## 사용 범위와 개인정보

RAW는 내장 미리보기이며 현상 도구가 아닙니다. HEIC/HEIF는 Windows 코덱에 의존합니다. 고해상도 보기에서 저장은 표시 미리보기 픽셀 기준이고 일괄 변환은 원본을 읽습니다. 성인 필터에는 오탐·미탐이 있을 수 있습니다.

[개인정보](PRIVACY.md), [외부 구성요소와 라이선스](THIRD_PARTY_NOTICES.md), [Windows 실행 안내](WINDOWS_SECURITY.md). 사용자 설정과 로컬 색인/캐시는 설치 폴더 외부에 저장되며 이번 자료 정리에서 삭제하지 않았습니다.
