# Kindlelator

Kindlelator는 웹 페이지나 전자책 화면을 캡처해서 OCR로 텍스트를 추출하고, DeepL로 번역한 뒤 결과를 브라우저 확장 프로그램에서 바로 확인할 수 있도록 만든 도구입니다.

이 프로젝트는 주로 다음 흐름으로 동작합니다.
- Chrome 확장 프로그램이 현재 브라우저 탭의 화면을 캡처합니다.
- 백엔드 서버가 이미지를 OCR로 읽어 텍스트를 추출합니다.
- DeepL로 번역을 수행하고, 필요하면 OpenAI로 문장을 더 자연스럽게 다듬습니다.
- 확장 프로그램의 사이드바에 번역 결과를 표시합니다.

---

## 1. 무엇을 할 수 있나요?

Kindlelator를 사용하면 다음과 같은 작업을 간단하게 처리할 수 있습니다.
- Kindle의 텍스트를 읽기
- 영어 문장을 한국어로 번역하기
- OCR 결과와 번역 결과를 한 번에 확인하기
---

## 2. 준비 사항

아래 항목이 필요합니다.
- Python 3.11 이상
- Chrome 또는 Edge 브라우저
- OpenAI API 키
- DeepL API 키
- 인터넷 연결

API 키는 외부 서비스에 요청을 보내기 위해 필요합니다. 키를 잘못 넣으면 실행이 실패할 수 있으니 주의하세요.

---

## 3. 설치 방법

### 3-1. 저장소를 다운로드합니다

아래 명령으로 프로젝트 폴더로 이동합니다.

```bash
git clone https://github.com/aLkdh/kindlelator.git
cd kindlelator
```

### 3-2. Python 가상환경을 생성합니다

macOS / Linux 기준입니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell을 사용하는 경우:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3-3. 필요한 패키지를 설치합니다

```bash
pip install -r requirements.txt
```

설치가 끝나면 다음 패키지들이 준비됩니다.
- fastapi
- uvicorn
- openai
- deepl

---

## 4. 환경 변수 설정

프로젝트 루트에 .env 파일을 만들어 API 키를 설정해야 합니다.

먼저 예시 파일을 복사합니다.

```bash
cp .env.example .env
```

그다음 .env 파일을 열어 아래처럼 수정합니다.

```env
OPENAI_API_KEY=여기에_OpenAI_API_키를_입력하세요
DEEPL_API_KEY=여기에_DeepL_API_키를_입력하세요
OPENAI_OCR_MODEL=gpt-5.4-nano
OPENAI_REFINE_MODEL=gpt-5.4-nano
HOST=127.0.0.1
PORT=8000
CORS_ORIGINS=*
```

주의사항:
- .env 파일은 민감한 정보가 들어 있으므로 공개 저장소에 올리지 마세요.
- 키가 올바르지 않으면 OCR나 번역 요청이 실패할 수 있습니다.

---

## 5. 백엔드 서버 실행

다음 명령으로 서버를 실행할 수 있습니다.

### 가장 간단한 실행 방법

```bash
./start.sh
```

### 직접 실행하는 방법

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

실행이 성공하면 다음 주소에서 API 문서를 확인할 수 있습니다.
- http://127.0.0.1:8000/docs

브라우저에서 열면 FastAPI 문서 페이지가 보입니다.

---

## 6. Chrome 확장 프로그램 로드

1. Chrome 브라우저를 엽니다.
2. 주소창에 다음을 입력합니다.
   ```text
   chrome://extensions
   ```
3. 오른쪽 상단의 개발자 모드(Developer mode)를 켭니다.
4. 「압축해제된 확장 프로그램 로드」를 클릭합니다.
5. 프로젝트 폴더 안의 extension 폴더를 선택합니다.

이제 브라우저 툴바에 Kindlelator 확장 프로그램 아이콘이 나타납니다.

---

## 7. 사용 방법

### 7-1. 백엔드 주소 설정

확장 프로그램 아이콘을 클릭하면 팝업이 열립니다.
- 기본 주소는 http://127.0.0.1:8000 입니다.
- 서버를 다른 주소에서 실행했다면 해당 주소로 바꿔주세요.
- 「Save」 또는 저장 버튼을 눌러 설정을 저장합니다.

### 7-2. 번역할 페이지 열기

번역하고 싶은 웹 페이지나 전자책 화면을 브라우저에서 엽니다.
- 페이지가 보이는 상태여야 합니다.
- 화면이 너무 작거나 숨겨져 있으면 결과가 잘리지 않을 수 있습니다.

### 7-3. 캡처 실행

확장 프로그램 팝업에서 Capture & Translate 버튼을 누르거나,
키보드 단축키를 사용할 수 있습니다.
- macOS: Command + Shift + Y
- Windows / Linux: Ctrl + Shift + Y

요청이 보내지면 잠시 기다린 뒤 결과가 페이지에 표시됩니다.

### 7-4. 결과 확인

번역 결과는 확장 프로그램이 동작하는 페이지에 표시됩니다.
- OCR로 추출된 텍스트
- DeepL 번역 결과
- 필요 시 OpenAI가 다듬은 문장

---

## 8. 프로젝트 폴더 구조

```text
Kindlelator/
├── main.py              # FastAPI 서버 코드
├── requirements.txt     # Python 패키지 목록
├── start.sh             # 서버 실행 스크립트
├── .env.example         # 환경 변수 예시
├── data/                # 이미지와 DB 저장 폴더
├── extension/           # Chrome 확장 프로그램 코드
└── static/              # 정적 웹 리소스
```

---

## 9. 자주 발생하는 문제

### 9-1. 서버가 실행되지 않는다
- Python 환경이 활성화되어 있는지 확인하세요.
- .env 파일이 제대로 생성되었는지 확인하세요.
- 포트 8000이 이미 사용 중이면 PORT 값을 바꿔보세요.

### 9-2. 확장 프로그램이 동작하지 않는다
- Chrome 확장 프로그램이 extension 폴더로 올바르게 로드되었는지 확인하세요.
- 백엔드 서버가 실행 중인지 확인하세요.
- 팝업에서 백엔드 URL이 127.0.0.1:8000으로 설정되어 있는지 확인하세요.

### 9-3. API 키 오류가 발생한다
- .env 파일에 OpenAI API 키와 DeepL API 키가 정확히 입력되었는지 확인하세요.
- 키에 따옴표가 들어가 있지 않은지 확인하세요.
- 네트워크 연결 상태를 점검하세요.

### 9-4. OCR 결과가 비어 있거나 이상하다
- 화면이 명확한지 확인하세요.
- 페이지가 너무 작거나 흐리면 인식률이 낮아질 수 있습니다.
- 텍스트가 잘 보이도록 확대한 뒤 다시 시도해 보세요.

---

## 10. 한 줄 요약

Kindlelator는 브라우저에서 보고 있는 화면을 OCR로 읽고, 번역해서 바로 확인하는 간단한 로컬 자동화 도구입니다.

문제가 있거나 실행 중 오류가 발생하면, 먼저 .env 설정과 백엔드 실행 상태부터 확인해 주세요.
