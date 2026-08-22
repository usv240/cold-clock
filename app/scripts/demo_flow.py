"""Executable ColdClock autonomy acceptance flow."""
from __future__ import annotations
import argparse,json
from urllib.error import HTTPError
from urllib.request import Request,urlopen

def call(base,method,path,body=None):
 data=json.dumps(body or {}).encode() if method=="POST" else None
 with urlopen(Request(base.rstrip("/")+path,data=data,method=method,headers={"Content-Type":"application/json"}),timeout=20) as response:return response.status,json.loads(response.read())
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--url",default="http://127.0.0.1:8000");args=parser.parse_args();checks=[]
 def check(name,value):checks.append(bool(value));print(f"{'PASS' if value else 'FAIL'}  {name}")
 _,health=call(args.url,"GET","/health");check("health identifies ColdClock",health["project"]=="cold-clock");check("health exposes event-driven autonomy",health["autonomy"]=="event-driven-safe-auto-continuation");check("clinical authority remains human",health["clinical_decisions"]=="human-only")
 _,case=call(args.url,"POST","/api/cases");case_id=case["case_id"];check("case waits for a real sensor event",case["status"]=="monitoring" and case["autonomy"]["current_wait"]=="sensor_event")
 try:call(args.url,"POST",f"/api/cases/{case_id}/fulfillment");blocked=False
 except HTTPError as exc:blocked=exc.code==409
 check("pre-approval fulfillment is blocked",blocked)
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/outage");check("one event automatically routes the review packet",case["status"]=="awaiting_professional_review" and case["autonomy"]["last_run_actions"]==["review_packet_routed"]);check("AI makes no medication disposition",case["excursion"]["ai_disposition"] is None)
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/review",{"disposition":"replace","reviewer_name":"Avery Chen, PharmD - synthetic","rationale":"Replacement approved in this synthetic acceptance flow."});check("named human remains the decision authority",not case["review"]["decision"]["made_by_ai"]);check("one decision automatically reserves and dispatches",case["status"]=="delivery_dispatched" and len(case["autonomy"]["last_run_actions"])==2)
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/confirm-delivery");check("receipt closes the workflow",case["status"]=="resolved")
 _,demo=call(args.url,"POST","/api/demo/full");check("one-request demo reaches end-to-end closure",demo["autonomy"]["complete"] and demo["status"]=="resolved")
 _,proof=call(args.url,"GET","/api/proof");check("safety proof is green",proof["passed"]==proof["total"])
 print()
 print(f"{sum(checks)}/{len(checks)} checks passed");return 0 if all(checks) else 1
if __name__=="__main__":raise SystemExit(main())