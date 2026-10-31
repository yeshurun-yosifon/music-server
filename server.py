from flask import Flask, jsonify, request, redirect
import yt_dlp
import os

app = Flask(__name__)


@app.route('/')
def home():
    return 'השרת עובד'


@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('name')
    if not q:
        return jsonify({'error': 'missing name'}), 400
    opts = {'quiet': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f'ytsearch5:{q}', download=False)
        results = [
            {'id': e.get('id'), 'title': e.get('title')}
            for e in info.get('entries', [])[:5]
        ]
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/audio', methods=['GET'])
def audio():
    vid = request.args.get('id')
    if not vid:
        return jsonify({'error': 'missing id'}), 400
    opts = {'quiet': True, 'format': 'bestaudio'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={vid}', download=False
            )
        return redirect(info['url'])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
