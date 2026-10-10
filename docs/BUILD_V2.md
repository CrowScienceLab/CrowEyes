# CrowEyes 2.0 build and review

Windows x64 Python 3.12 is required for the supplied optional binary modules. Create a clean virtual environment, install requirements.txt and PyInstaller 6.22.0. Optional packages are pinned in requirements-optional.txt and kept outside the core. Install c2pa-python, numpy and onnxruntime into .publish-venv, rawpy into .optional-vendor/formats, and tokenizers into .optional-vendor/semantic. Keep runtime versions aligned between core and optional modules.

The semantic module requires models/clip in .optional-vendor/semantic: onnx/text_model_quantized.onnx, onnx/vision_model_quantized.onnx, tokenizer.json, preprocessor_config.json, LICENSE, SOURCE.json. SOURCE.json records the pinned model revision and hashes. Do not substitute model files without reviewing their source and updating these records. The safety model source/hash is documented in THIRD_PARTY_NOTICES.md.

Only edit version.json to change a release. Run tools/sync_version.py, then tools/build_extensions.py **before** building the core: the core embeds extensions.json with the exact archive hashes. Changing optional ZIPs afterward requires rebuilding the core.

```powershell
python tools/sync_version.py
python tools/check_v20.py
python tools/check_v20_regressions.py
python tools/build_extensions.py
python -m PyInstaller --noconfirm --clean --distpath dist/review-v2.0.0 --workpath build/review-v2.0.0 CrowEyes.spec
```

Run CrowEyes.exe --v20-self-test <report.json> <release/review-v2.0.0> with isolated LOCALAPPDATA. This checks absent heavy imports at startup, real exports, Windows OCR, optional ZIP installation, C2PA, filter inference, rawpy and semantic inference. If heic.heic (120×80) and sample.CR2 (1936×1288 embedded preview) are placed beside the report, their codecs are also exercised. tools/benchmark_v20.py compares source startup and rendering; it is not a cold installed application benchmark.

Inno Setup: pass /DMyDistDir=<absolute dist/review-v2.0.0/CrowEyes> and /O<absolute release/review-v2.0.0> to installer/CrowEyes.iss. ZIP the distribution contents with CrowEyes.exe at the top level for Portable. Run tools/build_store_msix.ps1 with MakeAppxPath, DistributionPath and PythonPath; move its release/CrowEyes_2.0.0.0_x64.msix result into the review directory. Store identity/publisher remain the existing product identity. Generate SHA256SUMS.txt for Setup, Portable, MSIX and all four modules.

Review before publishing. The current executable is unsigned; MSIX packaging validation does not establish Store certification. HEIC depends on installed Windows codecs; RAW is an embedded preview, not a RAW developer. HEIC/RAW EXIF extraction is not supported. High resolution viewer exports use preview pixels; batch conversion reads original pixels. Optional models and indexing consume memory while in use; closing and restarting the viewer releases their loaded runtimes.
