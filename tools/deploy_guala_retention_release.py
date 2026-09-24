"""Bounded retention release, one image, one definition, one writer cutover.

Includes full release (tick acceleration + refusal suppression + mailbox expansion).
Invoke --plan first; --execute runs this same plan after local proof clearance.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import boto3
from botocore.config import Config

REGION = "us-east-1"
ACCOUNT = "418384447921"
CLUSTER = "tfe-web-cluster"
SERVICE = "dsf-ai-service-lb"
OLD_TASK = "9ea80524bf6f4aebb08940e6adbc5cb0"
OLD_DEFINITION = "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1539"
BASE = ACCOUNT+".dkr.ecr."+REGION+".amazonaws.com/dsf-ai@sha256:950d884876599f768c6478ee2d99edd0f0e398075854ad955bd32598df4801fe"
REPOSITORY = BASE.split("@")[0]
FILES = {
 "dsf_ai_service/substrate/embodiment_world.py": "9b9bc432450b69d4bad15e9a94a91b36ec3f5883af3075a4ef44243ef0657789",
 "dsf_ai_service/guala_caretaker_hand.py": "7b13a172e15594f5e6cffc9de8f8997e5d57a39bd523c111334fa1f8db8d9e5a",
 "dsf_ai_service/lean_production_app.py": "d157b4b89c2c0b14bdf2344ee18582cd9be7ca3e9b15a669ac2751e8772af20d",
 "dsf_ai_service/guala_functional_organism.py": "b98c1e36c9b50a966b16c283518db3e0464486f09df2023258e5cbd9eeed146a",
 "dsf_ai_service/lean_actor.py": "7bcb4658caeeead8c507f902698cb8bfa99f840d6ce0d0155c3d95f424ed5e7f",
 "dsf_ai_service/episodic_binding_engine.py": "f1cc108452cb512818f2e4f05f73e29838f997dd10a9ecdb42134486fe879cb4",
 "dsf_ai_service/substrate/native_core.py": "7144580489e9b739538a90f1c0360209b3a4e2ecb94d6a6362db6b4aa902fbe3",
}
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
ROOT = Path(__file__).resolve().parents[1]
CONFIG = Config(connect_timeout=10,read_timeout=30,retries={"max_attempts":2})
ecs = boto3.client("ecs",region_name=REGION,config=CONFIG)
ecr = boto3.client("ecr",region_name=REGION,config=CONFIG)
logs = boto3.client("logs",region_name=REGION,config=CONFIG)
journal = None

def emit(event, **data):
    record = {"at":datetime.now(timezone.utc).isoformat(),"event":event,**data}
    line = json.dumps(record,default=str)
    print(line,flush=True)
    if journal:
        with journal.open("a") as output:
            output.write(line+"\n")
            output.flush()
            os.fsync(output.fileno())

def service():
    response=ecs.describe_services(cluster=CLUSTER,services=[SERVICE])
    assert not response.get("failures"),response.get("failures")
    return response["services"][0]

def task(arn):
    response=ecs.describe_tasks(cluster=CLUSTER,tasks=[arn])
    assert not response.get("failures"),response.get("failures")
    return response["tasks"][0]

def observation():
    with urllib.request.urlopen("https://dsf-ai.com/api/v1/guala/observation",timeout=20) as response:
        data=response.read(8_000_001)
    assert len(data)<=8_000_000
    value=json.loads(data)
    assert value["identity"]==IDENTITY
    return {key:value.get(key) for key in ("identity","live_tick","persisted_tick","available",
        "checkpoint_error","cleanup_error","durability_blocked")}

def log_messages(arn, start_ms=0):
    stream="dsf-ai/dsf-ai/"+arn.split("/")[-1]
    messages=[]
    token=None
    seen=set()
    for _ in range(30):
        args={"logGroupName":"/ecs/dsf-ai","logStreamNames":[stream],
              "startTime":start_ms,"limit":500}
        if token:
            args["nextToken"]=token
        page=logs.filter_log_events(**args)
        messages.extend(e["message"] for e in page.get("events",[]))
        assert len(messages)<=5000,"log bound exceeded"
        token=page.get("nextToken")
        if not token:
            return messages
        assert token not in seen,"log token cycle"
        seen.add(token)
    raise RuntimeError("log page bound exceeded")

def wait_stopped(arn, seconds=480):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=task(arn)
        if value["lastStatus"]=="STOPPED":
            return value
        emit("waiting_task_stop",task=arn,status=value["lastStatus"])
        time.sleep(10)
    raise RuntimeError("exact task termination unverified: "+arn)

def zero_writers(arns):
    for arn in arns:
        assert task(arn)["lastStatus"]=="STOPPED"
    s=service()
    assert (s["desiredCount"],s["runningCount"],s["pendingCount"])==(0,0,0)
    for desired in ("RUNNING","STOPPED"):
        listed=ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus=desired)["taskArns"]
        for arn in listed:
            assert task(arn)["lastStatus"]=="STOPPED",arn

def oneoff(definition, network, mode, command=None):
    response=ecs.run_task(cluster=CLUSTER,taskDefinition=definition,launchType="FARGATE",
        count=1,networkConfiguration=network,
        overrides={"containerOverrides":[{"name":"dsf-ai","command":
            (command or ["python3","/opt/a1_retention_release_operator.py",mode])}]})
    assert not response.get("failures"),response.get("failures")
    arn=response["tasks"][0]["taskArn"]
    emit("operator_started",mode=mode,task=arn)
    final=wait_stopped(arn)
    container=next(c for c in final["containers"] if c["name"]=="dsf-ai")
    messages=log_messages(arn)
    emit("operator_finished",mode=mode,task=arn,exit=container.get("exitCode"),
         logs=messages,reason=final.get("stoppedReason"))
    assert container.get("exitCode")==0
    return messages

def records(messages,schema):
    found=[]
    for line in messages:
        try:
            value=json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value,dict) and value.get("schema")==schema:
            found.append(value)
    return found

def activate(definition,backup,source_arn,candidate_arns,digest):
    # Changing the definition and raising count together can race an ACTIVE
    # predecessor deployment. Install and converge the definition at ZERO first.
    zero_writers([source_arn])
    ecs.update_service(cluster=CLUSTER,service=SERVICE,taskDefinition=definition,desiredCount=0)
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        s=service()
        deployments=s["deployments"]
        if (s["taskDefinition"]==definition
            and (s["desiredCount"],s["runningCount"],s["pendingCount"])==(0,0,0)
            and len(deployments)==1):
            d=deployments[0]
            if (d["status"]=="PRIMARY" and d["taskDefinition"]==definition
                and d.get("rolloutState")=="COMPLETED"
                and (d["desiredCount"],d["runningCount"],d["pendingCount"])==(0,0,0)):
                break
        emit("waiting_zero_definition_convergence",definition=definition)
        time.sleep(10)
    else:
        raise RuntimeError("zero-count candidate deployment did not converge")
    zero_writers([source_arn])
    ecs.update_service(cluster=CLUSTER,service=SERVICE,desiredCount=1)
    emit("candidate_start_requested",definition=definition,backup=backup)
    deadline=time.monotonic()+600
    live=None
    while time.monotonic()<deadline:
        listed=ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus="RUNNING")["taskArns"]
        candidate_arns.update(listed)
        for arn in listed:
            value=task(arn)
            assert value["taskDefinitionArn"]==definition
            if value["lastStatus"]=="RUNNING" and value.get("healthStatus")=="HEALTHY":
                live=value
        if live is not None:
            break
        emit("waiting_candidate",tasks=listed)
        time.sleep(10)
    assert live is not None,"candidate failed to become healthy"
    assert len(ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus="RUNNING")["taskArns"])==1
    assert next(c for c in live["containers"] if c["name"]=="dsf-ai")["imageDigest"]==digest
    receipts=records(log_messages(live["taskArn"]),"guala.paired_predecessor.v1")
    assert len(receipts)==1
    for key in ("identity","organism_tick","body_sha256","body_bytes","world_sha256","world_bytes"):
        assert receipts[0][key]==backup["current"][key],key
    assert receipts[0]["functional_conversion"] is False
    first=observation()
    assert first["available"] and not first["checkpoint_error"] and not first["cleanup_error"]
    assert first["live_tick"]>=backup["current"]["organism_tick"]
    time.sleep(12)
    second=observation()
    assert second["available"]
    assert second["live_tick"]>first["live_tick"]
    assert second["persisted_tick"]>backup["current"]["organism_tick"]
    assert not second["checkpoint_error"] and not second["cleanup_error"] and not second["durability_blocked"]
    final_service=service()
    assert final_service["taskDefinition"]==definition
    assert (final_service["desiredCount"],final_service["runningCount"],final_service["pendingCount"])==(1,1,0)
    final_task=task(live["taskArn"])
    assert final_task["lastStatus"]=="RUNNING" and final_task.get("healthStatus")=="HEALTHY"
    assert ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus="RUNNING")["taskArns"]==[live["taskArn"]]
    emit("live_restore_and_progress_verified",task=live["taskArn"],definition=definition,
         digest=digest,first=first,second=second)

def main():
    global journal
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--plan",action="store_true")
    args=parser.parse_args()
    os.chdir(ROOT)
    assert boto3.client("sts",config=CONFIG).get_caller_identity()["Account"]==ACCOUNT
    assert shutil.which("docker")
    commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    for path,digest in FILES.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        committed=subprocess.check_output(["git","show",commit+":"+path])
        assert hashlib.sha256(committed).hexdigest()==digest,path+" is not committed"
    for path in ("tools/guala_retention_actor_proof.py","tools/guala_retention_release_operator.py",__file__):
        relative=str(Path(path).resolve().relative_to(ROOT))
        assert subprocess.check_output(["git","show",commit+":"+relative])==Path(path).read_bytes()
    s=service()
    assert s["taskDefinition"]==OLD_DEFINITION
    deployment=s["deploymentConfiguration"]
    assert not deployment.get("deploymentCircuitBreaker",{}).get("rollback",False)
    assert not deployment.get("alarms",{}).get("rollback",False)
    scaling=boto3.client("application-autoscaling",region_name=REGION,config=CONFIG)
    targets=scaling.describe_scalable_targets(ServiceNamespace="ecs",
        ResourceIds=["service/"+CLUSTER+"/"+SERVICE])["ScalableTargets"]
    assert not targets,"automatic scaling must not compete with single-writer cutover"
    assert (s["desiredCount"],s["runningCount"],s["pendingCount"])==(1,1,0)
    old=task(OLD_TASK)
    assert old["lastStatus"]=="RUNNING"
    assert next(c for c in old["containers"] if c["name"]=="dsf-ai")["imageDigest"]==BASE.split("@")[1]
    assert ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus="RUNNING")["taskArns"]==[old["taskArn"]]
    td=ecs.describe_task_definition(taskDefinition=OLD_DEFINITION)["taskDefinition"]
    assert td["cpu"]=="2048" and td["memory"]=="8192"
    assert len(td["containerDefinitions"])==1
    c=td["containerDefinitions"][0]
    assert c["name"]=="dsf-ai"
    env={e["name"]:e["value"] for e in c["environment"]}
    assert env["GUALA_PAIRED_ROOT"]=="/app/guala/paired-current-gen2"
    assert env["GUALA_MAX_WORLD_BYTES"]=="16777216"
    ob=observation()
    assert ob["available"] and not ob["checkpoint_error"] and not ob["durability_blocked"]
    proof=(ROOT/"backups/runtime/a1-retention-only-proof-20260924.log").read_text()
    assert "RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS" in proof
    emit("plan_verified",commit=commit,base=BASE,source_files=FILES,old_task=old["taskArn"],
         resources={"cpu":td["cpu"],"memory":td["memory"]},observation=ob,
         sequence="build, push, register, discarded-state rehearsal, recheck, drain, clean stop, final backup, start same candidate, exact restore/live verification",
         memory_candidate_included=True)
    if not args.execute:
        return
    folder=ROOT/"backups/runtime"/("a1-retention-release-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir()
    journal=folder/"receipt.jsonl"
    emit("release_start",commit=commit)
    context=Path(tempfile.mkdtemp(prefix="a1-retention-build-"))
    dockerfile=["FROM "+BASE,"ARG RELEASE_COMMIT","ENV GIT_SHA=${RELEASE_COMMIT}"]
    for path in FILES:
        destination=context/path
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/path,destination)
        dockerfile.append("COPY "+path+" /app/"+path)
    for source,name in (("tools/guala_retention_actor_proof.py","a1_retention_actor_proof.py"),
                        ("tools/guala_retention_release_operator.py","a1_retention_release_operator.py")):
        shutil.copyfile(ROOT/source,context/name)
        dockerfile.append("COPY "+name+" /opt/"+name)
    (context/"Dockerfile").write_text("\n".join(dockerfile)+"\n")
    tag=REPOSITORY+":a1-retention-"+commit[:12]
    with (folder/"build.log").open("w") as output:
        subprocess.run(["docker","build","--build-arg","RELEASE_COMMIT="+commit,"-t",tag,str(context)],
                       stdout=output,stderr=subprocess.STDOUT,check=True,timeout=600)
    emit("image_built",tag=tag)
    auth=ecr.get_authorization_token()["authorizationData"][0]
    username,password=base64.b64decode(auth["authorizationToken"]).decode().split(":",1)
    subprocess.run(["docker","login","--username",username,"--password-stdin",auth["proxyEndpoint"]],
                   input=password,text=True,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    with (folder/"push.log").open("w") as output:
        subprocess.run(["docker","push",tag],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=600)
    detail=ecr.describe_images(repositoryName="dsf-ai",imageIds=[{"imageTag":tag.split(":")[-1]}])["imageDetails"][0]
    digest=detail["imageDigest"]
    manifest=ecr.batch_get_image(repositoryName="dsf-ai",imageIds=[{"imageDigest":digest}])
    assert len(manifest.get("images",[]))==1 and not manifest.get("failures")
    emit("immutable_image",image=REPOSITORY+"@"+digest)
    allowed=set(ecs.meta.service_model.operation_model("RegisterTaskDefinition").input_shape.members)
    registration={k:copy.deepcopy(v) for k,v in td.items() if k in allowed}
    registration["containerDefinitions"][0]["image"]=REPOSITORY+"@"+digest
    definition=ecs.register_task_definition(**registration)["taskDefinition"]["taskDefinitionArn"]
    emit("registered",definition=definition)
    messages=oneoff(definition,s["networkConfiguration"],"rehearse")
    assert any("RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS" in line for line in messages)
    assert service()["taskDefinition"]==OLD_DEFINITION and task(OLD_TASK)["lastStatus"]=="RUNNING"
    before=observation()
    assert before["available"] and not before["checkpoint_error"]
    drained=False
    source_arn=old["taskArn"]
    candidate_arns=set()
    start_ms=int(time.time()*1000)-1000
    try:
        drained=True
        ecs.update_service(cluster=CLUSTER,service=SERVICE,desiredCount=0)
        emit("drain_requested",task=source_arn,observation=before)
        stopped=wait_stopped(source_arn)
        assert next(c for c in stopped["containers"] if c["name"]=="dsf-ai").get("exitCode")==0
        for _ in range(30):
            current=service()
            if (current["desiredCount"],current["runningCount"],current["pendingCount"])==(0,0,0):
                break
            time.sleep(2)
        zero_writers([source_arn])
        shutdown=log_messages(source_arn,start_ms)
        assert any("Application shutdown complete" in line for line in shutdown)
        assert not any("Traceback" in line or "Application shutdown failed" in line for line in shutdown)
        emit("clean_zero_writer",task=source_arn,logs=shutdown)
        backups=records(oneoff(definition,s["networkConfiguration"],"backup"),"a1.retention.final_backup.v1")
        assert len(backups)==1
        backup=backups[0]
        assert backup["current"]["identity"]==IDENTITY
        assert backup["current"]["organism_tick"]>=before["persisted_tick"]
        zero_writers([source_arn])
        activate(definition,backup,source_arn,candidate_arns,digest)
    except BaseException:
        if drained:
            ecs.update_service(cluster=CLUSTER,service=SERVICE,desiredCount=0)
            for desired in ("RUNNING","STOPPED"):
                candidate_arns.update(ecs.list_tasks(cluster=CLUSTER,serviceName=SERVICE,desiredStatus=desired)["taskArns"])
            for arn in candidate_arns|{source_arn}:
                wait_stopped(arn)
            for _ in range(30):
                current=service()
                if (current["desiredCount"],current["runningCount"],current["pendingCount"])==(0,0,0):
                    break
                time.sleep(2)
            zero_writers(candidate_arns|{source_arn})
            emit("failure_zero_writers_verified",state_preserved=True,no_old_checkpoint_restored=True)
        raise

if __name__=="__main__":
    main()
