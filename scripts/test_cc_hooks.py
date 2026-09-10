"""Regression probes for formatter hooks changing the Git staging boundary."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class FormatterHookTest(unittest.TestCase):

    def test_staged_changes_deletions_and_unstaged_hunks(self):
        for language, extension in [('python', 'py'), ('java-gradle', 'java')]:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                repo = pathlib.Path(directory)

                def git(*args):
                    return subprocess.check_output(['git', '-C', directory, *args])

                git('init', '-q')
                source = repo / ('Sample.' + extension)
                deleted = repo / ('Deleted.' + extension)
                source.write_text('value = 1\n' if extension == 'py' else 'class Sample {}\n')
                deleted.write_bytes(source.read_bytes())
                if extension == 'java':
                    gradle = repo / 'gradlew'
                    gradle.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> gradle-calls\n')
                    gradle.chmod(0o755)
                git('add', '.')
                git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Hook Test',
                    '-c', 'user.email=hook@example.invalid', 'commit', '-qm', 'baseline')
                hook = repo / '.git/hooks/pre-commit'
                partial = ROOT / 'skills/coding-conventions/templates' / language / 'pre-commit-hook.partial'
                hook.write_text('#!/bin/sh\nset -e\n' + partial.read_text())
                hook.chmod(0o755)

                # Both modifications and deletions must remain staged; the
                # deleted file must never be passed to a formatter/restaged.
                source.write_text('value=2\n' if extension == 'py' else 'class Sample { int value; }\n')
                git('add', source.name)
                git('rm', '-q', deleted.name)
                subprocess.run([str(hook)], cwd=repo, check=True, capture_output=True)
                self.assertEqual(git('diff', '--cached', '--name-status').decode().splitlines(),
                                 ['D\t' + deleted.name, 'M\t' + source.name])
                self.assertEqual(git('show', ':' + source.name), source.read_bytes())
                if extension == 'java':
                    self.assertEqual((repo / 'gradle-calls').read_text().splitlines(),
                                     ['spotlessApply', 'compileJava compileTestJava'])

                # A partial commit must fail before formatting, preserving the
                # index bytes and the user's unstaged working copy exactly.
                staged = git('write-tree')
                source.write_text(source.read_text() + ('# unstaged\n' if extension == 'py' else '// unstaged\n'))
                working = source.read_bytes()
                result = subprocess.run([str(hook)], cwd=repo, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'unstaged', result.stderr)
                self.assertEqual(git('write-tree'), staged)
                self.assertEqual(source.read_bytes(), working)
                if extension == 'java':
                    self.assertEqual(len((repo / 'gradle-calls').read_text().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
