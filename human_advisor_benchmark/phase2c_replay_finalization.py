"""Replay only deterministic response finalization over saved Phase 2C model output."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ai_advisor import finalize_student_answer
from human_advisor_benchmark.runner import check_turn


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'human_advisor_benchmark' / 'runs'
BASE = RUNS / 'phase2c_sol_medium_final_20260908'
REPAIR = RUNS / 'phase2c_sol_medium_quality_repair_20260908'
OUT = RUNS / 'phase2c_model_free_finalization_20260908'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    changed = []
    for number in range(1, 13):
        scenario_id = f'LONG-{number:02d}'
        source = REPAIR if (REPAIR / 'transcripts' / f'{scenario_id}.json').exists() else BASE
        transcript = deepcopy(load(source / 'transcripts' / f'{scenario_id}.json'))
        for turn in transcript['turns']:
            finalization = next((event for event in turn.get('events', [])
                                 if event.get('kind') == 'finalization'), None)
            if not finalization or turn.get('http_status') != 200:
                continue
            tool_results = [event['result'] for event in turn.get('events', [])
                            if event.get('kind') == 'tool']
            before = turn['response']['answer']
            after = finalize_student_answer(
                finalization['raw_answer'], turn['request']['question'], tool_results,
            )
            turn['response']['answer'] = after
            turn['assertions'] = check_turn(turn['expectation'], turn['response'])
            if before != after:
                changed.append({
                    'scenario_id': scenario_id, 'turn': turn['turn'],
                    'before_words': len(before.split()), 'after_words': len(after.split()),
                })
        transcript['replay'] = {
            'kind': 'model_free_finalization', 'source_run_id': source.name,
            'model_output_reused': True,
        }
        save(OUT / 'transcripts' / f'{scenario_id}.json', transcript)
    save(OUT / 'manifest.json', {
        'phase': '2C', 'kind': 'model_free_finalization_replay',
        'source_runs': [BASE.name, REPAIR.name],
        'model_calls': 0, 'astra_used': False,
        'changed_turns': changed,
    })
    print(json.dumps({'changed_turns': changed, 'count': len(changed)}, indent=2))


if __name__ == '__main__':
    main()
