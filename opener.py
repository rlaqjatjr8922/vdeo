import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

import psutil
import win32gui
import win32con
import win32process


# =========================
# 파일 기준 경로
# =========================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "search_result.json"
CHANNEL_SAVE_FILE = BASE_DIR / "saved_channels.json"

# 로그인 / 소리 / 사이트 설정 저장용 Edge 전용 프로필
EDGE_PROFILE_DIR = BASE_DIR / "edge_controller_profile"


# =========================
# Edge 설정
# =========================

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CONTROL_HEIGHT = 140


class EdgeController:
    def __init__(self):
        self.edge_path = self.find_edge()
        self.edge_hwnd = None

    def find_edge(self):
        for path in EDGE_PATHS:
            p = Path(path)

            if p.exists():
                return p

        return None

    def is_target_edge_process(self, pid):
        try:
            p = psutil.Process(pid)

            exe = p.exe().lower()
            cmdline = " ".join(p.cmdline()).lower()

            if "msedge.exe" not in exe:
                return False

            if str(EDGE_PROFILE_DIR.resolve()).lower() not in cmdline:
                return False

            return True

        except:
            return False

    def kill_edge(self):
        target = str(EDGE_PROFILE_DIR.resolve()).lower()
        targets = []

        for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                cmdline = " ".join(p.info.get("cmdline") or []).lower()

                if name == "msedge.exe" and target in cmdline:
                    targets.append(p)

            except:
                pass

        # 1차: 정상 종료 요청
        for p in targets:
            try:
                p.terminate()
            except:
                pass

        # 로그인/쿠키 저장 시간 주기
        try:
            gone, alive = psutil.wait_procs(
                targets,
                timeout=5
            )
        except:
            alive = []

        # 2차: 그래도 안 꺼진 것만 강제 종료
        for p in alive:
            try:
                p.kill()
            except:
                pass

        self.edge_hwnd = None
        time.sleep(0.5)

    def start_edge(self, url):
        if not self.edge_path:
            messagebox.showerror(
                "오류",
                "Microsoft Edge 경로를 못 찾음"
            )
            return False

        EDGE_PROFILE_DIR.mkdir(
            exist_ok=True
        )

        # 이전 방송창 종료
        self.kill_edge()

        subprocess.Popen([
            str(self.edge_path),

            # 이 폴더에 로그인/소리/사이트 설정 저장됨
            f"--user-data-dir={EDGE_PROFILE_DIR.resolve()}",

            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--disable-features=Translate",

            # 자동재생 소리 제한 완화
            "--autoplay-policy=no-user-gesture-required",

            # 앱창 모드 유지
            f"--app={url}",
        ])

        for _ in range(80):
            hwnd = self.find_edge_window()

            if hwnd:
                self.edge_hwnd = hwnd
                return True

            time.sleep(0.1)

        messagebox.showerror(
            "오류",
            "Edge 방송창을 못 찾음"
        )
        return False

    def find_edge_window(self):
        result = []

        def enum_handler(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return

            class_name = win32gui.GetClassName(hwnd)

            if class_name != "Chrome_WidgetWin_1":
                return

            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            if not self.is_target_edge_process(pid):
                return

            result.append(hwnd)

        win32gui.EnumWindows(enum_handler, None)

        if not result:
            return None

        return result[-1]

    def move_edge(self, x, y, width, height):
        if not self.edge_hwnd:
            self.edge_hwnd = self.find_edge_window()

        if not self.edge_hwnd:
            return

        try:
            win32gui.ShowWindow(
                self.edge_hwnd,
                win32con.SW_RESTORE
            )

            win32gui.MoveWindow(
                self.edge_hwnd,
                x,
                y,
                width,
                height,
                True
            )

        except:
            pass

    def focus_edge(self):
        if not self.edge_hwnd:
            self.edge_hwnd = self.find_edge_window()

        if not self.edge_hwnd:
            return

        try:
            win32gui.SetForegroundWindow(
                self.edge_hwnd
            )
        except:
            pass


class LiveController:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 방송 조작창")

        self.edge = EdgeController()

        self.lives = self.load_lives()
        self.index = 0

        if not self.lives:
            messagebox.showerror(
                "오류",
                f"search_result.json 없음 또는 비어있음\n{INPUT_FILE}"
            )
            self.root.destroy()
            return

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.edge_x = 0
        self.edge_y = 0
        self.edge_w = self.screen_w
        self.edge_h = self.screen_h - CONTROL_HEIGHT - 40

        self.control_x = 0
        self.control_y = self.edge_h
        self.control_w = self.screen_w
        self.control_h = CONTROL_HEIGHT

        self.create_ui()
        self.place_control_window()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.root.after(
            300,
            self.open_current_live
        )

    def load_lives(self):
        try:
            with open(
                INPUT_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            if isinstance(data, list):
                print("불러온 파일:", INPUT_FILE)
                print("방송 수:", len(data))
                return data

            print("search_result.json 내용이 리스트가 아님")
            return []

        except FileNotFoundError:
            print("search_result.json 없음:", INPUT_FILE)
            return []

        except json.JSONDecodeError:
            print("search_result.json JSON 오류:", INPUT_FILE)
            return []

    def load_saved_channels(self):
        try:
            with open(
                CHANNEL_SAVE_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            if isinstance(data, list):
                return data

            return []

        except FileNotFoundError:
            return []

        except json.JSONDecodeError:
            return []

    def save_saved_channels(self, channels):
        with open(
            CHANNEL_SAVE_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                channels,
                f,
                ensure_ascii=False,
                indent=4
            )

    def save_current_channel(self):
        live = self.get_current_live()

        channel = str(live.get("channel", "")).strip()
        url = str(live.get("url", "")).strip()
        title = live.get("title", "")
        viewer = live.get("viewer", 0)
        category = live.get("category", "")

        if not channel and not url:
            messagebox.showwarning(
                "오류",
                "저장할 채널 정보가 없음"
            )
            return

        channels = self.load_saved_channels()

        for item in channels:
            saved_channel = str(item.get("channel", "")).strip()
            saved_url = str(item.get("url", "")).strip()

            if channel and saved_channel == channel:
                messagebox.showinfo(
                    "이미 있음",
                    f"이미 저장된 채널임\n{channel}"
                )
                return

            if url and saved_url == url:
                messagebox.showinfo(
                    "이미 있음",
                    "이미 저장된 링크임"
                )
                return

        save_data = {
            "channel": channel,
            "url": url,
            "category": category,
            "title": title,
            "viewer": viewer,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        channels.append(save_data)

        self.save_saved_channels(channels)

        messagebox.showinfo(
            "저장 완료",
            f"채널 저장됨\n{channel}\n\n{CHANNEL_SAVE_FILE}"
        )

    def create_ui(self):
        self.root.geometry(
            f"{self.control_w}x{self.control_h}+{self.control_x}+{self.control_y}"
        )

        self.root.attributes(
            "-topmost",
            True
        )

        self.info_label = tk.Label(
            self.root,
            text="",
            font=("맑은 고딕", 13),
            anchor="w",
            justify="left"
        )
        self.info_label.pack(
            fill="x",
            padx=10,
            pady=6
        )

        button_frame = tk.Frame(self.root)
        button_frame.pack(
            fill="x",
            padx=10,
            pady=6
        )

        self.prev_button = tk.Button(
            button_frame,
            text="이전",
            font=("맑은 고딕", 14),
            command=self.prev_live
        )
        self.prev_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4
        )

        self.reload_button = tk.Button(
            button_frame,
            text="현재 방송 다시 열기",
            font=("맑은 고딕", 14),
            command=self.open_current_live
        )
        self.reload_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4
        )

        self.next_button = tk.Button(
            button_frame,
            text="다음",
            font=("맑은 고딕", 14),
            command=self.next_live
        )
        self.next_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4
        )

        self.copy_button = tk.Button(
            button_frame,
            text="링크 복사",
            font=("맑은 고딕", 14),
            command=self.copy_url
        )
        self.copy_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4
        )

        self.save_channel_button = tk.Button(
            button_frame,
            text="채널 저장",
            font=("맑은 고딕", 14),
            command=self.save_current_channel
        )
        self.save_channel_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4
        )

        self.jump_entry = tk.Entry(
            button_frame,
            font=("맑은 고딕", 14),
            width=8
        )
        self.jump_entry.pack(
            side="left",
            padx=4
        )

        self.jump_button = tk.Button(
            button_frame,
            text="이동",
            font=("맑은 고딕", 14),
            command=self.jump_live
        )
        self.jump_button.pack(
            side="left",
            padx=4
        )

        self.root.bind(
            "<Right>",
            lambda e: self.next_live()
        )

        self.root.bind(
            "<Left>",
            lambda e: self.prev_live()
        )

        self.root.bind(
            "<Return>",
            lambda e: self.jump_live()
        )

        self.root.bind(
            "s",
            lambda e: self.save_current_channel()
        )

    def place_control_window(self):
        self.root.geometry(
            f"{self.control_w}x{self.control_h}+{self.control_x}+{self.control_y}"
        )

    def get_current_live(self):
        return self.lives[self.index]

    def show_live_info(self):
        live = self.get_current_live()

        title = live.get("title", "")
        channel = live.get("channel", "")
        viewer = live.get("viewer", 0)
        category = live.get("category", "")

        text = (
            f"{self.index + 1} / {len(self.lives)} | "
            f"채널: {channel} | "
            f"시청자: {viewer} | "
            f"카테고리: {category}\n"
            f"제목: {title}"
        )

        self.info_label.config(text=text)

        self.prev_button.config(
            state="normal" if self.index > 0 else "disabled"
        )

        self.next_button.config(
            state="normal" if self.index < len(self.lives) - 1 else "disabled"
        )

    def open_current_live(self):
        live = self.get_current_live()
        url = live.get("url", "")

        if not url:
            messagebox.showwarning(
                "오류",
                "링크 없음"
            )
            return

        self.show_live_info()

        ok = self.edge.start_edge(url)

        if ok:
            self.edge.move_edge(
                self.edge_x,
                self.edge_y,
                self.edge_w,
                self.edge_h
            )

            self.place_control_window()

            self.root.lift()
            self.root.attributes(
                "-topmost",
                True
            )

    def next_live(self):
        if self.index >= len(self.lives) - 1:
            return

        self.index += 1
        self.open_current_live()

    def prev_live(self):
        if self.index <= 0:
            return

        self.index -= 1
        self.open_current_live()

    def copy_url(self):
        live = self.get_current_live()
        url = live.get("url", "")

        if not url:
            messagebox.showwarning(
                "오류",
                "링크 없음"
            )
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.root.update()

        messagebox.showinfo(
            "복사 완료",
            "링크 복사됨"
        )

    def jump_live(self):
        value = self.jump_entry.get().strip()

        if not value:
            return

        try:
            num = int(value)

        except ValueError:
            messagebox.showwarning(
                "오류",
                "숫자만 입력해"
            )
            return

        if num < 1 or num > len(self.lives):
            messagebox.showwarning(
                "오류",
                f"1부터 {len(self.lives)}까지만 가능"
            )
            return

        self.index = num - 1
        self.open_current_live()

    def on_close(self):
        self.edge.kill_edge()

        # 로그인/쿠키 저장 시간 조금 더 주기
        time.sleep(1)

        self.root.destroy()


def main():
    root = tk.Tk()
    LiveController(root)
    root.mainloop()


if __name__ == "__main__":
    main()
