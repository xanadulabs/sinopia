# Sinopia

A lightweight, minimalist compositor. The aim is an early Photoshop: layers, masks, and a few tools, without Camera Raw, a photo importer, or the rest of the modern suite.

The picture you keep is a folder of PNGs plus `stack.txt`. PSD, PNG, and JPEG are exports. If the program stops, the pictures are still files you can open.

Layers stack from the bottom. Each one has an image, a mask, an opacity, and a blend mode. Normal comes first. The window will show the same pixels the compositor writes. After that come a brush, type edited on the canvas, layer styles, and the healing brush. A PSD we write should open in Photoshop 7 and in current Photoshop. Smart objects wait until a normal layer already works.

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

That opens the same picture, with move, brush, and type in a column on the left. Drag moves the green layer. Press `b` to paint it, and `v` to move it again. Press `t`, click, and type; Enter keeps the letters and Escape drops them. Letting go of a drag or a stroke writes the folder.

```
python3 -m unittest discover -s tests
```
