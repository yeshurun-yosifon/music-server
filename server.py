from flask import Flask, jsonify, request, redirect, Response
import yt_dlp
import imageio_ffmpeg
import requests
import os

app = Flask(__name__)
app.json.ensure_ascii = False

YM_TOKEN = os.environ.get('YM_TOKEN', '')
YM_PATH = 'ivr2:/1/'
SONG = 'song'


@app.route('/')
def home():
    return 'השרת עובד'


def do_search(q):
    opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f'ytsearch5:{q}', download=False)
    return [
        {'id': e.get('id'), 'title': e.get('title')}
        for e in info.get('entries', [])[:5]
    ]


def make_wav(vid):
    out = f'/tmp/{vid}'
    wav = out + '.wav'
    if os.path.exists(wav):
        return wav
    opts = {
        'quiet': True,
        'format': 'bestaudio',
        'outtmpl': out + '.%(ext)s',
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}
        ],
        'postprocessor_args': {'extractaudio': ['-ar', '8000', '-ac', '1']},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([f'https://www.youtube.com/watch?v={vid}'])
    return wav


def upload(wav):
    with open(wav, 'rb') as f:
        r = requests.post(
            'https://www.call2all.co.il/ym/api/UploadFile',
            data={'token': YM_TOKEN, 'path': f'{YM_PATH}{SONG}.wav'},
            files={'file': f},
            timeout=100,
        )
    print('UPLOAD RESPONSE:', r.text, flush=True)
    return r.text


def ym(text):
    return Response(text, mimetype='text/plain; charset=utf-8')


@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('name')
    if not q:
        return jsonify({'error': 'missing name'}), 400
    try:
        return jsonify({'success': True, 'results': do_search(q)})
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


@app.route('/ivr', methods=['GET', 'POST'])
def ivr():
    q = request.values.get('search')
    print('SEARCH RECEIVED:', repr(q), flush=True)

    if not q:
        return ym(
            'read=t-אנא אמרו את החיפוש שלכם ובסיום הקישו סולמית'
            '=search,no,record,speech'
        )

    try:
        results = do_search(q)
        if not results:
            return ym('id_list_message=t-לא נמצאו תוצאות')
        wav = make_wav(results[0]['id'])
        upload(wav)
    except Exception as e:
        print('ERROR:', repr(e), flush=True)
        return ym('id_list_message=t-אירעה שגיאה בהשמעה')

    return ym(f'id_list_message=f-{SONG}')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
