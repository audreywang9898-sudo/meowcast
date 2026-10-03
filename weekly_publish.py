"""Publish exactly one weekly two-image carousel per city and forecast week.

An ambiguous publish response is reconciled against Instagram, never replaced
with a new carousel. State is independent of daily Reel rotation/markers.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image
from weekly import week_dates

API = 'https://graph.instagram.com/v24.0'
MEDIA_REPO = 'audreywang9898-sudo/meowcast-media'


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def publication_window(issue, now=None, allow_early=False):
    now = now or datetime.now(ZoneInfo('Asia/Taipei'))
    now = now.astimezone(ZoneInfo('Asia/Taipei'))
    if issue.weekday() != 6 or now.date() != issue or (now.hour < 8 and not allow_early):
        raise RuntimeError('Production weekly publish is allowed only on its Sunday issue date after 08:00 Asia/Taipei')


class MediaStore:
    def __init__(self, root, city, week_start):
        token = os.environ.get('MEDIA_REPO_TOKEN')
        if not token: raise RuntimeError('MEDIA_REPO_TOKEN missing')
        self.root = Path(root)
        self.env = os.environ.copy()
        auth = base64.b64encode(('x-access-token:' + token).encode()).decode()
        self.env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                         'GIT_CONFIG_VALUE_0': 'AUTHORIZATION: basic ' + auth, 'GIT_TERMINAL_PROMPT': '0'})
        subprocess.run(['git', 'clone', '--quiet', '--depth', '30',
                        f'https://github.com/{MEDIA_REPO}.git', str(self.root)], env=self.env, check=True)
        self.git('config', 'user.name', 'meowcast-bot')
        self.git('config', 'user.email', 'actions@users.noreply.github.com')
        self.path = self.root / 'weekly' / city / week_start / 'state.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                              check=check, capture_output=True, text=True)

    def read(self):
        if not self.path.exists(): return None
        return json.loads(self.path.read_text(encoding='utf-8'))

    def save(self, state):
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        self.flush([self.path.relative_to(self.root)])

    def flush(self, paths):
        self.git('add', '--', *(str(p) for p in paths))
        if self.git('diff', '--cached', '--quiet', check=False).returncode == 0: return
        self.git('commit', '-m', 'Persist weekly pawcast assets and publication evidence')
        for attempt in range(5):
            if self.git('push', 'origin', 'HEAD:main', check=False).returncode == 0: return
            # Other cities and daily Reels may write different paths concurrently.
            if self.git('pull', '--rebase', 'origin', 'main', check=False).returncode != 0:
                self.git('rebase', '--abort', check=False)
                raise RuntimeError('Weekly state conflict; stopped before further publishing')
            time.sleep(2 * (attempt + 1))
        raise RuntimeError('Could not persist weekly media state')

    def upload(self, images, city, issue):
        run = os.environ.get('GITHUB_RUN_ID', 'manual')
        attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
        relative = Path('weekly') / city / issue / f'run-{run}-{attempt}'
        target = self.root / relative
        target.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, image in enumerate(images, 1):
            dst = target / f'slide-{i}.jpg'
            shutil.copyfile(image, dst)
            paths.append(dst.relative_to(self.root))
        self.flush(paths)
        urls = [f'https://raw.githubusercontent.com/{MEDIA_REPO}/main/{p.as_posix()}' for p in paths]
        for image, url in zip(images, urls):
            expected = hashlib.sha256(image.read_bytes()).digest()
            for retry in range(12):
                try:
                    r = requests.get(url, timeout=30)
                    if r.ok and hashlib.sha256(r.content).digest() == expected: break
                except requests.RequestException: pass
                time.sleep(5)
            else: raise RuntimeError('Public carousel image unavailable or bytes differ')
        return urls


class Instagram:
    def __init__(self):
        self.ig = os.environ.get('IG_USER_ID')
        self.token = os.environ.get('IG_ACCESS_TOKEN')
        if not self.ig or not self.token: raise RuntimeError('Instagram credentials missing')

    def request(self, method, path, **values):
        values['access_token'] = self.token
        # Do not echo provider payloads or request URLs containing credentials.
        try:
            if method == 'GET': r = requests.get(API + '/' + path, params=values, timeout=45)
            else: r = requests.post(API + '/' + path, data=values, timeout=60)
        except requests.RequestException:
            raise RuntimeError('Instagram network request failed; result may be unconfirmed') from None
        if not r.ok:
            try:
                error = r.json().get('error', {})
                code, subcode = error.get('code'), error.get('error_subcode')
            except ValueError: code, subcode = None, None
            raise RuntimeError(f'Instagram HTTP {r.status_code}; code={code}, subcode={subcode}')
        return r.json()

    def identity(self):
        profile = self.request('GET', self.ig, fields='id,username')
        if not profile.get('id'): raise RuntimeError('Instagram profile verification failed')
        return str(profile['id'])

    def status(self, cid):
        return self.request('GET', cid, fields='status_code').get('status_code')

    def wait(self, cid):
        for attempt in range(30):
            status = self.status(cid)
            if status == 'FINISHED': return
            if status in ('ERROR', 'EXPIRED', 'PUBLISHED'):
                raise RuntimeError('Unexpected carousel container status: ' + str(status))
            time.sleep(5)
        raise RuntimeError('Instagram carousel processing timed out')

    def verify_media(self, media_id):
        media = self.request('GET', media_id, fields='id,media_type,children{id}')
        if media.get('media_type') != 'CAROUSEL_ALBUM' or len(media.get('children', {}).get('data', [])) != 2:
            raise RuntimeError('Published weekly post is not a two-image carousel')
        return media

    def reconcile(self, state):
        # Exact caption includes year, week range and city. Do not assume a
        # FINISHED container or a successful workflow means it was published.
        media = self.request('GET', self.ig + '/media',
            fields='id,caption,media_type,timestamp,children{id}', limit=50)
        for item in media.get('data', []):
            if item.get('caption') == state['caption']:
                self.verify_media(str(item['id']))
                return str(item['id'])
        return None


def publish(city, issue, out, store, ig):
    rows = week_dates(issue)
    week_start = rows[0].isoformat()
    state = store.read()
    if state:
        if state.get('city') != city or state.get('week_start') != week_start:
            raise RuntimeError('Weekly state identity mismatch')
        if str(state.get('ig_user_id')) != ig.ig:
            raise RuntimeError('Weekly state belongs to another Instagram account')
        if state.get('status') == 'published':
            if not state.get('media_id'): raise RuntimeError('Published state has no media ID')
            ig.verify_media(state['media_id'])
            print(f"Weekly slot already published: {city} {week_start} media={state['media_id']}")
            return state
        if state.get('status') == 'publishing':
            for attempt in range(6):
                found = ig.reconcile(state)
                if found:
                    state.update(status='published', media_id=found, published_at=now_text(), reconciled=True)
                    store.save(state)
                    print('Recovered published weekly media:', found)
                    return state
                time.sleep(10)
            raise RuntimeError('Previous weekly publish is unconfirmed. No new carousel was created; inspect Instagram before retrying.')
        if state.get('status') != 'prepared': raise RuntimeError('Unknown weekly state')
    else:
        metadata = json.loads((out / 'forecast.json').read_text(encoding='utf-8'))
        if metadata.get('mode') != 'production' or metadata.get('city') != city or metadata.get('issue_date') != issue.isoformat():
            raise RuntimeError('Refusing non-production or wrong-week render')
        if [r['date'] for r in metadata['days']] != [r.isoformat() for r in rows]:
            raise RuntimeError('Rendered forecast does not cover next Monday-Sunday')
        text = (out / 'caption.txt').read_text(encoding='utf-8')
        if not 0 < len(text) <= 2200: raise RuntimeError('Invalid caption length')
        images = [out / f'{city}-weekly-{i}.jpg' for i in (1, 2)]
        for path in images:
            with Image.open(path) as im:
                if im.format != 'JPEG' or im.size != (1080, 1350): raise RuntimeError('Invalid carousel JPEG')
                im.verify()
        urls = store.upload(images, city, issue.isoformat())
        state = {'city': city, 'issue_date': issue.isoformat(), 'week_start': week_start,
                 'week_end': rows[-1].isoformat(), 'slot': 'weekly-0800', 'ig_user_id': ig.ig,
                 'status': 'prepared', 'caption': text, 'image_urls': urls, 'children': [],
                 'run_id': os.environ.get('GITHUB_RUN_ID'), 'prepared_at': now_text()}
        store.save(state)
    while len(state['children']) < 2:
        index = len(state['children'])
        child = ig.request('POST', ig.ig + '/media', image_url=state['image_urls'][index], is_carousel_item='true')
        state['children'].append(str(child['id']))
        store.save(state)
    for child in state['children']: ig.wait(child)
    if not state.get('container_id'):
        parent = ig.request('POST', ig.ig + '/media', media_type='CAROUSEL',
                            children=','.join(state['children']), caption=state['caption'])
        state['container_id'] = str(parent['id'])
        store.save(state)
    ig.wait(state['container_id'])
    # Persist intent BEFORE sending the publishing request. A crash or timeout
    # after this point must reconcile, not create and publish another container.
    state.update(status='publishing', attempted_at=now_text(), run_id=os.environ.get('GITHUB_RUN_ID'))
    store.save(state)
    result = ig.request('POST', ig.ig + '/media_publish', creation_id=state['container_id'])
    if not result.get('id'): raise RuntimeError('Instagram returned no published media ID')
    state.update(status='published', media_id=str(result['id']), published_at=now_text())
    store.save(state)
    ig.verify_media(state['media_id'])
    print('Published weekly carousel:', state['media_id'])
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=['taipei', 'melbourne'], required=True)
    p.add_argument('--issue-date', required=True)
    p.add_argument('--output', default='output/weekly')
    p.add_argument('--publish', action='store_true', required=True)
    p.add_argument('--manual-early', action='store_true', help='Explicit manual Sunday publish before 08:00')
    a = p.parse_args()
    issue = date.fromisoformat(a.issue_date)
    if a.manual_early and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError('Early publication requires an explicit manual workflow invocation')
    publication_window(issue, allow_early=a.manual_early)
    out = Path(a.output) / a.city
    out.mkdir(parents=True, exist_ok=True)
    receipt = out / 'publish-result.json'
    receipt.unlink(missing_ok=True)
    ig = Instagram()
    ig.identity()
    with tempfile.TemporaryDirectory(prefix='weekly-media-') as tmp:
        store = MediaStore(Path(tmp) / 'repo', a.city, week_dates(issue)[0].isoformat())
        state = publish(a.city, issue, out, store, ig)
    receipt.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
