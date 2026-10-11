# CrowEyes 2.0 build and review

Windows x64 Python 3.12 is required. Create a clean environment, install requirements.txt and PyInstaller 6.22.0. Native packages are pinned in requirements-optional.txt. Install c2pa-python, numpy and onnxruntime into .publish-venv, rawpy into .optional-vendor/formats. Their runtime files are included as data under bundled, with shared dependencies merged, and are imported only when used. No CLIP model or tokenizers is shipped.

The safety model source/hash is documented in THIRD_PARTY_NOTICES.md. Keep runtime versions aligned with the core and retain all package licenses. AI content search was removed at the user's request.

Only edit version.json to change a release. tools/build_extensions.py creates three intermediate runtime archives. tools/prepare_bundled.py verifies their hashes, merges identical dependencies into .bundled-runtime and records included.json. Run both before building the core. The final release contains Setup, Portable and MSIX; the intermediate runtime ZIPs are build inputs, not downloads required from users.

```powershell
python tools/sync_version.py
python tools/check_v20.py
python tools/check_v20_regressions.py
python tools/check_workspace.py
python tools/check_inline.py
python tools/build_extensions.py
python tools/prepare_bundled.py
python -m PyInstaller --noconfirm --clean --distpath dist/review-v2.0.0 --workpath build/review-v2.0.0 CrowEyes.spec
```

Run CrowEyes.exe --v20-self-test <report.json> with isolated LOCALAPPDATA and no module directory. This checks absent heavy imports at startup, exports, Windows OCR runtime, built-in C2PA, filter inference and rawpy. If heic.heic (120×80) and sample.CR2 (1936×1288 embedded preview) are placed beside the report, their codecs are also exercised. tools/benchmark_v20.py compares source startup and rendering; it is not a cold installed application benchmark.

Inno Setup: pass /DMyDistDir=<absolute dist/review-v2.0.0/CrowEyes> and /O<absolute release/review-v2.0.0> to installer/CrowEyes.iss. ZIP the distribution contents with CrowEyes.exe at the top level for Portable. Archive intermediate runtime ZIPs before validating the final release. Run tools/build_store_msix.ps1 with MakeAppxPath, DistributionPath and PythonPath; move the result into the review directory. Store identity/publisher remain unchanged. tools/validate_release.py verifies all bundled runtime files and generates SHA256SUMS.txt for the three final artifacts.

The UI has viewer/editor workspaces and shared yellow-beaked crow branding. Also run `CrowEyes.exe --workspace-self-test <report.json>` with isolated LOCALAPPDATA to test the frozen menus, state retention, shared file list, inline editing and small-window bounds without changing user preferences.

Current review stage: use `--distpath dist/preview-v2.0.0 --workpath build/preview-v2.0.0` for a raw executable preview. Do not rebuild Setup, Portable ZIP or MSIX before UI review. The editor shares the viewer file list and edits on the main canvas; no sidebar or filmstrip is created. See PREVIEW_INLINE_V2.md.

Review before publishing. The current executable is unsigned; MSIX packaging validation does not establish Store certification. HEIC depends on installed Windows codecs; RAW is an embedded preview, not a RAW developer. HEIC/RAW EXIF extraction is not supported. High resolution viewer exports use preview pixels; batch conversion reads original pixels. Optional models and indexing consume memory while in use; closing and restarting the viewer releases their loaded runtimes.
