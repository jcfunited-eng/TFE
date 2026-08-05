# GL-BRIEF-PILEON-MODEL-WC-20260614-02

Supersedes -01. Models the full page-load + active-user load: polling pile-on plus sustained camera/sound/text uploads. Streaming endpoints from parent brief Parts C/D do not exist yet, so this uses /addpicture and /addsound upload endpoints. When C/D land, this gets a v3 that adds the 2 Hz sight stream and 1.5 s sound stream.

## The test

    NEW_SID="pileon_$(date +%s)"
    API="https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    ALB="http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
    PNG_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    WAV_B64=$(python3 -c "import struct,base64,io; b=io.BytesIO(); b.write(b'RIFF'); b.write(struct.pack('<I',36+4000)); b.write(b'WAVEfmt '); b.write(struct.pack('<IHHIIHH',16,1,1,8000,8000,1,8)); b.write(b'data'); b.write(struct.pack('<I',4000)); b.write(b'\x80'*4000); print(base64.b64encode(b.getvalue()).decode())")
    (
      curl -s -o /tmp/v7s.out -w "v7_state %{http_code} %{time_total}s\n" "$API/v7/state?session_id=$NEW_SID" &
      curl -s -o /tmp/status.out -w "status %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d '{"command":"/status","text":""}' "$API/api/v1/gualaloom" &
      curl -s -o /tmp/events.out -w "events %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d '{"command":"/events","text":""}' "$API/api/v1/gualaloom" &
      curl -s -o /tmp/presence.out -w "presence %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d '{"command":"/presence","text":"joe"}' "$API/api/v1/gualaloom" &
      for i in $(seq 1 30); do
        sleep 1
        curl -s -o /dev/null -w "ready@${i}s %{http_code} %{time_total}s\n" "$ALB/ready"
        if [ $((i % 5)) -eq 0 ]; then curl -s -o /dev/null -w "pic@${i}s %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d "{\"command\":\"/addpicture:test_${i}.png\",\"text\":\"$PNG_B64\"}" "$API/api/v1/gualaloom" & ; fi
        if [ $((i % 7)) -eq 0 ]; then curl -s -o /dev/null -w "snd@${i}s %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d "{\"command\":\"/addsound:test_${i}.wav\",\"text\":\"$WAV_B64\"}" "$API/api/v1/gualaloom" & ; fi
        if [ $((i % 3)) -eq 0 ]; then curl -s -o /dev/null -w "txt@${i}s %{http_code} %{time_total}s\n" -X POST -H 'Content-Type: application/json' -d "{\"command\":\"\",\"text\":\"hello daddy\"}" "$API/api/v1/gualaloom" & ; fi
      done
      wait
    )
    sleep 5
    aws logs filter-log-events --log-group-name "/ecs/dsf-ai" --start-time $(python3 -c "import time; print(int((time.time()-90)*1000))") --filter-pattern "v7 OR decode OR ERROR" --limit 60 --query 'events[].message' --output text | tr '\t' '\n' | grep -v "^$"
    aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb --query 'services[0].deployments[].{status:status,td:taskDefinition,desired:desiredCount,running:runningCount,pending:pendingCount}' --output table
    aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52 --query 'TargetHealthDescriptions[*].{ip:Target.Id,state:TargetHealth.State,reason:TargetHealth.Reason}' --output table

## Acceptance

All four immediate calls 200. Every ready@Ns probe 200 under 1s, all 30. Picture/sound/text uploads 200. No Target.Timeout, no unhealthy. ECS one PRIMARY, no new pending. [v7-session] create_new logged.

If any fail, Phase 2 did not solve the binding constraint under realistic load.

## No code. No deploy. Report raw output. Stop.
