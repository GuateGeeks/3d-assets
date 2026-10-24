"""Costo estimado en USD (precio de lista de API) desde transcripts de Claude Code.

python3 -I cost_estimate.py SESION.jsonl AGENTS.json MARCA_INICIO [MARCA_FIN]
Tarifas: tabla del skill claude-api (caché 2026-10-06), no verificadas en vivo. La salida usa
la cota inferior de receipts.py; el razonamiento oculto no se cuenta. Equivalente de API, no factura.
"""
import json, sys
from pathlib import Path
from collections import defaultdict
# USD por millón: entrada, escritura 5m, escritura 1h, lectura de caché, salida (lista del skill claude-api, caché 2026-10-06)
P = {'claude-opus-5-5': (4, 5, 8, 0.20, 20), 'claude-sonnet-5-5': (2, 2.5, 4, 0.20, 10), 'claude-haiku-5-5': (0.10, 0.125, 0.20, 0.01, 0.50)}
HAIKU_LONG = (0.50, 0.625, 1.0, 0.05, 2.50)  # prompts > 100K
def cost_lines(lines):
    msgs = {}
    for e in lines:
        if e.get('type') != 'assistant': continue
        m = e['message']
        if m.get('model') not in P: continue
        k = m.get('id') or e.get('uuid'); u = m.get('usage') or {}; cc = u.get('cache_creation') or {}
        prev = msgs.get(k, {'model': m['model'], 'in': 0, 'w5': 0, 'w1': 0, 'r': 0, 'out': 0, 'chars': 0})
        prev['in'] = max(prev['in'], u.get('input_tokens') or 0)
        prev['w5'] = max(prev['w5'], cc.get('ephemeral_5m_input_tokens') or 0)
        prev['w1'] = max(prev['w1'], cc.get('ephemeral_1h_input_tokens') or 0)
        if not cc: prev['w5'] = max(prev['w5'], u.get('cache_creation_input_tokens') or 0)
        prev['r'] = max(prev['r'], u.get('cache_read_input_tokens') or 0)
        prev['out'] = max(prev['out'], u.get('output_tokens') or 0)
        for b in m.get('content', []):
            prev['chars'] += len(b.get('text', '')) if b['type'] == 'text' else len(json.dumps(b.get('input', {}), ensure_ascii=False)) if b['type'] == 'tool_use' else 0
        msgs[k] = prev
    tot = defaultdict(float)
    for x in msgs.values():
        prompt = x['in'] + x['w5'] + x['w1'] + x['r']
        p = HAIKU_LONG if x['model'] == 'claude-haiku-5-5' and prompt > 100_000 else P[x['model']]
        out = max(x['out'], x['chars'] / 3.5)
        tot['input$'] += (x['in']*p[0] + x['w5']*p[1] + x['w1']*p[2]) / 1e6
        tot['cacheRead$'] += x['r']*p[3] / 1e6
        tot['output$'] += out*p[4] / 1e6
    tot['total$'] = tot['input$'] + tot['cacheRead$'] + tot['output$']
    return tot
def load(p): return [json.loads(l) for l in open(p)]
def main(session, agents_path, start, end=None):
    T = Path(session).with_suffix('')
    agents = json.load(open(agents_path))
    groups = defaultdict(lambda: defaultdict(float)); rows = {}
    for k, v in agents['authors'].items():
        c = cost_lines(load(T/'subagents'/f"agent-{v['agentId']}.jsonl")); rows[f'autor {k} ({v["requestedAlias"]})'] = c
        for f, val in c.items(): groups['autores'][f] += val
    for aid in agents.get('reviewers', {}):
        for f, val in cost_lines(load(T/'subagents'/f'agent-{aid}.jsonl')).items(): groups['revisores'][f] += val
    lines, on = [], False
    for e in load(session):
        c = e.get('message', {}).get('content') if e.get('type') == 'user' else None
        if isinstance(c, str) and start in c: on = True
        if on and end and isinstance(c, str) and end in c: break
        if on: lines.append(e)
    groups['coordinador'] = cost_lines(lines)
    print(f"total ${sum(g['total$'] for g in groups.values()):.2f}")
    for g, c in groups.items(): print(f"  {g:12} ${c['total$']:.2f}")
    for r, c in rows.items(): print(f"     {r:28} ${c['total$']:.3f}")
if __name__ == '__main__':
    main(*sys.argv[1:5])
