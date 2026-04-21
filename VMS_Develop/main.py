import sys
import tkinter as tk
from tkinter import messagebox
from base_logic import AppConfig
from downloader_logic import YTDLPEngine
from app_ui import MainGUI

def startup_check(engine):
    """起動時のアップデートチェック"""
    print("エンジンの更新を確認しています...")
    
    # 実際にはここでバージョン比較を行いますが、
    # 簡易的に yt-dlp -U を実行し、更新があったかメッセージで判断する例です
    update_msg = engine.check_update()
    
    # 標準的なメッセージボックスを出すために一時的に小さな隠しウィンドウを作成
    root = tk.Tk()
    root.withdraw() # ウィンドウ自体は非表示
    
    if "is up to date" in update_msg:
        print("yt-dlp は最新の状態です。")
    else:
        # 更新が完了またはエラーが起きた場合に通知
        messagebox.showinfo("システム更新", f"エンジンの更新状況:\n{update_msg}")
    
    root.destroy()

def main():
    # 1. 基本設定のロード
    config = AppConfig()
    
    # 2. ダウンロードエンジンの初期化
    engine = YTDLPEngine(config)

    # 3. 起動時のチェック
    startup_check(engine)

    # 4. メインGUIの起動
    app = MainGUI(config, engine)
    
    # 最後に保存先を記憶して終了するなどの後処理が必要ならここで行う
    app.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 万が一のクラッシュ時にエラーを表示
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fatal Error", f"アプリの起動に失敗しました:\n{e}")