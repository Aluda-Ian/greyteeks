from pathlib import Path
import shutil
import re

root = Path(__file__).resolve().parent.parent
assets_src = root / 'templates' / 'campaigns' / 'sofax' / 'assets'
assets_dst = root / 'static' / 'sofax' / 'assets'
assets_dst.parent.mkdir(parents=True, exist_ok=True)

if assets_src.exists():
    if assets_dst.exists():
        for item in assets_src.iterdir():
            target = assets_dst / item.name
            if target.exists():
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    target.unlink()
                    shutil.copy2(item, target)
            else:
                shutil.move(str(item), str(target))
        try:
            assets_src.rmdir()
        except OSError:
            pass
    else:
        shutil.move(str(assets_src), str(assets_dst.parent))

html_dir = root / 'templates' / 'campaigns' / 'sofax'
pattern = re.compile(r'(?P<prefix>(?:href|src)=)(?P<quote>["\'])(?P<path>assets/(?:css|js|fonts)/[^"\']+)(?P=quote)')

for html_file in html_dir.glob('*.html'):
    text = html_file.read_text(encoding='utf-8')
    if '{% load static %}' not in text:
        text = '{% load static %}\n' + text
    new_text = pattern.sub(
        lambda m: f"{m.group('prefix')}{m.group('quote')}{{% static 'sofax/{m.group('path')}' %}}{m.group('quote')}",
        text,
    )
    if new_text != text:
        html_file.write_text(new_text, encoding='utf-8')
