#!/usr/bin/env python3
"""Capability-aware local development runner with a small machine-readable report."""
from __future__ import annotations
import argparse, datetime as dt, json, os, shutil, subprocess, time
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
@dataclass(frozen=True)
class Check:
    name:str; command:tuple[str,...]; required:bool; available:bool; reason:str=''
def executable(path:Path)->bool: return path.is_file() and os.access(path,os.X_OK)
def plan(level:str,with_qemu:bool=False)->list[Check]:
    gradle=executable(ROOT/'android/podroid/gradlew')
    android=gradle and bool(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME'))
    checks=[Check('validate',('make','validate'),True,True),Check('guest',('make','test-guest'),True,True)]
    if level=='full':
        checks += [Check('jvm',('make','test-jvm'),False,gradle,'android/podroid/gradlew unavailable' if not gradle else ''),Check('android',('make','test-android'),False,android,'Gradle or Android SDK unavailable' if not android else '')]
    if with_qemu:
        missing=[name for name in ('qemu-system-aarch64','qemu-img','cloud-localds','ssh') if shutil.which(name) is None]
        checks.append(Check('qemu-lab',('make','qemu-lab-e2e'),False,not missing,'missing: '+', '.join(missing) if missing else ''))
    return checks
def execute(checks:list[Check])->tuple[list[dict[str,object]],bool]:
    results=[]; ok=True
    for check in checks:
        if not check.available:
            results.append({'name':check.name,'status':'SKIP','command':list(check.command),'reason':check.reason,'durationSeconds':0.0}); continue
        started=time.monotonic(); completed=subprocess.run(check.command,cwd=ROOT,text=True); duration=round(time.monotonic()-started,3); status='PASS' if completed.returncode==0 else 'FAIL'
        results.append({'name':check.name,'status':status,'command':list(check.command),'returnCode':completed.returncode,'durationSeconds':duration}); ok = ok and status=='PASS'
    return results,ok
def print_plan(checks:list[Check])->None:
    print('CHECK       REQUIRED  AVAILABLE  COMMAND/REASON')
    for item in checks:
        detail=' '.join(item.command) if item.available else item.reason
        print(f'{item.name:<11} {str(item.required).lower():<9} {str(item.available).lower():<10} {detail}')
def main()->int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='action',required=True)
    for name in ('plan','run'):
        p=sub.add_parser(name); p.add_argument('--level',choices=('quick','full'),default='full' if name=='plan' else 'quick'); p.add_argument('--with-qemu',action='store_true',default=os.environ.get('DEV_WITH_QEMU')=='1'); p.add_argument('--json',type=Path)
    args=parser.parse_args(); checks=plan(args.level,args.with_qemu)
    if args.action=='plan': print_plan(checks); return 0
    results,ok=execute(checks)
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip() or None
    dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True).stdout.strip())
    report={'schemaVersion':1,'recordedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'gitCommit':commit,'dirty':dirty,'level':args.level,'withQemu':args.with_qemu,'results':results}
    output=args.json or ROOT/'.local/development/report.json'; output=output if output.is_absolute() else ROOT/output; output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2)+'\n')
    for result in results: print(f"{result['status']:<5} {result['name']}")
    print(output.relative_to(ROOT) if ROOT in output.resolve().parents else output); return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
