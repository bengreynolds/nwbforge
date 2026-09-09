# Pilot Supported Adapter Baseline

Purpose: keep the repo-native supported-path fixture small while real NeuroConv routes scale.

Current baseline:
- The manifest-backed pilot still exists for deterministic architecture validation
- Real supported routes now use the shared NeuroConv adapter framework and family modules
- Supported route selection remains NeuroConv-first

Constraints:
- The pilot should not be mistaken for a long-term primary ingest format
- Supported-path work should prefer documented NeuroConv routes when available

Next step:
- Retire the pilot only when the supported-route coverage is representative enough for testing
