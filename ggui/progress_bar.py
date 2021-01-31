from .container import GuiContainer
from .widget import Widget
from .style import Style


class ProgressBar(GuiContainer):
    DEFAULT_FILL_STYLE = Style(color=(0, 0.4, 0.1, 1))

    def __init__(self, x, y, w, h, fill_style=None, **kwargs):
        super().__init__(x, y, w, h, **kwargs)
        self._ratio = 0.0
        self.fill_style = fill_style or self.DEFAULT_FILL_STYLE
        self.inner_rect = None

    def set_progress(self, ratio):
        ratio = min(max(ratio, 0), 1.0)
        border_w = self.style.border_line_w
        new_w = round((self.w - 2 * border_w) * ratio)
        if new_w <= 0:
            if self.inner_rect in self.elements:
                self.elements.remove(self.inner_rect)
            return
        if not self.inner_rect and new_w:
            self.inner_rect = Widget(border_w, border_w, self.w - 2 * border_w, self.h - 2 * border_w,
                                     style=self.fill_style)
        if new_w and self.inner_rect not in self.elements:
            self.add_element(self.inner_rect)
        self._ratio = ratio
        old_w = self.inner_rect.w
        self.inner_rect.w = new_w
        if self.inner_rect.w != old_w:
            self.inner_rect.clear()
            self.inner_rect.set_redraw()

