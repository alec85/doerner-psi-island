"""Check recorded replay behavior; no browser or visual layout claim."""
import argparse,hashlib,importlib.util,json,subprocess,shutil,pathlib
parser=argparse.ArgumentParser(description='Execute actual recorded HTML scripts in the DOM/Canvas harness, without browser layout claims.')
parser.add_argument('paths',nargs='+',type=pathlib.Path);parser.add_argument('--output',required=True,type=pathlib.Path);args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('replay_tests',str(root/'tests/picrawler/test_replay.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
paths=args.paths
reports=[]
for path in paths:
 doc=module._Document();doc.feed(path.read_text());assert not doc.external_resources
 assert len(doc.scripts)==2
 payload=json.loads(doc.scripts[0]['text'])
 assert payload['metadata']['backend']=='mujoco'
 run=subprocess.run([shutil.which('node'),'-e',module._NODE_DOM_TEST],input=json.dumps(dict(code=doc.scripts[1]['text'],data=doc.scripts[0]['text'],mode='peripherals')),capture_output=True,text=True,timeout=30,check=True)
 report=dict(file=path.name,frames=len(payload['frames']),**json.loads(run.stdout));reports.append(report);print(report)
args.output.write_text(json.dumps(dict(checks=reports,browser_visual_acceptance=False,script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()),indent=2))
