# CrowEyes third-party notices

CrowEyes 2.0 separates optional native libraries and AI models from the core.
Package license files are retained in each optional ZIP and the core distribution.

## Optional provenance, RAW and semantic search

- c2pa-python 0.37.10: https://github.com/contentauth/c2pa-python; MIT/Apache-2.0 notices in its package.
- rawpy 0.27.1: https://github.com/letmaik/rawpy; MIT wrapper and bundled LibRaw notices retained in rawpy distribution metadata.
- NumPy 2.5.2: https://numpy.org; BSD license and bundled OpenBLAS notices retained.
- tokenizers 0.23.3: https://github.com/huggingface/tokenizers; Apache-2.0 notices retained.
- Quantized CLIP: https://huggingface.co/Xenova/clip-vit-base-patch32, pinned revision d15189d7028b43f1d3e65039190477f6af591c2a. Based on OpenAI CLIP (https://github.com/openai/CLIP), MIT. Model source, revision, SHA-256 values and license are included in models/clip/SOURCE.json and LICENSE in the semantic module.
- HEIC uses installed Windows codecs. No pillow-heif/libheif/libx265 binary is shipped. Windows codec licenses and availability are managed separately by Windows/Microsoft Store.
- OCR uses installed Windows.Media.Ocr language components; no OCR model is bundled.

## NudeNet ONNX model

- Repository: <https://huggingface.co/deepghs/nudenet_onnx>
- Bundled file: `320n.onnx` (renamed to `nudenet-320n.onnx`)
- Model SHA-256: `C15D8273ADAD2D0A92F014CC69AB2D6C311A06777A55545F2C4EB46F51911F0F`
- Declared license: Apache License 2.0
- License text: `licenses/nudenet-onnx-Apache-2.0.txt`

CrowEyes applies its own conservative explicit-content policy to the model's
class scores. Covered-body classes are not blocking classes.

## ONNX Runtime

- Project: <https://github.com/microsoft/onnxruntime>
- Bundled version: 1.29.0 (CPU)
- License: MIT
- License text: `licenses/onnxruntime-MIT.txt`

Other Python dependencies retain their respective licenses and notices in the
packaged distribution where supplied by their wheels.
