import customtkinter as ctk
import os
import threading
from tkinter import filedialog, messagebox

class ConverterFrame(ctk.CTkFrame):
    def __init__(self, master, config, engine, sys_font):
        super().__init__(master, fg_color="transparent")
        self.config = config
        self.engine = engine
        self.sys_font = sys_font
        
        self.setup_widgets()

    """ファイル変換画面：大きな選択ボタンと詳細設定"""
    def setup_widgets(self): 
        self.conv_title = ctk.CTkLabel(self, text="ファイル変換", font=("Meiryo", 28, "bold"))
        self.conv_title.pack(pady=(20, 10))

        # 巨大なファイル選択エリア (D&Dの代わり)
        self.drop_zone = ctk.CTkButton(
            self, # self re:
            text="ここをクリックしてファイルを選択", 
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

        self.file_entry = ctk.CTkEntry(self, placeholder_text="選択されたファイルパス", font=self.sys_font, state="disabled") # ← self に変更
        self.file_entry.pack(pady=5, padx=40, fill="x")

        # 設定エリア
        self.conv_settings_frame = ctk.CTkFrame(self) # self re:
        self.conv_settings_frame.pack(pady=10, padx=40, fill="x")

        # 変換形式
        ctk.CTkLabel(self.conv_settings_frame, text="変換後の形式:", font=self.sys_font).grid(row=0, column=0, padx=10, pady=10)
        self.target_combo = ctk.CTkComboBox(self.conv_settings_frame, values=[".mp4", ".avi", ".mkv", ".mov", ".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"], font=self.sys_font, dropdown_font=self.sys_font, state="readonly")
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
        self.conv_progress = ctk.CTkProgressBar(self) # self re:
        self.conv_progress.set(0)
        self.conv_progress.pack(pady=20, padx=40, fill="x")

        self.conv_start_btn = ctk.CTkButton(self, text="変換を実行する", height=60, font=("Meiryo", 18, "bold"), # self re:
                                            fg_color="#2c3e50", hover_color="#34495e",
                                            command=self.start_conversion)
        self.conv_start_btn.pack(pady=20, padx=40, fill="x")

    # ============================
    # ファイルコンバーター制御
    # ============================
    """変換元のファイルを選択する"""
    def select_input_file(self):
        file_path = filedialog.askopenfilename(title="変換するファイルを選択")
        if file_path:
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.file_entry.configure(state="disabled")

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