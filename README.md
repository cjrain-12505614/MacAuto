# Mac Auto — macOS 매크로 자동화 도구

<p align="center">
  <img src="https://raw.githubusercontent.com/cjrain-12505614/MacAuto/main/icon.icns" width="128" alt="Mac Auto Icon">
</p>

macOS에서 마우스와 키보드 동작을 녹화하고 재생하는 자동화 도구입니다.

## ✨ 주요 기능

- 🔴 **녹화** — 마우스 이동/클릭/스크롤 + 키보드 입력을 실시간 캡처
- ▶️ **재생** — 녹화된 패턴을 정밀한 타이밍으로 재생
- 🔁 **반복** — 지정된 횟수 또는 무한 반복 재생
- ⚡ **속도 조절** — 0.1x ~ 10x 배속 지원
- 💾 **패턴 저장** — 이름을 지정하여 JSON으로 저장/로드
- ⌨️ **글로벌 단축키** — 앱이 백그라운드에 있어도 단축키로 제어
- ⚙️ **단축키 사용자 정의** — 원하는 키 조합으로 자유롭게 변경

## 📋 요구 사항

- macOS 12.0+
- Python 3.10+
- **접근성 권한** 필수 (시스템 설정 > 개인정보 보호 및 보안 > 접근성)

## 🚀 설치 및 실행

### 소스에서 직접 실행

```bash
git clone https://github.com/cjrain-12505614/MacAuto.git
cd MacAuto
pip3 install -r requirements.txt
python3 main.py
```

### .app 번들 빌드

```bash
pip3 install py2app
python3 setup.py py2app
open dist/Mac\ Auto.app
```

## 🎮 사용법

| 기본 단축키 | 동작 |
|------------|------|
| `F9` | 녹화 시작/중지 |
| `F10` | 재생 시작 |
| `ESC` | 재생/녹화 중지 |

> ⚙️ 단축키 설정 버튼에서 원하는 키 조합으로 변경 가능

### 워크플로우

1. **F9**를 눌러 녹화 시작
2. 마우스/키보드 동작 수행
3. **F9**를 눌러 녹화 중지 → 패턴 이름 입력 후 저장
4. 저장된 패턴 목록에서 선택
5. 반복 횟수/속도 설정 후 **F10**으로 재생

## 📁 프로젝트 구조

```
mac_auto/
├── main.py              # 앱 진입점 + 접근성 권한 체크
├── gui.py               # 다크 테마 tkinter GUI
├── keyboard_monitor.py  # Quartz CGEventTap 키보드 모니터
├── recorder.py          # 마우스(pynput) + 키보드(Quartz) 녹화
├── player.py            # 마우스(pynput) + 키보드(Quartz) 재생
├── storage.py           # JSON 패턴 저장/로드
├── models.py            # 이벤트 데이터 모델
├── settings.py          # 단축키 설정 저장/로드
├── setup.py             # py2app 빌드 설정
└── requirements.txt     # 의존성
```

## ⚠️ 접근성 권한

이 앱은 마우스/키보드 이벤트를 캡처하기 위해 macOS 접근성 권한이 필요합니다.

1. 앱 첫 실행 시 권한 요청 팝업이 표시됩니다
2. **시스템 설정 > 개인정보 보호 및 보안 > 접근성**으로 이동
3. Mac Auto (또는 Terminal/Python)에 권한을 허용

## 🛠 기술 스택

- **GUI**: tkinter (다크 테마)
- **마우스 제어**: pynput
- **키보드 모니터링**: Quartz CGEventTap (macOS 26+ 호환)
- **키보드 재생**: Quartz CGEventCreateKeyboardEvent
- **빌드**: py2app

## 📜 라이선스

MIT License
