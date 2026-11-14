"""CLI-level safety regressions using a scripted GitLab transport, never a real write."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
FAKE_GLAB = '''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
p=Path(os.environ['GITLAB_FIXTURE'])
s=json.loads(p.read_text()); step=s['steps'].pop(0)
args=sys.argv[1:]
for token in step.get('expect',[]):
    assert token in args, (token,args)
call={'args':args}
if '--input' in args:
    call['body']=json.loads(Path(args[args.index('--input')+1]).read_text())
s['calls'].append(call);p.write_text(json.dumps(s))
if step.get('sleep'):time.sleep(step['sleep'])
if step.get('error'):print(step['error'],file=sys.stderr)
if 'response' in step:print(json.dumps(step['response']))
sys.exit(step.get('code',0))
'''
SHA = 'a' * 40
PROJECT = {'id': 7, 'web_url': 'https://gitlab.example/g/p', 'path_with_namespace': 'g/p'}
PIPELINE = {'id': 81, 'project_id': 7, 'sha': SHA, 'status': 'success'}
MR = {'sha': SHA, 'head_pipeline': PIPELINE}


class GitlabWorkflowTest(unittest.TestCase):
    def call(self, cli, args, steps):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            glab = root / 'glab'; glab.write_text(FAKE_GLAB); glab.chmod(0o755)
            fixture = root / 'state.json'; fixture.write_text(json.dumps({'steps': steps, 'calls': []}))
            env = {**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH'],
                   'GITLAB_FIXTURE': str(fixture), 'AI_META_USAGE_DIR': str(root / 'usage')}
            proc = subprocess.run([str(SCRIPTS / cli), *args], env=env, text=True, capture_output=True, timeout=5)
            state = json.loads(fixture.read_text())
            usage = subprocess.run([str(SCRIPTS / cli), 'usage'], env=env, text=True, capture_output=True, timeout=5)
            self.assertEqual(0, usage.returncode, usage.stderr)
            self.assertEqual(1, json.loads(usage.stdout)['total_calls'])
            return proc, state

    def test_branch_scan_cli_paginates_and_keeps_settings_separate(self):
        settings = {'default_branch': 'main', 'merge_method': 'ff', 'only_allow_merge_if_pipeline_succeeds': True,
                    'allow_merge_on_skipped_pipeline': False, 'remove_source_branch_after_merge': True,
                    'only_allow_merge_if_all_discussions_are_resolved': True, 'squash_option': 'default_on'}
        prefix = [{'response': settings}, {'response': {}}, {'response': []},
                  {'response': {'branch_name_regex': '.*'}}, {'response': []}]
        args = ['--repo', 'g/p', '--flow', 'l2', '--scan-branches', '--json']
        proc, state = self.call('gitlab-project-lint', args, prefix + [
            {'expect': ['projects/g%2Fp/repository/branches?per_page=100&page=1'],
             'response': [{'name': 'main'}] + [{'name': f'feat-{i}'} for i in range(99)]},
            {'expect': ['projects/g%2Fp/repository/branches?per_page=100&page=2'],
             'response': [{'name': 'legacy-branch'}]},
        ])
        self.assertEqual(1, proc.returncode, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(['legacy-branch'], result['branch_scan']['violations'])
        self.assertEqual(101, result['branch_scan']['count'])
        self.assertTrue(result['branch_scan']['complete'])
        self.assertTrue(result['findings'])
        self.assertFalse(state['steps'])
        proc, _ = self.call('gitlab-project-lint', args, prefix + [{'response': {'message': 'bad'}}])
        self.assertEqual(2, proc.returncode)
        self.assertIn('scan incomplete', proc.stderr)
        self.assertEqual('', proc.stdout)

    def test_sha_wait_uses_pinned_pipeline_and_paginates_jobs(self):
        proc, state = self.call('gitlab-ci', ['wait', '--sha', SHA, '-R', 'g/p', '--interval', '0.001'], [
            {'response': PROJECT},
            {'expect': [f'projects/7/pipelines?sha={SHA}&order_by=id&sort=desc&per_page=1'], 'response': [PIPELINE]},
            {'expect': ['projects/7/pipelines/81'], 'response': {**PIPELINE, 'status': 'running'}},
            {'expect': ['projects/7/pipelines/81'], 'response': PIPELINE},
            {'expect': ['--paginate', 'projects/7/pipelines/81/jobs?per_page=100'], 'response': [{'id': 1, 'name': 'test', 'status': 'success'}]},
        ])
        self.assertEqual(0, proc.returncode, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result['complete']); self.assertEqual(SHA, result['pipeline']['sha'])
        self.assertEqual('test', result['jobs'][0]['name']); self.assertFalse(state['steps'])

    def test_mr_wait_rejects_old_green_pipeline_after_new_push(self):
        proc, state = self.call('gitlab-ci', ['wait', '--mr', 'https://gitlab.example/g/p/-/merge_requests/12'], [
            {'response': PROJECT}, {'response': MR}, {'response': PIPELINE},
            {'response': {**MR, 'sha': 'b' * 40}},
        ])
        self.assertEqual(4, proc.returncode, proc.stderr)
        self.assertEqual('superseded', json.loads(proc.stdout)['outcome'])
        self.assertFalse(json.loads(proc.stdout)['complete'])

    def test_mr_selection_refuses_stale_green_head_pipeline(self):
        proc, state = self.call('gitlab-ci', ['wait', '--mr', '12', '-R', 'g/p'], [
            {'response': PROJECT}, {'response': {**MR, 'sha': 'b' * 40}},
        ])
        self.assertEqual(1, proc.returncode)
        self.assertFalse(json.loads(proc.stdout)['complete'])
        self.assertIn('SHA differs', json.loads(proc.stdout)['error'])
        self.assertFalse(state['steps'])

    def test_wait_deadline_bounds_hung_request(self):
        proc, _ = self.call('gitlab-ci', ['wait', '81', '-R', 'g/p', '--timeout', '0.1'], [
            {'sleep': 2, 'response': PROJECT},
        ])
        self.assertEqual(124, proc.returncode, proc.stderr)
        self.assertEqual('timeout', json.loads(proc.stdout)['outcome'])

    def test_manual_pipeline_is_not_success(self):
        proc, _ = self.call('gitlab-ci', ['wait', '81', '-R', 'g/p'], [
            {'response': PROJECT}, {'response': {**PIPELINE, 'status': 'manual'}}, {'response': []},
        ])
        self.assertEqual(3, proc.returncode, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)['complete'])

    def test_title_and_exact_description_share_one_write(self):
        # Legacy Managed PR Agent tails lack the footer required by --description-file.
        before = {'title': 'Before', 'description':
                  'Colleague\r\n\n## Release Candidate\nold\n\n## PR Type\nEnhancement\n\n## Description\n  managed tail\n'}
        after = {'title': 'After', 'description': before['description'].replace('old', 'new')}
        proc, state = self.call('gitlab-mr', ['update', '12', '-R', 'g/p', '--hostname', 'gitlab.example',
                                          '--title', 'After', '--replace', 'old', 'new'], [
            {'response': before}, {'response': before},
            {'expect': ['PUT', '--header', 'Content-Type: application/json'], 'response': after}, {'response': after},
        ])
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(after, state['calls'][2]['body'])
        self.assertEqual(['description', 'title'], json.loads(proc.stdout)['verified_fields'])

    def test_replace_refuses_duplicates_and_concurrent_edits(self):
        for before, later in [({'description': 'old old'}, None),
                              ({'description': 'old\n'}, {'description': 'old\r\n'})]:
            with self.subTest(before=before):
                steps = [{'response': before}]
                if later: steps.append({'response': later})
                proc, state = self.call('gitlab-mr', ['update', '12', '-R', 'g/p', '--replace', 'old', 'new'], steps)
                self.assertEqual(1, proc.returncode)
                self.assertTrue(all('--input' not in c['args'] for c in state['calls']))

    def test_failed_update_readback_is_ambiguous_without_retry(self):
        before = {'title': 'Before', 'description': 'keep'}
        proc, state = self.call('gitlab-mr', ['update', '12', '-R', 'g/p', '--title', 'After'], [
            {'response': before}, {'response': before}, {'response': {}},
            {'code': 1, 'error': 'HTTP 503'},
        ])
        self.assertEqual(1, proc.returncode)
        self.assertIn('ambiguous', proc.stderr)
        self.assertEqual(1, sum('--input' in c['args'] for c in state['calls']))
        self.assertEqual({'title': 'After'}, state['calls'][2]['body'])


if __name__ == '__main__':
    unittest.main()
