# CrowEyes와 Windows 실행 보호

CrowEyes는 Crow Science Lab이 무료로 배포하는 Authenticode 무서명 프로그램입니다. 일부 Windows 11 PC에서는 Smart App Control 또는 Microsoft Defender SmartScreen이 실행을 막을 수 있습니다.

## 안전하게 확인하기

1. [CrowEyes 공식 GitHub Releases](https://github.com/CrowScienceLab/CrowEyes/releases)에서만 파일을 내려받습니다.
2. 같은 릴리스의 `SHA256SUMS.txt`와 다운로드한 파일의 SHA-256이 일치하는지 확인합니다.
3. 파일 이름과 버전이 릴리스 설명과 일치하는지 확인합니다.

## SmartScreen

SmartScreen 경고에 `추가 정보 → 실행` 선택이 제공되는 경우, 공식 배포처와 SHA-256을 확인한 사용자가 직접 실행 여부를 결정할 수 있습니다.

## Smart App Control

Smart App Control에는 CrowEyes 하나만 허용하는 예외 기능이 없습니다. 앱을 삭제하고 다시 설치해도 같은 무서명 파일이므로 해결되지 않습니다. PC 전체의 Smart App Control을 끄면 보안 범위가 넓게 약화되므로 CrowEyes는 이를 권장하거나 자동으로 변경하지 않습니다.

회사·학교에서 관리하는 PC라면 보안 설정을 변경하지 말고 시스템 관리자에게 문의하십시오.

Microsoft 공식 문서: [Smart App Control FAQ](https://support.microsoft.com/en-us/Windows/Security/threat-malware-protection/smart-app-control-frequently-asked-questions)
