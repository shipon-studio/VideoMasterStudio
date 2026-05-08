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

        self.paste_button = ctk.CTkButton(self.url_frame, 
                                          text="貼り付け", 
                                          font=self.sys_font_bold, 
                                          command=self.paste_from_clipboard, 
                                          width=60, height=40, 
                                          fg_color="#555555")
        self.paste_button.pack(side="left", padx=5)

        self.analyze_button = ctk.CTkButton(self.url_frame, 
                                            text="解析", 
                                            font=self.sys_font_bold, 
                                            command=self.start_analysis, 
                                            width=100, height=40)
        self.analyze_button.pack(side="right", padx=10)

        # 動画情報表示エリア (self に配置)
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(self.info_frame, text="URLを解析してください", font=("Meiryo", 16, "bold"))
        self.title_label.pack(pady=20)

        self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="[ 画像プレビュー ]", font=self.sys_font)
        self.thumbnail_label.pack(pady=5)

        # 設定エリア (self に配置)
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=5, padx=20, fill="x")

        # セグメントボタン
        self.mode_switch = ctk.CTkSegmentedButton(self.options_frame, 
                                                  values=["動画で保存", "音源で保存"], 
                                                  command=self.toggle_mode, 
                                                  font=self.sys_font)
        self.mode_switch.set("動画で保存")
        self.mode_switch.pack(pady=(10, 5))

        # self設定の派生形
        self.settings_subframe = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.settings_subframe.pack(pady=5)

        # 画質に関するプルタブ
        self.res_label = ctk.CTkLabel(self.settings_subframe, text="画質:", font=self.sys_font)
        self.res_label.grid(row=0, column=0, padx=5)
        self.res_combo = ctk.CTkComboBox(self.settings_subframe, values=["---"], font=self.sys_font, dropdown_font=self.sys_font)
        self.res_combo.grid(row=0, column=1, padx=5)
        self.res_combo.set("---") # 先にセットしてからブロック
        self.res_combo.configure(state="disabled")

        # 拡張子（フォーマット）に関するプルタブ
        self.ext_label = ctk.CTkLabel(self.settings_subframe, text="形式:", font=self.sys_font)
        self.ext_label.grid(row=0, column=2, padx=5)
        self.ext_combo = ctk.CTkComboBox(self.settings_subframe, 
                                         values=[".mp4", ".mkv", ".avi", ".mov", ".webm"], 
                                         font=self.sys_font, 
                                         dropdown_font=self.sys_font, 
                                         state="readonly")
        self.ext_combo.grid(row=0, column=3, padx=5)
        self.ext_combo.set(".mp4") # 初期値をセット
        self.ext_combo.configure(command=self.on_ext_change)

        # 範囲設定のボタン
        self.range_switch = ctk.CTkSwitch(self.options_frame, text="範囲指定：無効", state="disabled", font=self.sys_font)
        self.range_switch.pack(pady=5)
        self.range_switch.configure(command=self.range_check)

        # スライダー用の配置
        self.up_slider_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.up_slider_frame.pack(padx=20, pady=5, fill="x")
        self.dw_slider_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.dw_slider_frame.pack(padx=20, pady=5, fill="x")

        # スライダーと範囲の入力ボックス
        # 開始地点のスライダーと入力ボックス
        self.range_s_label = ctk.CTkLabel(self.up_slider_frame, 
                                          text="開始地点", 
                                          font=self.sys_font, 
                                          text_color="gray")
        self.range_s_label.pack(side="left", padx=(0, 10))
        self.range_s_slider = ctk.CTkSlider(self.up_slider_frame,
                                            from_=0, to=1, 
                                            state="disabled", 
                                            button_color="gray", 
                                            progress_color="gray")
        self.range_s_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.range_s_slider.set(0)
        self.range_s_combo = ctk.CTkEntry(self.up_slider_frame, 
                                          placeholder_text="00:00:00", 
                                          width=80, 
                                          justify="center",
                                          state="disabled",
                                          text_color="gray")
        self.range_s_combo.pack(side="right")
        
        # 終了地点のスライダーと入力ボックス
        self.range_f_label = ctk.CTkLabel(self.dw_slider_frame, 
                                          text="終了地点", 
                                          font=self.sys_font, 
                                          text_color="gray")
        self.range_f_label.pack(side="left", padx=(0, 10))
        self.range_f_slider = ctk.CTkSlider(self.dw_slider_frame, 
                                            from_=0, to=1, 
                                            state="disabled", 
                                            button_color="gray", 
                                            progress_color="gray")
        self.range_f_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.range_f_slider.set(0)
        self.range_f_combo = ctk.CTkEntry(self.dw_slider_frame, 
                                          placeholder_text="00:00:00", 
                                          width=80, 
                                          justify="center", 
                                          state="disabled",
                                          text_color="gray")
        self.range_f_combo.pack(side="right")

        # スライダー作成時に command を指定
        self.range_s_slider.configure(command=self.on_s_slider_move)
        self.range_f_slider.configure(command=self.on_f_slider_move)

        # 入力欄作成時に Enterキーイベントをバインド
        self.range_s_combo.bind("<Return>", self.on_s_entry_return)
        self.range_f_combo.bind("<Return>", self.on_f_entry_return)

        self.path_button = ctk.CTkButton(self.options_frame, text=f"保存先: {self.config.settings['last_save_path']}", 
                                         fg_color="gray", command=self.select_path, font=self.sys_font)
        self.path_button.pack(pady=10, padx=20, fill="x")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20, fill="x")

        self.dl_button = ctk.CTkButton(self, 
                                       text="ダウンロード開始", 
                                       state="disabled", 
                                       height=50, 
                                       command=self.start_download, 
                                       font=self.sys_font_bold)
        self.dl_button.pack(pady=10)

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

    """範囲指定が無効/有効状態を確認する"""
    def range_check(self):
        new_state = "normal" if self.range_switch.get() else "disabled"
        
        # 状態に応じた色を定義（タプルでライトモード/ダークモード両対応）
        if new_state == "normal":
            self.range_switch.configure(text="範囲設定：有効")
            label_color = ("black", "white")              # デフォルトの文字色
            slider_btn_color = ("#3B8ED0", "#1F6AA5") # デフォルトのスライダーツマミの青
            slider_prg_color = ("#3A7EBF", "#1F538D") # デフォルトのゲージの青
        else:
            self.range_switch.configure(text="範囲設定：無効")
            label_color = "gray"
            slider_btn_color = "gray"
            slider_prg_color = "gray"

        # 1. ラベルの色を更新
        self.range_s_label.configure(text_color=label_color)
        self.range_f_label.configure(text_color=label_color)

        # 2. スライダーの状態と色を更新
        self.range_s_slider.configure(state=new_state, button_color=slider_btn_color, progress_color=slider_prg_color)
        self.range_f_slider.configure(state=new_state, button_color=slider_btn_color, progress_color=slider_prg_color)

        # 3. ボックスの状態と色を更新
        self.range_s_combo.configure(state=new_state, text_color=label_color)
        self.range_f_combo.configure(state=new_state, text_color=label_color)

    """範囲指定スライダーの設定"""
    # 開始スライダーを動かした時の処理
    def on_s_slider_move(self, value):
        # 秒数を 00:00:00 形式に変換して入力欄に表示
        self.range_s_combo.configure(state="normal")
        self.range_s_combo.delete(0, "end")
        self.range_s_combo.insert(0, self.format_time(value))

    # 終了スライダーを動かしたときの処理
    def on_f_slider_move(self, value):
        self.range_f_combo.configure(state="normal")
        self.range_f_combo.delete(0, "end")
        self.range_f_combo.insert(0, self.format_time(value))

    # 入力欄でエンターキーを押した時の処理
    # 開始時間の入力
    def on_s_entry_return(self, event):
        # 入力された文字列を秒数に変換してスライダーを移動
        seconds = self.parse_time(self.range_s_combo.get())
        self.range_s_slider.set(seconds)

    # 終了時間の入力
    def on_f_entry_return(self, event):
        seconds = self.parse_time(self.range_f_combo.get())
        self.range_f_slider.set(seconds)

    """範囲指定スライダーの限界設定"""
    def on_s_slider_move(self, value):
        start_sec = int(value)
        end_sec = int(self.range_f_slider.get())
        
        # 開始が終了を越えようとしたら終了の場所でブロックする
        if start_sec > end_sec:
            start_sec = end_sec
            self.range_s_slider.set(start_sec) # スライダーのツマミを強制的に押し戻す
            
        # 自身の入力欄を更新
        self.range_s_combo.configure(state="normal")
        self.range_s_combo.delete(0, "end")
        self.range_s_combo.insert(0, self.format_time(start_sec))

    def on_f_slider_move(self, value):
        end_sec = int(value)
        start_sec = int(self.range_s_slider.get())
        
        # 終了が開始を越えようとしたら開始の場所でブロックする
        if end_sec < start_sec:
            end_sec = start_sec
            self.range_f_slider.set(end_sec) # スライダーのツマミを強制的に押し戻す
            
        # 自身の入力欄を更新
        self.range_f_combo.configure(state="normal")
        self.range_f_combo.delete(0, "end")
        self.range_f_combo.insert(0, self.format_time(end_sec))

    """範囲指定ボックスの限界設定"""
    def on_s_entry_return(self, event):
        start_sec = self.parse_time(self.range_s_combo.get())
        end_sec = int(self.range_f_slider.get())
        
        # 終了地点より後の時間を入力されたら終了地点の時間に合わせる
        if start_sec > end_sec:
            start_sec = end_sec

        # スライダーの位置を更新し、入力欄を上書き
        self.range_s_slider.set(start_sec)
        self.range_s_combo.configure(state="normal")
        self.range_s_combo.delete(0, "end")
        self.range_s_combo.insert(0, self.format_time(start_sec))

    def on_f_entry_return(self, event):
        end_sec = self.parse_time(self.range_f_combo.get())
        start_sec = int(self.range_s_slider.get())
        max_duration = getattr(self, 'current_duration', 1)

        # 動画の長さを超えたら動画の最後に合わせる
        if end_sec > max_duration:
            end_sec = max_duration
            
        # 開始地点より前の時間を入力されたら開始地点の時間に合わせる
        if end_sec < start_sec:
            end_sec = start_sec

        # スライダーの位置を更新し、入力欄を上書き
        self.range_f_slider.set(end_sec)
        self.range_f_combo.configure(state="normal")
        self.range_f_combo.delete(0, "end")
        self.range_f_combo.insert(0, self.format_time(end_sec))

    """秒数を時間文字列に変換する"""
    def format_time(self, seconds):
        seconds = int(seconds) # 整数で計算
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}" # 1時間以上なら 01:23:45
        else:
            return f"{m:02d}:{s:02d}" # 1時間未満なら 12:34
            
    """時間文字列を秒数に変換する"""
    def parse_time(self, time_str):
        try:
            parts = time_str.split(":")
            if len(parts) == 3: # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2: # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            else:
                return int(parts[0]) # SS
        except Exception:
            return 0 # エラー時は0秒に設定

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

            duration = info.get("duration", 0)
            self.current_duration = duration # 手入力の制限用に保存
            
            if duration > 0:
                # スライダーの最大値を動画の長さに更新
                self.range_s_slider.configure(to=duration, number_of_steps=duration)
                self.range_f_slider.configure(to=duration, number_of_steps=duration)
                
                # 初期位置をセット（開始は0、終了は動画の最後）
                self.range_s_slider.set(0)
                self.range_f_slider.set(duration)
                
                # テキストボックスの表記を更新（一時的にnormalにして書き換え、すぐdisabledに戻す）
                self.range_s_combo.configure(state="normal")
                self.range_s_combo.delete(0, "end")
                self.range_s_combo.insert(0, self.format_time(0))
                self.range_s_combo.configure(state="disabled")

                self.range_f_combo.configure(state="normal")
                self.range_f_combo.delete(0, "end")
                self.range_f_combo.insert(0, self.format_time(duration))
                self.range_f_combo.configure(state="disabled")

            else:
                self.range_s_slider.configure(to=1)
                self.range_f_slider.configure(to=1)
                
                # 取得不可であることを表示
                self.range_switch.configure(state="disabled", text="範囲指定：取得不可 (非対応サイト)")

            # 解析が終わり次第、範囲指定スイッチの封印を解く
            self.range_switch.configure(state="normal")

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
        if "自動" in res or res == "---":
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

        start_sec = None
        end_sec = None

        if self.range_switch.get():
            start_sec = int(self.range_s_slider.get())
            end_sec = int(self.range_f_slider.get())

        opts = {
            "mode": mode,
            "resolution": actual_res,
            "ext": ext,
            "bitrate": res.replace("k", ""),
            "save_path": save_path,
            "custom_title": temp_title,
            "final_path": expected_path,
            "start_time": start_sec,
            "end_time": end_sec
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