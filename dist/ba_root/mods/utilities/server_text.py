import bascenev1 as bs


def make_server_text(map_node: bs.Node) -> None:
    """makes the server text."""
    bs.newnode(
        "text",
        owner=map_node,
        attrs={
            "text": "C",
            "big": True,
            'h_align': 'center',
            'position': (440, -460),
            'scale': 0.5,
            'color': (1.0, 0.86, 0.27)
        }
    )

    bs.newnode(
        "text",
        owner=map_node,
        attrs={
            "text": "RDINALS",
            "big": True,
            'h_align': 'center',
            'position': (560, -460),
            'scale': 0.4,
            'color': (1.0, 0.86, 0.27)
        }
    )
    bs.newnode(
        'image',
        owner=map_node,
        attrs={
            'texture': bs.gettexture("trophy"),
            "position": (480, -690),
            "attach": "bottomRight",
            'scale': (45.0, 55.0),
            'color': (1.0, 0.86, 0.27)
        }
    )