"""Publish Taipei daily Reels to a Page, independently of Instagram markers.

Meta's start/upload/finish protocol is used with a Page access token. Once a
finish request might have been sent, retries only reconcile the same video ID.
"""
import argparse
import base64
import copy
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

MEDIA_REPO = 'audreywang9898-sudo/meowcast-media'
PAGE_NAME = '台北喵喵氣象台'
API = 'https://graph.facebook.com/v24.0'


def validate_source(source, day, slot):
    date.fromisoformat(day)
    if slot not in ('0700', '1630'):
        raise RuntimeError('Invalid Taipei daily slot')
    if (source.get('status') != 'published' or source.get('date') != day or
            source.get('slot') != slot or
            not re.fullmatch(r'\d+', str(source.get('media_id', ''))) or
            not re.fullmatch(r'\d+', str(source.get('run_id', '')))):
        raise RuntimeError('Confirmed Instagram receipt for this date/slot is required')
    expected = f"reels/{day}/meowcast-{slot}-{source['run_id']}.mp4"
    if source.get('video_path') != expected or not source.get('caption', '').strip():
        raise RuntimeError('This older Instagram receipt lacks Facebook assets; no Instagram repost performed')
    return copy.deepcopy(source)


class Store:
    def __init__(self, root):
        token = os.environ.get('MEDIA_REPO_TOKEN')
        if not token:
            raise RuntimeError('MEDIA_REPO_TOKEN missing')
        self.root = Path(root)
        self.env = os.environ.copy()
        auth = base64.b64encode(('x-access-token:' + token).encode()).decode()
        self.env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                         'GIT_CONFIG_VALUE_0': 'AUTHORIZATION: basic ' + auth, 'GIT_TERMINAL_PROMPT': '0'})
        subprocess.run(['git', 'clone', '--quiet', '--depth', '30',
                        f'https://github.com/{MEDIA_REPO}.git', str(self.root)],
                       env=self.env, check=True, capture_output=True)
        self.git('config', 'user.name', 'meowcast-bot')
        self.git('config', 'user.email', 'actions@users.noreply.github.com')

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                              check=check, capture_output=True, text=True)

    def source(self, day, slot, run_id=''):
        date.fromisoformat(day)
        if slot not in ('0700', '1630') or (run_id and not re.fullmatch(r'\d+', run_id)):
            raise RuntimeError('Invalid source date/slot/run')
        path = (self.root / 'reels' / day / f'meowcast-{slot}-{run_id}.json' if run_id
                else self.root / 'latest' / f'published-evidence-{slot}.json')
        source = validate_source(json.loads(path.read_text(encoding='utf-8')), day, slot)
        if run_id and str(source['run_id']) != run_id:
            raise RuntimeError('Original Instagram run ID does not match archived receipt')
        if not (self.root / source['video_path']).is_file():
            raise RuntimeError('Original Instagram video is missing; no Facebook publish attempted')
        return source

    def select(self, source):
        self.path = (self.root / 'facebook' / 'taipei' / source['date'] /
                     source['slot'] / f"{source['media_id']}.json")

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        self.git('add', '--', str(self.path.relative_to(self.root)))
        if self.git('diff', '--cached', '--quiet', check=False).returncode == 0:
            return
        self.git('commit', '-m', 'Persist Taipei Facebook Reel publication evidence')
        for attempt in range(5):
            if self.git('push', 'origin', 'HEAD:main', check=False).returncode == 0:
                return
            if self.git('pull', '--rebase', 'origin', 'main', check=False).returncode != 0:
                self.git('rebase', '--abort', check=False)
                raise RuntimeError('Facebook state conflict; stopped before further publishing')
            time.sleep(2 * (attempt + 1))
        raise RuntimeError('Facebook state could not be persisted')


class Facebook:
    def __init__(self):
        self.page = os.environ['TAIPEI_FB_PAGE_ID']
        self.token = os.environ['TAIPEI_FB_PAGE_ACCESS_TOKEN']
        if not re.fullmatch(r'\d+', self.page):
            raise RuntimeError('Invalid Facebook Page ID')

    def request(self, method, path, **values):
        try:
            response = requests.request(method, API + '/' + path,
                headers={'Authorization': 'Bearer ' + self.token},
                **({'params': values} if method == 'GET' else {'data': values}), timeout=60)
        except requests.RequestException:
            raise RuntimeError('Facebook network request failed; result may be unconfirmed') from None
        if not response.ok:
            try:
                error = response.json().get('error', {})
                code, subcode = error.get('code'), error.get('error_subcode')
            except ValueError:
                code, subcode = None, None
            raise RuntimeError(f'Facebook HTTP {response.status_code}; code={code}, subcode={subcode}')
        try:
            return response.json()
        except ValueError:
            raise RuntimeError('Facebook response could not be confirmed') from None

    def identity(self):
        profile = self.request('GET', 'me', fields='id,name')
        if str(profile.get('id')) != self.page:
            raise RuntimeError('Facebook Page token ID does not match configured Page ID')
        if not str(profile.get('name') or '').strip():
            raise RuntimeError('Facebook Page name is missing')
        if profile.get('name') != PAGE_NAME:
            print('Facebook Page display name changed; configured Page ID still matches and is authoritative.')
        return self.page

    def start(self):
        result = self.request('POST', 'me/video_reels', upload_phase='start')
        vid, url = str(result.get('video_id', '')), result.get('upload_url', '')
        parsed = urlparse(url)
        if (not vid.isdigit() or parsed.scheme != 'https' or parsed.hostname != 'rupload.facebook.com'
                or parsed.username or parsed.password or not parsed.path.endswith('/' + vid)):
            raise RuntimeError('Facebook did not return a valid Reel upload session')
        return vid, url

    def upload(self, url, source_url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'rupload.facebook.com' or parsed.username or parsed.password:
            raise RuntimeError('Invalid stored Facebook upload URL')
        try:
            response = requests.post(url, headers={'Authorization': 'OAuth ' + self.token,
                                      'file_url': source_url}, timeout=120, allow_redirects=False)
        except requests.RequestException:
            raise RuntimeError('Facebook upload response unconfirmed; retain the same video ID') from None
        try:
            success = response.ok and response.json().get('success') is True
        except ValueError:
            success = False
        if not success:
            raise RuntimeError('Facebook upload not confirmed; retain the same video ID')

    def status(self, vid):
        result = self.request('GET', vid, fields='status')
        if str(result.get('id')) != vid or not isinstance(result.get('status'), dict):
            raise RuntimeError('Facebook video status response invalid')
        return result['status']

    def wait(self, vid, phase):
        for attempt in range(36):
            try:
                status = self.status(vid)
            except RuntimeError as exc:
                # Meta can briefly return object-not-found (100/33) after a
                # successful Reel finish. Reconcile the SAME video ID; never
                # start or publish a second Reel on an ambiguous result.
                if (phase == 'publishing_phase' and
                        'Facebook HTTP 400; code=100, subcode=33' in str(exc) and
                        attempt < 12):
                    print('Facebook Reel status temporarily unavailable (100/33); checking same video ID again.')
                    time.sleep(5)
                    continue
                raise
            if status.get(phase, {}).get('status') == 'complete':
                return
            if any(status.get(p, {}).get('status') in ('error', 'failed')
                   for p in ('uploading_phase', 'processing_phase', 'publishing_phase')):
                raise RuntimeError('Facebook video processing failed; retain the same video ID')
            time.sleep(5)
        raise RuntimeError('Facebook processing pending; next run will check the same video ID')

    def finish(self, vid, caption):
        result = self.request('POST', 'me/video_reels', upload_phase='finish',
                              video_id=vid, video_state='PUBLISHED', description=caption)
        if result.get('success') is not True:
            raise RuntimeError('Facebook finish response unconfirmed; retain the same video ID')


def publish(source, store, fb, dry_run=False):
    source = validate_source(source, source['date'], source['slot'])
    if dry_run:
        return {'status': 'dry_run', 'source_media_id': source['media_id']}
    page = fb.identity()
    store.select(source)
    state = store.read()
    if state:
        if (state.get('page_id') != page or state.get('source_media_id') != source['media_id'] or
                state.get('video_path') != source['video_path'] or state.get('caption') != source['caption']):
            raise RuntimeError('Facebook publication state does not match this Instagram source')
        if state['status'] != 'prepared' and not str(state.get('video_id', '')).isdigit():
            raise RuntimeError('Facebook state lacks a valid video ID')
    else:
        state = {'status': 'prepared', 'page_id': page, 'source_media_id': source['media_id'],
                 'date': source['date'], 'slot': source['slot'],
                 'video_path': source['video_path'], 'caption': source['caption']}
        store.save(state)
    if state['status'] == 'published':
        return state
    if state['status'] == 'prepared':
        vid, url = fb.start()
        state.update(status='started', video_id=vid, upload_url=url)
        store.save(state)  # No upload or publication until video ID is durable.
    if state['status'] == 'started':
        state['status'] = 'uploading'
        store.save(state)
        fb.upload(state['upload_url'], f'https://raw.githubusercontent.com/{MEDIA_REPO}/main/{state["video_path"]}')
    if state['status'] == 'uploading':
        fb.wait(state['video_id'], 'uploading_phase')
        state['status'] = 'uploaded'
        store.save(state)
    if state['status'] == 'uploaded':
        state['status'] = 'publishing'
        store.save(state)  # Persist BEFORE finish, including on a network timeout.
        fb.finish(state['video_id'], state['caption'])
    if state['status'] != 'publishing':
        raise RuntimeError('Unknown Facebook publication state')
    fb.wait(state['video_id'], 'publishing_phase')
    state.update(status='published', published_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    store.save(state)
    return state


def summary(message):
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as out:
            out.write(message + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-config', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    present = [bool(os.environ.get(k)) for k in ('TAIPEI_FB_PAGE_ID', 'TAIPEI_FB_PAGE_ACCESS_TOKEN')]
    if not any(present):
        summary('::warning::Facebook Page publishing is not configured. Instagram continues normally. Add TAIPEI_FB_PAGE_ID and TAIPEI_FB_PAGE_ACCESS_TOKEN.')
        return
    if not all(present):
        raise RuntimeError('Both TAIPEI_FB_PAGE_ID and TAIPEI_FB_PAGE_ACCESS_TOKEN are required')
    fb = Facebook()
    if args.check_config:
        fb.identity()
        summary('Facebook Page identity verified: 台北喵喵氣象台. Read-only check; publishing permission still requires a live publish test.')
        return
    with tempfile.TemporaryDirectory(prefix='meowcast-facebook-') as root:
        store = Store(Path(root) / 'media')
        source = store.source(os.environ['PUBLISH_DATE'], os.environ['SLOT'], os.environ.get('SOURCE_RUN_ID', ''))
        result = publish(source, store, fb, dry_run=args.dry_run)
    Path('output').mkdir(exist_ok=True)
    Path('output/facebook-publish-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary(f"Facebook Taipei Reel: {result['status']}; Instagram source {result['source_media_id']}.")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print URLs/headers from requests or subprocess exceptions.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        summary('::error::Facebook publication failed: ' + message)
        raise SystemExit(1)
