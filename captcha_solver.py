import os
import json
import wave
import time
import tempfile
import subprocess
import urllib.request
from vosk import Model, KaldiRecognizer
from playwright.sync_api import sync_playwright

BASE_URL = "https://scraping-trial-test.vercel.app"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vosk-model")
MAX_CAPTCHA_ATTEMPTS = 5


class CaptchaSolverError(Exception):
    pass


class CaptchaSolver:

    def __init__(self, headless=True):
        self.headless = headless
        self._model = None

    def _ensure_vosk_model(self):
        if self._model:
            return
        model_path = VOSK_MODEL_DIR
        if not os.path.exists(model_path):
            print("[CAPTCHA] Downloading Vosk speech model (~50 MB)...")
            zip_path = model_path + ".zip"
            urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path)
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zf:
                extracted_name = zf.namelist()[0].split('/')[0]
                zf.extractall(os.path.dirname(model_path))
            extracted_path = os.path.join(os.path.dirname(model_path), extracted_name)
            if extracted_path != model_path:
                os.rename(extracted_path, model_path)
            os.remove(zip_path)
            print("[CAPTCHA] Vosk model ready.")
        self._model = Model(model_path)

    def _transcribe_audio(self, audio_path):
        self._ensure_vosk_model()
        wav_path = audio_path.replace(".mp3", ".wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        wf = wave.open(wav_path, "rb")
        rec = KaldiRecognizer(self._model, wf.getframerate())
        rec.SetWords(True)

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)

        final = json.loads(rec.FinalResult())
        result_text = final.get("text", "").strip()
        wf.close()

        try:
            os.remove(wav_path)
        except OSError:
            pass

        return result_text

    def solve(self):
        print("[CAPTCHA] Starting automated audio reCAPTCHA solve...")
        self._ensure_vosk_model()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            try:
                page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
                time.sleep(2)

                token = self._attempt_solve(page)
                if token:
                    return token

                raise CaptchaSolverError(
                    f"Failed to solve CAPTCHA after {MAX_CAPTCHA_ATTEMPTS} attempts"
                )
            finally:
                browser.close()

    def _attempt_solve(self, page):
        anchor_frame = page.frame_locator('iframe[src*="api2/anchor"]')
        checkbox = anchor_frame.locator('#recaptcha-anchor')
        checkbox.wait_for(state="visible", timeout=10000)
        checkbox.click()
        print("[CAPTCHA] Clicked reCAPTCHA checkbox.")
        time.sleep(2)

        token = self._check_token(page)
        if token:
            print("[CAPTCHA] Solved with checkbox click alone (no challenge).")
            return token

        for attempt in range(1, MAX_CAPTCHA_ATTEMPTS + 1):
            print(f"[CAPTCHA] Audio solve attempt {attempt}/{MAX_CAPTCHA_ATTEMPTS}...")
            try:
                token = self._solve_audio_challenge(page, attempt)
                if token:
                    return token
            except Exception as e:
                print(f"[CAPTCHA] Attempt {attempt} failed: {e}")
                time.sleep(1)

        return None

    def _solve_audio_challenge(self, page, attempt):
        challenge_frame = page.frame_locator('iframe[src*="api2/bframe"]')

        if attempt == 1:
            audio_btn = challenge_frame.locator('#recaptcha-audio-button')
            audio_btn.wait_for(state="visible", timeout=10000)
            audio_btn.click()
            print("[CAPTCHA] Switched to audio challenge.")
            time.sleep(2)

        try:
            error_msg = challenge_frame.locator('.rc-audiochallenge-error-message')
            if error_msg.is_visible(timeout=1000):
                err_text = error_msg.text_content()
                if err_text and "try again later" in err_text.lower():
                    raise CaptchaSolverError("Rate limited by reCAPTCHA. Try again later.")
        except Exception:
            pass

        download_link = challenge_frame.locator(
            '.rc-audiochallenge-tdownload-link'
        )
        download_link.wait_for(state="visible", timeout=10000)
        audio_url = download_link.get_attribute("href")

        if not audio_url:
            raise CaptchaSolverError("Could not find audio download URL")

        print(f"[CAPTCHA] Downloading audio challenge...")
        tmp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(tmp_dir, "captcha_audio.mp3")
        urllib.request.urlretrieve(audio_url, audio_path)

        print("[CAPTCHA] Transcribing with Vosk (offline)...")
        transcription = self._transcribe_audio(audio_path)
        print(f"[CAPTCHA] Transcription: '{transcription}'")

        try:
            os.remove(audio_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass

        if not transcription:
            reload_btn = challenge_frame.locator('#recaptcha-reload-button')
            if reload_btn.is_visible():
                reload_btn.click()
                time.sleep(2)
            raise CaptchaSolverError("Empty transcription")

        response_input = challenge_frame.locator('#audio-response')
        response_input.fill(transcription)
        time.sleep(0.5)

        verify_btn = challenge_frame.locator('#recaptcha-verify-button')
        verify_btn.click()
        print("[CAPTCHA] Submitted transcription.")
        time.sleep(3)

        token = self._check_token(page)
        if token:
            print("[CAPTCHA] Audio CAPTCHA solved successfully!")
            return token

        try:
            error_msg = challenge_frame.locator('.rc-audiochallenge-error-message')
            if error_msg.is_visible(timeout=2000):
                err_text = error_msg.text_content()
                if err_text and len(err_text.strip()) > 0:
                    print(f"[CAPTCHA] Challenge error: {err_text.strip()}")
                    reload_btn = challenge_frame.locator('#recaptcha-reload-button')
                    if reload_btn.is_visible():
                        reload_btn.click()
                        time.sleep(2)
        except Exception:
            pass

        return None

    def _check_token(self, page):
        try:
            token = page.evaluate(
                """() => {
                    const el = document.querySelector('#g-recaptcha-response');
                    return el ? el.value : '';
                }"""
            )
            if token and len(token) > 20:
                return token
        except Exception:
            pass
        return None
