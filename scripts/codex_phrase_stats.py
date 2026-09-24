#!/usr/bin/env python3
"""只读统计 Codex 人工任务中的短消息；Python 标准库，无网络依赖。"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

CST = timezone(timedelta(hours=8))
SKILL_ALIASES = {'ee': 'engineering-exit', 'ff': 'final-form', 'rr': 'review-router',
                 'dd': 'design-direction'}
BARE_SKILLS = set(SKILL_ALIASES) | set(SKILL_ALIASES.values()) | {
    'save-context', 'load-context', 'gtd', 'grill', 'steelman', 'daily-report',
    'coding-conventions', 'agent-doc-hygiene', 'doc-arch-review', 'release-candidate',
    'loop-ledger', 'lark-doc', 'lark-base', 'larkbot', 'skill-creator', 'skill-installer'}
SKILL_LINK = re.compile(r'\[\$([\w:-]+)\]\(([^\n]*?/SKILL\.md)\)')


def request_text(text):
    if '<response-annotations>' in text and '## My request:' in text:
        text = text.split('## My request:', 1)[1]
    return text.strip()


def skill_invocation(text):
    """Count an explicit leading invocation, not mentions or injected skill bodies."""
    text = request_text(text)
    linked = SKILL_LINK.match(text)
    if linked:
        name = linked.group(1).casefold()
    else:
        command = re.match(r'^([$\/]?)([\w-]+)(?=\s|$)', text)
        if not command:
            return None
        prefix, name = command.groups()
        name = name.casefold()
        # Unknown bare/$/slash expressions may be shell commands or variables.
        if name not in BARE_SKILLS:
            return None
    return SKILL_ALIASES.get(name, name)


def short_message(text, max_chars):
    # Annotation envelopes include quoted assistant text; only count the actual request.
    text = request_text(text)
    text = SKILL_LINK.sub(lambda match: '$' + match.group(1), text)
    if (not text or '<' in text or '```' in text or '://' in text
            or '\n' in text or len(text) > max_chars
            or text.startswith(('RS 外部消息', '#', '{', '['))):
        return None
    if re.search(r'[。！？!?；;].*\w', text) or not normalize(text):
        return None
    return text


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    # Keep symbols (+, =, etc.); drop formatting punctuation and whitespace only.
    return ''.join(c for c in text if not c.isspace()
                   and not unicodedata.category(c).startswith('P'))


def meaning_guard(text):
    text = unicodedata.normalize('NFKC', text)
    lowered = text.casefold()
    return (
        bool(re.search(r'不|没|别|无|勿|禁止|停止|暂停|取消|\b(no|not|never|stop|dont)\b', lowered)),
        bool(re.search(r'[?？]|吗|么|是否|能否|什么|为何|为什么|怎么', text)),
        tuple(re.findall(r'\d+(?:\.\d+)*', text)),
        tuple(re.findall(r'[a-z]+', lowered)),
    )


def grams(text):
    return {text[i:i + 2] for i in range(len(text) - 1)}


def similarity(left, right):
    """Normalized Levenshtein similarity: each insertion/deletion/substitution costs 1."""
    if not left and not right:
        return 1.0
    row = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        new = [i]
        for j, other in enumerate(right, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (char != other)))
        row = new
    return 1 - row[-1] / max(len(left), len(right))


def cluster(counts, threshold):
    """Frequency-first representative clustering: avoid transitive similarity chains."""
    exact = defaultdict(Counter)
    for text, count in counts.items():
        norm = normalize(text)
        if norm:
            exact[(norm, meaning_guard(text))][text] += count
    groups, index = [], defaultdict(set)
    ordered = sorted(exact.items(), key=lambda item: (-sum(item[1].values()), item[0]))
    for (norm, guard), variants in ordered:
        candidates = set()
        if len(norm) >= 4:
            if threshold < .8:
                candidates.update(i for i, group in enumerate(groups)
                                  if group['guard'] == guard and len(group['normalized']) >= 4)
            else:
                for gram in grams(norm):
                    candidates.update(index[(guard, gram)])
        best, best_score = None, threshold
        for i in sorted(candidates):
            rep = groups[i]['normalized']
            if min(len(rep), len(norm)) / max(len(rep), len(norm)) < threshold:
                continue
            score = similarity(rep, norm)
            if score >= best_score:
                best, best_score = i, score
        if best is not None:
            groups[best]['variants'].update(variants)
        else:
            i = len(groups)
            groups.append({'normalized': norm, 'guard': guard, 'variants': variants})
            if len(norm) >= 4:
                for gram in grams(norm):
                    index[(guard, gram)].add(i)
    result = []
    for group in groups:
        variants = group['variants'].most_common()
        result.append({'phrase': variants[0][0], 'count': sum(group['variants'].values()),
                       'variants': [{'text': t, 'count': n} for t, n in variants]})
    return sorted(result, key=lambda g: (-g['count'], g['phrase']))


def scan(db, max_chars, start, end, daily_counts=None):
    counts, stats, gaps, examples = Counter(), Counter(), [], {}
    seen, skill_counts, skill_examples = set(), Counter(), {}
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        rows = conn.execute('SELECT id, thread_source, rollout_path FROM threads').fetchall()
    stats['manifest_threads'] = len(rows)
    for thread_id, source, path in rows:
        # Unknown provenance is explicitly excluded rather than guessed from a title.
        if source != 'user':
            stats['excluded_source_' + str(source)] += 1
            continue
        stats['selected_threads'] += 1
        if not path:
            gaps.append({'thread_id': thread_id, 'error': 'missing rollout_path'})
            continue
        try:
            with Path(path).open() as stream:
                stats['readable_threads'] += 1
                for lineno, line in enumerate(stream, 1):
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        gaps.append({'path': path, 'line': lineno, 'error': 'invalid JSON'})
                        continue
                    payload = item.get('payload', {})
                    if (item.get('type') != 'response_item'
                            or payload.get('type') != 'message'
                            or payload.get('role') != 'user'):
                        continue
                    stats['user_message_records'] += 1
                    stamp = item.get('timestamp')
                    try:
                        when = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                        if when.tzinfo is None:
                            raise ValueError('timestamp without timezone')
                    except (AttributeError, TypeError, ValueError):
                        gaps.append({'path': path, 'line': lineno, 'error': 'invalid timestamp'})
                        continue
                    if (start and when < start) or (end and when >= end):
                        continue
                    text = '\n'.join(c.get('text', '') for c in payload.get('content', [])
                                     if c.get('type') in ('input_text', 'output_text'))
                    # Copies in forked rollouts retain timestamp and text; real repeats don't.
                    identity = (when.isoformat(), text)
                    if identity in seen:
                        stats['duplicate_records'] += 1
                        continue
                    seen.add(identity)
                    if daily_counts is not None:
                        request = request_text(text)
                        injected = re.match(
                            r'^(?:<|# AGENTS\.md instructions|# Instructions for|RS 外部消息|'
                            r'You are handling one fixed-schema Rollerskate|'
                            r'The following is the Codex agent history|Automation:|Automation ID:)',
                            request)
                        if request and not injected:
                            daily_counts[when.astimezone(CST).date().isoformat()] += 1
                    anchor = {'thread_id': thread_id, 'path': path, 'line': lineno,
                              'timestamp': stamp}
                    skill = skill_invocation(text)
                    if skill:
                        skill_counts[skill] += 1
                        skill_examples.setdefault(skill, anchor)
                    text = short_message(text, max_chars)
                    if text is None:
                        stats['filtered_messages'] += 1
                        continue
                    counts[text] += 1
                    stats['short_messages'] += 1
                    examples.setdefault(text, anchor)
        except OSError as exc:
            gaps.append({'path': path, 'error': str(exc)})
    skills = [{'skill': name, 'count': count, 'example': skill_examples[name]}
              for name, count in skill_counts.most_common()]
    return counts, stats, gaps, examples, skills


def date_bound(value):
    return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=CST)


def is_ack(text):
    # Explicit whole-message allowlist; never remove an affirmative prefix from a request.
    return normalize(text) in {
        'ok', 'okay', 'yes', 'y', '好', '好的', '好啊', '好呀', '好吧', '好哒',
        '可以', '可以的', '行', '行的', '行吧', '嗯', '嗯嗯', '恩', '是', '是的',
        '对', '对的', '没错', '同意', '收到', '明白', '明白了', '了解', '了解了',
        '知道了', '没问题', '没毛病', '好嘞', '好滴', 'ok好的', '嗯好的', '嗯可以'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path.home() / '.codex/state_5.sqlite')
    parser.add_argument('--since', type=date_bound, help='起始日期，上海时区，含当天')
    parser.add_argument('--until', type=date_bound, help='结束日期，上海时区，含当天')
    parser.add_argument('--max-chars', type=int, default=30)
    parser.add_argument('--threshold', type=float, default=.86, help='字符相似度，默认 0.86')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--exclude-acks', action='store_true', help='排除整条纯确认回复')
    parser.add_argument('--exclude-skills', action='store_true', help='短句榜排除 skill 调用，独立 skill 榜仍保留')
    parser.add_argument('--output', type=Path, default=Path.home() / '.codex/analysis/phrase-results.json',
                        help='完整结果 JSON，默认 ~/.codex/analysis/phrase-results.json；top 仅限制终端展示')
    args = parser.parse_args()
    if not 0 < args.threshold <= 1 or args.max_chars < 1 or args.top < 1:
        parser.error('threshold 必须在 (0,1]；max-chars/top 必须为正整数')
    if args.since and args.until and args.since > args.until:
        parser.error('since 不能晚于 until')
    end = args.until + timedelta(days=1) if args.until else None
    counts, stats, gaps, examples, skills = scan(args.db, args.max_chars, args.since, end)
    kept, excluded = Counter(), []
    for text, count in counts.items():
        reason = ('acknowledgement' if args.exclude_acks and is_ack(text) else
                  'skill_invocation' if args.exclude_skills and skill_invocation(text) else None)
        if reason:
            excluded.append({'text': text, 'count': count, 'reason': reason,
                             'example': examples[text]})
        else:
            kept[text] = count
    groups = cluster(kept, args.threshold)
    for group in groups:
        for variant in group['variants']:
            variant['example'] = examples[variant['text']]
    report = {'generated_at': datetime.now(CST).isoformat(),
              'parameters': {'since': args.since.isoformat() if args.since else None,
                             'until_exclusive': end.isoformat() if end else None,
                             'max_chars': args.max_chars, 'threshold': args.threshold,
                             'exclude_acks': args.exclude_acks, 'exclude_skills': args.exclude_skills,
                             'source': 'thread_source=user; response_item user messages'},
              'stats': dict(stats), 'unique_phrases': len(counts),
              'cluster_count': len(groups), 'gaps': gaps, 'groups': groups,
              'included_unique_phrases': len(kept), 'excluded_phrases': excluded,
              'skill_calls': skills}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('排名\t次数\t代表短句\t原话变体（前五个）')
    for i, group in enumerate(groups[:args.top], 1):
        variants = ' / '.join(f"{v['text']} ×{v['count']}" for v in group['variants'][:5])
        print(f"{i}\t{group['count']}\t{group['phrase']}\t{variants}")
    print('Skill 调用（不受短句长度限制；仅消息开头的明确调用）')
    for row in skills[:args.top]:
        print(f"{row['skill']}\t{row['count']}")
    print(json.dumps({'stats': dict(stats), 'gaps': len(gaps),
                      'unique_phrases': len(counts), 'clusters': len(groups)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
