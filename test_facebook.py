import copy
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import publish_facebook as publisher


SOURCE = {'status': 'published', 'media_id': '1234', 'date': '2026-10-04',
          'slot': '0700', 'run_id': '5678', 'caption': '台北天氣貓 ☀️\n喜歡記得按愛心！',
          'video_path': 'reels/2026-10-04/meowcast-0700-5678.mp4'}


class Store:
    def __init__(self):
        self.states = {}
        self.fail_status = None
    def select(self, source):
        self.key = source['media_id']
    def read(self):
        return copy.deepcopy(self.states.get(self.key))
    def save(self, state):
        if state['status'] == self.fail_status:
            raise RuntimeError('durable save failed')
        self.states[self.key] = copy.deepcopy(state)


class Facebook:
    def __init__(self):
        self.calls = []
        self.finish_timeout = False
        self.upload_timeout = False
        self.pending = False
    def identity(self):
        self.calls.append('identity')
        return '9999'
    def start(self):
        self.calls.append('start')
        return '7777', 'https://rupload.facebook.com/video-upload/v24.0/7777'
    def upload(self, url, source):
        self.calls.append('upload')
        if self.upload_timeout:
            raise RuntimeError('upload timeout')
    def wait(self, vid, phase):
        self.calls.append(phase)
        if self.pending:
            raise RuntimeError('pending')
    def finish(self, vid, caption):
        self.calls.append('finish')
        if self.finish_timeout:
            raise RuntimeError('finish timeout')


class FacebookTests(unittest.TestCase):
    def test_normal_publish_and_retry_do_not_duplicate(self):
        store, fb = Store(), Facebook()
        result = publisher.publish(SOURCE, store, fb)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['caption'], SOURCE['caption'])
        fb.calls.clear()
        publisher.publish(SOURCE, store, fb)
        self.assertEqual(fb.calls, ['identity'])

    def test_finish_timeout_only_reconciles_original_video(self):
        store, fb = Store(), Facebook()
        fb.finish_timeout = True
        with self.assertRaises(RuntimeError):
            publisher.publish(SOURCE, store, fb)
        self.assertEqual(store.states['1234']['status'], 'publishing')
        fb.calls.clear()
        result = publisher.publish(SOURCE, store, fb)
        self.assertEqual(result['video_id'], '7777')
        self.assertEqual(fb.calls, ['identity', 'publishing_phase'])

    def test_upload_timeout_checks_original_video_before_finish(self):
        store, fb = Store(), Facebook()
        fb.upload_timeout = True
        with self.assertRaises(RuntimeError):
            publisher.publish(SOURCE, store, fb)
        fb.calls.clear()
        publisher.publish(SOURCE, store, fb)
        self.assertEqual(fb.calls, ['identity', 'uploading_phase', 'finish', 'publishing_phase'])

    def test_pending_publish_never_creates_or_finishes_again(self):
        store, fb = Store(), Facebook()
        fb.finish_timeout = True
        with self.assertRaises(RuntimeError): publisher.publish(SOURCE, store, fb)
        fb.calls.clear()
        fb.pending = True
        with self.assertRaises(RuntimeError): publisher.publish(SOURCE, store, fb)
        self.assertEqual(fb.calls, ['identity', 'publishing_phase'])

    def test_failed_persistence_prevents_next_remote_mutation(self):
        for state, forbidden in [('prepared', 'start'), ('started', 'upload'),
                                 ('uploading', 'upload'), ('publishing', 'finish')]:
            with self.subTest(state=state):
                store, fb = Store(), Facebook()
                store.fail_status = state
                with self.assertRaises(RuntimeError): publisher.publish(SOURCE, store, fb)
                self.assertNotIn(forbidden, fb.calls)

    def test_early_manual_source_does_not_suppress_later_scheduled_source(self):
        store, fb = Store(), Facebook()
        publisher.publish(SOURCE, store, fb)
        second = dict(SOURCE, media_id='2222', run_id='8888',
                      video_path='reels/2026-10-04/meowcast-0700-8888.mp4')
        fb.calls.clear()
        publisher.publish(second, store, fb)
        self.assertIn('start', fb.calls)
        self.assertEqual(len(store.states), 2)

    def test_invalid_or_old_instagram_evidence_cannot_publish(self):
        for change in [{'status': 'prepared'}, {'date': '2026-10-03'}, {'slot': '1630'},
                       {'video_path': 'other.mp4'}, {'caption': ''}, {'run_id': '../bad'}]:
            with self.subTest(change=change):
                source = dict(SOURCE, **change)
                with self.assertRaises(RuntimeError):
                    publisher.validate_source(source, SOURCE['date'], SOURCE['slot'])

    def test_existing_page_mismatch_stops(self):
        store, fb = Store(), Facebook()
        publisher.publish(SOURCE, store, fb)
        store.states['1234']['page_id'] = 'wrong'
        fb.calls.clear()
        with self.assertRaises(RuntimeError): publisher.publish(SOURCE, store, fb)
        self.assertEqual(fb.calls, ['identity'])

    def test_dry_run_makes_no_api_calls_or_state_writes(self):
        store, fb = Store(), Facebook()
        self.assertEqual(publisher.publish(SOURCE, store, fb, dry_run=True)['status'], 'dry_run')
        self.assertEqual(fb.calls, [])
        self.assertEqual(store.states, {})

    def test_missing_credentials_preserves_instagram_and_warns(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['publish_facebook.py']), \
                patch.object(publisher, 'Facebook') as fb, patch.object(publisher, 'summary') as summary:
            publisher.main()
            fb.assert_not_called()
            self.assertIn('not configured', summary.call_args.args[0])

    def test_page_identity_rejects_user_token_or_wrong_page(self):
        with patch.dict(os.environ, {'TAIPEI_FB_PAGE_ID': '9999', 'TAIPEI_FB_PAGE_ACCESS_TOKEN': 'secret'}):
            fb = publisher.Facebook()
            for profile in [{'id': '1111', 'name': publisher.PAGE_NAME}, {'id': '9999', 'name': ''}]:
                with patch.object(fb, 'request', return_value=profile):
                    with self.assertRaises(RuntimeError): fb.identity()
            with patch.object(fb, 'request', return_value={'id': '9999', 'name': 'Taipei Meowcast 台北天氣貓'}):
                self.assertEqual(fb.identity(), '9999')

    def test_daily_workflow_preserves_cron_and_runs_fb_after_ig_marker(self):
        import yaml
        workflow = yaml.safe_load(Path('.github/workflows/daily.yml').read_text())
        trigger = workflow.get('on', workflow.get(True))
        self.assertEqual([x['cron'] for x in trigger['schedule']],
            ['7 23 * * *', '17 23 * * *', '7 0 * * *',
             '30 7 * * *', '30 8 * * *', '40 8 * * *', '50 8 * * *', '7 9 * * *'])
        steps = workflow['jobs']['reel']['steps']
        names = [s.get('name', '') for s in steps]
        self.assertGreater(names.index('Publish Taipei Reel to Facebook Page'), names.index('Mark scheduled slot as published'))
        facebook = steps[names.index('Publish Taipei Reel to Facebook Page')]
        self.assertNotIn('dedupe', facebook['if'])
        self.assertEqual(facebook['run'], 'python publish_facebook.py')
        self.assertTrue(facebook['continue-on-error'])
        self.assertIn("steps.facebook.outcome == 'failure'", steps[-1]['if'])

    def test_facebook_only_cannot_republish_instagram_or_block_daily_on_push(self):
        import yaml
        text = Path('.github/workflows/facebook.yml').read_text()
        workflow = yaml.safe_load(text)
        self.assertNotIn('publish_instagram', text)
        self.assertNotIn('concurrency', workflow['jobs']['validate'])
        self.assertIn("inputs.action == 'publish'", workflow['jobs']['publish']['if'])

    def test_upload_rejects_untrusted_url_before_sending_page_token(self):
        with patch.dict(os.environ, {'TAIPEI_FB_PAGE_ID': '9999', 'TAIPEI_FB_PAGE_ACCESS_TOKEN': 'secret'}):
            fb = publisher.Facebook()
            with patch.object(publisher.requests, 'post') as post:
                with self.assertRaises(RuntimeError):
                    fb.upload('https://example.com/upload', 'https://example.com/video.mp4')
                post.assert_not_called()

    def test_source_archive_checks_date_run_and_video_exists(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            store = object.__new__(publisher.Store)
            store.root = Path(root)
            video = store.root / SOURCE['video_path']
            video.parent.mkdir(parents=True)
            video.with_suffix('.json').write_text(json.dumps(SOURCE))
            with self.assertRaises(RuntimeError): store.source(SOURCE['date'], '0700', '5678')
            video.write_bytes(b'video')
            self.assertEqual(store.source(SOURCE['date'], '0700', '5678')['media_id'], '1234')
            with self.assertRaises(ValueError): store.source('../../bad', '0700')


if __name__ == '__main__':
    unittest.main()
