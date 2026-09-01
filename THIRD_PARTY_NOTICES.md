# CrowEyes third-party notices

CrowEyes Image Viewer 1.8 includes the following components for its optional,
fully local content-safety feature.

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
