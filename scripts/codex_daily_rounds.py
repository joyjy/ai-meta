#!/usr/bin/env python3
"""按上海时区统计用户消息轮数；平均值只以有消息的日期为分母。"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
from statistics import median

from codex_phrase_stats import CST, date_bound, scan


def summarize(days):
    total = sum(days.values())
    active = {day: count for day, count in sorted(days.items()) if count > 0}
    return {'active_days': len(active), 'rounds': total,
            'mean': total / len(active) if active else None,
            'median': median(active.values()) if active else None,
            'first': min(active) if active else None,
            'last': max(active) if active else None,
            'daily': active}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path.home() / '.codex/state_5.sqlite')
    parser.add_argument('--since', type=date_bound)
    parser.add_argument('--until', type=date_bound)
    parser.add_argument('--output', type=Path, default=Path.home() / '.codex/analysis/daily-rounds.json')
    args = parser.parse_args()
    if args.since and args.until and args.since > args.until:
        parser.error('since 不能晚于 until')
    days = Counter()
    end = args.until + timedelta(days=1) if args.until else None
    _, stats, gaps, _, _ = scan(args.db, 0, args.since, end, daily_counts=days)
    report = summarize(days)
    report.update({'generated_at': datetime.now(CST).isoformat(),
                   'definition': 'one non-injected user message = one round; source=user; Asia/Shanghai',
                   'selected_threads': stats['selected_threads'],
                   'readable_threads': stats['readable_threads'], 'gaps': gaps,
                   'since': args.since.isoformat() if args.since else None,
                   'until_exclusive': end.isoformat() if end else None})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'daily'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
