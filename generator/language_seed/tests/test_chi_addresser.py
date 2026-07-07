import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import chi_addresser as ca
from generator.language_seed import config


def test_stable_hash_deterministic():
    assert ca.stable_hash("dog") == ca.stable_hash("dog")
    assert ca.stable_hash("dog") != ca.stable_hash("cat")


def test_compute_cluster_bands_covers_full_space_no_overlap():
    counts = {"noun.animal": 100, "verb.motion": 50, "adj.all": 25}
    bands = ca.compute_cluster_bands(counts, n_cells=1000, headroom=1.0)
    total = sum(size for _, size in bands.values())
    assert total == 1000
    intervals = sorted(bands.values())
    for i in range(len(intervals) - 1):
        start_a, size_a = intervals[i]
        start_b, _ = intervals[i + 1]
        assert start_a + size_a <= start_b


def test_assign_no_collisions_within_and_across_clusters():
    counts = {"a": 5, "b": 5}
    addresser = ca.ChiAddresser(counts)
    words_a = [f"a{i}" for i in range(5)]
    words_b = [f"b{i}" for i in range(5)]
    chis = []
    for w in words_a:
        chis.append(addresser.assign(w, "a"))
    for w in words_b:
        chis.append(addresser.assign(w, "b"))
    assert len(chis) == len(set(chis)), "chi collision detected"
    for chi in chis:
        assert config.CHI_MIN <= chi <= config.CHI_MAX


def test_assign_idempotent():
    addresser = ca.ChiAddresser({"a": 3})
    c1 = addresser.assign("word", "a")
    c2 = addresser.assign("word", "a")
    assert c1 == c2


def test_band_exhaustion_falls_back_to_global_probe():
    # tiny band (size 1) forces overflow for the 2nd word in the same cluster
    counts = {"a": 1}
    addresser = ca.ChiAddresser(counts)
    c1 = addresser.assign("first", "a")
    c2 = addresser.assign("second", "a")
    assert c1 != c2
    assert config.CHI_MIN <= c2 <= config.CHI_MAX


if __name__ == "__main__":
    test_stable_hash_deterministic()
    test_compute_cluster_bands_covers_full_space_no_overlap()
    test_assign_no_collisions_within_and_across_clusters()
    test_assign_idempotent()
    test_band_exhaustion_falls_back_to_global_probe()
    print("ALL PASS: test_chi_addresser")
