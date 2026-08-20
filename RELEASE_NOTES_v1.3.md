# CrowEyes Image Viewer 1.3

## 새 기능

- Windows 기본 프린터 선택 창을 이용한 이미지 인쇄 및 `Ctrl+P`
- Pillow 합성 미리보기를 이용한 PSD 보기
- `resvg_py` 기반 SVG 보기
- SVG 확대 시 필요한 해상도로 고해상도 재렌더링
- Ghostscript가 설치된 PC에서 EPS 보기

## 개선

- PSD·SVG·EPS의 파일 열기, 폴더 검색, 썸네일과 형식 정보 처리
- 손상 파일, 외부 리소스 SVG, Ghostscript 부재와 인쇄 취소/오류 처리
- SVG/EPS bitmap을 16,000,000픽셀로 제한하는 메모리 보호
- PyInstaller onedir에 SVG 네이티브 렌더러를 포함한 배포 안정성

## 참고

- EPS는 Ghostscript가 설치된 PC에서만 지원하며 CrowEyes에는 Ghostscript가 포함되지 않습니다.
- AI 파일은 이번 버전에서 지원하지 않습니다.
