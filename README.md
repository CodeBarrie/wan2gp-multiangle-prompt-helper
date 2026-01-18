# Multi-Angle Prompt Helper

A [WAN2GP](https://github.com/deepbeepmeep/Wan2GP) plugin that helps generate multi-angle prompts for 3D-consistent video generation with the Qwen Image Edit 2511 Multiple Angles LoRA.

## Screenshot

Adds a collapsible panel under the LoRA multiplier:

![Plugin UI](Main%20UI%20Change.png)

### Builder Tab
Build single prompts by selecting azimuth, elevation, and distance:

![Builder Tab](UI%20First%20Half.png)

### Batch Tab
Generate multiple prompts at once (8-view sweeps, 4-elevation sweeps, all 96 poses, etc.):

![Batch Tab](UI%202nd%20Half.png)

## Features

- **Builder**: Select azimuth (8 angles), elevation (4 levels), and distance (3 options) to create prompts
- **Presets**: Quick access to all 96 possible pose combinations
- **Batch generation**: Create 8-view sweeps, elevation sweeps, distance sweeps, or all 96 prompts at once
- **Direct injection**: Apply generated prompts directly to the main prompt box

## Installation

Copy the `wan2gp-multiangle-prompt-helper` folder into your WAN2GP `plugins` directory.

## Usage

1. Expand the "Multi-Angle Prompt Helper" accordion in the UI
2. Use the Builder tab for single prompts or Batch tab for multiple
3. Click "Apply to Prompts box" to inject the prompts

## License

MIT
