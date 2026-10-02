# Sinopia

A lightweight, minimalist compositor. The aim is an early Photoshop: layers, masks, and a few tools, without Camera Raw, a photo importer, or the rest of the modern suite.

The picture you keep is a folder of PNGs plus `stack.txt`. PSD, PNG, and JPEG are exports. If the program stops, the pictures are still files you can open.

Layers stack from the bottom. Each one has an image, a mask, an opacity, and a blend mode. Normal comes first. The window will show the same pixels the compositor writes. After that come a brush, type edited on the canvas, layer styles, and the healing brush. A PSD we write should open in Photoshop 7 and in current Photoshop. Smart objects wait until a normal layer already works.

## Milestones

1. **Composite.** Done. A headless Normal blend of layers and masks, written to a PNG.
2. **Folder document.** Done. `stack.txt` plus one PNG per layer and mask. Loading the folder matches the proof.
3. **Window.** Done. The window shows the composite. Drag the picture to move the top layer.
4. **Brush.** Paint on a layer once the picture on screen matches the PNG.
5. **Type and layer styles.** Type edited on the canvas, and layer styles.
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

That opens the same picture. Drag it to move the green layer. The position is written back into `out/document/stack.txt`.

```
python3 -m unittest discover -s tests
```
