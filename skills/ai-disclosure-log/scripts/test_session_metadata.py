"""Self-check metadata privacy, identity checks, and incomplete live records."""

import json
from pathlib import Path
import tempfile
import unittest

from session_metadata import find_session, read_session


class MetadataTest(unittest.TestCase):
    def test_metadata_only_and_identity(self):
        sid = '01a160e2-45e3-7c51-a7e6-2954964085f3'
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / 'sessions').mkdir()
            path = home / 'sessions' / f'rollout-{sid}.jsonl'
            records = [
                {'type': 'session_meta', 'payload': {'id': sid, 'timestamp': '2026-10-21T23:53:24Z', 'secret': 'PRIVATE'}},
                {'type': 'response_item', 'payload': {'role': 'system', 'text': 'PRIVATE'}},
                {'type': 'turn_context', 'timestamp': '2026-10-21T23:53:26Z', 'payload': {'model': 'model-a', 'effort': 'high', 'private_instructions': 'PRIVATE'}},
                {'type': 'turn_context', 'payload': {'model': 'model-b', 'effort': 'low'}},
            ]
            path.write_text(''.join(json.dumps(row) + '\n' for row in records) + '{"incomplete":')
            result = read_session(find_session(home, sid), sid)
            self.assertNotIn('PRIVATE', json.dumps(result))
            self.assertEqual([turn['model'] for turn in result['turns']], ['model-a', 'model-b'])
            self.assertTrue(result['warnings'])
            with self.assertRaises(ValueError):
                read_session(path, 'another-session')
            with self.assertRaises(ValueError):
                find_session(home, '../*')
            (home / 'archived_sessions').mkdir()
            (home / 'archived_sessions' / path.name).write_text(path.read_text())
            with self.assertRaises(ValueError):
                find_session(home, sid)
            path.write_text('not json\n')
            with self.assertRaises(ValueError):
                read_session(path, sid)


if __name__ == '__main__':
    unittest.main()
