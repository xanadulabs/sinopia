"""Write the proof picture and the folder it came from."""

from pathlib import Path

from sinopia.document import flatten, save
from sinopia.png import write_png
from sinopia.proof import SIZE, proof_document


def main() -> None:
    document = proof_document()
    image = flatten(document)
    # Corner of the mask is 0, so the red layer shows through unchanged.
    if image.get(0, 0) != (180, 24, 24, 255):
        raise SystemExit(f"corner pixel was {image.get(0, 0)}")
    # Center of the mask is 255, so the green layer replaces the red.
    mid = SIZE // 2
    if image.get(mid, mid) != (32, 140, 64, 255):
        raise SystemExit(f"center pixel was {image.get(mid, mid)}")

    out = Path("out")
    out.mkdir(exist_ok=True)
    picture = out / "proof.png"
    folder = out / "document"
    write_png(picture, image)
    save(document, folder)
    print(picture)
    print(folder / "stack.txt")


if __name__ == "__main__":
    main()
