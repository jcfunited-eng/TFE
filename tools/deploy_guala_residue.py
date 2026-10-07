"""Existing household supplier: exact remnant export and declared-site renewal."""
import deploy_guala_item1 as release
release.ITEM = 'residue'
release.BASE = '418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@sha256:e7f9cfcb715a3ff36a4ac96d554075a65d17e30a42610e7b567a08fd44fe50fb'
release.OLD_DEFINITION = 'arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1590'
release.OLD_TASK = '1c5c045495cb438c9bf5081b78050905'
release.PRODUCTION = ('dsf_ai_service/guala_home_world.py', 'guala_caretaker/caretaker.py')
release.OPERATORS = {'tools/guala_residue_actor_proof.py': 'guala_item1_actor_proof.py', 'tools/guala_item1_release_operator.py': 'guala_item1_release_operator.py', 'tools/guala_retention_release_operator.py': 'a1_retention_release_operator.py'}
release.EXTRA_FILES = ('tools/deploy_guala_residue.py', 'tests/test_residual_food_housekeeping.py', 'tests/test_caretaker_satiety_supply.py', 'tests/test_wake_food_provision.py')
release.MARKER = 'RESIDUE_REAL_EXPORT_RENEWAL_RETAINED_COLD_PASS'
if __name__ == '__main__':
    release.main()
