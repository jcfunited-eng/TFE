"""
experience.py — ExperiencePipeline: delivers words to the LoomBrain.

GL-CMD-114 V2.1.

Ties together SensoryTransducer, SensoryCatalog, and LoomBrain.
Each word is delivered as a multi-modal broadcast to all 8 hemispheres.
No per-hemisphere routing by modality — hemispheres develop preferences
through experience, never by design.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .brain import LoomBrain
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer
from dsf_ai_service.substrate.sensory_generators import (
    generate_touch_waveform, generate_smell_waveform, generate_taste_waveform,
    transduce_sensory_signals,
)


# Modalities with waveform generators
_WAVEFORM_GENERATORS = {
    "touch": generate_touch_waveform,
    "smell": generate_smell_waveform,
    "taste": generate_taste_waveform,
}


class ExperiencePipeline:
    """Delivers words to the LoomBrain with multi-modal sensory grounding.

    For each word:
      1. Check catalog for applicable modalities (touch/smell/taste)
      2. Generate physical parameters via SensoryTransducer
      3. Produce waveforms and derive chi addresses
      4. Broadcast word + sensory data to all 8 hemispheres via brain.step()
    """

    def __init__(self, brain: LoomBrain, transducer: SensoryTransducer):
        self.brain = brain
        self.transducer = transducer

    def deliver_word(self, word: str, tick: int) -> Dict[str, Any]:
        """Deliver a single word to the brain with sensory grounding.

        Returns dict with modality chi values and step metadata.
        """
        modality_chis = {}

        # Generate sensory signals for applicable modalities
        for modality, gen_fn in _WAVEFORM_GENERATORS.items():
            params = self.transducer.transduce(modality, word, tick)
            waveform = gen_fn(params)
            channel_results = transduce_sensory_signals(waveform)
            for ch_name, ch_data in channel_results.items():
                modality_chis[f"{modality}_{ch_name}"] = ch_data["chi"]

        # Broadcast word to all hemispheres via brain.step()
        # The word string itself serves as the input signal for language krimelack
        results = self.brain.step(word, tick)

        # Count spike activity
        total_committed = 0
        per_hemi_committed = {}
        for hemi_id, hemi_results in results.items():
            committed = sum(1 for r in hemi_results.values() if r.get("committed"))
            per_hemi_committed[hemi_id] = committed
            total_committed += committed

        return {
            "word": word,
            "tick": tick,
            "modality_chis": modality_chis,
            "total_committed": total_committed,
            "per_hemi_committed": per_hemi_committed,
            "folds": dict(self.brain._last_fold_ids) if self.brain._last_fold_ids else {},
        }

    def deliver_sentence(self, sentence: str, tick_start: int,
                         ticks_per_word: int = 1) -> List[Dict]:
        """Deliver a sentence word-by-word at successive ticks."""
        words = sentence.strip().lower().split()
        results = []
        for i, word in enumerate(words):
            tick = tick_start + i * ticks_per_word
            result = self.deliver_word(word, tick)
            results.append(result)
        return results

    def deliver_corpus(self, sentences: List[str], tick_start: int = 0,
                       ticks_per_word: int = 1) -> Dict[str, Any]:
        """Deliver a list of sentences to the brain.

        Returns summary: total ticks, words delivered, final population per hemisphere.
        """
        tick = tick_start
        total_words = 0
        total_folds = 0

        for sentence in sentences:
            words = sentence.strip().lower().split()
            for word in words:
                self.deliver_word(word, tick)
                folds = self.brain._last_fold_ids
                total_folds += sum(len(v) for v in folds.values()) if folds else 0
                tick += ticks_per_word
                total_words += 1

        populations = {
            h.hemi_id: len(h.cluster.neurons)
            for h in self.brain.hemispheres
        }

        return {
            "total_ticks": tick - tick_start,
            "total_words": total_words,
            "total_folds": total_folds,
            "populations": populations,
            "total_neurons": self.brain.total_neurons(),
        }
