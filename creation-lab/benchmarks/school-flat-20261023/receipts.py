"""Recibos por agente desde transcripts de Claude Code: modelo real, entrada y salida.

python3 -I receipts.py SESION.jsonl AGENTS.json OUT.json MARCA_INICIO [MARCA_FIN]
SESION.jsonl es el transcript del coordinador; los subagentes se leen de SESION/subagents/.
La entrada es fiable; la salida es máx(registrada, texto/código visible/3.5): cota inferior.
Las marcas son textos del mensaje del usuario que abre/cierra el tramo de la condición."""
import json, sys
from pathlib import Path
from collections import Counter, defaultdict
T = Path(sys.argv[1]).with_suffix('')
agents_path, out_path, start_marker = sys.argv[2:5]
end_marker = sys.argv[5] if len(sys.argv) > 5 else None
agents = json.load(open(agents_path))
def count(lines):
    usage, chars, models = {}, defaultdict(int), set()
    for e in lines:
        if e.get('type') != 'assistant': continue
        m = e['message']
        if m.get('model') == '<synthetic>': continue
        k = m.get('id') or e.get('uuid'); models.add(m.get('model'))
        u = m.get('usage') or {}; prev = usage.get(k, {})
        usage[k] = {f: max(prev.get(f, 0), u.get(f) or 0) for f in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')}
        for b in m.get('content', []):
            if b['type'] == 'text': chars[k] += len(b['text'])
            elif b['type'] == 'tool_use': chars[k] += len(json.dumps(b.get('input', {}), ensure_ascii=False))
    t = Counter()
    for u in usage.values(): t.update(u)
    est = round(sum(chars.values())/3.5)
    return {'responseModels': sorted(models), 'apiResponses': len(usage),
            'inputTokensTotal': t['input_tokens']+t['cache_creation_input_tokens']+t['cache_read_input_tokens'],
            'cacheReadTokens': t['cache_read_input_tokens'], 'outputTokensRecorded': t['output_tokens'],
            'outputTokensVisibleEstimate': est, 'outputTokensLowerBound': max(t['output_tokens'], est)}
def load(p): return [json.loads(l) for l in open(p)]
out = {'method': 'Entrada fiable; salida = máx(registrada, texto/código visible/3.5): cota inferior sin razonamiento oculto. Coste no disponible.', 'agents': {}}
roles = [(aid, f'autor {k}', v.get('requestedAlias'), v.get('requestedEffort')) for k, v in agents['authors'].items() for aid in [v['agentId']]]
roles += [(aid, f'revisor {desc}', 'opus', 'medium') for aid, desc in agents.get('reviewers', {}).items()]
for aid, role, alias, eff in roles:
    out['agents'][aid] = {'role': role, 'requested': [alias, eff], **count(load(T/'subagents'/f'agent-{aid}.jsonl'))}
lines, on = [], False
for e in load(T.with_suffix('.jsonl')):
    c = e.get('message', {}).get('content') if e.get('type') == 'user' else None
    if isinstance(c, str) and start_marker in c: on = True
    if on and end_marker and isinstance(c, str) and end_marker in c: break
    if on: lines.append(e)
out['coordinator'] = {'role': 'coordinador (tramo de esta condición en la sesión principal)', 'requested': ['claude-opus-5-5', 'high'], **count(lines)}
Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1))
tot = Counter()
for a in list(out['agents'].values()) + [out['coordinator']]:
    tot['in'] += a['inputTokensTotal']; tot['cache'] += a['cacheReadTokens']; tot['out'] += a['outputTokensLowerBound']
    print(f"{a['role'][:44]:44} req={a['requested']} real={a['responseModels']} in={a['inputTokensTotal']:,} out≥{a['outputTokensLowerBound']:,}")
print('TOTAL', dict(tot))
