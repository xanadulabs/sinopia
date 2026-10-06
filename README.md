# Sinopia

A lightweight, minimalist compositor. The aim is an early Photoshop: layers, masks, and a few tools, without Camera Raw, a photo importer, or the rest of the modern suite.

The picture you keep is a folder of PNGs plus `stack.txt`. PSD, PNG, and JPEG are exports. If the program stops, the pictures are still files you can open.

Sinopia is by Will Hinds. Published 2026. The mark is a plaster fragment with a mother and child drawn in sinopia. That picture is the window icon, and `sinopia.png` is the same file for a desktop shortcut.

What it does now: layers and groups, masks, a drop shadow, brush, type, transform, marquee, zoom, undo, canvas size, and PNG or JPEG open and save. The window shows the same pixels the compositor writes. Still ahead: the healing brush, PSD export, and smart objects.

## Milestones

1. **Composite.** Done. A headless Normal blend of layers and masks, written to a PNG.
2. **Folder document.** Done. `stack.txt` plus one PNG per layer and mask. Loading the folder matches the proof.
3. **Window.** Done. The window shows the composite. Drag the picture to move the top layer.
4. **Brush.** Done. Press `b` and drag to paint the top layer. Press `v` to drag that layer again. The mask is not painted.
5. **Type and layer styles.** Type is on the canvas: press `t`, click, type, and press Enter to keep the letters. The top bar sets the font, the size in px or pt, bold, italic, strike, underline, kerning, and stroke. The built-in face is Sinopia. Other names are fontconfig families drawn by Pango; Enter bakes the pixels into the layer PNG, which stays the file you keep. The first layer style is a drop shadow, stored on the layer as `shadow dx dy`.
6. **Healing brush.**
7. **PSD, PNG, and JPEG export.** PNG and JPEG open and save from the File menu. The folder stays the file we keep. PSD is still ahead.
8. **Smart objects.** A nested folder plus a transform.

## How to use it

```
python3 -m sinopia
```

That writes `out/proof.png`, a red field with a soft green circle over it, and `out/document/`.

```
python3 -m sinopia.window
```

That opens the same picture. The workspace stays one size. A smaller picture sits in the gray middle. A larger one scrolls. The picture opens at actual pixels, and the zoom stays there until you change it.

```
python3 -m unittest discover -s tests
```

### File

File → New asks for a width and height. If the clipboard holds a picture, including one from Print Screen, those dimensions are filled in. Leaving that size puts the picture on the layer. A size you type is a white picture. A rectangle copied with the marquee is offered the same way.

File → Open lists the pictures in a folder and shows a small preview of the one you select, with its real pixel size, before it opens. PNG and JPEG both open.

Save writes the folder of PNGs plus `stack.txt`. That folder is the file you keep. Save As writes a PNG or JPEG copy of the picture you see. Letting go of a drag or a stroke saves the folder too. Exit closes the window.

### Edit

Copy keeps the pixels inside the marquee, from the picture you see, and puts them on the clipboard. Select All selects the whole picture. Deselect clears the marquee. Free Transform selects the transform tool.

Canvas Size adds pixels. Pick the square where the picture stays, then type how many pixels to add. The new area is empty and shows white. Photoshop 7 has no shortcut for this, so it stays on the menu.

### View

Zoom In and Zoom Out change the view. Fit on Screen picks the largest whole-pixel zoom that fits in the workspace, and it does not zoom out past actual pixels. A picture larger than the window stays at 1× and scrolls. Actual Pixels is 1×. The magnifying glass does the same: click zooms in, Alt-click zooms out. `+` and `−` zoom too.

### Tools

The tools sit in a column on the left. Each button keeps its shortcut letter in the corner, and the pointer on the picture matches the tool.

| Key | Tool | What you do |
| --- | --- | --- |
| `m` | Marquee | Drag a rectangle. Shift keeps it square. |
| `v` | Move | Drag the selected layer. |
| `z` | Zoom | Click to zoom in. Alt-click to zoom out. |
| `b` | Brush | Drag to paint the selected layer. The mask is left alone. `[` and `]` change the size. |
| `t` | Type | Click, type, Enter keeps the letters, Escape drops them. |
| `f` | Transform | Drag a corner, an edge, or the inside of the box. |

Click the picture and the top layer that covers that spot becomes the selection, even when a higher layer is transparent there. That row stays highlighted.

With the brush selected, the top bar sets the size, from 0 to 64. With type selected, it sets the font, the size in px or pt, bold, italic, strike, underline, kerning, and stroke. The built-in face is Sinopia. Other names are fontconfig families drawn by Pango. Enter bakes the letters into the layer PNG, so the picture does not need that font later.

Transform draws a box around the layer. Drag a corner and the opposite corner stays put. Drag an edge to scale one side. Drag inside the box to move the layer. Shift on a corner keeps the proportions.

### Layers

Layers are listed on the right, top of the picture first. Drag a name to restack it. A group's name moves the whole group. Drop a row on the upper half of a layer to put it above that layer, or the lower half to put it under. Drop it on a group's name to put it inside that group. Click a selected name to rename it. Spaces become hyphens, because the name is the PNG file.

New, Group, and Delete sit under the list. New adds a layer. Group wraps the selected layer. Delete removes the selected layer or group, and the last layer stays.

A layer in the folder can carry a mask PNG. The brush does not paint that mask. A drop shadow is stored on the layer as `shadow dx dy`.

### History

The list under the layers is the history, forty steps at most. A step is named New, Open, Move, Brush, Type, Transform, Canvas Size, Layer, Group, Delete Layer, Delete Group, Restack, or Rename. Click a row to jump there. Ctrl+Z steps backward through that list. Alt+Ctrl+Z does the same step. Ctrl+Shift+Z steps forward, and so does Ctrl+Y.

### About

About Sinopia shows the mark on the left, about half the box, and the description on the right, with the name and the year. The same mark sits in the title bar.

### Shortcuts

These match Photoshop 7 where the feature exists here.

| Action | Shortcut |
| --- | --- |
| New | Ctrl+N |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Exit | Ctrl+Q |
| Undo, step backward | Ctrl+Z, and Alt+Ctrl+Z |
| Step forward | Ctrl+Shift+Z, and Ctrl+Y |
| Copy | Ctrl+C, and Ctrl+Shift+C |
| Select All | Ctrl+A |
| Deselect | Ctrl+D |
| Free Transform | Ctrl+T, and `f` |
| New Layer | Ctrl+Shift+N |
| Group | Ctrl+G |
| Zoom In | Ctrl++ , and `+` |
| Zoom Out | Ctrl+− , and `−` |
| Fit on Screen | Ctrl+0 |
| Actual Pixels | Ctrl+Alt+0 |
| Brush smaller, larger | `[` `]` |
