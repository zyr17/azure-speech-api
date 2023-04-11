import os
from tqdm import tqdm
import requests
import sys
import time
import multiprocessing
import multiprocessing.dummy
from pydub import AudioSegment as AS
from dotenv import load_dotenv


load_dotenv('.env')
SUBSCRIPTION_KEY = os.environ['SUBSCRIPTION_KEY']
LOCALE = os.environ['LOCALE']
LANGUAGE = os.environ['LANGUAGE']
SEGMENT_LENGTH = int(os.environ['SEGMENT_LENGTH'])
REPEAT_END = int(os.environ['REPEAT_END'])
THREADS = int(os.environ['THREADS'])


temp_name = f'{time.time_ns()}'


def text_to_speech_one(audio_bytes):
    one_temp_name = f'{temp_name}_{id(multiprocessing.current_process())}.wav'
    audio_bytes.export(one_temp_name, format = 'wav')
    with open(one_temp_name, 'rb') as f:
        audio_bytes = f.read()
    os.system(f'rm {one_temp_name}')
    get_text_url = f'https://{LOCALE}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={LANGUAGE}'
    headers = {
        'Ocp-Apim-Subscription-Key': f'{SUBSCRIPTION_KEY}',
        'Content-Type': 'audio/wav'
    }
    response = requests.post(get_text_url, data=audio_bytes, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.status_code, response.text)
    res = response.json()
    if res['RecognitionStatus'] == 'EndOfDictation':
        return ''
    if res['RecognitionStatus'] != 'Success':
        raise ValueError(f"response status {res['RecognitionStatus']}")
    return res['DisplayText']


def text_to_speech(audio_bytes: AS, one_length = 25000, repeat_end = 500, 
                   threads = 1):
    """
    audio_bytes: AudioSegment
    one_length: length (in ms) for one segment.
    repeat_end: how long (in ms) repeat between two segments. e.g. one_length
        25000 + repeat_end 500 will generate first three segments as 0:25000,
        24500:49500, 49000:74000
    threads: multiprocessing threads
    """

    segments = []
    current = repeat_end
    while current < len(audio_bytes):
        current -= repeat_end
        segments.append(audio_bytes[current:current + one_length])
        current += one_length
    print(f'segment number: {len(segments)}')
    with multiprocessing.Pool(threads) as pool:
        res = []
        for i in tqdm(pool.imap(text_to_speech_one, segments), total = len(segments)):
            res.append(i)
    return ''.join(res)


def get_audio(fname):
    if fname[-4:] == '.mp4':
        os.system(f'ffmpeg -loglevel error -i {fname} -vn -codec copy {temp_name}.m4a')
        fname = f'{temp_name}.m4a'
        return fname
    else:
        return fname


if __name__ == '__main__':
    audio_name = get_audio(sys.argv[1])
    audio = AS.from_file(audio_name)
    if temp_name in audio_name:
        os.system(f'rm {audio_name}')
    audio.set_frame_rate(16000)
    res = text_to_speech(audio, SEGMENT_LENGTH, REPEAT_END, THREADS)
    print(res)
