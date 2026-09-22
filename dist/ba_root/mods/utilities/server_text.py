import bascenev1 as bs

GRADIENT_STOPS = [
    (1.0, 0.2, 0.6),  # Pink
    (0.6, 0.1, 0.9),  # Purple
    (0.0, 0.8, 1.0),  # Cyan
    (0.1, 0.3, 1.0),  # Blue
]


def get_gradient_color(progress: float) -> tuple[float, float, float]:
    """returns an RGB color along a 4-stop gradient."""
    scaled = progress * (len(GRADIENT_STOPS) - 1)
    idx = min(int(scaled), len(GRADIENT_STOPS) - 2)
    factor = scaled - idx

    c1, c2 = GRADIENT_STOPS[idx], GRADIENT_STOPS[idx + 1]
    return tuple(a + (b - a) * factor for a, b in zip(c1, c2))


def make_server_text() -> None:
    """makes the server text."""
    bs.newnode(
        "text",
        attrs={
            "text": "C",
            "big": True,
            "h_align": "center",
            "position": (-68.0, 196.0),
            "scale": 0.4,
            "color": get_gradient_color(0.0),
        },
    )

    items = ["TROPHY", "R", "D", "I", "N", "A", "L", "S"]
    x_positions = [-35.0, -18.0, 2.0, 20.0, 38.0, 58.0, 76.0, 94.0]
    total_elements = len(items) + 1

    for i, (item, x_pos) in enumerate(zip(items, x_positions), start=1):
        color = get_gradient_color(i / (total_elements - 1))

        if item == "TROPHY":
            bs.newnode(
                "image",
                attrs={
                    "texture": bs.gettexture("trophy"),
                    "position": (x_pos, 323.5),
                    "scale": (31.0, 41.0),
                    "color": color,
                },
            )
        else:
            bs.newnode(
                "text",
                attrs={
                    "text": item,
                    "big": True,
                    "h_align": "center",
                    "position": (x_pos, 200.0),
                    "scale": 0.3,
                    "color": color,
                },
            )
