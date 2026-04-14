import os
import sys
import json

class AppConfig:
    def __init__(self):
        # 1. 実行ファイルの場所を基準にパスを解決 (設計図 ⑦)
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.ffmpeg_path = os.path.join(self.base_path, "ffmpeg.exe")
        self.config_file = os.path.join(self.base_path, "config.json")
        
        # デフォルト設定 (設計図 ⑤)
        self.settings = {
            "last_save_path": os.path.join(os.path.expanduser("~"), "Downloads"),
            "default_format": "mp4",
            "audio_bitrate": "192"
        }
        self.load_settings()

    def load_settings(self):
        """設定ファイルがあれば読み込む"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def save_settings(self, new_settings):
        """設定を保存する (設計図 ⑤)"""
        self.settings.update(new_settings)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

# テスト用
if __name__ == "__main__":
    config = AppConfig()
    print(f"Base Path: {config.base_path}")
    print(f"FFmpeg Path: {config.ffmpeg_path}")
    print(f"Current Settings: {config.settings}")