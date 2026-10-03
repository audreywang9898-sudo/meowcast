import copy
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from PIL import Image
import weekly
import weekly_publish as publisher
from weekly_schedule import resolve


class Store:
    def __init__(self, state=None): self.state = copy.deepcopy(state); self.uploads = 0
    def read(self): return copy.deepcopy(self.state)
    def save(self, state): self.state = copy.deepcopy(state)
    def upload(self, *args): self.uploads += 1; return ['https://example.com/1.jpg', 'https://example.com/2.jpg']


class IG:
    ig = '123'
    def __init__(self): self.calls = []; self.found = None; self.fail_publish = False
    def request(self, method, path, **values):
        self.calls.append((method, path, values))
        if path.endswith('/media_publish'):
            if self.fail_publish: raise RuntimeError('Ambiguous timeout')
            return {'id': 'published-id'}
        return {'id': str(len(self.calls))}
    def wait(self, cid): pass
    def verify_media(self, media): return {'id': media}
    def reconcile(self, state): return self.found


class WeeklyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.issue = date(2026, 10, 4)
        self.dates = weekly.week_dates(self.issue)
        self.meta = {'mode': 'production', 'city': 'taipei', 'issue_date': '2026-10-04',
                     'days': [{'date': d.isoformat()} for d in self.dates]}
        (self.out / 'forecast.json').write_text(json.dumps(self.meta))
        (self.out / 'caption.txt').write_text('2026/10/05–2026/10/11 Taipei weekly weather ❤️')
        for i in (1, 2): Image.new('RGB', (1080, 1350)).save(self.out / f'taipei-weekly-{i}.jpg')
    def tearDown(self): self.tmp.cleanup()
    def test_calendar(self):
        self.assertEqual(weekly.week_dates(date(2026, 12, 27))[-1], date(2027, 1, 3))
        with self.assertRaises(ValueError): weekly.week_dates(date(2026, 10, 3))
    def test_schedule(self):
        early = datetime(2026, 10, 4, 7, 59, tzinfo=ZoneInfo('Asia/Taipei'))
        due = datetime(2026, 10, 4, 8, 0, tzinfo=ZoneInfo('Asia/Taipei'))
        self.assertFalse(resolve('schedule', now=early)['publish'])
        self.assertTrue(resolve('schedule', now=due)['publish'])
        self.assertFalse(resolve('push', now=due)['publish'])
        self.assertFalse(resolve('workflow_dispatch', now=due)['publish'])
        with self.assertRaises(RuntimeError): publisher.publication_window(self.issue, early)
        publisher.publication_window(self.issue, early, allow_early=True)
        self.assertTrue(resolve('workflow_dispatch', '2026-10-04', True, now=early)['publish'])
        self.assertFalse(resolve('push', '2026-10-04', True, now=early)['publish'])
        publisher.publication_window(self.issue, due)
        monday = datetime(2026, 10, 5, 8, tzinfo=ZoneInfo('Asia/Taipei'))
        self.assertFalse(resolve('schedule', now=monday)['run'])
    def test_two_children_then_parent(self):
        store, ig = Store(), IG()
        result = publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(len(result['children']), 2)
        self.assertEqual(ig.calls[2][2]['media_type'], 'CAROUSEL')
        self.assertEqual(ig.calls[2][2]['children'], '1,2')
        self.assertEqual(sum(x[1].endswith('/media_publish') for x in ig.calls), 1)
    def test_published_week_dedupes(self):
        store, ig = Store(), IG()
        publisher.publish('taipei', self.issue, self.out, store, ig)
        ig.calls.clear()
        publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(ig.calls, [])
        self.assertEqual(store.uploads, 1)
    @patch('weekly_publish.time.sleep')
    def test_ambiguous_response_reconciles_without_post(self, sleep):
        store, ig = Store(), IG(); ig.fail_publish = True
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(store.state['status'], 'publishing')
        ig.calls.clear(); ig.found = 'recovered-id'
        result = publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(result['media_id'], 'recovered-id')
        self.assertEqual(ig.calls, [])
    @patch('weekly_publish.time.sleep')
    def test_unconfirmed_publish_does_not_duplicate(self, sleep):
        store, ig = Store(), IG(); ig.fail_publish = True
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        ig.calls.clear()
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(ig.calls, [])
    def test_state_must_persist_before_publish(self):
        store, ig = Store(), IG()
        original = store.save
        def fail_intent(state):
            if state['status'] == 'publishing': raise RuntimeError('Cannot push state')
            original(state)
        store.save = fail_intent
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertFalse(any(x[1].endswith('/media_publish') for x in ig.calls))
    def test_different_account_rejected(self):
        store, ig = Store(), IG()
        publisher.publish('taipei', self.issue, self.out, store, ig)
        ig.ig = '456'
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
    def test_dry_run_cannot_publish(self):
        self.meta['mode'] = 'dry_run'
        (self.out / 'forecast.json').write_text(json.dumps(self.meta))
        store, ig = Store(), IG()
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(ig.calls, [])
    def test_missing_forecast_aborts(self):
        daily = {'time': [d.isoformat() for d in self.dates]}
        for key in weekly.DAILY_KEYS: daily[key] = [0] * 7
        data = {'timezone': 'Asia/Taipei', 'daily': daily}
        daily['temperature_2m_max'][0] = None
        with self.assertRaises(ValueError): weekly.select_week(data, self.dates, {'timezone': 'Asia/Taipei'})


if __name__ == '__main__': unittest.main()
