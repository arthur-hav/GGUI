from pubsub import pub

from .widget import Event
from .container import GuiContainer
from .style import Style
from .text import TextOverlay


class Button(GuiContainer):
    def __init__(self, x, y, w, h, text, font, outline_font=None, padding_x=16, padding_y=8, text_style=None, **kwargs):
        self.caption = TextOverlay(padding_x, padding_y, text, font, outline_font=outline_font, text_style=text_style)
        super().__init__(x, y, w or self.caption.w + 2 * padding_x, h or self.caption.h + 2 * padding_y, **kwargs)
        self.add_element(self.caption)


class DropDown(GuiContainer):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 0))

    def __init__(self, x, y, w, h, top_text, option_list, font, **kwargs):
        if 'style' not in kwargs:
            kwargs['style'] = self.DEFAULT_STYLE
        self.button = Button(0, 0, w, h, top_text, font, style=kwargs['style'])
        options_h = 0
        self.options = []
        for i, text in enumerate(option_list):
            queue_args = {}
            option = Button(0, 0, w, h, text, font, style=kwargs['style'], **queue_args)
            option.y = options_h
            options_h += option.h
            self.options.append(option)
        total_h = options_h + self.button.h
        max_h = kwargs.get('max_h', total_h)
        overflow_h = total_h - max_h
        self.drop_down = GuiContainer(0, self.button.h, w, max_h - self.button.h,
                                      style=Style(color=(1, 1, 1, 0)), overflow_h=overflow_h)
        for option in self.options:
            self.drop_down.add_element(option)
        super().__init__(x, y, w, max_h, style=Style(color=(1, 1, 1, 0)))
        self.add_element(self.button)
        self.focus = False

    def mouse_down(self, x, y, button):
        super(DropDown, self).mouse_down(x, y, button)
        if button != 1 or self.drop_down.overflow_h and self.drop_down._scrollbar.clicked:
            return
        if self.hovered and not self.focus:
            pub.sendMessage(f'{self.uid}.focus', event=Event({}))
            self.focus = True
            self.add_element(self.drop_down)
            self.clear()
            self.set_redraw()
        elif self.focus:
            for i, element in enumerate(self.options):
                if element.clicked:
                    pub.sendMessage(f'{self.uid}.select', event=Event({'index': i}))
            self.elements.remove(self.drop_down)
            pub.sendMessage(f'{self.uid}.unfocus', event=Event({}))
            self.focus = False
            self.clear()
            self.set_redraw()
            for option in self.options:
                option.reset()
            self.drop_down.reset()
            self.drop_down.unbind()

    def hover_pred(self, x, y):
        if not self.focus:
            return self.button.hover_pred(self.to_element_x(x), self.to_element_y(y))
        return super().hover_pred(x, y)
