
class Style:
    def __init__(self, color=(0, 0, 0, 0),
                 hover_color=None,
                 click_color=None,
                 border_color=None,
                 border_line_w=0,
                 fade_in_time=0.0,
                 fade_out_time=0.0,
                 transparent=None):
        self.default_color = self.premultiply(color)
        self.hover_color = self.premultiply(hover_color)
        self.click_color = self.premultiply(click_color)
        self.transparent = transparent if transparent is not None else self.default_color[3] < 1.0
        self.fade_in_time = fade_in_time
        self.fade_out_time = fade_out_time
        self.border_color = border_color
        self.border_line_w = border_line_w

    @property
    def background(self):
        return self.hover_color or self.border_color

    def premultiply(self, color):
        if not color:
            return color
        return color[0] * color[3], color[1] * color[3], color[2] * color[3], color[3]

    def __str__(self):
        return f'#{int(255 * self.default_color[0]):02X}{int(255 * self.default_color[1]):02X}' \
               f'{int(255 * self.default_color[2]):02X}{int(255 * self.default_color[3]):02X}'
