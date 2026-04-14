import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from PIL import Image
import requests
from io import BytesIO
import re
import os
import uuid
import ctypes

class MainGUI(ctk.CTk):
    def __init__(self, config, engine):
        super().__init__()
        self.config = config
        self.engine = engine
        
        # --- 1. 基本設定 ---
        self.title("Video Master Studio") # ウィンドウタイトル
        self.geometry("1000x750") # 初期起動ウィンドウ

        # 共通フォントを定義
        self.sys_font = ("Meiryo", 13)
        self.sys_font_bold = ("Meiryo", 14, "bold")

        # タスクバーアイコンの強制適用
        if os.name == 'nt': # Windowsの場合のみ実行
            try:
                # OSに独立したアプリであることを認識させるID（好きな英数字でOK）
                myappid = 'shiponstudio.videomasterstudio.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # ウィンドウのアイコン設定
        icon_path = os.path.join(self.config.base_path, "Video_Master_Studio.ico")
        if os.path.exists(icon_path):
            try:
                self.wm_iconbitmap(icon_path)
            except Exception:
                pass # 万が一読み込めなくてもエラーで落ちないようにする

        # 保存されたテーマ（なければSystem）を読み込んで適用
        saved_theme = self.config.settings.get("theme", "System")
        ctk.set_appearance_mode(saved_theme)

        # 変数初期化
        self.current_resolutions = []
        self.current_title = ""

        # --- 2. レイアウト設定 (2列構成) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 3. サイドバーの作成 ---
        self.setup_sidebar()

        # --- 4. メインコンテンツエリア (フレーム) の作成 ---
        # YouTube DL 用フレーム
        self.yt_frame = ctk.CTkFrame(self, fg_color="transparent")
        # ファイル変換用フレーム
        self.conv_frame = ctk.CTkFrame(self, fg_color="transparent")

        # 各フレームの中身を組み立てる
        self.setup_yt_widgets()
        self.setup_conv_widgets()

        # 初期表示
        self.show_yt_frame()

    # --- レイアウト組み立て用メソッド ---

    """左側のメニューを作成"""
    def setup_sidebar(self):
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0, width=160)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        
        self.label_nav = ctk.CTkLabel(self.navigation_frame, text="機能一覧", font=("Meiryo", 20, "bold"))
        self.label_nav.pack(pady=20, padx=10)

        self.btn_yt = ctk.CTkButton(self.navigation_frame, text="YouTube DL", font=self.sys_font_bold,
                                    fg_color="transparent", text_color=("gray10", "gray90"),
                                    hover_color=("gray70", "gray30"), anchor="w",
                                    command=self.show_yt_frame)
        self.btn_yt.pack(pady=5, padx=10, fill="x")

        self.btn_conv = ctk.CTkButton(self.navigation_frame, text="ファイル変換", font=self.sys_font_bold,
                                      fg_color="transparent", text_color=("gray10", "gray90"),
                                      hover_color=("gray70", "gray30"), anchor="w",
                                      command=self.show_convert_frame)
        self.btn_conv.pack(pady=5, padx=10, fill="x")

        # 下部にウィジェットを押しやるためのスペーサー
        self.spacer = ctk.CTkLabel(self.navigation_frame, text="")
        self.spacer.pack(expand=True, fill="both")

        # 情報（このソフトについて）ボタン
        self.btn_about = ctk.CTkButton(self.navigation_frame, text="このソフトについて", font=self.sys_font,
                                      fg_color="transparent", text_color=("gray10", "gray90"),
                                      hover_color=("gray70", "gray30"), anchor="w",
                                      command=self.show_about_window)
        self.btn_about.pack(pady=(5, 10), padx=10, fill="x")

        # テーマ設定プルダウン
        self.appearance_mode_label = ctk.CTkLabel(self.navigation_frame, text="テーマ設定:", font=self.sys_font, anchor="w")
        self.appearance_mode_label.pack(padx=20, pady=(0, 0), fill="x")
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.navigation_frame, 
            values=["システム", "ライト", "ダーク"],
            font=self.sys_font,
            dropdown_font=self.sys_font,
            command=self.change_appearance_mode_event,
            # --- ここから色指定の引数を追加 ---
            fg_color=("#e5e5e5", "#333333"),         # ボックスの基本色 (ライトモード時, ダークモード時)
            button_color=("#d9d9d9", "#2b2b2b"),     # 右側の矢印部分の色
            button_hover_color=("#cccccc", "#444444"), # マウスオーバー時の色
            text_color=("black", "white")            # 文字色
        )
        self.appearance_mode_menu.pack(padx=20, pady=(5, 20), fill="x")

        current_theme = self.config.settings.get("theme", "System")
        theme_to_jp = {"System": "システム", "Light": "ライト", "Dark": "ダーク"}
        self.appearance_mode_menu.set(theme_to_jp.get(current_theme, "システム"))

    """テーマ（Light/Dark/System）を変更し、設定を保存する"""
    def change_appearance_mode_event(self, new_appearance_mode: str):
        # プルダウンの日本語を、CustomTkinterが認識する英語に変換
        jp_to_theme = {"システム": "System", "ライト": "Light", "ダーク": "Dark"}
        internal_theme = jp_to_theme.get(new_appearance_mode, "System")
        
        ctk.set_appearance_mode(internal_theme)
        # 変更したテーマ（英語）を config.json に保存
        self.config.save_settings({"theme": internal_theme})

    """ソフトウェア仕様を表示する専用のポップアップウィンドウ（CTkToplevel）"""
    def show_about_window(self):
        about_win = ctk.CTkToplevel(self)
        about_win.title("このソフトについて")
        about_win.geometry("550x500")
        
        # 親ウィンドウの中心付近に表示し、フォーカスを当てる（後ろを操作できないようにする）
        about_win.transient(self)
        about_win.grab_set()

        # タイトルとバージョン
        title_label = ctk.CTkLabel(about_win, text="Video Master Studio", font=("Yu Gothic", 25, "bold"))
        title_label.pack(pady=(30, 5))
        
        version_label = ctk.CTkLabel(about_win, text="Version 1.0.1", font=("Yu Gothic", 17), text_color="gray")
        version_label.pack(pady=(0, 15))

        # ソフトウェアの仕様説明
        desc_text = (
            "【システム構成】\n"
            "・GUIフレームワーク: CustomTkinter\n"
            "・ダウンロードエンジン: yt-dlp\n"
            "・メディアプロセッサ: FFmpeg\n\n"
            "【主な機能】\n"
            "・YouTube動画・音声の安全な抽出と結合\n"
            "・ローカルメディアファイルの無劣化/再エンコード変換\n"
            "・既存ファイルの上書き・破損を防止する安全機構搭載\n"
            
        )
        desc_label = ctk.CTkLabel(about_win, text=desc_text, justify="left", font=("Yu Gothic", 15))
        desc_label.pack(pady=10, padx=20)

        # 権利者表示
        copyright_text = (
            "Creator: Shipon Studio\n"
            "© 2026 VOICE PALLETE Studio. All rights reserved."
        )
        copyright_label = ctk.CTkLabel(about_win, text=copyright_text, font=("Yu Gothic", 15))
        copyright_label.pack(pady=(0, 15))
        
        close_btn = ctk.CTkButton(about_win, text="閉じる", font=self.sys_font_bold, command=about_win.destroy, width=120)
        close_btn.pack(pady=20)

    """YouTube DL 画面のパーツを作成 (self.yt_frame の中に配置)"""
    def setup_yt_widgets(self):
        
        # URL入力エリア
        self.url_frame = ctk.CTkFrame(self.yt_frame)
        self.url_frame.pack(pady=20, padx=20, fill="x")

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="YouTubeのURLを入力してください...", font=self.sys_font, height=40)
        self.url_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.paste_button = ctk.CTkButton(self.url_frame, text="貼り付け", font=self.sys_font_bold, command=self.paste_from_clipboard, width=60, height=40, fg_color="#555555")
        self.paste_button.pack(side="left", padx=5)

        self.analyze_button = ctk.CTkButton(self.url_frame, text="解析", font=self.sys_font_bold, command=self.start_analysis, width=100, height=40)
        self.analyze_button.pack(side="right", padx=10)

        # 動画情報表示エリア
        self.info_frame = ctk.CTkFrame(self.yt_frame)
        self.info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(self.info_frame, text="URLを解析してください", font=("Meiryo", 16, "bold"))
        self.title_label.pack(pady=20)

        self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="[ 画像プレビュー ]", font=self.sys_font)
        self.thumbnail_label.pack(pady=5)

        # 設定エリア
        self.options_frame = ctk.CTkFrame(self.yt_frame)
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

        self.ext_label = ctk.CTkLabel(self.settings_subframe, text="形式:", font=self.sys_font)
        self.ext_label.grid(row=0, column=2, padx=5)
        self.ext_combo = ctk.CTkComboBox(self.settings_subframe, values=[".mp4", ".mkv", ".avi", ".mov", ".webm"], font=self.sys_font, dropdown_font=self.sys_font)
        self.ext_combo.grid(row=0, column=3, padx=5)
        self.ext_combo.configure(command=self.on_ext_change)

        self.path_button = ctk.CTkButton(self.options_frame, text=f"保存先: {self.config.settings['last_save_path']}", 
                                         fg_color="gray", command=self.select_path, font=self.sys_font)
        self.path_button.pack(pady=10, padx=20, fill="x")

        self.progress_bar = ctk.CTkProgressBar(self.yt_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20, fill="x")

        self.dl_button = ctk.CTkButton(self.yt_frame, text="ダウンロード開始", state="disabled", height=50, command=self.start_download, font=self.sys_font_bold)
        self.dl_button.pack(pady=20)

    """ファイル変換画面：大きな選択ボタンと詳細設定"""
    def setup_conv_widgets(self):
        self.conv_title = ctk.CTkLabel(self.conv_frame, text="ファイル変換", font=("Meiryo", 28, "bold"))
        self.conv_title.pack(pady=(20, 10))

        # 巨大なファイル選択エリア (D&Dの代わり)
        self.drop_zone = ctk.CTkButton(
            self.conv_frame, 
            text="ここをクリックしてファイルを選択", # \n\n(対応: MP4, AVI, MOV, WMV, MP3, etc...)
            font=("Meiryo", 16, "bold"),
            height=150,
            fg_color=("gray85", "gray20"),
            text_color=("gray10", "gray90"),
            border_width=2,
            border_color=("gray70", "gray40"),
            hover_color=("gray80", "gray30"),
            command=self.select_input_file
        )
        self.drop_zone.pack(pady=20, padx=40, fill="x")

        self.file_entry = ctk.CTkEntry(self.conv_frame, placeholder_text="選択されたファイルパス", font=self.sys_font, state="disabled")
        self.file_entry.pack(pady=5, padx=40, fill="x")

        # 設定エリア
        self.conv_settings_frame = ctk.CTkFrame(self.conv_frame)
        self.conv_settings_frame.pack(pady=10, padx=40, fill="x")

        # 変換形式
        ctk.CTkLabel(self.conv_settings_frame, text="変換後の形式:", font=self.sys_font).grid(row=0, column=0, padx=10, pady=10)
        self.target_combo = ctk.CTkComboBox(self.conv_settings_frame, values=[".mp4", ".avi", ".mkv", ".mov", ".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"], font=self.sys_font, dropdown_font=self.sys_font)
        self.target_combo.set("mp4")
        self.target_combo.grid(row=0, column=1, padx=10, pady=10)

        # 保存先
        self.conv_path_btn = ctk.CTkButton(
            self.conv_settings_frame, 
            text=f"保存先: {self.config.settings['last_save_path']}",
            font=self.sys_font,
            fg_color="gray",
            command=self.select_conv_save_path
        )
        self.conv_path_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        self.conv_settings_frame.grid_columnconfigure(2, weight=1)

        # 実行エリア
        self.conv_progress = ctk.CTkProgressBar(self.conv_frame)
        self.conv_progress.set(0)
        self.conv_progress.pack(pady=20, padx=40, fill="x")

        self.conv_start_btn = ctk.CTkButton(self.conv_frame, text="変換を実行する", height=60, font=("Meiryo", 18, "bold"),
                                            fg_color="#2c3e50", hover_color="#34495e",
                                            command=self.start_conversion)
        self.conv_start_btn.pack(pady=20, padx=40, fill="x")

    # --- 画面切り替え制御 ---

    """YouTube画面を表示"""
    def show_yt_frame(self):
        self.conv_frame.grid_forget()
        self.yt_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.btn_yt.configure(fg_color=("gray75", "gray25")) # 選択状態っぽく見せる
        self.btn_conv.configure(fg_color="transparent")

    """変換画面を表示"""
    def show_convert_frame(self):
        self.yt_frame.grid_forget()
        self.conv_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.btn_conv.configure(fg_color=("gray75", "gray25"))
        self.btn_yt.configure(fg_color="transparent")

    # --- 制御ロジック ---

    # ============================
    # YouTube DL制御
    # ============================
    """動画/音声モードの切り替えによってUIパーツを変える"""
    def toggle_mode(self, value):
        if value == "動画で保存":
            self.res_label.configure(text="画質:")
            self.ext_combo.configure(values=[".mp4", ".mkv", ".avi", ".mov", ".webm"])
            self.ext_combo.set(".mp4")
            
            # 解析済みのデータがあれば復元、なければ初期状態
            if self.current_resolutions:
                self.res_combo.configure(state="normal", values=self.current_resolutions)
                self.res_combo.set(self.current_resolutions[0])
            else:
                # 一度normalにしないと値のsetが効かないのを回避
                self.res_combo.configure(state="normal")
                self.res_combo.configure(values=["---"])
                self.res_combo.set("---")
                self.res_combo.configure(state="disabled")
        else:
            self.res_label.configure(text="ビットレート:")
            self.ext_combo.configure(values=[".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg"])
            self.ext_combo.set(".mp3")
            
            # デフォルトはmp3なのでビットレート選択可能にする
            self.res_combo.configure(state="normal", values=["128k", "192k", "256k", "320k"])
            self.res_combo.set("320k")

    """ファイル形式が変わったとき、最適なビットレートの選択肢を提示する"""
    def on_ext_change(self, value):
        if self.mode_switch.get() == "音源で保存":
            if value == ".wav":
                self.res_combo.configure(state="normal", values=["1411k"])
                self.res_combo.set("1411k")
                self.res_combo.configure(state="disabled") # WAVは固定
                
            elif value == ".flac":
                self.res_combo.configure(state="normal", values=["Lossless"])
                self.res_combo.set("Lossless")
                self.res_combo.configure(state="disabled") # FLACは可逆なので指定不要
                
            elif value in [".m4a", ".aac"]:
                # AAC系は256kが一つの基準なので、選択肢に入れる
                self.res_combo.configure(state="normal", values=["128k", "192k", "256k", "320k"])
                self.res_combo.set("256k")
                
            else:
                # MP3, OGGなどは320kを上限に選択
                self.res_combo.configure(state="normal", values=["128k", "192k", "256k", "320k"])
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
            # tkinterのmessageboxはメインスレッドで呼ぶのが安全なため
            self.after(0, lambda: messagebox.showerror("エラー", info["error"]))
            self.analyze_button.configure(state="normal", text="解析")
        else:
            # 1. タイトルの更新
            self.title_label.configure(text=info["title"])
            self.current_title = info["title"]
            self.current_resolutions = info["resolutions"]

            # 2. 動画モードなら画質リストを有効化してセット
            if self.mode_switch.get() == "動画で保存":
                self.res_combo.configure(values=info["resolutions"], state="normal")
                if info["resolutions"]:
                    self.res_combo.set(info["resolutions"][0])

            # 3. サムネイルの取得と表示 (Pillowを使用)
            if info.get("thumbnail"):
                try:
                    # 画像URLからデータをダウンロード
                    response = requests.get(info["thumbnail"])
                    img_data = Image.open(BytesIO(response.content))
                    # UIに合わせてリサイズ (16:9比率)
                    img_data.thumbnail((320, 180))
                    
                    # CustomTkinter用の画像オブジェクトに変換
                    ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(img_data.width, img_data.height))
                    
                    # ラベルに画像をセットし、テキストを消す
                    self.thumbnail_label.configure(image=ctk_img, text="")
                except Exception as e:
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

        # yt-dlpには絶対に既存ファイルと被らない名前（temp_ランダム文字_タイトル）で作業させる
        temp_id = str(uuid.uuid4())[:8] 
        temp_title = f"temp_{temp_id}_{final_title}"

        opts = {
            "mode": mode, "resolution": res, "ext": ext,
            "bitrate": res.replace("k", ""), "save_path": save_path,
            "custom_title": temp_title,  # yt-dlp には一時ファイル名を渡す
            "final_path": expected_path  # 最後にこの名前にリネームする
        }

        self.dl_button.configure(state="disabled", text="ダウンロード中...")
        self.progress_bar.set(0)
        threading.Thread(target=self.execute_download, args=(url, opts), daemon=True).start()

    """ダウンロードの実行"""
    def execute_download(self, url, opts):
        def update_progress(p):
            self.progress_bar.set(p / 100.0)

        success = self.engine.run_download(url, opts, update_progress)

        # ダウンロード成功後のリネーム処理
        if success:
            save_path = opts['save_path']
            temp_title = opts['custom_title']
            final_path = opts['final_path']
            
            # yt-dlp が拡張子を勝手に変えた場合（aac -> m4a等）に備えて、実際の出力ファイルを探す
            downloaded_file = None
            for file in os.listdir(save_path):
                if file.startswith(temp_title):
                    downloaded_file = os.path.join(save_path, file)
                    break
            
            # 見つけたファイルを、ユーザーが希望した名前・拡張子に確実にリネームする
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
            # OSのクリップボードからテキストを取得
            clipboard_text = self.clipboard_get()
            # 念のため現在の入力内容をクリア
            self.url_entry.delete(0, "end")
            # 取得したテキストを挿入
            self.url_entry.insert(0, clipboard_text)
        except Exception:
            # クリップボードが空だったり、画像がコピーされている場合は何もしない
            pass

    """変換元のファイルを選択する"""
    def select_input_file(self):
        file_path = filedialog.askopenfilename(title="変換するファイルを選択")
        if file_path:
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.file_entry.configure(state="disabled")

    # ============================
    # ファイルコンバーター制御
    # ============================
    """変換後の保存フォルダを選択"""
    def select_conv_save_path(self):
        path = filedialog.askdirectory(initialdir=self.config.settings['last_save_path'])
        if path:
            # YouTube側と共通の設定を更新
            self.config.save_settings({"last_save_path": path})
            self.conv_path_btn.configure(text=f"保存先: {path}")

    """変換処理をスレッドで開始"""
    def start_conversion(self):
        input_path = self.file_entry.get()
        if not input_path:
            messagebox.showwarning("警告", "ファイルを選択してください。")
            return
        
        # 1. ターゲット拡張子を取得
        target_ext = self.target_combo.get().replace(".", "").lower()
        
        # 2. 現在の拡張子を取得
        current_ext = os.path.splitext(input_path)[1].replace(".", "").lower()

        # 3. 同一形式ならここで強制終了
        if current_ext == target_ext:
            messagebox.showwarning("変換不要", f"このファイルはすでに .{target_ext} 形式です。")
            return

        # 4. 保存先とボタンの状態更新
        save_dir = self.config.settings['last_save_path']
        self.conv_start_btn.configure(state="disabled", text="変換中...")
        self.conv_progress.set(0)
        
        # 5. 引数を3つ渡して実行
        threading.Thread(
            target=self.execute_conversion,
            args=(input_path, target_ext, save_dir),
            daemon=True
        ).start()

    """別スレッドで変換を実行"""
    def execute_conversion(self, input_path, target_ext, save_dir):
        def update_p(p):
            # メインスレッドでプログレスバーを更新
            self.after(0, lambda: self.conv_progress.set(p / 100))

        # 引数を4つ（input, target, save_dir, update_p）すべて渡す
        success, out_path = self.engine.convert_file(input_path, target_ext, save_dir, update_p)
        
        def finished():
            self.conv_start_btn.configure(state="normal", text="変換を実行する")
            if success:
                messagebox.showinfo("成功", f"変換が完了しました。\n\n保存先: {out_path}")
            else:
                messagebox.showerror("エラー", "変換に失敗しました。")
            self.conv_progress.set(0)

        self.after(0, finished)