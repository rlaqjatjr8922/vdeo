import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


STEPS = [
    ("1. API로 방송 목록 가져오기", "api.py"),
    ("2. 조건 검색하기", "search.py"),
    ("3. 추천/방송창 열기", "opener.py"),
]


def run_step(title, filename):
    path = BASE_DIR / filename

    if not path.exists():
        print(f"파일 없음: {path}")
        return False

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    result = subprocess.run(
        [PYTHON, str(path)],
        cwd=str(BASE_DIR)
    )

    if result.returncode != 0:
        print()
        print(f"중단됨: {filename}")
        print(f"종료 코드: {result.returncode}")
        return False

    return True


def main():
    for title, filename in STEPS:
        ok = run_step(title, filename)

        if not ok:
            input("엔터 누르면 종료...")
            return

    print()
    print("전체 실행 완료")


if __name__ == "__main__":
    main()
