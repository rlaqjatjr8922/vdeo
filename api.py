import json
import secrets
import urllib.parse
import webbrowser
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests


# =========================
# 파일 기준 경로
# =========================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "all_lives.json"


# =========================
# 치지직 API 설정
# =========================

CLIENT_ID = os.getenv("CHZZK_CLIENT_ID", "28c39305-5584-4001-8454-a7ab6b6db036")
CLIENT_SECRET = os.getenv("CHZZK_CLIENT_SECRET", "")

REDIRECT_URI = "http://127.0.0.1:8765/callback"
MAX_PAGES = 10000


auth_result = {
    "code": None,
    "state": None,
}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        auth_result["code"] = qs.get("code", [None])[0]
        auth_result["state"] = qs.get("state", [None])[0]

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            "인증 완료. 창 닫고 프로그램으로 돌아가."
            .encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def delete_old_json():
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
        print("기존 JSON 삭제:", OUTPUT_FILE)
    else:
        print("기존 JSON 없음")


def save_lives(all_lives):
    all_lives.sort(
        key=lambda x: int(x.get("viewer", 0))
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            all_lives,
            f,
            ensure_ascii=False,
            indent=4
        )


def get_token():
    if not CLIENT_SECRET:
        print("CHZZK_CLIENT_SECRET 환경변수가 없음")
        print("PowerShell 예시: $env:CHZZK_CLIENT_SECRET=\"발급받은_시크릿\"")
        return None

    state = secrets.token_hex(8)

    server = HTTPServer(
        ("127.0.0.1", 8765),
        CallbackHandler
    )

    login_url = (
        "https://chzzk.naver.com/account-interlock?"
        + urllib.parse.urlencode({
            "clientId": CLIENT_ID,
            "redirectUri": REDIRECT_URI,
            "state": state,
        })
    )

    print("아래 링크 열기:")
    print(login_url)
    print()

    try:
        webbrowser.open(login_url)
    except:
        pass

    server.handle_request()
    server.server_close()

    if auth_result["state"] != state:
        print("state 불일치")
        return None

    if not auth_result["code"]:
        print("인증 code 없음")
        return None

    body = {
        "grantType": "authorization_code",
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "code": auth_result["code"],
        "state": state,
    }

    r = requests.post(
        "https://openapi.chzzk.naver.com/auth/v1/token",
        json=body,
        timeout=10
    )

    print("토큰 응답 코드:", r.status_code)

    try:
        data = r.json()
    except:
        print(r.text)
        return None

    if "content" not in data:
        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
        )
        return None

    return data["content"]["accessToken"]


def get_lives(access_token=None):
    delete_old_json()

    all_lives = []
    next_cursor = None

    headers = {
        "Client-Id": CLIENT_ID,
        "Client-Secret": CLIENT_SECRET,
        "Content-Type": "application/json",
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    for page_num in range(1, MAX_PAGES + 1):
        params = {
            "size": 20
        }

        if next_cursor:
            params["next"] = next_cursor

        r = requests.get(
            "https://openapi.chzzk.naver.com/open/v1/lives",
            headers=headers,
            params=params,
            timeout=10
        )

        print(
            "페이지:",
            page_num,
            "응답:",
            r.status_code
        )

        try:
            data = r.json()
        except:
            print(r.text)
            break

        if "content" not in data:
            print(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )
            )
            break

        content = data["content"]

        lives = content.get(
            "data",
            []
        )

        page = content.get(
            "page",
            {}
        )

        if not lives:
            break

        for live in lives:
            channel_id = live.get(
                "channelId",
                ""
            )

            all_lives.append({
                "title":
                    live.get(
                        "liveTitle",
                        ""
                    ),

                "channel":
                    live.get(
                        "channelName",
                        ""
                    ),

                "viewer":
                    live.get(
                        "concurrentUserCount",
                        0
                    ),

                "category":
                    live.get(
                        "liveCategoryValue",
                        ""
                    ),

                "channel_id":
                    channel_id,

                "url":
                    f"https://chzzk.naver.com/live/{channel_id}"
            })

        # 페이지마다 저장
        save_lives(all_lives)

        print(
            "현재 저장 개수:",
            len(all_lives)
        )

        next_cursor = page.get("next")

        if not next_cursor:
            break

    # 마지막 최종 저장
    save_lives(all_lives)

    print()
    print("=" * 50)
    print("저장 완료")
    print("방송 수:", len(all_lives))
    print("파일:", OUTPUT_FILE)
    print("=" * 50)

    return all_lives


token = get_token()

if not token:
    print("토큰 발급 실패")
else:
    get_lives(token)
