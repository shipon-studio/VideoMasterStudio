import customtkinter as ctk
import os
import ctypes

# --- 分割した新しいUI部品を読み込む ---
from ui_video_dl import VideoDLFrame
from ui_converter import ConverterFrame

class MainGUI(ctk.CTk):
    def __init__(self, config, engine):
        super().__init__()
        self.config = config
        self.engine = engine
        
        # --- 1. 基本設定 ---
        self.title("Video Master Studio") # ウィンドウタイトル
        self.geometry("1000x750") # 初期起動ウィンドウ
        self.minsize(750, 560) # ウィンドウ最小サイズ

        # 共通フォントを定義
        self.sys_font = ("Meiryo", 13)
        self.sys_font_bold = ("Meiryo", 14, "bold")

        # タスクバーアイコンの強制適用
        if os.name == 'nt':
            try:
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
                pass

        # 保存されたテーマを読み込んで適用
        saved_theme = self.config.settings.get("theme", "System")
        ctk.set_appearance_mode(saved_theme)

        # --- 2. レイアウト設定 (2列構成) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 3. サイドバーの作成 ---
        self.setup_sidebar()

        # --- 4. メインコンテンツエリア (フレーム) の組み立て ---
        # 分割したクラスをここで呼び出して画面を作る
        self.video_dl_frame = VideoDLFrame(self, self.config, self.engine, self.sys_font, self.sys_font_bold)
        self.conv_frame = ConverterFrame(self, self.config, self.engine, self.sys_font)

        # 初期表示
        self.show_video_dl_frame()

    # --- レイアウト組み立て用メソッド ---

    def setup_sidebar(self):
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0, width=160)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        
        self.label_nav = ctk.CTkLabel(self.navigation_frame, text="機能一覧", font=("Meiryo", 20, "bold"))
        self.label_nav.pack(pady=20, padx=10)

        self.btn_yt = ctk.CTkButton(self.navigation_frame, text="Web Media DL", font=self.sys_font_bold,
                                    fg_color="transparent", text_color=("gray10", "gray90"),
                                    hover_color=("gray70", "gray30"), anchor="w",
                                    command=self.show_video_dl_frame)
        self.btn_yt.pack(pady=5, padx=10, fill="x")

        self.btn_conv = ctk.CTkButton(self.navigation_frame, text="ファイル変換", font=self.sys_font_bold,
                                      fg_color="transparent", text_color=("gray10", "gray90"),
                                      hover_color=("gray70", "gray30"), anchor="w",
                                      command=self.show_convert_frame)
        self.btn_conv.pack(pady=5, padx=10, fill="x")

        self.spacer = ctk.CTkLabel(self.navigation_frame, text="")
        self.spacer.pack(expand=True, fill="both")

        self.btn_about = ctk.CTkButton(self.navigation_frame, text="このソフトについて", font=self.sys_font,
                                      fg_color="transparent", text_color=("gray10", "gray90"),
                                      hover_color=("gray70", "gray30"), anchor="w",
                                      command=self.show_about_window)
        self.btn_about.pack(pady=(5, 10), padx=10, fill="x")

        self.appearance_mode_label = ctk.CTkLabel(self.navigation_frame, text="テーマ設定:", font=self.sys_font, anchor="w")
        self.appearance_mode_label.pack(padx=20, pady=(0, 0), fill="x")
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.navigation_frame, 
            values=["システム", "ライト", "ダーク"],
            font=self.sys_font,
            dropdown_font=self.sys_font,
            command=self.change_appearance_mode_event,
            fg_color=("#e5e5e5", "#333333"),
            button_color=("#d9d9d9", "#2b2b2b"),
            button_hover_color=("#cccccc", "#444444"),
            text_color=("black", "white")
        )
        self.appearance_mode_menu.pack(padx=20, pady=(5, 20), fill="x")

        current_theme = self.config.settings.get("theme", "System")
        theme_to_jp = {"System": "システム", "Light": "ライト", "Dark": "ダーク"}
        self.appearance_mode_menu.set(theme_to_jp.get(current_theme, "システム"))

    def change_appearance_mode_event(self, new_appearance_mode: str):
        jp_to_theme = {"システム": "System", "ライト": "Light", "ダーク": "Dark"}
        internal_theme = jp_to_theme.get(new_appearance_mode, "System")
        ctk.set_appearance_mode(internal_theme)
        self.config.save_settings({"theme": internal_theme})

    def show_about_window(self):
        about_win = ctk.CTkToplevel(self)
        about_win.title("このソフトについて")
        about_win.geometry("550x500")
        about_win.transient(self)
        about_win.grab_set()

        title_label = ctk.CTkLabel(about_win, text="Video Master Studio", font=("Yu Gothic", 25, "bold"))
        title_label.pack(pady=(30, 5))
        
        version_label = ctk.CTkLabel(about_win, text="Version 1.1.0", font=("Yu Gothic", 17), text_color="gray")
        version_label.pack(pady=(0, 15))

        desc_text = (
            "【システム構成】\n"
            "・GUIフレームワーク: CustomTkinter\n"
            "・ダウンロードエンジン: yt-dlp\n"
            "・メディアプロセッサ: FFmpeg\n\n"
            "【主な機能】\n"
            "・Web動画・音声の安全な抽出と結合\n"
            "・ローカルメディアファイルの無劣化/再エンコード変換\n"
            "・既存ファイルの上書き・破損を防止する安全機構搭載\n"
        )
        desc_label = ctk.CTkLabel(about_win, text=desc_text, justify="left", font=("Yu Gothic", 15))
        desc_label.pack(pady=10, padx=20)

        copyright_text = (
            "Creator: Shipon Studio\n"
            "© 2026 VOICE PALLETE Studio. All rights reserved."
        )
        copyright_label = ctk.CTkLabel(about_win, text=copyright_text, font=("Yu Gothic", 15))
        copyright_label.pack(pady=(0, 15))
        
        close_btn = ctk.CTkButton(about_win, text="閉じる", font=self.sys_font_bold, command=about_win.destroy, width=120)
        close_btn.pack(pady=20)

    # --- 画面切り替え制御 ---

    def show_video_dl_frame(self):
        self.conv_frame.grid_forget()
        self.video_dl_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.btn_yt.configure(fg_color=("gray75", "gray25"))
        self.btn_conv.configure(fg_color="transparent")

    def show_convert_frame(self):
        self.video_dl_frame.grid_forget()
        self.conv_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.btn_conv.configure(fg_color=("gray75", "gray25"))
        self.btn_yt.configure(fg_color="transparent")