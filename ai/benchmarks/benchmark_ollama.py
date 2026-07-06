#!/usr/bin/env python3
"""Benchmark EMS AI prompts against one or more Ollama models."""
import argparse, json, statistics, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMPT = ROOT / 'ai' / 'prompts' / 'commentator.txt'
DEFAULT_EXAMPLE = ROOT / 'ai' / 'examples' / 'safety_event.json'

def call_ollama(url, model, prompt, snapshot, num_predict):
    payload = {
        'model': model,
        'prompt': f'{prompt}\n\nStav:\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}',
        'stream': False,
        'options': {'temperature': 0.1, 'num_predict': num_predict},
    }
    data = json.dumps(payload).encode('utf-8')
    start = time.perf_counter()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    duration = time.perf_counter() - start
    return duration, (body.get('response') or '').strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://10.200.5.122:11434/api/generate')
    parser.add_argument('--model', action='append', default=[], help='Ollama model; repeat to compare multiple models')
    parser.add_argument('--prompt', type=Path, default=DEFAULT_PROMPT)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--num-predict', type=int, default=120)
    args = parser.parse_args()
    models = args.model or ['gemma3:4b']
    prompt = args.prompt.read_text(encoding='utf-8').strip()
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))

    print('| model | runs | avg_s | min_s | max_s | chars | sample |')
    print('|---|---:|---:|---:|---:|---:|---|')
    for model in models:
        durations, responses = [], []
        for _ in range(args.runs):
            duration, response = call_ollama(args.url, model, prompt, snapshot, args.num_predict)
            durations.append(duration); responses.append(response)
        sample = responses[-1].replace('|', '\\|').replace('\n', ' ')[:160]
        print(f'| {model} | {args.runs} | {statistics.mean(durations):.2f} | {min(durations):.2f} | {max(durations):.2f} | {len(responses[-1])} | {sample} |')

if __name__ == '__main__':
    main()
