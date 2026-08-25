from fastapi import APIRouter,Header,HTTPException
from cold_clock.wake_actions import ColdClockWakeExecutor
from service import worker_status
from spine.scheduler_auth import verify_scheduler_token
def build_scheduler_router(store,scheduler):
 router=APIRouter(prefix="/internal",tags=["scheduler-worker"]);executor=ColdClockWakeExecutor(store,scheduler.clock,scheduler)
 @router.post("/wakes/scan")
 def scan(authorization:str|None=Header(default=None)):
  try:identity=verify_scheduler_token(authorization)
  except ValueError as exc:raise HTTPException(401,str(exc)) from exc
  rows=scheduler.dispatch_due(lambda wake:executor.execute(wake,trigger=identity));dispatched=[row.wake_id for row in rows];worker_status.record_scan(identity,dispatched)
  return {"ok":True,"identity":identity,"dispatched":dispatched,"dead_letters":[row.wake_id for row in scheduler.dead_letters]}
 return router
