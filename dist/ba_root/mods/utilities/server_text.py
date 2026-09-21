import bascenev1 as bs

def make_server_text() -> None:
    """makes the server text."""
    bs.newnode(
        "text",
        attrs={
            "text": "C",
            "big": True,
            'h_align': 'center',
            'position': (-48, 198),
            'scale': 0.24,
            'color': (1.0, 0.86, 0.27)
        }
    )

    bs.newnode(
        "text",
        attrs={
            "text": "RDINALS",
            "big": True,
            'h_align': 'center',
            'position': (10, 200),
            'scale': 0.2,
            'color': (1.0, 0.86, 0.27)
        }
    )
    bs.newnode(
        'image',
        attrs={
            'texture': bs.gettexture("trophy"),
            "position": (-25, 317.5),
            'scale': (20.0, 30.0),
            'color': (1.0, 0.86, 0.27)
        }
    )
