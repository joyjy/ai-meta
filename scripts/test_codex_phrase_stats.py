import unittest
from collections import Counter
from io import StringIO
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from codex_phrase_stats import cluster, scan, short_message, similarity, skill_invocation, is_ack
from codex_daily_rounds import summarize


class PhraseTests(unittest.TestCase):
    def test_active_day_denominator_excludes_empty_dates(self):
        result = summarize({'2026-09-01': 10, '2026-09-02': 0, '2026-09-03': 20})
        self.assertEqual(result['active_days'], 2)
        self.assertEqual(result['mean'], 15)
        self.assertIsNone(summarize({})['mean'])

    def test_ack_filter_does_not_remove_real_requests(self):
        for text in ['ＯＫ！', '好的', '嗯嗯', '可以', '是的', 'Y']:
            self.assertTrue(is_ack(text))
        for text in ['OK，继续修复', '可以自动提交了', '不可以', '改吧', '知道了然后呢']:
            self.assertFalse(is_ack(text))

    def test_skill_links_arguments_aliases_and_injections(self):
        linked = '[$save-context](/Users/example/skills/save-context/SKILL.md) partner'
        self.assertEqual(short_message(linked, 30), '$save-context partner')
        self.assertEqual(skill_invocation(linked), 'save-context')
        for text in ['/ee', 'ee', '$engineering-exit',
                     '[$ee](/skills/engineering-exit/SKILL.md)']:
            self.assertEqual(skill_invocation(text), 'engineering-exit')
        self.assertEqual(skill_invocation('/rr ' + '检查' * 100), 'review-router')
        for text in ['你觉得 ee 怎么样', '<skill>save-context</skill>',
                     '```\n/ee\n```', '/Users/example/file', '$pwd', '$HOME']:
            self.assertIsNone(skill_invocation(text))

    def test_automation_and_quoted_text_are_not_user_phrases(self):
        for text in ['<hook_prompt>继续</hook_prompt>', 'RS 外部消息：继续',
                     '```继续```', 'https://example.com', '先检查。再修改']:
            self.assertIsNone(short_message(text, 30))
        envelope = '<response-annotations>quoted</response-annotations>\n## My request:\n继续'
        self.assertEqual(short_message(envelope, 30), '继续')

    def test_edit_distance_and_variants(self):
        self.assertEqual(similarity('帮我继续检查一下', '帮我继续检查下'), .875)
        result = cluster(Counter({'帮我继续检查一下': 4, '帮我继续检查下': 2}), .86)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['count'], 6)
        self.assertEqual(len(result[0]['variants']), 2)

    def test_guard_opposites_questions_numbers_and_commands(self):
        pairs = [('请继续执行后面的工作', '请不要继续执行后面的工作'),
                 ('继续检查一下', '继续检查一下？'),
                 ('检查第123456号任务', '检查第123457号任务'),
                 ('请执行git push命令', '请执行git pull命令'),
                 ('好的', '好呀')]
        for left, right in pairs:
            with self.subTest(pair=(left, right)):
                self.assertEqual(len(cluster(Counter({left: 1, right: 1}), .8)), 2)

    def test_formatting_normalization_retains_originals(self):
        result = cluster(Counter({'ＯＫ': 2, 'ok': 3, 'OK！': 1}), .86)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['count'], 6)

    def test_no_transitive_chaining(self):
        result = cluster(Counter({'甲乙丙丁戊己庚辛': 3, '甲乙丙丁戊己庚壬': 2,
                                  '甲乙丙丁戊己癸壬': 1}), .86)
        self.assertEqual(len(result), 2)

    def test_no_top_limit_in_clustering(self):
        counts = Counter({f'检查任务{i}': i + 1 for i in range(20)})
        result = cluster(counts, .86)
        self.assertEqual(len(result), 20)
        self.assertEqual(sum(g['count'] for g in result), sum(counts.values()))

    def test_fork_dedup_preserves_real_repetition_and_excludes_automation(self):
        def message(second):
            return json.dumps({'timestamp': f'2026-09-14T00:00:0{second}Z',
                               'type': 'response_item', 'payload': {
                                   'type': 'message', 'role': 'user',
                                   'content': [{'type': 'input_text', 'text': '继续'}]}}) + '\n'
        conn = MagicMock()
        conn.__enter__.return_value.execute.return_value.fetchall.return_value = [
            ('a', 'user', '/a'), ('b', 'user', '/b'), ('c', 'automation', '/c')]
        days = Counter()
        with patch('codex_phrase_stats.sqlite3.connect', return_value=conn), patch.object(
                Path, 'open', side_effect=lambda: StringIO(message(1) + message(2))):
            counts, stats, gaps, _, _ = scan(Path('/db'), 30, None, None, daily_counts=days)
        self.assertEqual(counts['继续'], 2)
        self.assertEqual(stats['duplicate_records'], 2)
        self.assertEqual(stats['excluded_source_automation'], 1)
        self.assertEqual(gaps, [])
        self.assertEqual(days, {'2026-09-14': 2})


if __name__ == '__main__':
    unittest.main()
