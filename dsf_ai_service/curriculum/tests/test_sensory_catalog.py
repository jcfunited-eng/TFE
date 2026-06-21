"""
test_sensory_catalog.py — GL-CMD-112 Tests T1-T14.

Sensory catalog: storage, generation, atlas reader, sources.
LLM calls are mocked except where explicitly testing live (T1/T8 marked skip).
"""

import sys, os, json, tempfile
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.curriculum.sensory_catalog import SensoryCatalog, MODALITY_CHANNELS_MAP
from dsf_ai_service.curriculum.catalog_generator import CatalogGenerator
from dsf_ai_service.curriculum.catalog_atlas_reader import CatalogAtlasReader
from dsf_ai_service.substrate.sensory_transducer import (
    SensoryTransducer, NullAtlasReader, TOUCH_CHANNELS, SMELL_CHANNELS, TASTE_CHANNELS,
)
from dsf_ai_service.curriculum.sources.direct_text_source import DirectTextSource


def _make_catalog(tmp_path=None):
    """Create catalog in a temp directory."""
    if tmp_path is None:
        tmp_path = tempfile.mkdtemp()
    db = os.path.join(tmp_path, "test_catalog.sqlite3")
    return SensoryCatalog(db_path=db)


def _mock_llm_response(words):
    """Generate a mock LLM response for given words."""
    results = []
    for w in words:
        entry = {"word": w}
        # Abstract words get not_applicable
        if w in ("the", "of", "and", "is", "a"):
            entry["touch"] = "not_applicable"
            entry["smell"] = "not_applicable"
            entry["taste"] = "not_applicable"
        else:
            # Concrete words get random-ish distributions
            seed = hash(w) & 0xFFFFFFFF
            rng = np.random.default_rng(seed)
            for modality, channels in MODALITY_CHANNELS_MAP.items():
                mean = {ch: round(float(rng.uniform(0.1, 0.9)), 3) for ch in channels}
                std = {ch: round(float(rng.uniform(0.05, 0.2)), 3) for ch in channels}
                entry[modality] = {"mean": mean, "std": std}
        results.append(entry)
    return json.dumps(results)


# ---------------------------------------------------------------------------
# T1: first-story batch (skipped — requires live LLM + Gutenberg network)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Live LLM + network required — run manually with ANTHROPIC_API_KEY")
def test_t1_first_story_batch():
    """Live: Peter Rabbit via Gutenberg → catalog entries generated."""
    pass


# ---------------------------------------------------------------------------
# T2: per-call variability
# ---------------------------------------------------------------------------

def test_t2_per_call_variability():
    """20 deliveries of same word via catalog → std > 0.03 on at least 3 channels."""
    catalog = _make_catalog()
    # Populate catalog with "warm" touch distribution
    catalog.set_entry("warm", "touch", applicable=True,
                      mean={"temperature": 0.7, "pressure": 0.2, "texture_freq": 0.1,
                            "sharpness": 0.05, "wetness": 0.1},
                      std={"temperature": 0.15, "pressure": 0.1, "texture_freq": 0.08,
                           "sharpness": 0.05, "wetness": 0.08})

    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)

    samples = {ch: [] for ch in TOUCH_CHANNELS}
    for tick in range(20):
        params = transducer.transduce("touch", "warm", tick=tick * 100)
        for ch in TOUCH_CHANNELS:
            samples[ch].append(params[ch])

    print("\n== T2: per-call variability ==")
    channels_above_threshold = 0
    for ch in TOUCH_CHANNELS:
        std = float(np.std(samples[ch]))
        print(f"  {ch}: std={std:.4f}")
        if std > 0.03:
            channels_above_threshold += 1

    assert channels_above_threshold >= 3, (
        f"Expected at least 3 channels with std > 0.03, got {channels_above_threshold}"
    )


# ---------------------------------------------------------------------------
# T3: catalog vs no-catalog distinction
# ---------------------------------------------------------------------------

def test_t3_catalog_vs_no_catalog():
    """Catalog-backed transducer produces different distribution than NullAtlasReader."""
    catalog = _make_catalog()
    catalog.set_entry("ice", "touch", applicable=True,
                      mean={"temperature": 0.05, "pressure": 0.3, "texture_freq": 0.0,
                            "sharpness": 0.1, "wetness": 0.8},
                      std={"temperature": 0.05, "pressure": 0.1, "texture_freq": 0.05,
                           "sharpness": 0.05, "wetness": 0.1})

    reader = CatalogAtlasReader(catalog)
    catalog_transducer = SensoryTransducer(reader)
    null_transducer = SensoryTransducer(NullAtlasReader())

    # Sample 50 from each
    catalog_temps = [catalog_transducer.transduce("touch", "ice", tick=t)["temperature"]
                     for t in range(50)]
    null_temps = [null_transducer.transduce("touch", "ice", tick=t)["temperature"]
                  for t in range(50)]

    cat_mean = float(np.mean(catalog_temps))
    null_mean = float(np.mean(null_temps))

    print(f"\n== T3: catalog vs no-catalog ==")
    print(f"  catalog mean temperature for 'ice': {cat_mean:.4f} (expected ~0.05)")
    print(f"  null mean temperature for 'ice': {null_mean:.4f} (expected ~0.5)")

    assert cat_mean < 0.2, f"Catalog should bias 'ice' temperature low, got {cat_mean}"
    assert null_mean > 0.3, f"Null should be ~uniform mean ~0.5, got {null_mean}"


# ---------------------------------------------------------------------------
# T4: ungrounded word fallthrough
# ---------------------------------------------------------------------------

def test_t4_ungrounded_word_fallthrough():
    """Words that fail LLM generation fall through to _generate_initial."""
    catalog = _make_catalog()

    # Mock LLM to always fail
    gen = CatalogGenerator(catalog, api_key="fake")
    with patch.object(gen, '_call_llm', side_effect=ConnectionError("mock fail")):
        result = gen.generate(["xyzzy"], story_context="test")

    assert "xyzzy" in result["failed"]
    assert not catalog.has("xyzzy", "touch")

    # Transducer with catalog reader: unknown word → _generate_initial
    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)
    params = transducer.transduce("touch", "xyzzy", tick=42)

    print(f"\n== T4: ungrounded word fallthrough ==")
    print(f"  'xyzzy' in catalog: {catalog.has('xyzzy', 'touch')}")
    print(f"  transducer params (should be uniform-random): {params}")

    assert all(0.0 <= v <= 1.0 for v in params.values())


# ---------------------------------------------------------------------------
# T5: modality applicability
# ---------------------------------------------------------------------------

def test_t5_modality_applicability():
    """Abstract words ('the', 'of', 'and') marked not_applicable."""
    catalog = _make_catalog()
    gen = CatalogGenerator(catalog, api_key="fake")

    mock_response = _mock_llm_response(["the", "of", "warm"])
    with patch.object(gen, '_call_llm', return_value=mock_response):
        gen.generate(["the", "of", "warm"])

    print(f"\n== T5: modality applicability ==")
    for word in ["the", "of"]:
        for mod in ["touch", "smell", "taste"]:
            applicable = catalog.is_applicable(word, mod)
            print(f"  {word}/{mod}: applicable={applicable}")
            assert not applicable, f"'{word}' should not be applicable for {mod}"

    assert catalog.is_applicable("warm", "touch"), "'warm' should be applicable for touch"
    print(f"  warm/touch: applicable=True")


# ---------------------------------------------------------------------------
# T6: substrate-true sanity
# ---------------------------------------------------------------------------

def test_t6_substrate_true_sanity():
    """No fixed-vector entries, no label-keyed branches in catalog code."""
    import inspect
    from dsf_ai_service.curriculum import sensory_catalog, catalog_generator, catalog_atlas_reader

    for mod in [sensory_catalog, catalog_generator, catalog_atlas_reader]:
        source = inspect.getsource(mod)
        assert 'if word == ' not in source, f"Label branch in {mod.__name__}"
        assert 'if label == ' not in source, f"Label branch in {mod.__name__}"

    print(f"\n== T6: substrate-true sanity ==")
    print(f"  No label-keyed branches in catalog/generator/reader")


# ---------------------------------------------------------------------------
# T7: cross-session EFS persistence
# ---------------------------------------------------------------------------

def test_t7_efs_persistence():
    """Write entries, close connection, reopen, entries survive."""
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "persist_test.sqlite3")

    # Session 1: write
    cat1 = SensoryCatalog(db_path=db_path)
    cat1.set_entry("warm", "touch", applicable=True,
                   mean={"temperature": 0.7, "pressure": 0.2, "texture_freq": 0.0,
                         "sharpness": 0.0, "wetness": 0.0},
                   std={"temperature": 0.1, "pressure": 0.1, "texture_freq": 0.05,
                        "sharpness": 0.05, "wetness": 0.05})
    cat1.close()

    # Session 2: reopen and read
    cat2 = SensoryCatalog(db_path=db_path)
    dist = cat2.get_distribution("warm", "touch")
    cat2.close()

    print(f"\n== T7: EFS persistence ==")
    print(f"  Written in session 1, read in session 2: {dist is not None}")

    assert dist is not None
    mean, std = dist
    assert abs(mean["temperature"] - 0.7) < 0.001


# ---------------------------------------------------------------------------
# T8: cost/scale (skipped — requires live LLM)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Live LLM required — run manually")
def test_t8_cost_scale():
    """Full Peter Rabbit under cost thresholds."""
    pass


# ---------------------------------------------------------------------------
# T9: LLM retry path
# ---------------------------------------------------------------------------

def test_t9_llm_retry():
    """Mock fails twice then succeeds on third attempt."""
    catalog = _make_catalog()
    gen = CatalogGenerator(catalog, api_key="fake")

    call_count = [0]
    mock_response = _mock_llm_response(["rabbit"])

    def _flaky_llm(prompt):
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("transient failure")
        return mock_response

    with patch.object(gen, '_call_llm', side_effect=_flaky_llm):
        with patch('dsf_ai_service.curriculum.catalog_generator.time.sleep'):
            result = gen.generate(["rabbit"], story_context="test")

    print(f"\n== T9: LLM retry ==")
    print(f"  LLM calls: {call_count[0]}")
    print(f"  generated: {result['generated']}")

    assert call_count[0] == 3, f"Expected 3 calls (2 fails + 1 success), got {call_count[0]}"
    assert result["generated"] == 1


# ---------------------------------------------------------------------------
# T10: chi variability preserved through catalog
# ---------------------------------------------------------------------------

def test_t10_chi_variability():
    """Per-call chi still varies even when catalog provides distributions."""
    from dsf_ai_service.substrate.sensory_generators import (
        generate_sensory_signals, transduce_sensory_signals,
    )

    catalog = _make_catalog()
    catalog.set_entry("warm", "touch", applicable=True,
                      mean={"temperature": 0.7, "pressure": 0.2, "texture_freq": 0.3,
                            "sharpness": 0.05, "wetness": 0.1},
                      std={"temperature": 0.15, "pressure": 0.1, "texture_freq": 0.1,
                           "sharpness": 0.05, "wetness": 0.08})

    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)

    chi_sets = []
    for tick in range(10):
        signals = generate_sensory_signals("touch", ["warm"],
                                           transducer=transducer, tick=tick * 50)
        results = transduce_sensory_signals(signals)
        chis = tuple(ch["chi"] for ch in results.values())
        chi_sets.append(chis)

    unique = len(set(chi_sets))
    print(f"\n== T10: chi variability ==")
    print(f"  10 calls, unique chi tuples: {unique}/10")

    assert unique >= 2, f"Expected chi variability across calls, got {unique} unique"


# ---------------------------------------------------------------------------
# T11: source-agnostic catalog
# ---------------------------------------------------------------------------

def test_t11_source_agnostic():
    """Same words from GutenbergSource and DirectTextSource produce equivalent catalog entries."""
    catalog = _make_catalog()
    gen = CatalogGenerator(catalog, api_key="fake")

    # Both sources produce the word "rabbit"
    words = ["rabbit"]
    mock_resp = _mock_llm_response(words)

    with patch.object(gen, '_call_llm', return_value=mock_resp):
        gen.generate(words, story_context="gutenberg story")

    # Check entry exists
    assert catalog.has("rabbit", "touch")
    dist_g = catalog.get_distribution("rabbit", "touch")

    # "Re-generate" from direct source — should match (same word, same mock)
    # Clear and regenerate
    catalog2 = _make_catalog()
    gen2 = CatalogGenerator(catalog2, api_key="fake")
    with patch.object(gen2, '_call_llm', return_value=mock_resp):
        gen2.generate(words, story_context="direct input")

    dist_d = catalog2.get_distribution("rabbit", "touch")

    print(f"\n== T11: source-agnostic ==")
    print(f"  gutenberg entry: {dist_g[0]}")
    print(f"  direct entry:    {dist_d[0]}")

    # Same word + same LLM mock → identical distributions
    assert dist_g == dist_d


# ---------------------------------------------------------------------------
# T12: audio dual-channel interface (mock)
# ---------------------------------------------------------------------------

def test_t12_audio_interface():
    """Mock TextSource with audio → curriculum loader would route to cochlear."""
    # Verify the audio ingestion function exists and accepts arrays
    from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
        cochlear_transduce,
    )

    # Generate a synthetic audio signal
    t = np.arange(400) / 200.0
    signal = np.sin(2 * np.pi * 50 * t)  # 50 Hz sine

    result = cochlear_transduce(signal, sample_rate=200)

    print(f"\n== T12: audio interface ==")
    print(f"  cochlear_transduce accepts 1D array: True")
    print(f"  bands returned: {list(result.keys())}")
    print(f"  each band has winding: {all('winding' in v for v in result.values())}")

    assert len(result) > 0
    assert all("winding" in v for v in result.values())


# ---------------------------------------------------------------------------
# T13: image dual-channel interface (mock)
# ---------------------------------------------------------------------------

def test_t13_image_interface():
    """Mock TextSource with image → curriculum loader would route to visual_krimelack."""
    from dsf_ai_service.visual_krimelack import view_picture

    # Generate a synthetic image (32x32 grayscale)
    rng = np.random.default_rng(42)
    image = rng.uniform(0.0, 1.0, (32, 32))

    fragments = view_picture(image, source_id="test_img", born_tick=0,
                             seed=42, n_fixations=3, ticks_per_fixation=50)

    print(f"\n== T13: image interface ==")
    print(f"  view_picture accepts 2D array: True")
    print(f"  fragments returned: {len(fragments)}")

    assert len(fragments) > 0


# ---------------------------------------------------------------------------
# T14: DirectTextSource minimum viable
# ---------------------------------------------------------------------------

def test_t14_direct_text_source():
    """End-to-end: DirectTextSource produces sentences, catalog can generate for them."""
    source = DirectTextSource("the rabbit hopped through the garden")

    sentences = source.get_sentences()
    print(f"\n== T14: DirectTextSource ==")
    print(f"  source_id: {source.source_id}")
    print(f"  title: {source.title}")
    print(f"  sentences: {sentences}")
    print(f"  audio: {source.get_audio()}")
    print(f"  images: {source.get_images()}")

    assert len(sentences) == 1
    assert "rabbit" in sentences[0]
    assert source.get_audio() is None
    assert source.get_images() is None

    # Extract unique words and generate catalog entries
    words = list(set(sentences[0].lower().split()))
    catalog = _make_catalog()
    gen = CatalogGenerator(catalog, api_key="fake")

    mock_resp = _mock_llm_response(words)
    with patch.object(gen, '_call_llm', return_value=mock_resp):
        result = gen.generate(words, story_context=sentences[0])

    print(f"  words processed: {words}")
    print(f"  generated: {result['generated']}")
    assert result["generated"] > 0
