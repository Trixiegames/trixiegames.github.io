"""Store immutable, timestamped editions alongside the current digest."""
from datetime import datetime, timezone
from pathlib import Path
import json

def archive_edition(dest, edition):
    stamp = datetime.fromisoformat(edition['updated_at']).astimezone(timezone.utc)
    relative = Path(stamp.strftime('%Y-%m-%d')) / (stamp.strftime('%H-%M-%S-%f') + '.json')
    root = Path(dest) / 'archive'
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps(edition, ensure_ascii=False, indent=2) + '\n')
    else:
        # An old edition must not change when rendering rules are updated.
        edition = json.loads(target.read_text())
    index_path = root / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else []
    entry = dict(updated_at=edition['updated_at'], path='archive/'+relative.as_posix(), count=len(edition['articles']))
    index = [x for x in index if x['path'] != entry['path']] + [entry]
    index.sort(key=lambda x:datetime.fromisoformat(x['updated_at']), reverse=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    return target
