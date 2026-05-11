#!/usr/bin/env python3
"""
catsdkr1_tui_1_0_tkinter.py

catsdkr1-tui 1.0 tkinter

A tiny all-Tkinter LM Studio coding-agent style chat app.
Blue-on-black terminal vibe, but implemented entirely with Tkinter.

Requirements:
  - Python 3.10+
  - LM Studio running locally with OpenAI-compatible server enabled

Default endpoint:
  http://127.0.0.1:1234/v1/chat/completions

Environment variables:
  LM_STUDIO_URL      override endpoint
  LM_STUDIO_MODEL    override model name
"""

import json
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from urllib import request, error


APP_NAME = "catsdkr1-tui 1.0 tkinter"
DEFAULT_URL = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_MODEL = "local-model"

BG = "#000000"
PANEL = "#050914"
BLUE = "#2f8cff"
BLUE_DIM = "#1155aa"
TEXT = "#2f8cff"
MUTED = "#5f9fff"
ERROR = "#ff5c8a"


class CatsDKR1TUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x620")
        self.root.minsize(720, 480)
        self.root.configure(bg=BG)

        self.reply_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.is_loading = False

        self.url_var = tk.StringVar(value=os.getenv("LM_STUDIO_URL", DEFAULT_URL))
        self.model_var = tk.StringVar(value=os.getenv("LM_STUDIO_MODEL", DEFAULT_MODEL))
        self.status_var = tk.StringVar(value="READY :: LM Studio endpoint idle")

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill=tk.X, padx=10, pady=(10, 4))

        title = tk.Label(
            top,
            text="catsdkr1-tui 1.0 tkinter",
            fg=BLUE,
            bg=BG,
            font=("Menlo", 18, "bold"),
        )
        title.pack(side=tk.LEFT)

        subtitle = tk.Label(
            top,
            text="  DeepSeek-style local coding agent via LM Studio",
            fg=MUTED,
            bg=BG,
            font=("Menlo", 10),
        )
        subtitle.pack(side=tk.LEFT, padx=(8, 0))

        config = tk.LabelFrame(
            self.root,
            text="CONFIG",
            fg=BLUE,
            bg=BG,
            bd=1,
            relief=tk.GROOVE,
            labelanchor="nw",
            font=("Menlo", 10, "bold"),
        )
        config.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(config, text="LM_STUDIO_URL", fg=TEXT, bg=BG, font=("Menlo", 10)).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        url_entry = tk.Entry(config, textvariable=self.url_var, fg=TEXT, bg=PANEL, insertbackground=BLUE, relief=tk.FLAT, font=("Menlo", 10))
        url_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(config, text="MODEL", fg=TEXT, bg=BG, font=("Menlo", 10)).grid(row=0, column=2, sticky="w", padx=8, pady=6)
        model_entry = tk.Entry(config, textvariable=self.model_var, fg=TEXT, bg=PANEL, insertbackground=BLUE, relief=tk.FLAT, font=("Menlo", 10), width=22)
        model_entry.grid(row=0, column=3, sticky="ew", padx=8, pady=6)

        ping = tk.Button(config, text="TEST", command=self.test_connection, fg=TEXT, bg=BG, activeforeground=BG, activebackground=BLUE, relief=tk.GROOVE, font=("Menlo", 10, "bold"))
        ping.grid(row=0, column=4, padx=8, pady=6)

        config.columnconfigure(1, weight=1)

        chat_frame = tk.LabelFrame(
            self.root,
            text="AGENT LOG",
            fg=BLUE,
            bg=BG,
            bd=1,
            relief=tk.GROOVE,
            labelanchor="nw",
            font=("Menlo", 10, "bold"),
        )
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self.chat = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            fg=TEXT,
            bg=BG,
            insertbackground=BLUE,
            selectbackground=BLUE_DIM,
            relief=tk.FLAT,
            font=("Menlo", 11),
        )
        self.chat.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.chat.insert(tk.END, "catsdkr1 booted.\n")
        self.chat.insert(tk.END, "Start LM Studio server, load a model, then ask for code.\n\n")
        self.chat.configure(state=tk.DISABLED)

        input_frame = tk.Frame(self.root, bg=BG)
        input_frame.pack(fill=tk.X, padx=10, pady=4)

        self.prompt = tk.Text(
            input_frame,
            height=4,
            fg=TEXT,
            bg=PANEL,
            insertbackground=BLUE,
            selectbackground=BLUE_DIM,
            relief=tk.FLAT,
            font=("Menlo", 11),
        )
        self.prompt.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prompt.bind("<Control-Return>", lambda event: self.send_prompt())

        buttons = tk.Frame(input_frame, bg=BG)
        buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        self.send_button = tk.Button(
            buttons,
            text="SEND\nCTRL+ENTER",
            command=self.send_prompt,
            fg=TEXT,
            bg=BG,
            activeforeground=BG,
            activebackground=BLUE,
            relief=tk.GROOVE,
            width=14,
            font=("Menlo", 10, "bold"),
        )
        self.send_button.pack(fill=tk.BOTH, expand=True)

        clear = tk.Button(
            buttons,
            text="CLEAR",
            command=self.clear_chat,
            fg=TEXT,
            bg=BG,
            activeforeground=BG,
            activebackground=BLUE,
            relief=tk.GROOVE,
            width=14,
            font=("Menlo", 10, "bold"),
        )
        clear.pack(fill=tk.X, pady=(6, 0))

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg=BLUE,
            bg=BG,
            anchor="w",
            font=("Menlo", 10),
        )
        status.pack(fill=tk.X, padx=10, pady=(0, 8))

    def append(self, speaker: str, text: str, color: str = TEXT):
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{speaker}> ", ("speaker",))
        self.chat.insert(tk.END, text + "\n\n")
        self.chat.tag_config("speaker", foreground=BLUE, font=("Menlo", 11, "bold"))
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def clear_chat(self):
        self.chat.configure(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.insert(tk.END, "catsdkr1 log cleared.\n\n")
        self.chat.configure(state=tk.DISABLED)

    def test_connection(self):
        if self.is_loading:
            return
        self._start_worker("ping", "Say exactly: catsdkr1 online")

    def send_prompt(self):
        if self.is_loading:
            return

        user_text = self.prompt.get("1.0", tk.END).strip()
        if not user_text:
            messagebox.showinfo(APP_NAME, "Type a prompt first.")
            return

        self.prompt.delete("1.0", tk.END)
        self.append("YOU", user_text)
        self._start_worker("chat", user_text)

    def _start_worker(self, mode: str, user_text: str):
        self.is_loading = True
        self.send_button.configure(state=tk.DISABLED, text="LOADING...")
        self.status_var.set("LOADING :: waiting for LM Studio response")

        thread = threading.Thread(target=self._call_lm_studio, args=(mode, user_text), daemon=True)
        thread.start()

    def _call_lm_studio(self, mode: str, user_text: str):
        system_prompt = (
            "You are catsdkr1-tui 1.0 tkinter, a compact local coding agent. "
            "Be direct, practical, and code-focused. Prefer small working examples."
        )

        payload = {
            "model": self.model_var.get().strip() or DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.4,
            "stream": False,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = request.Request(
                self.url_var.get().strip() or DEFAULT_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with request.urlopen(req, timeout=90) as response:
                raw = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw)

            content = parsed["choices"][0]["message"]["content"]
            self.reply_queue.put(("ok", content.strip() or "(empty response)"))

        except error.URLError as exc:
            self.reply_queue.put(("err", f"Connection failed. Is LM Studio server running?\n\n{exc}"))
        except KeyError:
            self.reply_queue.put(("err", "LM Studio returned JSON, but not in OpenAI chat format."))
        except Exception as exc:
            self.reply_queue.put(("err", f"Failure:\n{type(exc).__name__}: {exc}"))

    def _poll_queue(self):
        try:
            status, text = self.reply_queue.get_nowait()
        except queue.Empty:
            self.root.after(80, self._poll_queue)
            return

        self.is_loading = False
        self.send_button.configure(state=tk.NORMAL, text="SEND\nCTRL+ENTER")

        if status == "ok":
            self.status_var.set("SUCCESS :: response received")
            self.append("CATSDKR1", text)
        else:
            self.status_var.set("FAILURE :: check endpoint/model/server")
            self.append("ERROR", text, ERROR)

        self.root.after(80, self._poll_queue)


def main():
    root = tk.Tk()
    app = CatsDKR1TUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
