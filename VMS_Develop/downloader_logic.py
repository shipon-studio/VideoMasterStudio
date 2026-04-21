import subprocess
import json
import re
import os
import threading

class YTDLPEngine:
    def __init__(self, config):
        self.config = config
        # base_logicで解決したパスを使用
        self.ytdlp_exe = os.path.join(self.config.base_path, "yt-dlp.exe")
        self.ffmpeg_exe = self.config.ffmpeg_path

    """yt-dlpのアップデートを実行"""
    def check_update(self):
        # 1. ファイルがあるかチェック（デッドロック回避用）
        if not os.path.exists(self.ytdlp_exe):
            return "エラー: yt-dlp.exe と ffmpeg.exe をアプリと同じフォルダに入れてください。"

        try:
            # 2. コマンドプロンプト画面のポップアップ防止
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW

            # -U オプションでアップデートを実行
            result = subprocess.run(
                [self.ytdlp_exe, "-U"], 
                capture_output=True, text=True, encoding='utf-8',
                creationflags=creationflags
            )
            return result.stdout
        except Exception as e:
            return f"アップデート確認エラー: {str(e)}"

    """URLを解析して画質リストやタイトルを返す"""
    def get_video_info(self, url):
        try:
            # 黒窓対策
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW

            # -j オプションで詳細情報をJSON形式で取得 (creationflagsを追加)
            cmd = [self.ytdlp_exe, "-j", "--no-playlist", url]
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                creationflags=creationflags
            )
            
            if result.returncode != 0:
                return {"error": "解析に失敗しました。URLが正しいか確認してください。"}

            info = json.loads(result.stdout)
            
            # 利用可能な「高さ(height)」を抽出して、重複を除去＆降順ソート
            formats = info.get('formats', [])
            resolutions = set()
            for f in formats:
                h = f.get('height')
                # 映像があるフォーマットのみ抽出
                if h and f.get('vcodec') != 'none':
                    resolutions.add(h)
            
            sorted_res = sorted(list(resolutions), reverse=True)
            
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "resolutions": [f"{r}p" for r in sorted_res], # [2160p, 1080p, ...]
                "ext": info.get('ext')
            }
        except Exception as e:
            return {"error": str(e)}

    """
    実際のダウンロードを実行
    opts: GUIから渡される設定（画質、形式、保存先など）
    progress_callback: 進捗率（0-100）をUIに渡すための関数
    """
    def run_download(self, url, opts, progress_callback):
        # コマンドの組み立て
        cmd = [self.ytdlp_exe, "--newline", "--progress"]
        
        # 保存先の指定
        custom_title = opts.get('custom_title', '%(title)s')
        output_template = os.path.join(opts['save_path'], f"{custom_title}.%(ext)s")
        cmd += ["-o", output_template]

        # FFmpegの場所を教える
        cmd += ["--ffmpeg-location", self.ffmpeg_exe]

        # モード別の設定
        if opts['mode'] == 'video':
            res = opts['resolution'].replace("p", "")
            
            # 画質にbestが送られた場合の処理
            if res == "best":
                if opts['ext'] == 'mp4':
                    fmt = "bestvideo+bestaudio[ext=m4a]/best"
                elif opts['ext'] == 'webm':
                    fmt = "bestvideo+bestaudio[ext=webm]/best"
                else:
                    fmt = "bestvideo+bestaudio/best" 

            # best以外のサイズが送られた場合の処理
            else:              
                if opts['ext'] == 'mp4':
                    fmt = f"bestvideo[height<={res}]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best"
                elif opts['ext'] == 'webm':
                    fmt = f"bestvideo[height<={res}]+bestaudio[ext=webm]/bestvideo[height<={res}]+bestaudio/best"
                else:
                    fmt = f"bestvideo[height<={res}]+bestaudio/best"
            
            target_ext = opts['ext'].lower()
            
            if target_ext in ['avi', 'mov']:
                cmd += ["-f", fmt, "--recode-video", target_ext]
            else:
                cmd += ["-f", fmt, "--merge-output-format", target_ext]
            
        else:
            # 音声モード
            audio_format = opts['ext']
            
            # ogg（yt-dlpの内部名vorbisに変換して伝える）
            if audio_format == 'ogg':
                audio_format = 'vorbis'
            
            cmd += ["-x", "--audio-format", audio_format]
            if opts['ext'] in ['mp3', 'm4a', 'aac', 'ogg']:
                if opts['bitrate'].isdigit():
                    cmd += ["--audio-quality", opts['bitrate']]

        cmd.append(url)

        # 黒窓対策
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW

        # 実行と進捗の解析
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, errors='replace', universal_newlines=True,
            creationflags=creationflags
        )

        # stdoutを一行ずつ読み取って進捗率を探す
        for line in process.stdout:
            # 正規表現で "[download]  12.3% of ..." のような形式から数値を抜く
            match = re.search(r'(\d+(\.\d+)?)%', line)
            if match:
                percent = float(match.group(1))
                progress_callback(percent)
        
        process.wait()
        return process.returncode == 0
    
    """FFmpegを使用して指定のフォルダに変換保存する"""
    def convert_file(self, input_path, output_ext, output_dir, progress_callback):
        filename = os.path.basename(input_path)
        name_no_ext = os.path.splitext(filename)[0]
        
        # 拡張子からドットを取り除く（念のため小文字化）
        clean_ext = output_ext.replace(".", "").lower()
        output_path = os.path.join(output_dir, f"{name_no_ext}.{clean_ext}")
        
        # コマンド作成
        cmd = [self.ffmpeg_exe, "-y", "-i", input_path]

        # ターゲットが音声形式の場合は、映像のエンコードを防ぐため「-vn」を付ける
        audio_formats = ['mp3', 'wav', 'aac', 'ogg', 'flac', 'm4a']
        if clean_ext in audio_formats:
            cmd.append("-vn") # 映像をカットし、音声のみを超高速抽出する
            
        cmd.append(output_path)

        # ▼ 黒窓対策 (追加)
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            progress_callback(10) # 開始報告
            
            # デッドロック防止のため stdout と stderr を統合して処理
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors='replace', universal_newlines=True,
                creationflags=creationflags
            )

            # ログを読み飛ばして終了を待つ
            while True:
                line = process.stdout.readline()
                if not line: break
            
            process.wait()
            progress_callback(100) # 完了報告
            return process.returncode == 0, output_path
        except Exception:
            return False, ""