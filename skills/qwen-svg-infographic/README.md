# Qwen SVG Infographic

A weak-model wrapper for local LLMs, tuned on qwen3.8-27b, that guides creation of technical process infographics as editable SVG and PNG using Skillstead's renderer.

## Install

From the repository root, run `skills/qwen-svg-infographic/scripts/setup.sh`. Requires Node.js 18+, Python 3, Pillow, DejaVu Sans fonts, and a Chromium-family browser. Set `SVG_INFOGRAPHIC_BROWSER` to the browser executable if automatic discovery does not find it.

## Use

Ask: “Use the qwen-svg-infographic skill to make a one-page technical infographic about [topic].” Give the skill the output directory and content file path in your environment.

## Results

The retained best version is v5 (attempt 5), with an overall critic score of 6.2/10. The attempt history is 1–4: no scores recorded; 5: 6.2; 6: 6.0. These scores are an AI critic's assessment, not benchmarks. See `examples/best-attempt.png`.

## License

The upstream Skillstead svg-infographic license applies (Apache-2.0; see `LICENSE.txt`). Under Apache License 2.0, Section 4(b), this derivative distribution adds the Qwen wrapper skill, adjusts the renderer's paths and launcher for the bundled upstream renderer, and includes a template, setup script, and example image.
