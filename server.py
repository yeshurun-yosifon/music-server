from flask import Flask, jsonify, request, Response
import yt_dlp
import imageio_ffmpeg
import requests
import subprocess
import time
import os

app = Flask(__name__)
app.json.ensure_ascii = False

YM_TOKEN = os.environ.get('YM_TOKEN', '')
RAPID_KEY = os.environ.get('RAPID_KEY', '')
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


def get_audio_url(vid):
    # הפונקציה היחידה שתלויה בשירות ההמרה. כדי להחליף שירות משנים רק אותה.
    host = 'youtube-mp36.p.rapidapi.com'
    headers = {'x-rapidapi-key': RAPID_KEY, 'x-rapidapi-host': host}
    for _ in range(6):
        r = requests.get(
            f'https://{host}/dl',
            params={'id': vid},
            headers=headers,
            timeout=60,
        )
        print('CONVERTER RESPONSE:', r.text[:500], flush=True)
        data = r.json()
        if data.get('status') == 'ok' and data.get('link'):
            return data['link']
        time.sleep(4)
    raise Exception('converter did not return a link')


def make_wav(vid):
    mp3 = f'/tmp/{vid}.mp3'
    wav = f'/tmp/{vid}.wav'
    url = get_audio_url(vid)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(mp3, 'wb') as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', mp3,
         '-ar', '8000', '-ac', '1', wav],
        check=True,
    )
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


@app.route('/ivr', methods=['GET', 'POST'])
def ivr():
    q = request.values.get('search')
    print('SEARCH RECEIVED:', repr(q), flush=True)

    if not q:
        return ym(
            'read=t-אנא אמרו את החיפוש שלכם ובסיום הקישו סולמית'
            '=search,no,record,speech'
        )

    # זמני: כל עוד אין תמלול, q הוא שם קובץ, ולכן מחפשים משהו קבוע לבדיקה
    if q.startswith('speech/'):
        q = 'אייל גולן'

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
