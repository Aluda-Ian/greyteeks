import re
from pathlib import Path
from django.conf import settings

ENV_PATH = Path(settings.BASE_DIR) / '.env'


def _render_env_value(value):
    text = '' if value is None else str(value)
    if not text:
        return ''
    if re.search(r"[\s#'\"\\]", text):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _load_env_lines(path):
    if not path.exists():
        return []
    return path.read_text(encoding='utf-8').splitlines()


def update_env_file(values):
    """Update or append env vars in BASE_DIR/.env."""
    if not values:
        return

    values = {str(k): '' if v is None else str(v) for k, v in values.items()}
    lines = _load_env_lines(ENV_PATH)
    seen = set()
    output_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in line:
            output_lines.append(line)
            continue

        key, _, _ = line.partition('=')
        key = key.strip()
        if key in values:
            output_lines.append(f"{key}={_render_env_value(values[key])}")
            seen.add(key)
        else:
            output_lines.append(line)

    for key, value in values.items():
        if key not in seen:
            output_lines.append(f"{key}={_render_env_value(value)}")

    ENV_PATH.write_text('\n'.join(output_lines).rstrip() + '\n', encoding='utf-8')
