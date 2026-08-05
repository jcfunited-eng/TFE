
# intrinsic_motivation.py
import numpy as np, random
class DriveController:
    def __init__(self):
        self.last_phi = None
        self.energy_floor = 0.28
        self.explore_bias = 0.18

    def score(self, phi, energy, entropy):
        dphi = 0.0 if self.last_phi is None else (phi - self.last_phi)
        self.last_phi = phi
        return float(0.6*dphi + 0.2*(entropy) + 0.2*(energy - self.energy_floor))

    def propose_microgoal(self, ms):
        meanE = float(np.mean([n.energy for n in ms.nodes.values()]))
        if meanE < self.energy_floor: return "REST"
        return "EXPLORE" if random.random() < self.explore_bias else "STABILIZE"
