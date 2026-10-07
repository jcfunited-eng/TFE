"""Item 2 uses the verified release sequence with its own exact scoped artifact."""
import deploy_guala_item1 as release
release.ITEM='item2'
release.BASE='418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@sha256:a9142bd076614df7b6d8c82e15d374b8df4e07e0955600ea64f68d0b8a85ed43'
release.OLD_DEFINITION='arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1587'
release.OLD_TASK='37ffd51aa93d40fcae9011ccc7ca5912'
release.PRODUCTION=('dsf_ai_service/guala_functional_organism.py','dsf_ai_service/substrate/embodiment_world.py')
release.OPERATORS={'tools/guala_item2_actor_proof.py':'guala_item1_actor_proof.py',
                   'tools/guala_item1_release_operator.py':'guala_item1_release_operator.py',
                   'tools/guala_retention_release_operator.py':'a1_retention_release_operator.py'}
release.EXTRA_FILES=('tools/deploy_guala_item2.py','tests/test_guala_selected_pick.py','tests/test_backyard_apple_tree_foraging.py')
release.MARKER='ITEM2_ACTUAL_UNATTENDED_INTAKE_COLD_PASS'
if __name__=='__main__':release.main()
