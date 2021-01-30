import pygame
from OpenGL.GL import *

from .widget import Widget
from .style import Style


class OverflowWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overflow_w = kwargs.get('overflow_w', 0)
        self.overflow_h = kwargs.get('overflow_h', 0)
        self.offset_x = 0
        self.offset_y = kwargs.get('overflow_h', 0)
        if self.overflow_h or self.overflow_w and not self.parent:
            self._scrollbar = ScrollBar(window=self)
            self.add_element(self._scrollbar)
        self.direct_rendering = self.direct_rendering and not self.overflow_h and not self.overflow_w

    @property
    def total_w(self):
        return self.w + self.overflow_w

    @property
    def total_h(self):
        return self.h + self.overflow_h

    def mouse_wheel(self, relative_y):
        if self.hovered:
            for element in self.elements:
                element.mouse_wheel(relative_y)
            if self.overflow_h:
                self._scrollbar.y -= 30 * relative_y
                self._scrollbar.scroll()

    def to_element_x(self, x):
        return x - self.x - self.offset_x

    def to_element_y(self, y):
        return y - self.offset_y + self.overflow_h - self.y

    def update(self, frame_time):
        super().update(frame_time)
        if self.dirty and (self.overflow_h or self.overflow_w):
            self._scrollbar.dirty = 1
            self.clear()
            self.set_redraw()

    def reset(self):
        super().reset()
        self.offset_x = 0
        self.offset_y = self.overflow_h
        if self.overflow_h or self.overflow_w:
            self._scrollbar.y = 0


class GuiContainer(OverflowWidget):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 1))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fbo, self.texture = self.create_fbo(self.total_w, self.total_h)
        self.clear()
        self.set_redraw()

    def create_fbo(self, w, h):
        texID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texID)
        glTexImage2D(GL_TEXTURE_2D, 0, self.get_mode(), w, h, 0, self.get_mode(), GL_UNSIGNED_BYTE, b'\x22' * 4 * w * h)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        fb_id = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fb_id)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, texID, 0)
        glDrawBuffers(1, GL_COLOR_ATTACHMENT0)
        return fb_id, texID

    def get_mode(self):
        return GL_RGBA

    def clear(self, cascade=True):
        if self.cleared:
            return
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glClearColor(*self.get_color())
        glClear(GL_COLOR_BUFFER_BIT)
        if self.style.background:
            x, y, w, h = self.x, self.y, self.w, self.h
            self.x, self.y, self.w, self.h = 0, self.overflow_h, self.total_w, self.total_h
            self.draw_background(self.fbo, self.total_w, self.total_h, 0, 0)
            self.x, self.y, self.w, self.h = x, y, w, h
        super().clear()

    def parent_draw(self):
        fbo, w_disp, h_disp, x_disp, y_disp = self.get_draw_parent_fbo()
        self.gl_draw_rectangle((1, 1, 1, 1), self.texture, fbo, w_disp, h_disp,
                               off_x=x_disp-self.x, off_y=y_disp-self.y,
                               tex_w=self.total_w, tex_h=self.total_h,
                               tex_x=self.offset_x, tex_y=self.offset_y)


class MainWindow(GuiContainer):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 1))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        self.direct_rendering = False

    def process_events(self):

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                self.key_down(event.key, event.unicode)
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down(*pygame.mouse.get_pos(), event.button)
            if event.type == pygame.MOUSEWHEEL:
                self.mouse_wheel(event.y)
            if event.type == pygame.MOUSEBUTTONUP:
                self.mouse_up(*pygame.mouse.get_pos())
            if event.type == pygame.MOUSEMOTION:
                self.check_mouse(*pygame.mouse.get_pos())


class ScrollBar(Widget):
    DEFAULT_STYLE = Style(color=(1, 1, 1, 0.1), hover_color=(1, 1, 1, 0.2), click_color=(1, 1, 1, 1))

    def __init__(self, window):
        super().__init__(window.w - 8, 0, 8, window.h ** 2 // window.total_h)
        self.drag_start = False
        self.window = window
        self.z = 1
        self.hovered = False

    def hover_pred(self, x, y):
        return self.x < x < self.x + self.w and self.window.overflow_h - self.window.offset_y < y < self.y + self.window.h

    def check_mouse(self, x, y):
        super().check_mouse(x, y)
        if self.clicked:
            self.y += (y - self.y - self.h // 2) * self.window.total_h / (self.window.h - self.h)
            self.scroll()

    def scroll(self):
        self.y = min(max(self.y, 0), self.window.total_h - self.h)
        self.window.offset_y = self.window.overflow_h - self.y * (self.window.overflow_h / (self.window.total_h - self.h))
        self.draw_parent.clear()
        self.draw_parent.set_redraw()

    def mouse_down(self, x, y, button):
        super().mouse_down(x, y, button)
        if button != 1:
            return
        if self.hovered:
            if not self.y < y < self.y + self.h:  # Jump click
                self.y += (y - self.y - self.h//2) * self.window.total_h / (self.window.h - self.h)
                self.scroll()

    def mouse_up(self, x, y):
        super().mouse_up(x, y)
        if not self.hovered:
            self.mouse_leave()