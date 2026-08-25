"""Executable ColdClock autonomy acceptance flow."""
from __future__ import annotations
import argparse,json,time
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request,urlopen

def call(base,method,path,body=None):
 data=json.dumps(body or {}).encode() if method=="POST" else None
 with urlopen(Request(base.rstrip("/")+path,data=data,method=method,headers={"Content-Type":"application/json"}),timeout=150) as response:return response.status,json.loads(response.read())
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--url",default="http://127.0.0.1:8000");parser.add_argument("--wait-for-scheduler",type=int,default=0,help="seconds to wait for the real Cloud Scheduler tick instead of advancing the simulated clock");args=parser.parse_args();checks=[]
 def check(name,value):checks.append(bool(value));print(f"{'PASS' if value else 'FAIL'}  {name}")
 _,health=call(args.url,"GET","/health");check("health identifies ColdClock",health["project"]=="cold-clock");check("health exposes event-driven autonomy",health["autonomy"]=="event-driven-safe-auto-continuation");check("clinical authority remains human",health["clinical_decisions"]=="human-only")
 _,case=call(args.url,"POST","/api/cases");case_id=case["case_id"];check("case waits for a real sensor event",case["status"]=="monitoring" and case["autonomy"]["current_wait"]=="sensor_event")
 try:call(args.url,"POST",f"/api/cases/{case_id}/fulfillment");blocked=False
 except HTTPError as exc:blocked=exc.code==409
 check("pre-approval fulfillment is blocked",blocked)
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/outage");check("one event automatically routes the review packet",case["status"]=="awaiting_professional_review" and case["autonomy"]["last_run_actions"]==["review_packet_routed"]);check("AI makes no medication disposition",case["excursion"]["ai_disposition"] is None)
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/review",{"disposition":"replace","reviewer_name":"Avery Chen, PharmD - synthetic","rationale":"Replacement approved in this synthetic acceptance flow."});check("named human remains the decision authority",not case["review"]["decision"]["made_by_ai"]);check("one decision automatically reserves and dispatches",case["status"]=="delivery_dispatched" and len(case["autonomy"]["last_run_actions"])==2)
 _,wakes=call(args.url,"GET",f"/api/cases/{case_id}/wakes");check("dispatch registers a durable courier poll wake",{row["kind"] for row in wakes["wakes"]}>={"courier_status_poll","receipt_followup"})
 _,case=call(args.url,"POST",f"/api/cases/{case_id}/confirm-delivery");check("receipt closes the workflow",case["status"]=="resolved")
 _,demo=call(args.url,"POST","/api/demo/full");check("one-request demo reaches end-to-end closure",demo["autonomy"]["complete"] and demo["status"]=="resolved")
 _,bg=call(args.url,"POST","/api/demo/unattended");bg_id=bg["case_id"];check("unattended run stops at the courier ETA without a receipt",bg["status"]=="delivery_dispatched" and not bg["autonomy"]["closed_by_background_wake"])
 if args.wait_for_scheduler>0:
  deadline=time.time()+args.wait_for_scheduler;closed=bg
  while time.time()<deadline and closed["status"]!="resolved":time.sleep(5);_,closed=call(args.url,"GET",f"/api/cases/{bg_id}")
  trigger=(closed.get("background_executions") or [{}])[0].get("trigger");check("Cloud Scheduler wake closed the case with zero clicks",closed["status"]=="resolved" and closed["autonomy"]["closed_by_background_wake"] and trigger=="google-oidc")
 else:
  call(args.url,"POST","/api/hardening/advance",{"minutes":2});_,closed=call(args.url,"GET",f"/api/cases/{bg_id}");check("courier poll wake closed the case with zero clicks",closed["status"]=="resolved" and closed["autonomy"]["closed_by_background_wake"])
 check("background closure keeps proof integrity",closed["autonomy_proof"]["proof_integrity"]=="verified" and closed["autonomy_proof"]["operator_continue_clicks"]==0)
 _,signed=call(args.url,"GET",f"/api/cases/{bg_id}/autonomy-proof");_,verified=call(args.url,"POST","/api/receipts/verify",{"proof":signed});_,tampered=call(args.url,"POST","/api/receipts/verify",{"proof":{**signed,"operator_continue_clicks":9}});check("autonomy receipt is signed and tamper-evident",verified["valid"] and not tampered["valid"])
 packet=(closed.get("packet_agent") or {});check("review packet came from the ADK agent through scoped tools" if packet.get("live") else "review packet used the deterministic path (no live packet agent)",packet.get("accepted") if packet.get("live") else True)
 area=f"grid-demo-{uuid4().hex[:6]}";_,fan=call(args.url,"POST","/api/demo/outage-fanout",{"service_area":area,"enroll":2});check("one grid outage fans out to every enrolled case",set(fan["affected_cases"])==set(fan["enrolled"]) and len(fan["enrolled"])==2)
 _,fw=call(args.url,"GET",f"/api/cases/{fan['enrolled'][0]}/wakes");check("each affected case holds a pending outage_watch wake",any(row["kind"]=="outage_watch" and row["status"]=="pending" for row in fw["wakes"]))
 _,proof=call(args.url,"GET","/api/proof");check("safety proof is green",proof["passed"]==proof["total"])
 _,hardening=call(args.url,"GET","/api/hardening/proof");check("hardening proof is green",hardening["passed"]==hardening["total"])
 print()
 print(f"{sum(checks)}/{len(checks)} checks passed");return 0 if all(checks) else 1
if __name__=="__main__":raise SystemExit(main())
