#!/usr/bin/env python3
"""Write bounded machine-readable host-QEMU laboratory evidence."""
from __future__ import annotations
import argparse, hashlib, json, socket, time
from pathlib import Path
def sha(path:Path):
    if not path.is_file(): return None
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def _reply(stream):
    for _ in range(32):
        message=json.loads(stream.readline())
        if 'return' in message or 'error' in message: return message
    raise RuntimeError('QMP reply limit exceeded')
def qmp_status(path:Path):
    if not path.exists(): return {'connected':False,'status':None}
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(3); s.connect(str(path)); stream=s.makefile('r'); greeting=json.loads(stream.readline()); s.sendall(b'{"execute":"qmp_capabilities"}\n'); cap=_reply(stream); s.sendall(b'{"execute":"query-status"}\n'); reply=_reply(stream)
        return {'connected':True,'greeting':bool(greeting.get('QMP')),'capabilities':'return' in cap,'status':reply.get('return',{}).get('status')}
    except Exception as exc: return {'connected':False,'status':None,'errorClass':type(exc).__name__}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--state',type=Path,required=True); p.add_argument('--status',choices=('PASS','FAIL'),required=True); p.add_argument('--started-at',required=True); p.add_argument('--summary',required=True); p.add_argument('--output',type=Path); args=p.parse_args(); state=args.state.resolve(); output=(args.output or state/'evidence.json').resolve()
    artifacts={name:{'sha256':sha(state/name),'sizeBytes':(state/name).stat().st_size if (state/name).is_file() else None} for name in ('noble-server-cloudimg-arm64.img','system.qcow2','seed.img','AAVMF_CODE.fd','AAVMF_VARS.fd')}
    report={'schemaVersion':1,'status':args.status,'startedAt':args.started_at,'endedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'summary':args.summary,'qmp':qmp_status(state/'qmp.sock'),'artifacts':artifacts,'logs':{name:{'sizeBytes':(state/name).stat().st_size if (state/name).is_file() else None} for name in ('serial.log','qemu.stderr.log','qemu.stdout.log')},'androidHardwareValidated':False}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2)+'\n'); print(output); return 0
if __name__=='__main__': raise SystemExit(main())
