# Sinopia

A lightweight, minimalist compositor. The aim is an early Photoshop: layers, masks, and a few tools, without Camera Raw, a photo importer, or the rest of the modern suite.

The picture you keep is a folder of PNGs plus `stack.txt`. PSD, PNG, and JPEG are exports. If the program stops, the pictures are still files you can open.

What it does now: stack layers and groups, rename them, mask them, paint, type in a chosen font and size, drop a shadow, zoom the view, and save. The window shows the same pixels the compositor writes. Still ahead: the healing brush, PSD export, and smart objects.

## Milestones

1. **Composite.** Done. A headless Normal blend of layers and masks, written to a PNG.
2. **Folder document.** Done. `stack.txt` plus one PNG per layer and mask. Loading the folder matches the proof.
3. **Window.** Done. The window shows the composite. Drag the picture to move the top layer.
4. **Brush.** Done. Press `b` and drag to paint the top layer. Press `v` to drag that layer again. The mask is not painted.
5. **Type and layer styles.** Type is on the canvas: press `t`, click, type, and press Enter to keep the letters. The top bar sets the font, the size in px or pt, bold, italic, strike, underline, kerning, and stroke. The built-in face is Sinopia. Other names are fontconfig families drawn by Pango; Enter bakes the pixels into the layer PNG, which stays the file you keep. The first layer style is a drop shadow, stored on the layer as `shadow dx dy`.
6. **Healing brush.**
7. **PSD, PNG, and JPEG export.** The folder stays the file we keep.
8. **Smart objects.** A nested folder plus a transform.

```
python3 -m sinopia
```

That writes `out/proof.png`, a red field with a soft green circle over it, and `out/document/`.

```
python3 -m sinopia.window
```

That opens the same picture. Move, brush, and type are in a column on the left: a cross, a brush nib, and an A, with the shortcut letter in the corner of each button. The pointer on the picture matches the tool. Layers are listed on the right, top of the picture first. Drag a name to restack it, including a group's name, which moves the whole group. Drop a row on the upper half of a layer to put it above that layer, or the lower half to put it under. Drop it on a group's name to put it inside that group. Click a selected name to rename it; spaces become hyphens, because the name is the PNG file. New, Group, and Delete sit under the list. Drag on the picture moves the selected layer. Press `b` to paint it, and `v` to move it again. Press `t` and the top bar shows the type options. Click, and type; Enter keeps the letters and Escape drops them. The letters are baked into the layer, so the picture does not need that font later. `+` and `−` zoom the view. Save writes the folder and `out/proof.png`. Letting go of a drag or a stroke saves too.

```
python3 -m unittest discover -s tests
```
