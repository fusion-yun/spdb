

from .surface import Surface


@Surface.register("bspline_surface")
class BSplineSurface(Surface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        raise NotImplementedError()
