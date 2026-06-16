import json
from pathlib import Path

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


# =========================
# 파일 위치 기준 경로
# =========================
BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "all_lives.json"
OUTPUT_FILE = BASE_DIR / "search_result.json"


FUZZY_LIMIT = 70


ALIASES = {
    "발로": [
        "발로",
        "발로란트",
        "valorant",
        "val",
    ],
    "발로란트": [
        "발로",
        "발로란트",
        "valorant",
        "val",
    ],
    "valorant": [
        "발로",
        "발로란트",
        "valorant",
        "val",
    ],
    "val": [
        "발로",
        "발로란트",
        "valorant",
        "val",
    ],

    "롤": [
        "롤",
        "리그오브레전드",
        "리그 오브 레전드",
        "league of legends",
        "lol",
    ],
    "lol": [
        "롤",
        "리그오브레전드",
        "리그 오브 레전드",
        "league of legends",
        "lol",
    ],
    "리그오브레전드": [
        "롤",
        "리그오브레전드",
        "리그 오브 레전드",
        "league of legends",
        "lol",
    ],
}


def load_lives():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        print(f"{INPUT_FILE} 없음")
        print("먼저 api.py 실행해서 방송 목록 저장해.")
        return []

    except json.JSONDecodeError:
        print(f"{INPUT_FILE} 파일 JSON 형식이 이상함")
        return []


def input_number(text):
    value = input(text).strip()

    if value == "":
        return None

    try:
        return int(value)

    except ValueError:
        print("숫자만 입력해야 함")
        return input_number(text)


def make_search_keywords(keyword):
    keyword = keyword.strip().lower()

    if not keyword:
        return []

    if keyword in ALIASES:
        return [
            k.lower()
            for k in ALIASES[keyword]
        ]

    return [keyword]


def normal_match(search_keywords, text):
    for keyword in search_keywords:
        if keyword in text:
            return True

    return False


def fuzzy_match(search_keywords, text):
    if fuzz is None:
        return False

    for keyword in search_keywords:
        score = fuzz.partial_ratio(
            keyword,
            text
        )

        if score >= FUZZY_LIMIT:
            return True

    return False


def is_keyword_match(search_keywords, title, channel, category):
    text = f"{title} {channel} {category}"

    if normal_match(search_keywords, text):
        return True

    if fuzzy_match(search_keywords, text):
        return True

    return False


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


def search_lives(lives):
    keyword = input(
        "검색어(제목/채널/카테고리, 엔터=전체): "
    ).strip().lower()

    min_viewer = input_number(
        "최소 시청자 수(엔터=제한 없음): "
    )

    max_viewer = input_number(
        "최대 시청자 수(엔터=제한 없음): "
    )

    search_keywords = make_search_keywords(keyword)

    results = []

    for live in lives:
        title = str(
            live.get("title", "")
        ).lower()

        channel = str(
            live.get("channel", "")
        ).lower()

        category = str(
            live.get("category", "")
        ).lower()

        viewer = safe_int(
            live.get("viewer", 0)
        )

        if search_keywords:
            if not is_keyword_match(
                search_keywords,
                title,
                channel,
                category
            ):
                continue

        if min_viewer is not None:
            if viewer < min_viewer:
                continue

        if max_viewer is not None:
            if viewer > max_viewer:
                continue

        results.append(live)

    results.sort(
        key=lambda x: safe_int(
            x.get("viewer", 0)
        )
    )

    return results


def save_results(results):
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=4
        )


def print_results(results, limit=50):
    print()
    print("=" * 50)
    print("검색 결과:", len(results), "개")
    print("저장 파일:", OUTPUT_FILE)
    print("=" * 50)

    for live in results[:limit]:
        print()
        print("-" * 50)
        print("제목:", live.get("title", ""))
        print("채널:", live.get("channel", ""))
        print("시청자:", live.get("viewer", 0))
        print("카테고리:", live.get("category", ""))
        print("링크:", live.get("url", ""))

    if len(results) > limit:
        print()
        print(f"... {len(results) - limit}개 더 있음")


def main():
    if fuzz is None:
        print("rapidfuzz 없음")
        print("오타 검색은 꺼짐")
        print("설치 명령어: pip install rapidfuzz")
        print()

    lives = load_lives()

    if not lives:
        return

    results = search_lives(lives)

    save_results(results)

    print_results(results)


if __name__ == "__main__":
    main()
