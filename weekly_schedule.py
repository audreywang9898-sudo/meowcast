"""Resolve weekly issue dates in Taiwan time, regardless of city DST."""
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def resolve(event, manual_date='', manual_publish=False, now=None):
    now = (now or datetime.now(ZoneInfo('Asia/Taipei'))).astimezone(ZoneInfo('Asia/Taipei'))
    today = now.date()
    if event == 'schedule':
        if today.weekday() != 6 or now.hour < 8:
            return {'run': False, 'publish': False, 'issue_date': today.isoformat()}
        issue = today
        publish = True
    elif event in ('workflow_dispatch', 'push'):
        issue = date.fromisoformat(manual_date) if manual_date else today + timedelta(days=(6 - today.weekday()) % 7)
        publish = event == 'workflow_dispatch' and manual_publish
        if publish and (issue != today or today.weekday() != 6):
            raise ValueError('Manual production publish must target today, Sunday in Taiwan time')
    else:
        raise ValueError('Unexpected weekly trigger')
    if issue.weekday() != 6: raise ValueError('Weekly issue must be Sunday')
    return {'run': True, 'publish': publish, 'issue_date': issue.isoformat()}


if __name__ == '__main__':
    result = resolve(os.environ.get('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                     os.environ.get('ISSUE_DATE', ''), os.environ.get('PUBLISH', 'false').lower() == 'true')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        for k, v in result.items(): f.write(f'{k}={str(v).lower() if isinstance(v, bool) else v}\n')
    print(result)
