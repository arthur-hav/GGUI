import pygame
from OpenGL.GL import *
from PIL import Image
from pubsub import pub
import uuid

from .style import Style


class Event:
    def __init__(self, value_dict):
        for k, v in value_dict.items():
            setattr(self, k, v)


class Widget:
    DEFAULT_STYLE = Style(color=(1, 1, 1, 1))

    def __init__(self, x=0, y=0, w=0, h=0, style=None, *args, **kwargs):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.z = 0
        self.hovered = False
        self.parent = None
        self.elements = []
        if not style:
            style = self.DEFAULT_STYLE
        self.style = style
        self.clicked = None
        self.fade_timer = 0
        self.animation_ratio = 0
        self._color_start = self.style.default_color
        self._color_end = self.style.default_color
        self.texture = 0
        self.direct_rendering = True
        self.dirty = 1
        self.uid = str(uuid.uuid4())
        self.disabled = False

    def disable(self):
        prev_disabled = self.disabled
        self.disabled = True
        if not prev_disabled:
            self.clear()
            self.set_redraw()

    def enable(self):
        prev_disabled = self.disabled
        self.disabled = False
        if prev_disabled:
            self.clear()
            self.set_redraw()

    def find_element(self, uid):
        if self.uid == uid:
            return self
        for element in self.elements:
            searched = element.find_element(uid)
            if searched:
                return searched
        return None

    def overlaps(self, x, y, w, h):
        s_fbo, fbo_w, fbo_h, s_x, s_y = self.get_draw_parent_fbo()
        rect_1 = pygame.rect.Rect(s_x, s_y, self.w, self.h)
        rect_2 = pygame.rect.Rect(x, y, w, h)
        return rect_1.colliderect(rect_2)

    def clear(self):
        pass

    def set_redraw(self, overlap_elem=None):
        if not overlap_elem:
            overlap_elem = self
        stk = self.elements[:]
        while stk:
            element = stk.pop(0)
            for son in element.elements:
                stk.append(son)
            e_fbo, fbo_w, fbo_h, e_x, e_y = element.get_draw_parent_fbo()

            if element.draw_parent == self.draw_parent:
                if overlap_elem.overlaps(e_x, e_y, element.w, element.h):
                    element.dirty = max(element.dirty, 1)
            if element.draw_parent == self:
                element.dirty = max(element.dirty, 1)
        self.dirty = max(self.dirty, 1)
        if self.draw_parent and self.style.transparent:
            self.draw_parent.clear()
            self.draw_parent.set_redraw()
        elif self.draw_parent:
            self.draw_parent.dirty = 1

    @property
    def draw_parent(self):
        if self.parent and self.parent.direct_rendering:
            return self.parent.draw_parent
        return self.parent

    def __repr__(self):
        pres = f"""{self.__class__.__name__}{(self.x, self.y)}"""
        parent = self.parent
        while parent:
            pres = '\t' + pres
            parent = parent.parent
        return pres

    def get_draw_parent_fbo(self):
        if self.parent and self.parent.direct_rendering:
            fbo, w, h, x_parent, y_parent = self.parent.get_draw_parent_fbo()
            return fbo, w, h, x_parent + self.x, y_parent + self.y
        if self.parent:
            return self.parent.fbo, self.parent.total_w, self.parent.total_h, self.x, self.y
        return 0, self.w, self.h, self.x, self.y

    def update(self, frame_time):
        if self.animation_ratio:
            self.animation_ratio = max(0, self.animation_ratio - frame_time / (1000 * self.fade_timer))
            self.clear()
            self.set_redraw()
        for element in self.elements:
            element.update(frame_time)
        if self.dirty and self.draw_parent:
            if self.style.transparent or self.draw_parent.style.transparent:
                self.draw_parent.clear()
                self.draw_parent.set_redraw()
            else:
                self.draw_parent.dirty = self.dirty

    def get_color(self):
        if self.animation_ratio:
            return tuple(self._color_start[i] * self.animation_ratio + \
                         self._color_end[i] * (1 - self.animation_ratio) for i in range(4))
        if self.disabled and self.style.disabled_color:
            return self.style.disabled_color
        if self.clicked and self.style.click_color:
            return self.style.click_color
        if self.hovered and self.style.hover_color:
            return self.style.hover_color
        return self.style.default_color

    def to_element_x(self, x):
        return x - self.x

    def to_element_y(self, y):
        return y - self.y

    def hover_pred(self, x, y):
        return self.x < x < self.x + self.w and self.y < y < self.y + self.h

    def check_mouse(self, x, y):
        if self.disabled:
            return
        for element in self.elements:
            element_x, element_y = self.to_element_x(x), self.to_element_y(y)
            element.check_mouse(element_x, element_y)
        if self.hover_pred(x, y):
            if not self.hovered:
                self.mouse_enter()
        elif self.hovered:
            self.mouse_leave()

    def bind(self, parent):
        self.parent = parent
        if not self.parent.parent:
            self.dirty = 2

    def unbind(self):
        self.parent = None

    def mouse_enter(self):
        redraw = not self.hovered and not self.clicked and self.style.hover_color
        color_start = self.get_color()
        self.hovered = True
        if redraw:
            self._color_start = color_start
            self.fade_timer = self.style.fade_in_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self._color_end = self.style.hover_color
            self.dirty = 1
            self.clear()
            self.set_redraw()

    def mouse_leave(self):
        redraw = not self.clicked and self.style.hover_color
        color_start = self.get_color()
        self.hovered = False
        if redraw:
            self._color_start = color_start
            self.fade_timer = self.style.fade_out_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self._color_end = self.style.default_color
            self.dirty = 1
            self.clear()
            self.set_redraw()

    def mouse_wheel(self, relative_y):
        pass

    def mouse_down(self, x, y, button):
        if self.disabled:
            return
        if not self.hovered:
            return
        if button != 1:
            return
        if not self.clicked:
            event = Event({'x': x, 'y': y, 'button': button})
            pub.sendMessage(f'{self.uid}.click', event=event)
        for element in self.elements:
            element.mouse_down(self.to_element_x(x), self.to_element_y(y), button)
        redraw = not self.clicked and self.style.click_color
        color_start = self.get_color()
        self.clicked = button
        if redraw:
            self._color_start = color_start
            self.fade_timer = self.style.fade_in_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self._color_end = self.style.click_color
            self.dirty = 1
            self.clear()
            self.set_redraw()

    def mouse_up(self, x, y):
        if self.disabled:
            return
        for element in self.elements:
            element.mouse_up(self.to_element_x(x), self.to_element_y(y))
        redraw = self.clicked and self.style.click_color
        color_start = self.get_color()
        if self.clicked and self.hovered:
            event = Event({'x': x, 'y': y, 'button': self.clicked})
            pub.sendMessage(f'{self.uid}.confirm-click', event=event)
        self.clicked = None
        if redraw:
            self._color_start = color_start
            self._color_end = self.style.hover_color if self.hovered else self.style.default_color
            self.fade_timer = self.style.fade_out_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self.dirty = 1
            self.clear()
            self.set_redraw()

    def key_down(self, keycode, key_char):
        for element in self.elements:
            element.key_down(keycode, key_char)

    def draw(self, force=False):
        if self.direct_rendering and (self.dirty or force):
            self.parent_draw()
        for element in sorted(self.elements, key=lambda w: w.z):
            element.draw()
        if not self.direct_rendering and (self.dirty or force):
            self.parent_draw()
        self.dirty = max(self.dirty - 1, 0)

    def parent_draw(self):
        fbo, w_parent, h_parent, x, y = self.get_draw_parent_fbo()
        if self.texture:
            self.gl_draw_rectangle(self.get_color(), self.texture, fbo, w_parent, h_parent,
                                   off_x=x-self.x, off_y=y-self.y)
        else:
            self.draw_background(fbo, w_parent, h_parent, x, y)

    def draw_background(self, fbo, w_disp, h_disp, x_disp, y_disp):
        if self.style.border_color and self.style.border_line_w:
            self.gl_draw_border(self.style.border_color, 0, fbo, w_disp, h_disp, self.style.border_line_w)
        border_w = self.style.border_line_w
        self.gl_draw_rectangle(self.get_color(), 0, fbo,
                               w_disp, h_disp, border_w+x_disp-self.x,
                               border_w+y_disp-self.y, -2*border_w, -2*border_w)

    def gl_draw_border(self, color, texture, fbo, viewport_w, viewport_h, line_width):
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, viewport_w, viewport_h)
        glLineWidth(line_width)
        x, y, w, h = self.x / viewport_w, 1 - (self.y + self.h) / viewport_h, \
                     self.w / viewport_w, self.h / viewport_h

        vert_x1, vert_x2, = x + line_width / viewport_w / 2, x + w - line_width / viewport_w / 2
        v_x1, v_y1, v_x2, v_y2 = -1 + 2 * vert_x1, -1 + 2 * y, -1 + 2 * vert_x2, -1 + (2 * y + 2 * h)
        hori_x, hori_w, = x + line_width / viewport_w, w - line_width / viewport_w * 2
        hori_y1, hori_y2 = y + line_width / viewport_h / 2, y + h - line_width / viewport_h / 2
        h_x1, h_y1, h_x2, h_y2 = -1 + 2 * hori_x, -1 + 2 * hori_y1, -1 + 2 * (hori_x + hori_w), -1 + 2 * hori_y2
        glColor4f(*color)
        glBegin(GL_LINES)
        glVertex2f(v_x1, v_y2)
        glVertex2f(v_x1, v_y1)
        glVertex2f(v_x2, v_y2)
        glVertex2f(v_x2, v_y1)

        glVertex2f(h_x1, h_y1)
        glVertex2f(h_x2, h_y1)
        glVertex2f(h_x1, h_y2)
        glVertex2f(h_x2, h_y2)
        glEnd()

    def gl_draw_rectangle(self, color, texture, fbo, viewport_w, viewport_h, off_x=0, off_y=0, off_w=0, off_h=0,
                          tex_x=0, tex_y=0, tex_w=None, tex_h=None):
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, viewport_w, viewport_h)
        x, y, w, h = (self.x + off_x) / viewport_w, 1 - (self.y + self.h + off_y + off_h) / viewport_h, \
                     (self.w + off_w) / viewport_w, (self.h + off_h) / viewport_h
        x1, y1, x2, y2 = -1 + 2 * x, -1 + 2 * y, -1 + 2 * x + 2 * w, -1 + (2 * y + 2 * h)
        tex_x0 = tex_x / (tex_w or self.w)
        tex_y0 = tex_y / (tex_h or self.h)
        tex_x1 = (tex_x + self.w) / (tex_w or self.w)
        tex_y1 = (tex_y + self.h) / (tex_h or self.h)
        glColor4f(*color)
        glBegin(GL_TRIANGLES)
        glTexCoord2f(tex_x0, tex_y0)
        glVertex2f(x1, y1)
        glTexCoord2f(tex_x1, tex_y1)
        glVertex2f(x2, y2)
        glTexCoord2f(tex_x0, tex_y1)

        glVertex2f(x1, y2)
        glTexCoord2f(tex_x0, tex_y0)
        glVertex2f(x1, y1)
        glTexCoord2f(tex_x1, tex_y0)
        glVertex2f(x2, y1)
        glTexCoord2f(tex_x1, tex_y1)
        glVertex2f(x2, y2)
        glEnd()

    def add_element(self, element):
        self.elements.append(element)
        if element.style.transparent:
            self.direct_rendering = False
        element.bind(self)

    def reset(self):
        self.hovered = False
        self.clicked = None
        self.animation_ratio = 0
        self.clear()
        self.set_redraw()

    def load_image(self, image_path, resize=True):
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        im = Image.open(image_path)
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, im.width, im.height,
                     0, GL_RGBA if im.mode == 'RGBA' else GL_RGB, GL_UNSIGNED_BYTE, im.tobytes())
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        if resize:
            self.w = im.width
            self.h = im.height

