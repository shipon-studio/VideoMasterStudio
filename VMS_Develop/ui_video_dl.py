import customtkinter as ctk
import threading
import requests
from PIL import Image
from io import BytesIO
import re
import os
import uuid
from tkinter import filedialog, messagebox

class VideoDLFrame(ctk.CTkFrame):
    def __init__(self, master, config, engine, sys_font, sys_font_bold):
        super().__init__(master, fg_color="transparent")
        self.config = config
        self.engine = engine
        self.sys_font = sys_font
        self.sys_font_bold = sys_font_bold
        
        # 変数初期化
        self.current_resolutions = []
        self.current_title = ""
        
        # 画面パーツの組み立てを呼び出し
        self.setup_widgets()

    """Web Media DL 画面のパーツを作成"""
    def setup_widgets(self):
        
        # URL入力エリア (self.yt_frame ではなく self に配置)
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.pack(pady=20, padx=20, fill="x")

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="動画のURLを入力してください...", font=self.sys_font, height=40)
        self.url_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.paste_button = ctk.CTkButton(self.url_frame, text="貼り付け", font=self.sys_font_bold, command=self.paste_from_clipboard, width=60, height=40, fg_color="#555555")
        self.paste_button.pack(side="left", padx=5)

        self.analyze_button = ctk.CTkButton(self.url_frame, text="解析", font=self.sys_font_bold, command=self.start_analysis, width=100, height=40)
        self.analyze_button.pack(side="right", padx=10)

        # 動画情報表示エリア (self に配置！)
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(self.info_frame, text="URLを解析してください", font=("Meiryo", 16, "bold"))
        self.title_label.pack(pady=20)

        self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="[ 画像プレビュー ]", font=self.sys_font)
        self.thumbnail_label.pack(pady=5)

        # 設定エリア (self に配置)
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, padx=20, fill="x")

        self.mode_switch = ctk.CTkSegmentedButton(self.options_frame, values=["動画で保存", "音源で保存"], command=self.toggle_mode, font=self.sys_font)
        self.mode_switch.set("動画で保存")
        self.mode_switch.pack(pady=10)

        self.settings_subframe = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.settings_subframe.pack(pady=10)

        self.res_label = ctk.CTkLabel(self.settings_subframe, text="画質:", font=self.sys_font)
        self.res_label.grid(row=0, column=0, padx=5)
        self.res_combo = ctk.CTkComboBox(self.settings_subframe, values=["---"], font=self.sys_font, dropdown_font=self.sys_font)
        self.res_combo.grid(row=0, column=1, padx=5)
        self.res_combo.set("---") # 先にセットしてからブロック
        self.res_combo.configure(state="disabled")

        self.ext_label = ctk.CTkLabel(self.settings_subframe, text="形式:", font=self.sys_font)
        self.ext_label.grid(row=0, column=2, padx=5)
        self.ext_combo = ctk.CTkComboBox(self.settings_subframe, values=[".mp4", ".mkv", ".avi", ".mov", ".webm"], font=self.sys_font, dropdown_font=self.sys_font, state="readonly")
        self.ext_combo.grid(row=0, column=3, padx=5)
        self.ext_combo.set(".mp4") # 初期値をセット
        self.ext_combo.configure(command=self.on_ext_change)

        self.path_button = ctk.CTkButton(self.options_frame, text=f"保存先: {self.config.settings['last_save_path']}", 
                                         fg_color="gray", command=self.select_path, font=self.sys_font)
        self.path_button.pack(pady=10, padx=20, fill="x")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20, fill="x")

        self.dl_button = ctk.CTkButton(self, text="ダウンロード開始", state="disabled", height=50, command=self.start_download, font=self.sys_font_bold)
        self.dl_button.pack(pady=20)

    # ============================
    # Web Media DL 制御ロジック
    # ============================
    """動画/音声モードの切り替えによってUIパーツを変える"""
    def toggle_mode(self, value):
        if value == "動画で保存":
            self.res_label.configure(text="画質:")
            self.ext_combo.configure(values=[".mp4", ".mkv", ".avi", ".mov", ".webm"])
            self.ext_combo.set(".mp4")
            
            if self.current_resolutions:
                self.res_combo.configure(state="readonly", values=self.current_resolutions)
                self.res_combo.set(self.current_resolutions[0])
            else:
                self.res_combo.configure(state="readonly")
                self.res_combo.configure(values=["---"])
                self.res_combo.set("---")
                self.res_combo.configure(state="disabled")
        else:
            self.res_label.configure(text="ビットレート:")
            self.ext_combo.configure(values=[".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg"])
            self.ext_combo.set(".mp3")
            
            self.res_combo.configure(state="readonly", values=["128k", "192k", "256k", "320k"])
            self.res_combo.set("320k")

    """ファイル形式が変わったとき、最適なビットレートの選択肢を提示する"""
    def on_ext_change(self, value):
        if self.mode_switch.get() == "音源で保存":
            if value == ".wav":
                self.res_combo.configure(state="readonly", values=["1411k"])
                self.res_combo.set("1411k")
                self.res_combo.configure(state="disabled")
                
            elif value == ".flac":
                self.res_combo.configure(state="readonly", values=["Lossless"])
                self.res_combo.set("Lossless")
                self.res_combo.configure(state="disabled")
                
            elif value in [".m4a", ".aac"]:
                self.res_combo.configure(state="readonly", values=["128k", "192k", "256k", "320k"])
                self.res_combo.set("256k")
                
            else:
                self.res_combo.configure(state="readonly", values=["128k", "192k", "256k", "320k"])
                if self.res_combo.get() not in ["128k", "192k", "256k", "320k"]:
                    self.res_combo.set("192k")

    """保存フォルダを選択して記憶する"""
    def select_path(self):
        path = filedialog.askdirectory(initialdir=self.config.settings['last_save_path'])
        if path:
            self.config.save_settings({"last_save_path": path})
            self.path_button.configure(text=f"保存先: {path}")

    """解析を別スレッドで開始"""
    def start_analysis(self):
        url = self.url_entry.get()
        if not url: return
        self.analyze_button.configure(state="disabled", text="解析中...")
        threading.Thread(target=self.run_analysis, args=(url,), daemon=True).start()

    """解析の実行"""
    def run_analysis(self, url):
        info = self.engine.get_video_info(url)
        if "error" in info:
            self.after(0, lambda: messagebox.showerror("エラー", info["error"]))
            self.analyze_button.configure(state="normal", text="解析")
        else:
            self.title_label.configure(text=info["title"])
            self.current_title = info["title"]
            self.current_resolutions = info["resolutions"]

            if self.mode_switch.get() == "動画で保存":
                self.res_combo.configure(values=info["resolutions"], state="readonly")
                if info["resolutions"]:
                    self.res_combo.set(info["resolutions"][0])
                else:
                    # リストが空っぽだった場合の回避策
                    self.res_combo.configure(state="normal")
                    self.res_combo.configure(values=["自動 (最高画質)"])
                    self.res_combo.set("自動 (最高画質)")
                    self.res_combo.configure(state="readonly")

            if info.get("thumbnail"):
                try:
                    response = requests.get(info["thumbnail"])
                    img_data = Image.open(BytesIO(response.content))
                    img_data.thumbnail((320, 180))
                    ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(img_data.width, img_data.height))
                    self.thumbnail_label.configure(image=ctk_img, text="")
                except Exception:
                    self.thumbnail_label.configure(text="サムネイル取得失敗")

            self.analyze_button.configure(state="normal", text="解析完了")
            self.dl_button.configure(state="normal")

    """ダウンロードをスレッドで開始"""
    def start_download(self):
        url = self.url_entry.get()
        if not url: return messagebox.showwarning("警告", "URLを入力してください。")
        if not hasattr(self, 'current_title') or not self.current_title:
            return messagebox.showwarning("警告", "先に「解析」ボタンを押して動画情報を取得してください。")

        mode = "video" if self.mode_switch.get() == "動画で保存" else "audio"
        res = self.res_combo.get()
        ext = self.ext_combo.get().replace(".", "")

        # 自動を選んでいる場合はyt-dlp用に変換
        if res == "自動（最高画質）" or res == "---":
            actual_res = "best"
        else:
            actual_res = res

        save_path = self.config.settings['last_save_path']
        
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.current_title)
        final_title = safe_title
        expected_path = os.path.join(save_path, f"{final_title}.{ext}")
        
        if os.path.exists(expected_path):
            if messagebox.askyesno("確認", "同名のファイルが存在します。別名で保存しますか？"):
                counter = 1
                while os.path.exists(os.path.join(save_path, f"{safe_title} ({counter}).{ext}")):
                    counter += 1
                final_title = f"{safe_title} ({counter})"
                expected_path = os.path.join(save_path, f"{final_title}.{ext}")
            else:
                return 

        temp_id = str(uuid.uuid4())[:8] 
        temp_title = f"temp_{temp_id}_{final_title}"

        opts = {
            "mode": mode,
            "resolution": actual_res,
            "ext": ext,
            "bitrate": res.replace("k", ""),
            "save_path": save_path,
            "custom_title": temp_title,
            "final_path": expected_path
        }

        self.dl_button.configure(state="disabled", text="ダウンロード中...")
        self.progress_bar.set(0)
        threading.Thread(target=self.execute_download, args=(url, opts), daemon=True).start()

    """ダウンロードの実行"""
    def execute_download(self, url, opts):
        def update_progress(p):
            self.progress_bar.set(p / 100.0)

        success = self.engine.run_download(url, opts, update_progress)

        if success:
            save_path = opts['save_path']
            temp_title = opts['custom_title']
            final_path = opts['final_path']
            
            downloaded_file = None
            for file in os.listdir(save_path):
                if file.startswith(temp_title):
                    downloaded_file = os.path.join(save_path, file)
                    break
            
            if downloaded_file:
                try:
                    if os.path.exists(final_path): os.remove(final_path)
                    os.rename(downloaded_file, final_path)
                except Exception as e:
                    print(f"リネームエラー: {e}")
                    success = False

        def download_finished():
            self.dl_button.configure(state="normal", text="ダウンロード開始")
            self.progress_bar.set(0)
            if success:
                messagebox.showinfo("成功", f"ダウンロードが完了しました。\n\n保存先: {opts['final_path']}")
            else:
                messagebox.showerror("エラー", "ダウンロード中に問題が発生しました。")
                
        self.after(0, download_finished)

    """クリップボードのテキストを入力欄に貼り付ける"""
    def paste_from_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_text)
        except Exception:
            pass