from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"status": "VidFetch API is running!"})

@app.route('/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen = set()
            for f in info.get('formats', []):
                height = f.get('height')
                ext = f.get('ext')
                if height and ext in ['mp4', 'webm']:
                    label = f"{height}p"
                    if label not in seen:
                        seen.add(label)
                        formats.append({
                            "format_id": f['format_id'],
                            "quality": label,
                            "ext": ext,
                            "filesize": f.get('filesize')
                        })
            formats.append({"format_id": "bestaudio/best", "quality": "Audio Only", "ext": "mp3", "filesize": None})
            return jsonify({
                "title": info.get('title', 'Video'),
                "duration": info.get('duration_string', '0:00'),
                "thumbnail": info.get('thumbnail', ''),
                "channel": info.get('uploader', 'Unknown'),
                "view_count": info.get('view_count', 0),
                "formats": formats
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id', 'best')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        tmpdir = tempfile.mkdtemp()
        if format_id == 'bestaudio/best':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                'quiet': True
            }
        else:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best',
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'quiet': True,
                'merge_output_format': 'mp4'
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if format_id == 'bestaudio/best':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True)
            for f in os.listdir(tmpdir):
                full = os.path.join(tmpdir, f)
                return send_file(full, as_attachment=True)
        return jsonify({"error": "File not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
