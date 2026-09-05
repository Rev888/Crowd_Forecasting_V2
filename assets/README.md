# Artwork

Drop the pixel-art deity image here as **`deity.png`**.

`lib/pixel_art.py` picks up the first match of `deity.png`, `deity.webp`,
`deity.jpg`, `deity.jpeg` or `deity.gif`, inlines it as a base64 data URI, and
scales it with `image-rendering: pixelated` so the pixel grid stays crisp.

If no file is present the dashboard falls back to a hand-drawn SVG silhouette,
so the layout still renders — but the real artwork is preferred.

A transparent background (PNG) sits best on the dashboard's near-black ground.
