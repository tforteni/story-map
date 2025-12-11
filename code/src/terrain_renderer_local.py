import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import os
from noise import pnoise2
from matplotlib.colors import LinearSegmentedColormap

colors = [
    (0.0, "#001d4a"),  # deep ocean blue
    (0.3, "#004f8c"),  # lighter ocean
    (0.4, "#5fa777"),  # gentle coastal green
    (0.6, "#a18d61"),  # tan hills
    (0.8, "#d8cab8"),  # highlands
    (1.0, "#ffffff"),  # snowy peaks
]
world_cmap = LinearSegmentedColormap.from_list("world_cmap", colors)


def normalized(coords, width, height, pad=40):
    xs = np.array([p[0] for p in coords.values()])
    ys = np.array([p[1] for p in coords.values()])
    span_x = max(xs.max() - xs.min(), 1.0)
    span_y = max(ys.max() - ys.min(), 1.0)
    scale = 0.7 * min((width - 2*pad)/span_x, (height - 2*pad)/span_y)
    return {
        name: ((x - xs.min()) * scale + pad,
                (y - ys.min()) * scale + pad)
        for name, (x, y) in coords.items()
    }

def draw_terrain(coords, distances, conflicts, direction_conflicts, with_routes):
    if not coords:
        return
    w, h = 800, 600
    norm_coords = normalized(coords, w, h)
    terrain = np.zeros((h, w), dtype=float)
    
    rr, cc = np.ogrid[:h, :w]
    for (x, y) in norm_coords.values():
        dist = np.sqrt((rr - y)**2 + (cc - x)**2)
        terrain += np.exp(-(dist**2) / (2 * 350**2))
    terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())
    terrain = terrain ** 2.0 

    # add noise everywhere:
    for y in range(h):
        for x in range(w):
            terrain[y, x] += 0.2 * pnoise2(x * 0.02, y * 0.02)
    terrain = np.clip(terrain, 0, 1)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(terrain, cmap=world_cmap, origin="lower")
    for name, (x, y) in norm_coords.items():
        ax.text(x, y, name, ha="center", va="center", color="black")

    for (a, b), d in distances.items():
        d = d[0]
        xa, ya = norm_coords[a]
        xb, yb = norm_coords[b]
        if with_routes:
            plt.plot([xa, xb], [ya, yb], "k--", alpha=0.6)
            midx, midy = (xa+xb)/2, (ya+yb)/2
            plt.text(midx, midy, f"{d:.1f}", fontsize=8, color="gray")

        s_key = tuple(sorted((a, b)))
        if s_key in conflicts or s_key in direction_conflicts:
            plt.text(xa+0.6, ya+8, "⚠️", fontsize=16, color="red")
                         
    ax.axis("off")

    plt.savefig("map.png", dpi=300, bbox_inches="tight")  # best for submissions or reports
    return