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
    def find_week(self, state): return self.found


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
    def test_oct_18_2026_sunday_issue_resolves_next_week(self):
        """Read-only preview on Thursday must target Sunday 10/18 and forecast 10/19-10/25."""
        thursday = datetime(2026, 10, 15, 12, 0, tzinfo=ZoneInfo('Asia/Taipei'))
        sunday = datetime(2026, 10, 18, 8, 5, tzinfo=ZoneInfo('Asia/Taipei'))
        preview = resolve('push', now=thursday)
        self.assertTrue(preview['run'])
        self.assertFalse(preview['publish'])
        self.assertEqual(preview['issue_date'], '2026-10-18')
        scheduled = resolve('schedule', now=sunday)
        self.assertTrue(scheduled['run'])
        self.assertTrue(scheduled['publish'])
        self.assertEqual(scheduled['issue_date'], '2026-10-18')
        self.assertEqual(
            [d.isoformat() for d in weekly.week_dates(date(2026, 10, 18))],
            ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22',
             '2026-10-23', '2026-10-24', '2026-10-25'])

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
    def deleted_slot(self):
        store, ig = Store(), IG()
        publisher.publish('taipei', self.issue, self.out, store, ig)
        ig.calls.clear()
        def verify(media):
            if media == 'published-id': raise publisher.InstagramObjectUnavailable('missing')
            return {'id': media}
        ig.verify_media = verify
        return store, ig
    def test_deleted_week_requires_manual(self):
        store, ig = self.deleted_slot()
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig)
        self.assertEqual(ig.calls, [])
        self.assertEqual(store.state['status'], 'published')
    def test_manual_deleted_week_republishes_and_archives(self):
        store, ig = self.deleted_slot()
        ig.verify_media = lambda media: (_ for _ in ()).throw(publisher.InstagramObjectUnavailable('missing')) if media == 'published-id' and not ig.calls else {'id': media}
        result = publisher.publish('taipei', self.issue, self.out, store, ig, recover_deleted=True)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['previous_publications'][0]['media_id'], 'published-id')
        self.assertEqual(sum(c[1].endswith('/media_publish') for c in ig.calls), 1)
    def test_manual_existing_week_never_duplicates(self):
        store, ig = self.deleted_slot()
        ig.found = 'existing-new-id'
        result = publisher.publish('taipei', self.issue, self.out, store, ig, recover_deleted=True)
        self.assertEqual(result['media_id'], 'existing-new-id')
        self.assertEqual(ig.calls, [])
    def test_feed_permission_failure_never_republishes(self):
        store, ig = self.deleted_slot()
        def fail(state): raise RuntimeError('feed denied')
        ig.find_week = fail
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig, recover_deleted=True)
        self.assertEqual(ig.calls, [])
    def test_network_failure_never_republishes(self):
        store, ig = self.deleted_slot()
        def fail(media): raise RuntimeError('network timeout')
        ig.verify_media = fail
        with self.assertRaises(RuntimeError): publisher.publish('taipei', self.issue, self.out, store, ig, recover_deleted=True)
        self.assertEqual(ig.calls, [])
    def test_feed_scan_checks_next_page(self):
        ig = object.__new__(publisher.Instagram); ig.ig = '123'
        responses = iter([{'data': [], 'paging': {'next': 'opaque', 'cursors': {'after': 'cursor'}}},
                          {'data': [{'id': 'existing', 'caption': 'Taipei Meowcast | Next-week pawcast\n2026-10-05 – 2026-10-11'}]}])
        ig.request = lambda *a, **kw: next(responses)
        ig.verify_media = lambda media: {'id': media}
        state = {'media_id': 'old', 'caption': 'old caption', 'week_start': '2026-10-05', 'week_end': '2026-10-11'}
        self.assertEqual(ig.find_week(state), 'existing')

    def test_missing_forecast_aborts(self):
        daily = {'time': [d.isoformat() for d in self.dates]}
        for key in weekly.DAILY_KEYS: daily[key] = [0] * 7
        data = {'timezone': 'Asia/Taipei', 'daily': daily}
        daily['temperature_2m_max'][0] = None
        with self.assertRaises(ValueError): weekly.select_week(data, self.dates, {'timezone': 'Asia/Taipei'})


if __name__ == '__main__': unittest.main()
