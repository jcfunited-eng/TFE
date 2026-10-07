"""Item 3 reuses the verified retained-state release and exact native artifact."""
import deploy_guala_item1 as release
release.ITEM='item3'
release.BASE='418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@sha256:7d9e7ecf05dafe0dd3321663782ffe9fa064223e6e7e49904faf54be1b9e35c7'
release.OLD_DEFINITION='arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1588'
release.OLD_TASK='cea3ca4e43d545fb85ef2d3438123545'
release.PRODUCTION=('dsf_ai_service/guala_caretaker_hand.py','dsf_ai_service/lean_embodiment_observation.py',
                    'guala_caretaker/caretaker.py','guala_caretaker/media.py','guala_caretaker/keep_caretaker.sh')
release.OPERATORS={'tools/guala_item3_actor_proof.py':'guala_item1_actor_proof.py',
                   'tools/guala_item1_release_operator.py':'guala_item1_release_operator.py',
                   'tools/guala_retention_release_operator.py':'a1_retention_release_operator.py',
                   'tools/guala_item3_asset.json':'item3_asset.json',
                   'guala_caretaker/curriculum/audio/number-08-eight-tutor-v1.wav':'item3_tutor.wav',
                   'guala_caretaker/curriculum/cards/number-08-eight-v1.png':'item3_card.png'}
release.EXTRA_FILES=('tools/deploy_guala_item3.py','tests/test_caretaker_pcm_tail.py',
                     'tests/test_caretaker_wav_blocks.py','tests/test_caretaker_accompaniment.py')
release.MARKER='ITEM3_PHYSICAL_CARETAKER_PCM_COLD_PASS'
if __name__=='__main__':release.main()
