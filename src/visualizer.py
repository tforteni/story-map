import matplotlib.pyplot as plt

def plot_map(coords, distances, conflicts, with_routes):
    plt.figure(figsize=(8, 6))

    # draw points
    for name, (x, y) in coords.items():
        plt.scatter(x, y, s=100, marker="o")
        plt.text(x+0.2, y+0.2, name, fontsize=10)

    # draw edges
    if with_routes:
        for (a, b), d in distances.items():
            xa, ya = coords[a]
            xb, yb = coords[b]
            plt.plot([xa, xb], [ya, yb], "k--", alpha=0.6)  # dashed line
            midx, midy = (xa+xb)/2, (ya+yb)/2
            plt.text(midx, midy, f"{d:.1f}", fontsize=8, color="gray")

            key = tuple(sorted((a, b)))
            if key in conflicts:
                plt.text(xa+0.6, ya+16, "⚠️", fontsize=16, color="red")

    plt.title("Fantasy Map with Travel Routes")
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")
    plt.axis("equal")
    plt.show()