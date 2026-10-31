from flask import Flask, jsonify, request, redirect, Response
import yt_dlp
import os

app = Flask(__name__)
app.json.ensure_ascii = False

BASE = 'https://music-server-lf9r.onrender.com'
CACHE = {}

NUMS = {1: 'אחת', 2: 'שתיים', 3: 'שלוש', 4: 'ארבע', 5: 'חמש', 6: 'שש'}


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


def clean(t):
    # משאיר רק אותיות עבריות ורווחים, כדי שההקראה תהיה בעברית
    keep = []
    for ch in t:
        if '\u05d0' <= ch <= '\u05ea' or ch == ' ':
            keep.append(ch)
        else:
            keep.append(' ')
    return ' '.join(''.join(keep).split())


def clean_any(t):
    # לשמיעת התמלול: משאיר אותיות (עברית ואנגלית), ספרות ורווחים
    keep = []
    for ch in t:
        if ch.isalnum() or ch == ' ':
            keep.append(ch)
        else:
            keep.append(' ')
    return ' '.join(''.join(keep).split())


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
    args = request.values
    call_id = args.get('ApiCallId', 'x')
    q = args.get('search')
    choice = args.get('choice')

    print('SEARCH RECEIVED:', repr(q), flush=True)

    # שלב 1: בקשת הקלטה ותמלול
    if not q:
        return ym(
            'read=t-אנא אמרו את החיפוש שלכם ובסיום הקישו סולמית'
            '=search,no,record,speech'
        )

    # שלב 2: חיפוש והקראה
    if call_id not in CACHE:
        try:
            CACHE[call_id] = do_search(q)
        except Exception:
            return ym('id_list_message=t-אירעה שגיאה בחיפוש')
    results = CACHE[call_id]

    if not choice or choice == '6':
        text = f'החיפוש שלכם הוא {clean_any(q)} '
        for i, r in enumerate(results, 1):
            name = clean(r['title']) or 'שיר ללא שם בעברית'
            text += f'{name} להשמעה הקישו {NUMS[i]} '
        text += f'לשמיעה חוזרת הקישו {NUMS[6]}'
        return ym(f'read=t-{text}=choice,no,number,1,1,7,Number,no,no')

    # שלב 3: השמעה (בינתיים רק הודעה, ההשמעה האמיתית אחר כך)
    try:
        idx = int(choice) - 1
        title = clean(results[idx]['title']) or 'השיר שבחרתם'
    except Exception:
        return ym('id_list_message=t-בחירה לא תקינה')
    return ym(f'id_list_message=t-בחרתם {title}')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
