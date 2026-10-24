# CrowEyes 2.1 — 더 선명한 아이콘, 정렬·보기, 파일 숨김

CrowEyes 2.1은 빠른 사진 탐색을 유지하면서 파일목록 사용성과 아이콘을 개선한 업데이트입니다. 앱/설치형/Portable은 **2.1.0**, Microsoft Store 패키지는 **2.1.0.0**입니다.

## 눈에 잘 들어오는 아이콘

도구마다 알아보기 쉬운 실루엣과 컬러·입체감을 적용했습니다. 공통 사각 테두리를 줄이고 주요 도구 아이콘을 36px로 확대했습니다. 창 제목줄에도 노란부리 까마귀 아이콘을 적용하여 Crow 시리즈의 브랜드를 통일했습니다. 테마나 뷰어·편집 모드를 바꿔도 유지됩니다.

## 파일목록 바로 옆에서 정렬하고 보기

**정렬**에서 이름·수정한 날짜·유형·크기와 오름차순·내림차순을 선택하세요. 숫자가 있는 이름은 사진1 → 사진2 → 사진10 순으로 정렬됩니다. 정렬 후에도 선택한 실제 파일을 유지합니다.

**보기**에서 파일명·작은 아이콘+파일명·아이콘 격자를 선택할 수 있습니다. 우클릭 메뉴와 상단 메뉴에서도 같은 기능에 접근합니다.

## 숨기고, 다시 표시하고, 해제하기

1. 파일목록에서 하나 이상의 이미지를 선택하거나 열린 그림을 우클릭하여 **숨김**을 누르세요.
2. 파일의 Windows 숨김 속성이 켜지고 기본 목록에서 제외됩니다. 파일명과 사진 내용은 바뀌지 않습니다.
3. **보기 → 숨김 파일 표시**를 켜면 다시 확인할 수 있습니다.
4. 해당 파일을 우클릭하여 **숨김 해제**하면 일반 파일로 돌아옵니다.

숨김은 Windows 파일 속성으로, 암호화나 비밀번호 보호 기능은 아닙니다. 모든 사진을 숨기면 화면을 비우고, 늦게 완료된 로딩 결과가 다시 표시되지 않도록 처리했습니다.

## 점검과 오류 수정

- 제한된 환경에서 Windows OCR이 임시 파일 경로를 열지 못하던 문제를 수정했습니다. 앱이 읽은 이미지를 메모리 스트림으로 전달하며 시스템 보안 설정이나 실행 정책을 변경하지 않습니다.
- OCR 작업에 60초 제한을 추가했습니다.
- 실제 Windows 숨김/해제·파일 내용 보존, 정렬/선택, 테마/창 크기/작업 모드, 편집·색인·내보내기·슬라이드쇼·형식 지원과 패키지를 검사했습니다.
- C2PA·성인 필터·RAW 미리보기는 그대로 기본 포함하고 사용할 때 로드합니다. 시작 시 무거운 AI 모듈을 불러오지 않습니다.

## 다운로드와 업데이트

- **Setup EXE**: 일반 설치 및 기존 GitHub 설치형 업데이트에 사용합니다.
- **Portable ZIP**: 전체를 풀고 CrowEyes.exe를 실행하세요. EXE만 따로 옮기지 마세요.
- **SHA256SUMS.txt**: 다운로드 파일의 무결성 확인 자료입니다.
- Microsoft Store 설치형은 Store를 통해 업데이트합니다. Store 반영 시점은 심사·게시 처리에 따라 GitHub와 다를 수 있습니다.

RAW는 내장 미리보기이며 HEIC/HEIF에는 Windows 코덱이 필요합니다. 고해상도 뷰어 편집·저장은 표시 미리보기 픽셀을 사용하며 원본 픽셀 변환은 일괄 변환을 사용하세요. 기존 2.0의 편집·영역 복사/저장·OCR 검색·비교·인쇄 기능은 유지됩니다.

---
English: CrowEyes 2.1 refreshes colorful command icons and the native crow title-bar icon; restores Sort/View menus beside the file list; adds reversible Windows Hidden attributes and Show hidden files; preserves file selections during natural numeric sorting; and fixes Windows OCR temporary-path access using a read-only memory stream. C2PA, on-device adult filtering and RAW previews remain bundled and load on demand.
