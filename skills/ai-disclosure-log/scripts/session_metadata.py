#!/usr/bin/env python3
"""Read allowlisted metadata for one local Codex session; never emit transcripts."""

import argparse
import json
import os
from pathlib import Path
from uuid import UUID


def read_session(path, session_id):
    result = {'session_id': session_id, 'source': str(path), 'turns': [], 'warnings': []}
    identity = None
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if not line.endswith('\n'):
                    result['warnings'].append('Ignored an incomplete final JSONL record.')
                    break
                raise ValueError('Invalid complete JSONL record; metadata was not exported.') from None
            payload = record.get('payload', {})
            if record.get('type') == 'session_meta':
                identity = payload.get('id')
                result['session'] = {key: payload[key] for key in ('timestamp', 'cli_version', 'source') if key in payload}
            elif record.get('type') == 'turn_context':
                result['turns'].append({
                    'recorded_at_utc': record.get('timestamp'),
                    **{key: payload[key] for key in ('turn_id', 'model', 'effort') if key in payload},
                })
    if identity != session_id:
        raise ValueError('Missing or mismatched session identity; metadata was not exported.')
    if not result['turns']:
        result['warnings'].append('No turn_context records found; model/timing coverage is unknown.')
    return result


def find_session(home, session_id):
    UUID(session_id)  # Reject paths, wildcards, and non-session identifiers.
    matches = [path for name in ('sessions', 'archived_sessions')
               for path in (Path(home) / name).rglob(f'*{session_id}.jsonl')]
    if len(matches) != 1:
        raise ValueError(f'Expected one file for this session; found {len(matches)}.')
    return matches[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-id', default=os.environ.get('CODEX_THREAD_ID'))
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'))
    args = parser.parse_args()
    if not args.session_id:
        parser.error('Supply --session-id or CODEX_THREAD_ID.')
    try:
        result = read_session(find_session(args.codex_home, args.session_id), args.session_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))
