"""Existing household stock supply and canonical satiety, exact retained native."""
import deploy_guala_item1 as release
release.ITEM='item5'
release.BASE='418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@sha256:098f219393b47f3e5ff8939696956e057b18aa518ec5a579a1a40fd893f93dc4'
release.OLD_DEFINITION='arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1589'
release.OLD_TASK='817cd5ea9a3c4dd0a73f9678373fecc8'
release.PRODUCTION=('dsf_ai_service/guala_caretaker_hand.py','guala_caretaker/caretaker.py')
release.OPERATORS={'tools/guala_item5_satiety_proof.py':'guala_item1_actor_proof.py',
                   'tools/guala_item1_release_operator.py':'guala_item1_release_operator.py',
                   'tools/guala_retention_release_operator.py':'a1_retention_release_operator.py'}
release.EXTRA_FILES=('tools/deploy_guala_item5.py','tests/test_caretaker_satiety_supply.py')
release.MARKER='ITEM5_ACTUAL_UNATTENDED_SATIETY_COLD_PASS'
if __name__=='__main__':release.main()
