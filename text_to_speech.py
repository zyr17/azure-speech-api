from re import sub
import requests
import os
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
from pydub import AudioSegment as AS
import json


load_dotenv('.env')
SUBSCRIPTION_KEY = os.environ['SUBSCRIPTION_KEY']
LOCALE = os.environ['LOCALE']
LANGUAGE = os.environ['LANGUAGE']
OUTPUT_AUDIO_FORMAT = os.environ['OUTPUT_AUDIO_FORMAT']
TEXT_SPLIT_LENGTH = int(os.environ['TEXT_SPLIT_LENGTH'])
SPEECH_SPEEDUP = float(os.environ['SPEECH_SPEEDUP'])


def get_token():
    fetch_token_url = f'https://{LOCALE}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
    headers = {
        'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY
    }
    response = requests.post(fetch_token_url, headers=headers)
    access_token = str(response.text)
    return access_token


def check_voices():
    fetch_token_url = f'https://{LOCALE}.tts.speech.microsoft.com/cognitiveservices/voices/list'
    headers = {
        'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY
    }
    response = requests.get(fetch_token_url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f'{response.status_code} {response.text}')
    resp = response.json()
    return resp


def text_to_speech_one(text, token = None, all_voices = None, speaker = 'Xiaoxiao'):
    if token is None:
        token = get_token()
    if all_voices is None:
        all_voices = check_voices()
    voice = [x for x in all_voices if x['DisplayName'] == speaker and 'sichuan' not in x['Name']]
    assert len(voice) == 1, f'matched {len(voice)} voice {voice}'
    voice = voice[0]
    get_speech_url = f'https://{LOCALE}.tts.speech.microsoft.com/cognitiveservices/v1'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': OUTPUT_AUDIO_FORMAT,
        'User-Agent': 'Text-To-Speech'
    }
    template = f'''
    <speak version='1.0' xml:lang='{voice["Locale"]}'><voice xml:lang='{voice["Locale"]}' xml:gender='{voice["Gender"]}'
        name='{voice["ShortName"]}'>
            <prosody rate="{SPEECH_SPEEDUP}">
                {text}
        </prosody></voice></speak>
    '''
    response = requests.post(get_speech_url, template.encode('utf8'), headers=headers)
    if response.status_code != 200:
        raise ValueError(response.status_code, response.text)
    return response.content


def text_split(all_text):
    all_text = all_text.strip().split('\n')
    res = []
    while len(all_text) > 0:
        now = ''
        while len(all_text) > 0 and len(now) + len(all_text[0]) < TEXT_SPLIT_LENGTH:
            now = now + '\n' + all_text[0]
            all_text = all_text[1:]
        if len(all_text) > 0 and len(all_text[0]) > TEXT_SPLIT_LENGTH:
            raise ValueError("one line length too long")
        res.append(now)
    return res


def text_to_speech(all_text, savepath, speaker = 'Xiaoxiao'):
    all_text = text_split(all_text)
    token = get_token()
    all_voices = check_voices()
    res = None
    for num, t in enumerate(all_text):
        print(f'{num}/{len(all_text)}')
        res_bytes = text_to_speech_one(t, token, all_voices, speaker)
        f = NamedTemporaryFile(delete = False)
        f.write(res_bytes)
        f.close()
        r = AS.from_file(f.name)
        if res is None:
            res = r
        else:
            res += r
    res.export(savepath)


if __name__ == '__main__':
    resp = check_voices()
    # print(json.dumps(resp, indent = 2))
    voices = [x['Name'] for x in resp]
    language_names = [x.split(', ')[1].replace('Neural)', '') for x in voices 
                      if LANGUAGE in x and 'sichuan' not in x]  # selected language, and exclude sichuan voices
    # print(language_names)
    # exit()
    text_sample = open('sample.txt', encoding = 'utf8').read()
    # res = (text_split(text_sample))
    # print(len(res), res)
    for language_name in language_names[10:]:
        print(language_name)
        text_to_speech(text_sample, f'speech/{language_name}.mp3', speaker = language_name)