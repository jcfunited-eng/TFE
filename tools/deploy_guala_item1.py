"""Item 1 overlay release; preserve the deployed native artifact and lived pair.

--plan is read-only. --execute uses the verified zero-writer activation sequence.
"""
import argparse,base64,copy,hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
import boto3
import deploy_guala_retention_release as release

ROOT=Path(__file__).resolve().parents[1]
BASE='418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@sha256:8c2589d3b4a5583255a65aadb6f34deb4f394fa1a66e0d9fdaf0889926ff8451'
OLD_DEFINITION='arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1586'
OLD_TASK='36e5e4e7841d41bf959d4c7654eecd35'
PRODUCTION=('dsf_ai_service/guala_caretaker_hand.py','dsf_ai_service/guala_functional_organism.py')
OPERATORS={'tools/guala_item1_actor_proof.py':'guala_item1_actor_proof.py',
           'tools/guala_item1_release_operator.py':'guala_item1_release_operator.py',
           'tools/guala_retention_release_operator.py':'a1_retention_release_operator.py'}
MARKER='ITEM1_ELIGIBILITY_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS'

def main():
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--evidence',type=Path,required=True)
 p.add_argument('--execute',action='store_true');p.add_argument('--plan',action='store_true');a=p.parse_args()
 os.chdir(ROOT);a.evidence=a.evidence.resolve();commit=a.commit
 assert boto3.client('sts',region_name=release.REGION,config=release.CONFIG).get_caller_identity()['Account']==release.ACCOUNT
 assert shutil.which('docker') and shutil.which('git')
 paths=(*PRODUCTION,*OPERATORS,'tools/deploy_guala_item1.py','tools/deploy_guala_retention_release.py','tests/test_guala_food_depletion.py')
 hashes={}
 for path in paths:
  raw=(ROOT/path).read_bytes();assert subprocess.check_output(['git','show',commit+':'+path])==raw,path
  hashes[path]=hashlib.sha256(raw).hexdigest()
 for filename in ('focused-result.json','operator-proof-result.json'):
  proof=json.loads((a.evidence/filename).read_text());assert proof['exit']==0 and not proof['state']['OOMKilled']
  for path in PRODUCTION:assert proof['files'][path]==hashes[path]
 assert MARKER in (a.evidence/'operator-proof.log').read_text()
 s=release.service();assert s['taskDefinition']==OLD_DEFINITION
 assert (s['desiredCount'],s['runningCount'],s['pendingCount'])==(1,1,0)
 dc=s['deploymentConfiguration'];assert not dc.get('deploymentCircuitBreaker',{}).get('rollback',False)
 assert not dc.get('alarms',{}).get('rollback',False)
 scaling=boto3.client('application-autoscaling',region_name=release.REGION,config=release.CONFIG)
 assert not scaling.describe_scalable_targets(ServiceNamespace='ecs',ResourceIds=['service/'+release.CLUSTER+'/'+release.SERVICE])['ScalableTargets']
 old=release.task(OLD_TASK);assert old['lastStatus']=='RUNNING'
 assert next(c for c in old['containers'] if c['name']=='dsf-ai')['imageDigest']==BASE.split('@')[1]
 assert release.ecs.list_tasks(cluster=release.CLUSTER,serviceName=release.SERVICE,desiredStatus='RUNNING')['taskArns']==[old['taskArn']]
 td=release.ecs.describe_task_definition(taskDefinition=OLD_DEFINITION)['taskDefinition']
 assert (td['cpu'],td['memory'])==('2048','8192') and len(td['containerDefinitions'])==1
 env={e['name']:e['value'] for e in td['containerDefinitions'][0]['environment']}
 assert env['GUALA_PAIRED_ROOT']=='/app/guala/paired-current-gen2' and env['GUALA_MAX_WORLD_BYTES']=='16777216'
 ob=release.observation();assert ob['available'] and not any(ob[k] for k in ('checkpoint_error','cleanup_error','durability_blocked'))
 release.emit('item1_plan_verified',commit=commit,base=BASE,files=hashes,source=old['taskArn'],observation=ob,
              operator_command=['python3','/opt/guala_item1_release_operator.py','rehearse'],ui_changed=False)
 if not a.execute:return
 folder=a.evidence/'release';folder.mkdir();release.journal=folder/'receipt.jsonl';release.emit('item1_release_start',commit=commit)
 context=Path(tempfile.mkdtemp(prefix='guala-item1-build-'))
 dockerfile=['FROM '+BASE,'ARG RELEASE_COMMIT','ENV GIT_SHA=${RELEASE_COMMIT}']
 for path in PRODUCTION:
  dest=context/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,dest);dockerfile.append('COPY '+path+' /app/'+path)
 for path,name in OPERATORS.items():
  shutil.copy2(ROOT/path,context/name);dockerfile.append('COPY '+name+' /opt/'+name)
 (context/'Dockerfile').write_text('\n'.join(dockerfile)+'\n')
 tag=release.REPOSITORY+':a1-item1-'+commit[:12]
 with (folder/'build.log').open('w') as log:
  subprocess.run(['docker','build','--build-arg','RELEASE_COMMIT='+commit,'-t',tag,str(context)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 release.emit('image_built',tag=tag)
 auth=release.ecr.get_authorization_token()['authorizationData'][0];user,password=base64.b64decode(auth['authorizationToken']).decode().split(':',1)
 subprocess.run(['docker','login','--username',user,'--password-stdin',auth['proxyEndpoint']],input=password,text=True,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with (folder/'push.log').open('w') as log:subprocess.run(['docker','push',tag],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 digest=release.ecr.describe_images(repositoryName='dsf-ai',imageIds=[{'imageTag':tag.split(':')[-1]}])['imageDetails'][0]['imageDigest']
 manifest=release.ecr.batch_get_image(repositoryName='dsf-ai',imageIds=[{'imageDigest':digest}]);assert len(manifest.get('images',[]))==1 and not manifest.get('failures')
 release.emit('immutable_image',image=release.REPOSITORY+'@'+digest)
 allowed=set(release.ecs.meta.service_model.operation_model('RegisterTaskDefinition').input_shape.members)
 registration={k:copy.deepcopy(v) for k,v in td.items() if k in allowed};registration['containerDefinitions'][0]['image']=release.REPOSITORY+'@'+digest
 definition=release.ecs.register_task_definition(**registration)['taskDefinition']['taskDefinitionArn'];release.emit('registered',definition=definition)
 messages=release.oneoff(definition,s['networkConfiguration'],'rehearse',command=['python3','/opt/guala_item1_release_operator.py','rehearse'])
 assert any(MARKER in line for line in messages)
 assert release.service()['taskDefinition']==OLD_DEFINITION and release.task(OLD_TASK)['lastStatus']=='RUNNING'
 before=release.observation();assert before['available'] and not before['checkpoint_error']
 source=old['taskArn'];candidate_arns=set();drained=False;start_ms=int(time.time()*1000)-1000
 try:
  drained=True;release.ecs.update_service(cluster=release.CLUSTER,service=release.SERVICE,desiredCount=0)
  release.emit('drain_requested',task=source,observation=before)
  stopped=release.wait_stopped(source);assert next(c for c in stopped['containers'] if c['name']=='dsf-ai').get('exitCode')==0
  for _ in range(30):
   current=release.service()
   if (current['desiredCount'],current['runningCount'],current['pendingCount'])==(0,0,0):break
   time.sleep(2)
  release.zero_writers([source]);shutdown=release.log_messages(source,start_ms)
  assert any('Application shutdown complete' in line for line in shutdown)
  assert not any('Traceback' in line or 'Application shutdown failed' in line for line in shutdown)
  release.emit('clean_zero_writer',task=source,logs=shutdown)
  backups=release.records(release.oneoff(definition,s['networkConfiguration'],'backup',command=['python3','/opt/guala_item1_release_operator.py','backup']),'a1.retention.final_backup.v1')
  assert len(backups)==1;backup=backups[0];assert backup['current']['identity']==release.IDENTITY
  assert backup['current']['organism_tick']>=before['persisted_tick'];release.zero_writers([source])
  release.activate(definition,backup,source,candidate_arns,digest)
 except BaseException:
  if drained:
   release.ecs.update_service(cluster=release.CLUSTER,service=release.SERVICE,desiredCount=0)
   for desired in ('RUNNING','STOPPED'):candidate_arns.update(release.ecs.list_tasks(cluster=release.CLUSTER,serviceName=release.SERVICE,desiredStatus=desired)['taskArns'])
   for arn in candidate_arns|{source}:release.wait_stopped(arn)
   for _ in range(30):
    current=release.service()
    if (current['desiredCount'],current['runningCount'],current['pendingCount'])==(0,0,0):break
    time.sleep(2)
   release.zero_writers(candidate_arns|{source});release.emit('failure_zero_writers_verified',state_preserved=True)
  raise
if __name__=='__main__':main()
