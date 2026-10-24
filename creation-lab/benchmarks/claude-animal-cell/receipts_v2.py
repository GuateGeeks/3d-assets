"""Receipt amendment v1.5 for the Claude animal-cell benchmark.

bench.py is frozen by hash, so its `receipts` command is not edited. Claude
Code transcripts usually store the usage of a message as seen at stream start;
bench.py keeps the last entry per message, which heavily undercounts output.
This script reuses bench.receipt() (model, effort, audit, timing) unchanged and
adds, per agent:

- tokensMaxPerMessage: field-wise maximum over every entry of each message.id.
- visibleOutputTokensEstimate: (characters of text + JSON tool_use input) / 3.5,
  deduplicated per message.id and block. Thinking is omitted in transcripts, so
  this is only a lower bound for visible output, never a cost measurement.
- outputTokensLowerBound: max of the two output figures.
- scratchpadReferences: tool calls that touch a shared session scratchpad.
- activeSecondsV2: work segments split at every non-tool-result user entry,
  including SendMessage resumes, so idle gaps between stages are excluded.

Cost stays NOT_AVAILABLE. Usage: receipts_v2.py --root BATCH --transcripts DIR
"""
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bench', HERE / 'bench.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
FIELDS = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')


def usage_v2(log):
    maxima, blocks, thinking = defaultdict(dict), {}, defaultdict(int)
    for line in log.read_text(encoding='utf-8').splitlines():
        entry = json.loads(line)
        if entry.get('type') != 'assistant':
            continue
        message = entry['message']
        key = message.get('id') or entry.get('requestId') or entry.get('uuid')
        usage = message.get('usage') or {}
        for field in FIELDS:
            maxima[key][field] = max(maxima[key].get(field, 0), usage.get(field) or 0)
        details = usage.get('output_tokens_details') or {}
        thinking[key] = max(thinking[key], details.get('thinking_tokens') or 0)
        for index, block in enumerate(message.get('content', [])):
            if block.get('type') == 'text':
                blocks[(key, 'text', block.get('text', ''))] = len(block.get('text', ''))
            elif block.get('type') == 'tool_use':
                text = json.dumps(block.get('input', {}), ensure_ascii=False)
                blocks[(key, block.get('id') or index, 'tool')] = len(block.get('name', '')) + len(text)
    totals = {field: sum(m.get(field, 0) for m in maxima.values()) for field in FIELDS}
    visible = round(sum(blocks.values()) / 3.5)
    return {'tokensMaxPerMessage': totals, 'reportedThinkingTokensMaxPerMessage': sum(thinking.values()),
            'visibleOutputChars': sum(blocks.values()), 'visibleOutputTokensEstimate': visible,
            'outputTokensLowerBound': max(totals['output_tokens'], visible), 'apiMessages': len(maxima)}


def active_seconds(log):
    """Sum of work segments. A segment starts at any non-tool-result user entry,
    including isMeta resumes (SendMessage), and ends at the last entry before the
    next one, so idle time between hand-back and resume is excluded."""
    from datetime import datetime
    segments, current = [], None
    for line in log.read_text(encoding='utf-8').splitlines():
        entry = json.loads(line)
        stamp = entry.get('timestamp')
        if not stamp:
            continue
        moment = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if entry.get('type') == 'user':
            content = entry.get('message', {}).get('content')
            result = isinstance(content, list) and any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content)
            if not result and (current is None or (moment - current[1]).total_seconds() > 1):
                current = [moment, moment]
                segments.append(current)
                continue
        if current:
            current[1] = moment
    return round(sum((end - start).total_seconds() for start, end in segments), 3), len(segments)


def scratchpad(receipt_calls):
    return [c for c in receipt_calls if 'scratchpad' in json.dumps(c.get('input', {}), ensure_ascii=False)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=bench.DEFAULT_ROOT)
    p.add_argument('--transcripts', type=Path, required=True)
    args = p.parse_args()
    root = args.root
    agents = bench.read(root / 'coordinator/agents.json')
    mapping = bench.mapping(root)
    profile = bench.profile()
    out = root / 'coordinator/receipts-v2'
    out.mkdir(exist_ok=True)
    jobs = [('author', replica, agent, root / 'authors' / replica,
             profile['conditions'][mapping['replicas'][replica]['condition']]['author']['models'][0])
            for replica, agent in agents['authors'].items()]
    jobs += [('reviewer', blind, agent, root / 'blind' / blind, profile['roles']['reviewer']['models'][0])
             for blind, agent in agents['reviewers'].items()]
    summary = {}
    for role, name, agent, own, model in jobs:
        value = bench.receipt(root, args.transcripts, agent, role, own, model)
        log = Path(args.transcripts) / 'subagents' / f'agent-{agent}.jsonl'
        calls = []
        for line in log.read_text(encoding='utf-8').splitlines():
            entry = json.loads(line)
            if entry.get('type') == 'assistant':
                calls += [{'tool': b['name'], 'input': b.get('input', {})} for b in entry['message'].get('content', []) if b.get('type') == 'tool_use']
        seconds, count = active_seconds(log)
        value.update(usage_v2(log), amendment='1.5', activeSecondsV2=seconds, workSegmentsV2=count,
                     activeSecondsBenchPyNote='bench.py splits only on non-meta user entries; SendMessage resumes are isMeta, so it counts idle time', tokensObservedBenchPy=value.pop('tokensObserved'),
                     scratchpadReferences=[{'tool': c['tool'], 'text': json.dumps(c['input'], ensure_ascii=False)[:300]} for c in scratchpad(calls)],
                     tokenLimitation='usage per message is mostly the stream-start value; output is a lower bound; thinking text is omitted; cost NOT_AVAILABLE')
        (out / f'{role}-{name}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        summary[f'{role}-{name}'] = {'agent': agent, 'models': value['responseModels'], 'switch': value['modelSwitchOrMismatch'],
                                     'effort': value['runtimePrefix'].get('effortValue'), 'flags': len(value['auditFlags']),
                                     'scratchpad': len(value['scratchpadReferences']), 'activeSecondsV2': value['activeSecondsV2'],
                                     'outputLowerBound': value['outputTokensLowerBound']}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
