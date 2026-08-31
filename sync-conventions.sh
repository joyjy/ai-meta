#!/usr/bin/env bash
# sync-conventions.sh — 将 coding-conventions 模板内容展开写入项目 AGENTS.md
#
# 用法：
#   ./sync-conventions.sh                  # 扫描默认搜索目录
#   ./sync-conventions.sh /path/to/dir     # 只处理指定目录
#
# 触发条件：AGENTS.md 中包含以下 begin/end 受控块：
#   <!-- coding-conventions:begin general -->
#   ...
#   <!-- coding-conventions:end general -->
#
# begin marker 同时声明启用的模板 ID；同步器幂等更新块内容。
# 旧的 `<!-- coding-conventions: <id> -->` 声明会在同步时迁移并移除。

set -euo pipefail

# 默认搜索目录
SEARCH_DIRS=(
  "$HOME/Documents/projects"
  "$HOME/Documents/me/Projects"
)

if [ $# -gt 0 ]; then
  SEARCH_DIRS=("$@")
fi

process_file() {
  local agents_file="$1"
  grep -Eq '<!-- coding-conventions:(begin | )' "$agents_file" || return 0

  python3 - "$agents_file" "$HOME" <<'PYEOF'
import sys, os, re

agents_file, home = sys.argv[1], sys.argv[2]
content = open(agents_file).read()

LEGACY_DECL_RE = re.compile(r'<!-- coding-conventions: (?!begin |end )([^>]+?) -->')
BEGIN_RE = re.compile(r'<!-- coding-conventions:begin ([^>]+?) -->')
TEMPLATE_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(agents_file), 'skills/coding-conventions/templates')
)
if not os.path.isdir(TEMPLATE_ROOT):
    TEMPLATE_ROOT = os.path.realpath(
        os.path.join(home, '.ai/skills/coding-conventions/templates')
    )
PREFERENCES_ROOT = os.path.realpath(os.path.join(os.path.dirname(TEMPLATE_ROOT), 'preferences'))
PREFERENCES_AGENTS = os.path.realpath(os.path.join(home, 'Documents/projects/AGENTS.md'))
IS_PREFERENCES_AGENTS = os.path.realpath(agents_file) == PREFERENCES_AGENTS
CONVENTIONS_SECTION = '## 编码规范'
KNOWN_TEMPLATES = {
    'general',
    'api',
    'java-gradle',
    'python',
    'testing',
    'node-test-kit',
    'lintest',
    'cli',
    'frontend',
    'git',
}
DEPRECATED_TEMPLATES = {'gitlab'}

def resolve(spec, home):
    spec = spec.strip()
    if spec in KNOWN_TEMPLATES:
        return os.path.join(TEMPLATE_ROOT, spec, 'AGENTS.md'), spec
    path = spec.replace('~', home, 1) if spec.startswith('~') else spec
    path = os.path.realpath(path)  # 兼容旧路径声明
    return path, os.path.basename(os.path.dirname(path))

def marker(name, kind):
    return f'<!-- coding-conventions:{kind} {name} -->'

def remove_managed_block(content, name):
    begin = marker(name, 'begin')
    end = marker(name, 'end')
    return re.sub(
        re.escape(begin) + r'.*?' + re.escape(end) + r'\n?',
        '',
        content,
        flags=re.DOTALL,
    )

def preference_paths(tpl_name):
    if not IS_PREFERENCES_AGENTS or tpl_name != 'general':
        return []
    if not os.path.isdir(PREFERENCES_ROOT):
        return []
    return [
        os.path.join(PREFERENCES_ROOT, name)
        for name in sorted(os.listdir(PREFERENCES_ROOT))
        if name.endswith('.md') and os.path.isfile(os.path.join(PREFERENCES_ROOT, name))
    ]

def preference_content(paths):
    return '\n\n'.join(open(path).read().strip() for path in paths)

def demote_headings(text, levels):
    def repl(match):
        hashes = match.group(1)
        return '#' * min(6, len(hashes) + levels) + match.group(2)
    return re.sub(r'^(#{1,6})(\s+)', repl, text, flags=re.MULTILINE)

def ensure_conventions_section(content):
    if IS_PREFERENCES_AGENTS:
        return content
    first = BEGIN_RE.search(content)
    if not first:
        return content
    before = content[:first.start()].rstrip()
    if before.splitlines() and before.splitlines()[-1].strip() == CONVENTIONS_SECTION:
        return content
    return before + '\n\n' + CONVENTIONS_SECTION + '\n\n' + content[first.start():]

def inject(content, tpl_name, tpl_content, *, prepend=False):
    begin = marker(tpl_name, 'begin')
    end   = marker(tpl_name, 'end')
    block = f'{begin}\n{tpl_content.rstrip()}\n{end}\n'

    if begin in content:
        # 替换已有块
        pattern = re.compile(
            re.escape(begin) + r'.*?' + re.escape(end) + r'\n?',
            re.DOTALL
        )
        return pattern.sub(block, content), 'updated'
    first = BEGIN_RE.search(content)
    if prepend and first:
        before = content[:first.start()].rstrip()
        after = content[first.start():]
        return before + '\n\n' + block + '\n' + after, 'injected'
    return content.rstrip() + '\n\n' + block, 'injected'

changed = False

legacy_specs = []
for match in list(LEGACY_DECL_RE.finditer(content)):
    spec = match.group(1).strip()
    tpl_path, tpl_name = resolve(spec, home)
    if (spec in DEPRECATED_TEMPLATES or tpl_name in DEPRECATED_TEMPLATES
            or os.path.isfile(tpl_path)):
        content = content.replace(match.group(0) + '\n', '', 1)
        content = content.replace(match.group(0), '', 1)
        legacy_specs.append(spec)
        print(f'  migrated legacy declaration [{tpl_name}]: {agents_file}')
        changed = True
    else:
        print(f'  [WARN] 模板不存在，保留旧声明: {tpl_path}')

block_specs = [m.group(1).strip() for m in BEGIN_RE.finditer(content)]
decl_specs = list(dict.fromkeys([*legacy_specs, *block_specs]))
has_general = any(
    spec == 'general' or spec.endswith('templates/general/AGENTS.md')
    for spec in decl_specs
)

def parent_has_general(path):
    current = os.path.dirname(os.path.abspath(path))
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            return False
        parent_agents = os.path.join(parent, 'AGENTS.md')
        if os.path.isfile(parent_agents):
            parent_content = open(parent_agents).read()
            return bool(re.search(
                r'<!-- coding-conventions:begin general -->'
                r'|<!-- coding-conventions: (general|[^>]+templates/general/AGENTS\.md) -->',
                parent_content
            ))
        current = parent

if decl_specs and not has_general and not parent_has_general(agents_file):
    decl_specs.insert(0, 'general')
    print(f'  added [general block]: {agents_file}')

for spec in decl_specs:
    tpl_path, tpl_name = resolve(spec, home)

    if spec in DEPRECATED_TEMPLATES or tpl_name in DEPRECATED_TEMPLATES:
        deprecated_name = spec if spec in DEPRECATED_TEMPLATES else tpl_name
        content = remove_managed_block(content, deprecated_name)
        print(f'  removed deprecated [{deprecated_name}]: {agents_file}')
        changed = True
        continue

    if not os.path.isfile(tpl_path):
        print(f'  [WARN] 模板不存在，跳过: {tpl_path}')
        continue

    prefs = preference_paths(tpl_name)
    tpl_content = preference_content(prefs) if prefs else open(tpl_path).read()
    if not prefs and not IS_PREFERENCES_AGENTS:
        tpl_content = demote_headings(tpl_content, 2)
    content, action = inject(
        content,
        tpl_name,
        tpl_content,
        prepend=tpl_name == 'general',
    )
    print(f'  {action} [{tpl_name}]: {agents_file}')
    changed = True

if changed:
    content = ensure_conventions_section(content)
    content = re.sub(r'\n{3,}(?=<!-- coding-conventions:)', '\n\n', content)
    content = re.sub(
        r'(<!-- coding-conventions:end [^>]+ -->)\n{3,}(?=<!-- coding-conventions:)',
        r'\1\n\n',
        content,
    )
    open(agents_file, 'w').write(content)
PYEOF
}

echo "==> sync-conventions"

for target in "${SEARCH_DIRS[@]}"; do
  if [ -f "$target" ]; then
    # 直接传了文件路径
    process_file "$target"
  elif [ -d "$target" ]; then
    while IFS= read -r -d '' f; do
      process_file "$f"
    done < <(find "$target" -maxdepth 3 -name "AGENTS.md" -print0 2>/dev/null)
  fi
done

echo "==> done"
