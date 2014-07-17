"""
    The Mic class handles all interactions with the microphone and speaker.
"""

import os
import json
from wave import open as open_audio
import audioop
import pyaudio
import alteration
import urllib2
import urllib

# quirky bug where first import doesn't work
try:
    import pocketsphinx as ps
except:
    import pocketsphinx as ps

LANG_CODE = 'en-US'  # Language to use

FLAC_CONV = 'flac -f'

STT_KEY = os.environ.get("GOOGLE_STT_KEY", None)

GOOGLE_SPEECH_URL = 'https://www.google.com/speech-api/v2/recognize?lang={lang}&key={key}'.format(key=STT_KEY, lang=LANG_CODE);

PLAY_CMD = os.environ.get('JASPER_PLAY', 'aplay -D hw:1,0 {}')

class Mic:

    speechRec = None
    speechRec_persona = None

    def __init__(self, lmd, dictd, lmd_persona, dictd_persona, lmd_music=None, dictd_music=None):
        """
            Initiates the pocketsphinx instance.

            Arguments:
            lmd -- filename of the full language model
            dictd -- filename of the full dictionary (.dic)
            lmd_persona -- filename of the 'Persona' language model (containing, e.g., 'Jasper')
            dictd_persona -- filename of the 'Persona' dictionary (.dic)
        """

        hmdir = "/usr/local/share/pocketsphinx/model/hmm/en_US/hub4wsj_sc_8k"

        if lmd_music and dictd_music:
            self.speechRec_music = ps.Decoder(hmm = hmdir, lm = lmd_music, dict = dictd_music)
        self.speechRec_persona = ps.Decoder(
            hmm=hmdir, lm=lmd_persona, dict=dictd_persona)
        self.speechRec = ps.Decoder(hmm=hmdir, lm=lmd, dict=dictd)

    def transcribe(self, audio_file_path, PERSONA_ONLY=False, MUSIC=False):
        """
            Performs TTS, transcribing an audio file and returning the result.

            Arguments:
            audio_file_path -- the path to the audio file to-be transcribed
            PERSONA_ONLY -- if True, uses the 'Persona' language model and dictionary
            MUSIC -- if True, uses the 'Music' language model and dictionary
        """

        wavFile = file(audio_file_path, 'rb')
        wavFile.seek(44)

        if MUSIC:
            self.speechRec_music.decode_raw(wavFile)
            result = self.speechRec_music.get_hyp()
        elif PERSONA_ONLY:
            self.speechRec_persona.decode_raw(wavFile)
            result = self.speechRec_persona.get_hyp()
        else:
            self.speechRec.decode_raw(wavFile)
            result = self.speechRec.get_hyp()

        print "==================="
        print "JASPER: " + result[0]
        print "==================="

        return result[0]

    def google_transcribe(self, audio_file_path):
        """ Sends audio file (audio_file_path) to Google's text to speech
            service and returns service's response. We need a FLAC
            converter if audio is not FLAC (check FLAC_CONV). """

        print "Sending ", audio_file_path
        #Convert to flac first
        filename = audio_file_path
        del_flac = False
        if 'flac' not in filename:
            del_flac = True
            print "Converting to flac"
            print FLAC_CONV + filename
            os.system(FLAC_CONV + ' ' + filename)
            filename = filename.split('.')[0] + '.flac'

        f = open(filename, 'rb')
        flac_cont = f.read()
        f.close()

        # Headers. A common Chromium (Linux) User-Agent
        hrs = {"User-Agent": "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.63 Safari/535.7",
               'Content-type': 'audio/x-flac; rate=16000'}

        req = urllib2.Request(GOOGLE_SPEECH_URL, data=flac_cont, headers=hrs)
        print "Sending request to Google TTS"
        #print "response", response
        try:
            p = urllib2.urlopen(req)
            response = p.read()
            res = eval(response)['hypotheses']
        except:
            print "Couldn't parse service response"
            res = None

        if del_flac:
            os.remove(filename)  # Remove temp file

        return res

    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms / 3
        return score

    def fetchThreshold(self):

        # TODO: Consolidate all of these variables from the next three
        # functions
        THRESHOLD_MULTIPLIER = 1.8
        AUDIO_FILE = "passive.wav"
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # number of seconds to listen before forcing restart
        LISTEN_TIME = 10

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(20)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        return THRESHOLD

    def passiveListen(self, PERSONA):
        """
            Listens for PERSONA in everyday sound
            Times out after LISTEN_TIME, so needs to be restarted
        """

        THRESHOLD_MULTIPLIER = 1.8
        AUDIO_FILE = "passive.wav"
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # number of seconds to listen before forcing restart
        LISTEN_TIME = 10

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(30)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        # save some memory for sound data
        frames = []

        # flag raised when sound disturbance detected
        didDetect = False

        # start passively listening for disturbance above threshold
        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            if score > THRESHOLD:
                didDetect = True
                break

        # no use continuing if no flag raised
        if not didDetect:
            print "No disturbance detected"
            return

        # cutoff any recording before this disturbance was detected
        frames = frames[-20:]

        # otherwise, let's keep recording for few seconds and save the file
        DELAY_MULTIPLIER = 1
        for i in range(0, RATE / CHUNK * DELAY_MULTIPLIER):

            data = stream.read(CHUNK)
            frames.append(data)

        # save the audio data
        stream.stop_stream()
        stream.close()
        audio.terminate()
        write_frames = open_audio(AUDIO_FILE, 'wb')
        write_frames.setnchannels(1)
        write_frames.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        write_frames.setframerate(RATE)
        write_frames.writeframes(''.join(frames))
        write_frames.close()

        # check if PERSONA was said
        transcribed = self.transcribe(AUDIO_FILE, PERSONA_ONLY=True)

        if PERSONA in transcribed:
            return (THRESHOLD, PERSONA)

        return (False, transcribed)

    def activeListen(self, THRESHOLD=None, LISTEN=True, MUSIC=False, google_stt=False):
        """
            Records until a second of silence or times out after 12 seconds
        """

        AUDIO_FILE = "active.wav"
        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 12

        # user can request pre-recorded sound
        if not LISTEN:
            if not os.path.exists(AUDIO_FILE):
                return None

            return self.transcribe(AUDIO_FILE)

        # check if no threshold provided
        if THRESHOLD == None:
            THRESHOLD = self.fetchThreshold()

        os.system(PLAY_CMD.format('beep_hi.wav'))

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        frames = []
        # increasing the range # results in longer pause after command
        # generation
        lastN = [THRESHOLD * 1.2 for i in range(30)]

        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            lastN.pop(0)
            lastN.append(score)

            average = sum(lastN) / float(len(lastN))

            # TODO: 0.8 should not be a MAGIC NUMBER!
            if average < THRESHOLD * 0.8:
                break

        os.system(PLAY_CMD.format('beep_lo.wav'))

        # save the audio data
        stream.stop_stream()
        stream.close()
        audio.terminate()
        write_frames = open_audio(AUDIO_FILE, 'wb')
        write_frames.setnchannels(1)
        write_frames.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        write_frames.setframerate(RATE)
        write_frames.writeframes(''.join(frames))
        write_frames.close()

        # DO SOME AMPLIFICATION
        # os.system("sox "+AUDIO_FILE+" temp.wav vol 20dB")

        if MUSIC:
            return self.transcribe(AUDIO_FILE, MUSIC=True)

        if google_stt:
            return self.google_transcribe(AUDIO_FILE)
        else:
            return self.transcribe(AUDIO_FILE)

    def say(self, phrase, OPTIONS=" -vdefault+m3 -p 40 -s 160 --stdout > say.wav"):
        # alter phrase before speaking
        phrase = alteration.clean(phrase)

        os.system("espeak " + json.dumps(phrase) + OPTIONS)
        os.system(PLAY_CMD.format('say.wav'))
