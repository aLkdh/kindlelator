import base64
import mimetypes
import os
import re
import sqlite3
import sys
import uuid
from pathlib import Path

import deepl
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import APIConnectionError, OpenAI
from pydantic import BaseModel
import uvicorn


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
IMAGE_PATH = BASE_DIR / "data" / "image.png"
OUTPUT_PATH = BASE_DIR / "output.txt"
TRANSLATED_OUTPUT_PATH = BASE_DIR / "translated.txt"
STARWARS_DB_PATH = BASE_DIR / "data" / "starwars.db"

OCR_PROMPT = (
    "이미지에서 읽을 수 있는 모든 텍스트를 추출하십시오. "
    "원래의 읽는 순서를 유지하고, 문단 구조는 가능한 한 유지하십시오. "
    "장식용 레이아웃, 페이지 번호, 헤더, 푸터, 메뉴, 버튼, 하이라이트, 북마크 등은 무시하십시오. "
    "추출 결과만 출력하고, 번역, 설명, 요약, 의견은 추가하지 마십시오."
)

def load_env(env_path: Path = ENV_PATH) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key and key not in os.environ:
            os.environ[key] = value


load_env()
OCR_MODEL = os.getenv("OPENAI_OCR_MODEL", "gpt-4o-mini")
REFINE_MODEL = os.getenv("OPENAI_REFINE_MODEL", OCR_MODEL)
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]

app = FastAPI(title="Kindlelator OCR API")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
)


class OcrResponse(BaseModel):
    text: str
    output_path: str


class TranslateResponse(BaseModel):
    text: str
    output_path: str


class StarwarsTerm(BaseModel):
    english: str
    korean: str


def image_to_data_url(image_path: Path) -> str:
    mime_type, _encoding = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_image}"


def extract_text_from_image(image_path: Path = IMAGE_PATH) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env: OPENAI_API_KEY='your-api-key'"
        )

    client = OpenAI()
    try:
        response = client.responses.create(
            model=OCR_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": OCR_PROMPT,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_to_data_url(image_path),
                        },
                    ],
                }
            ],
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            "Could not connect to the OpenAI API. Check your internet connection "
            "or run this script outside the restricted sandbox."
        ) from exc

    return response.output_text


def save_output(text: str, output_path: Path) -> None:
    output_path.write_text(text, encoding="utf-8")


def read_output(output_path: Path) -> str:
    if not output_path.exists():
        raise FileNotFoundError(f"Output not found: {output_path}")

    return output_path.read_text(encoding="utf-8")


def ensure_starwars_db(db_path: Path = STARWARS_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS starwars_term (english TEXT PRIMARY KEY, korean TEXT NOT NULL)"
        )
        conn.commit()


def lookup_starwars_korean(english: str, db_path: Path = STARWARS_DB_PATH) -> str | None:
    ensure_starwars_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT korean FROM starwars_term WHERE english = ?",
            (english.strip(),),
        )
        row = cur.fetchone()
    return row[0] if row else None


def list_starwars_terms(db_path: Path = STARWARS_DB_PATH) -> list[StarwarsTerm]:
    ensure_starwars_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT english, korean FROM starwars_term ORDER BY english")
        rows = cur.fetchall()
    return [StarwarsTerm(english=row[0], korean=row[1]) for row in rows]


def upsert_starwars_term(english: str, korean: str, db_path: Path = STARWARS_DB_PATH) -> None:
    ensure_starwars_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO starwars_term (english, korean) VALUES (?, ?)"
            " ON CONFLICT(english) DO UPDATE SET korean = excluded.korean",
            (english.strip(), korean.strip()),
        )
        conn.commit()

def delete_starwars_term(english: str, db_path: Path = STARWARS_DB_PATH) -> None:
    ensure_starwars_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM starwars_term WHERE english = ?", (english.strip(),))
        conn.commit()


def build_starwars_mapping(raw_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for term in sorted(list_starwars_terms(), key=lambda item: len(item.english), reverse=True):
        if re.search(rf"(?<!\w){re.escape(term.english)}(?!\w)", raw_text):
            mapping[term.english] = term.korean
    return mapping


def choose_glossary_name() -> str:
    return f"starwars_glossary_{uuid.uuid4().hex[:8]}"


def create_temporary_glossary(
    translator: deepl.Translator,
    glossary_name: str,
    mapping: dict[str, str],
) -> deepl.api_data.GlossaryInfo:
    return translator.create_glossary(
        name=glossary_name,
        source_lang="EN",
        target_lang="KO",
        entries={en: ko for en, ko in mapping.items()},
    )


def delete_temporary_glossary(
    translator: deepl.Translator,
    glossary: deepl.api_data.GlossaryInfo,
) -> None:
    translator.delete_glossary(glossary)


def strip_translation_metadata(text: str) -> str:
    metadata_prefixes = (
        "스타워즈 고유명사:",
        "스타워즈 인물:",
        "관계도:",
    )
    lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith(metadata_prefixes)
    ]
    return "\n".join(lines).strip()


def refine_translation_with_openai(translated_text: str, source_text: str | None = None) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return strip_translation_metadata(translated_text)

    client = OpenAI()
    source_section = ""
    if source_text:
        source_section = (
            "[영어 원문]\n"
            f"{source_text.strip()}\n\n"
        )

    prompt = (
        "당신은 영어 장르소설을 한국어 단행본 문체로 다듬는 전문 번역 편집자입니다. "
        "DeepL 초벌 번역을 그대로 믿지 말고, 영어 원문이 제공되면 원문을 기준으로 의미와 뉘앙스를 확인한 뒤 "
        "자연스러운 한국어 소설 문장으로 재번역에 가깝게 다듬으세요.\n\n"

        "작업 순서:\n"
        "1. 영어 원문과 한국어 초벌 번역 끝에 붙은 '스타워즈 고유명사:', '스타워즈 인물:', '관계도:' 줄을 먼저 읽고, "
        "등장인물 목록, 고유명사 표기, 인물 관계, 상하 관계, 사제 관계를 판별 자료로 사용합니다.\n"
        "2. 영어 원문과 한국어 초벌 번역을 대조해 오역, 빠진 의미, 과한 직역을 찾습니다.\n"
        "3. 모든 대사마다 화자와 상대를 따옴표 주변 서술로 확정한 뒤, 판별 자료와 본문 맥락을 함께 사용해 "
        "누가 반말을 써야 하는지, 누가 존댓말을 써야 하는지 결정합니다.\n"
        "4. 결정한 말투에 맞춰 대사의 종결어미, 1인칭, 2인칭, 호칭을 고칩니다. 같은 화자가 같은 상대에게 말할 때는 "
        "처음부터 끝까지 같은 존비어 방향을 유지합니다.\n"
        "5. DeepL 특유의 영어식 어순과 딱딱한 표현을 한국어 장르소설 문체로 강하게 교정합니다.\n"
        "6. 스타워즈 용어, 호칭, 전투 묘사는 팬 번역투가 아니라 출판 번역에 가까운 자연스러운 표현으로 정리합니다.\n\n"

        "화자 판단 규칙:\n"
        "- '스타워즈 인물:' 줄과 '관계도:' 줄이 있으면 본문 밖 메모가 아니라 말투 판별용 입력 정보로 반드시 사용하세요.\n"
        "- '스타워즈 고유명사:' 줄은 인물명과 용어 표기 통일에 사용하세요.\n"
        "- 따옴표 밖의 서술(예: '오비완이 말했다', '아나킨이 대답했다')을 이용해 화자를 판단하세요.\n"
        "- 화자를 확실히 알 수 없으면 직전/직후 행동, 시선, 응답 관계, 호칭을 근거로 추정하세요. 그래도 불명확한 경우에만 기존 말투를 유지하세요.\n"
        "- 말투는 반드시 '화자 → 상대방' 방향으로 결정하세요.\n"
        "- 관계가 서로 대칭이라고 가정하지 마세요. A가 B에게 존댓말을 해도 B가 A에게 존댓말을 해야 한다는 뜻은 아닙니다.\n\n"

        "말투 규칙:\n"
        "- 스승 → 제자 : 반말, 평어, 권위 있는 말투를 사용합니다. '당신' 같은 어색한 2인칭은 피하고 필요하면 '너' 또는 이름을 씁니다.\n"
        "- 제자 → 스승 : 존댓말 또는 존중하는 말투를 사용합니다.\n"
        "- 상급자, 지휘관, 지도자 → 하급자 : 일반적으로 반말 또는 권위 있는 평어를 사용합니다.\n"
        "- 하급자 → 상급자 : 존댓말을 사용합니다.\n"
        "- 황제, 군주, 권력자, 지도자는 자신의 지위에 맞는 권위적인 말투를 유지합니다.\n"
        "- 친구, 동료, 가족, 연인처럼 가까운 관계에서는 상황에 맞는 자연스러운 반말을 우선 고려합니다.\n"
        "- 같은 인물은 같은 상대에게 처음부터 끝까지 동일한 말투를 유지하세요.\n"
        "- 한 대화 중에 특별한 이유 없이 반말과 존댓말을 섞지 마세요.\n"
        "- 호칭(마스터, 폐하, 장군, 대장 등)은 유지하되, 호칭 하나 때문에 문장 전체의 존비어 방향을 뒤집지 마세요.\n"
        "- 관계도나 본문 맥락상 스승이 제자에게 말하는 경우는 기본적으로 차분한 반말/평어를 씁니다.\n"
        "- 관계도나 본문 맥락상 제자가 스승에게 말하는 경우는 '마스터' 같은 호칭과 존댓말을 유지합니다.\n\n"

        "말투 교정 예시:\n"
        "- 스승 → 제자(예: 오비완 → 아나킨): '당신의 광선검이 ... 감사해야 할 것 같군요.'는 금지입니다. "
        "'네 광선검이 ... 감사해야겠군.'처럼 반말/평어로 고치세요.\n"
        "- 스승 → 제자(예: 오비완 → 아나킨): '제가 한 순간만 더 늦었더라면'은 금지입니다. "
        "'내가 한순간만 더 늦었더라면'처럼 고치세요.\n"
        "- 제자 → 스승(예: 아나킨 → 오비완): '죄송합니다, 마스터'처럼 존댓말을 유지하세요.\n\n"

        "스타워즈 세계관 규칙:\n"
        "- 제다이 사제 관계, 시스 사제 관계, 군대 계급 관계에서는 반드시 화자와 상대방의 방향을 구분하세요.\n"
        "- 관계도가 제공되면 관계도를 최우선 기준으로 사용하세요.\n"
        "- 관계도에 없는 관계는 대화 내용과 상황으로 판단하되, 근거 없는 관계를 만들지 마세요.\n"
        "- 스타워즈 고유명사와 호칭은 임의로 변경하지 마세요.\n"
        "- Roger, roger는 기계적인 드로이드 대사 느낌이 살아나게 '라저, 라저'처럼 처리하세요.\n"
        "- lightsaber는 기존 용어집 표기가 있으면 따르되, 한 본문 안에서 '광선검'과 '라이트세이버'를 섞지 마세요.\n\n"

        "문체 규칙:\n"
        "- 의미, 내용, 감정, 분위기는 그대로 유지하세요.\n"
        "- 필요한 경우 문장 구조를 크게 바꿔도 됩니다. 단, 사건 순서와 정보량은 유지하세요.\n"
        "- 영어식 어순과 DeepL 번역투를 자연스러운 한국어 소설 문체로 바꾸세요.\n"
        "- 한국어에서 잘 쓰지 않는 직역 표현은 의미를 유지한 채 자연스럽게 수정하세요.\n"
        "- '선명한 빛들', '피 한 방울 흘리지 않는 정밀함', '가야 할 곳은 머리였다'처럼 어색한 직역은 과감히 풀어 쓰세요.\n"
        "- 묘사문은 설명문처럼 딱딱하게 만들지 말고, 장면의 속도감과 긴장을 살리세요.\n"
        "- 불필요하게 현대적인 표현이나 구어체를 사용하지 마세요.\n"
        "- 문장을 삭제하거나 요약하지 마세요. 다만 한국어 문장 흐름을 위해 분리하거나 합치는 것은 허용합니다.\n\n"

        "출력 규칙:\n"
        "- '스타워즈 고유명사:'로 시작하는 줄은 말투와 용어 판별에 사용한 뒤 최종 본문에서는 제외하세요.\n"
        "- '스타워즈 인물:'로 시작하는 줄은 말투와 용어 판별에 사용한 뒤 최종 본문에서는 제외하세요.\n"
        "- '관계도:'로 시작하는 줄은 말투와 용어 판별에 사용한 뒤 최종 본문에서는 제외하세요.\n"
        "- 영어 원문, 초벌 번역, 작업 과정, 설명, 메모, 분석, 제목을 출력하지 마세요.\n"
        "- 수정된 본문만 출력하세요.\n"
        "- 본문 끝에 용어 목록이나 주석을 붙이지 마세요.\n\n"

        f"{source_section}"
        "[DeepL 한국어 초벌 번역]\n"
        f"{translated_text}"
    )

    try:
        response = client.responses.create(
            model=REFINE_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )
        return strip_translation_metadata(response.output_text or translated_text)
    except Exception:
        return strip_translation_metadata(translated_text)


def translate_text(raw_text: str, starwars_mapping: dict[str, str] | None = None) -> str:
    deepl_api_key = os.getenv("DEEPL_API_KEY")
    if not deepl_api_key:
        raise RuntimeError(
            "DEEPL_API_KEY is not set. Add it to .env: DEEPL_API_KEY='your-api-key'"
        )

    translator = deepl.Translator(deepl_api_key)
    glossary = None

    try:
        if starwars_mapping:
            glossary = create_temporary_glossary(translator, choose_glossary_name(), starwars_mapping)
            translated = translator.translate_text_with_glossary(
                raw_text,
                glossary=glossary,
                target_lang="KO",
                preserve_formatting=True,
            ).text
        else:
            translated = translator.translate_text(
                raw_text,
                target_lang="KO",
                preserve_formatting=True,
            ).text
    except deepl.DeepLException as exc:
        raise RuntimeError(
            "DeepL translation failed. Check your DEEPL_API_KEY and network connection."
        ) from exc
    finally:
        if glossary is not None:
            try:
                delete_temporary_glossary(translator, glossary)
            except deepl.DeepLException:
                pass

    return translated


def save_image_from_upload(file: UploadFile) -> None:
    content = file.file.read()
    IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_PATH.write_bytes(content)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "Kindlelator OCR API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ocr", response_model=OcrResponse)
def run_ocr(image: UploadFile | None = File(None)) -> OcrResponse:
    if image is not None:
        save_image_from_upload(image)

    if not IMAGE_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {IMAGE_PATH}")

    try:
        text = extract_text_from_image(IMAGE_PATH)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    save_output(text, OUTPUT_PATH)
    return OcrResponse(text=text, output_path=str(OUTPUT_PATH))


@app.get("/starwars-terms", response_model=list[StarwarsTerm])
def get_starwars_terms() -> list[StarwarsTerm]:
    return list_starwars_terms()


@app.post("/starwars-term", response_model=StarwarsTerm)
def add_starwars_term(term: StarwarsTerm) -> StarwarsTerm:
    upsert_starwars_term(term.english, term.korean)
    return term


@app.delete("/starwars-term/{english}")
def remove_starwars_term(english: str) -> dict[str, str]:
    delete_starwars_term(english)
    return {"status": "deleted", "english": english}


@app.post("/translate", response_model=TranslateResponse)
def run_translate() -> TranslateResponse:
    try:
        raw_text = read_output(OUTPUT_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    starwars_mapping = build_starwars_mapping(raw_text)

    try:
        translated = translate_text(raw_text, starwars_mapping)
        refined_text = refine_translation_with_openai(translated, raw_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    save_output(refined_text, TRANSLATED_OUTPUT_PATH)
    return TranslateResponse(text=refined_text, output_path=str(TRANSLATED_OUTPUT_PATH))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "ocr":
        if not IMAGE_PATH.exists():
            raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")

        text = extract_text_from_image(IMAGE_PATH)
        save_output(text, OUTPUT_PATH)
        print(f"Saved OCR text to {OUTPUT_PATH}")
        return

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
