#!/usr/bin/env python3
"""Safely add one compact task packet to the active task cycle."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; ID=re.compile(r'^[A-Z][0-9]{2}$'); SLUG=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
def load(path:Path): return json.loads(path.read_text())
def dump(path:Path,data): path.write_text(json.dumps(data,indent=2)+'\n')
def build(args):
    task=args.id.upper()
    if not ID.fullmatch(task): raise ValueError('--id must look like H05')
    if not SLUG.fullmatch(args.slug): raise ValueError('--slug must be lower-kebab-case')
    if not args.allowed_path: raise ValueError('at least one --allowed-path is required')
    if not args.acceptance: raise ValueError('at least one --acceptance is required')
    for value in [*args.allowed_path,*args.context]:
        if value.startswith('/') or '..' in Path(value).parts: raise ValueError(f'path must stay repository-relative: {value}')
    missing=[value for value in args.context if not (ROOT/value).is_file()]
    if missing: raise ValueError(f'missing context files: {missing}')
    if len(args.context)>12: raise ValueError('context list may contain at most 12 paths')
    dag=load(ROOT/'agents/task-dag.json'); registry=load(ROOT/'agents/task-registry.json'); ids={item['id'] for item in dag['tasks']}
    if task in ids or (ROOT/'agents/tasks'/task).exists(): raise ValueError(f'task already exists: {task}')
    unknown=set(args.depends_on)-ids
    if unknown: raise ValueError(f'unknown dependencies: {sorted(unknown)}')
    dag['tasks'].append({'id':task,'slug':args.slug,'dependsOn':args.depends_on,'parallelGroup':args.group,'mvpPlus':args.mvp_plus}); registry['tasks'].append({'id':task,'name':args.name,'dependsOn':args.depends_on,'packet':f'agents/tasks/{task}/task.md'})
    acceptance='\n'.join(f'- {item}' for item in args.acceptance)
    task_md=f"# {task} — {args.name}\n\n## Outcome\n\n{args.outcome}\n\n## Prerequisites\n\n{', '.join(args.depends_on) if args.depends_on else 'None.'}\n\n## Allowed paths\n\nSee `allowed-paths.txt`. Changes outside them require an orchestrator handoff.\n\n## Acceptance\n\n{acceptance}\n\n## Required checks\n\n```sh\nmake validate\n```\n\n## Handoff\n\nReport commit SHA(s), tests, unavailable checks, evidence paths, concrete TODOs, and the smallest next blocker.\n"
    return task,dag,registry,task_md
def main():
    p=argparse.ArgumentParser(); p.add_argument('--id',required=True); p.add_argument('--slug',required=True); p.add_argument('--name',required=True); p.add_argument('--outcome',default='Implement the scoped task outcome.'); p.add_argument('--group',type=int,required=True); p.add_argument('--depends-on',action='append',default=[]); p.add_argument('--allowed-path',action='append',default=[]); p.add_argument('--context',action='append',default=[]); p.add_argument('--acceptance',action='append',default=[]); p.add_argument('--mvp-plus',action='store_true'); p.add_argument('--write',action='store_true'); args=p.parse_args()
    try: task,dag,registry,task_md=build(args)
    except ValueError as exc: raise SystemExit(str(exc)) from None
    preview={'task':task,'dagEntry':dag['tasks'][-1],'registryEntry':registry['tasks'][-1],'allowedPaths':args.allowed_path,'context':args.context,'acceptance':args.acceptance}
    if not args.write: print(json.dumps(preview,indent=2)); print('dry-run: pass --write to modify the repository'); return 0
    target=ROOT/'agents/tasks'/task; target.mkdir(parents=True)
    files={target/'task.md':task_md,target/'allowed-paths.txt':'\n'.join(args.allowed_path)+'\n',target/'context.list':'\n'.join(args.context)+'\n',target/'README.md':f'# {task}\n\nGenerate context with `make context TASK={task}`.\n'}
    for path,body in files.items(): path.write_text(body)
    for path,data in ((ROOT/'agents/task-dag.json',dag),(ROOT/'agents/task-registry.json',registry)):
        tmp=path.with_suffix(path.suffix+'.tmp'); dump(tmp,data); tmp.replace(path)
    print(json.dumps(preview,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
