# Sinopia

A lightweight, minimalist compositor. The aim is an early Photoshop: layers, masks, and a few tools, without Camera Raw, a photo importer, or the rest of the modern suite.

The picture you keep is a folder of PNGs plus `stack.txt`. PSD, PNG, and JPEG are exports. If the program stops, the pictures are still files you can open.

What it does now: stack layers and groups, mask them, paint, type, drop a shadow, zoom the view, and save. The window shows the same pixels the compositor writes. Still ahead: the healing brush, PSD export, and smart objects.

## Milestones

1. **Composite.** Done. A headless Normal blend of layers and masks, written to a PNG.
2. **Folder document.** Done. `stack.txt` plus one PNG per layer and mask. Loading the folder matches the proof.
3. **Window.** Done. The window shows the composite. Drag the picture to move the top layer.
4. **Brush.** Done. Press `b` and drag to paint the top layer. Press `v` to drag that layer again. The mask is not painted.
5. **Type and layer styles.** Type is on the canvas: press `t`, click, type, and press Enter to keep the letters. The first layer style is a drop shadow, stored on the layer as `shadow dx dy`.
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

That opens the same picture. Move, brush, and type are in a column on the left. Layers are listed on the right, top of the picture first. Drag a name to restack it. Drop it on the upper half of another row to put it above that layer, the lower half to put it under, or the middle of a group to put it inside. New, Group, and Delete sit under the list. Drag on the picture moves the selected layer. Press `b` to paint it, and `v` to move it again. Press `t`, click, and type; Enter keeps the letters and Escape drops them. `+` and `−` zoom the view. Save writes the folder and `out/proof.png`. Letting go of a drag or a stroke saves too.

```
python3 -m unittest discover -s tests
```
