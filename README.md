# Locator-Inside
Center of Mass locator addon for Blender



# COM Locator – Blender Addon

A Blender addon that visualizes the **Center of Mass** of an armature in real time, with an optional support plane for balance analysis.

<img width="1250" height="834" alt="image" src="https://github.com/user-attachments/assets/de0274a0-4d54-4741-8da5-b6c03c9eeea1" />

## Features

- Tracks center of mass based on selected bones (or all bones if none selected)
- Each bone can have a custom weight
- Support plane shows the base of support (e.g. both feet)
- Locator updates in real time and during animation playback
- All objects are placed in a dedicated **COM Locator** collection

## Installation

1. Download `__init__.py`
2. In Blender: **Edit → Preferences → Add-ons → Install**
3. Select the downloaded file
4. Enable the addon by checking the checkbox

## Usage

1. Open the sidebar in 3D Viewport: press **N**
2. Go to the **COM Locator** tab
3. Select your armature
4. Add bones to **Tracked Bones** (center of mass) and **Support Bones** (support plane)
5. Press **Setup COM Locator**

## Requirements

- Blender 4.0 or newer

## License

MIT
