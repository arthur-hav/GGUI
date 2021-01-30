import pygame
from OpenGL.GL import *
import freetype
import numpy
import time
from PIL import Image
from pubsub import pub

WRAP_CHAR = 'char'
WRAP_WORDS = 'words'
LOREM_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec risus enim, congue nec eleifend vitae, placerat quis sapien. Nunc felis erat, blandit at turpis in, tincidunt varius lacus. Duis elementum molestie erat nec faucibus. Aliquam erat volutpat. Aliquam erat volutpat. Fusce dapibus tortor purus, ut fringilla tortor pharetra nec. Sed efficitur nunc quis mauris pellentesque pellentesque. Fusce laoreet pretium odio eget dictum. Aliquam consectetur ligula eu odio iaculis, nec venenatis sapien iaculis. Suspendisse a mi massa. Maecenas quis finibus nulla. Ut fermentum tortor id venenatis maximus.
Donec ut laoreet quam, in tincidunt ipsum. Sed in faucibus est, eu ultrices velit. Sed egestas elit eget ipsum interdum, non pharetra libero porta. Duis condimentum, elit vitae tempus varius, lacus turpis convallis nunc, ac mollis dui justo eget ipsum. Aliquam nec convallis lorem. Pellentesque mollis semper ante, eget ornare arcu ultricies eget. In vel purus gravida, ultricies mauris vel, pretium urna. Quisque tincidunt rutrum lacinia. Morbi et augue at metus tempus vehicula non non est. Morbi sed sagittis leo. Aliquam non bibendum mi. Duis in ex neque. Donec sit amet ante leo.
Nullam rhoncus massa nec felis luctus hendrerit. Ut rhoncus vehicula diam eu tincidunt. Etiam tempor lobortis sodales. Aliquam volutpat et elit ut rhoncus. Nunc facilisis, sapien ac laoreet auctor, tellus enim ornare risus, at tincidunt ligula neque non lectus. Morbi rhoncus ex malesuada libero dictum auctor. Pellentesque vitae arcu eget felis facilisis tempus eu sit amet diam. Donec sem ipsum, molestie ut tempor a, ultrices pulvinar erat. Mauris lacinia augue quis luctus rutrum. Mauris consequat orci at magna tincidunt, vel lacinia magna molestie. Nam vulputate faucibus urna, vel auctor nibh vulputate vel. Aliquam bibendum nisl in euismod mattis.
Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Vivamus bibendum magna justo, consequat sollicitudin risus tincidunt at. Etiam blandit finibus elit, ut facilisis ipsum vehicula eget. Maecenas ultricies erat sed hendrerit condimentum. Aenean semper bibendum elit. Cras molestie posuere metus a euismod. Nunc nec ligula metus. Nam pellentesque, nulla id faucibus interdum, nunc dui molestie turpis, nec semper nulla tortor at nibh. Quisque tempus fermentum egestas. Donec feugiat turpis et dolor vehicula, sed convallis nunc ultricies. Nulla vestibulum odio et sapien facilisis, eget ultrices elit blandit. Nullam a justo porttitor, luctus ex a, venenatis augue. Ut et leo sit amet felis mattis ultricies. Quisque sollicitudin, lorem vitae sagittis viverra, nunc erat finibus tellus, in pharetra felis diam ut elit.
Cras blandit eget arcu sed maximus. Suspendisse faucibus, quam nec hendrerit placerat, ipsum dolor gravida diam, vitae posuere enim justo nec quam. Fusce arcu neque, lacinia vitae magna nec, finibus maximus urna. Phasellus congue varius nibh. Morbi vestibulum a nisl eget luctus. Quisque condimentum nulla ut turpis rutrum, ut pharetra eros rutrum. Nam vel pulvinar ex. Lorem ipsum dolor sit amet, consectetur adipiscing elit. """
FRAMERATE = 60

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


class Event:
    def __init__(self, value_dict):
        for k, v in value_dict.items():
            setattr(self, k, v)


class KeyboardEvent(Event):
    pass


class MouseEvent(Event):
    pass


class Widget:
    DEFAULT_STYLE = Style(color=(1, 1, 1, 1))

    def __init__(self, x=0, y=0, w=0, h=0, style=None, queue_name=None, *args, **kwargs):
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
        self.cleared = False
        self.direct_rendering = True
        self.dirty = 1
        self.queue_name = queue_name

    def overlaps(self, x, y, w, h):
        s_fbo, fbo_w, fbo_h, s_x, s_y = self.get_draw_parent_fbo()
        rect_1 = pygame.rect.Rect(s_x, s_y, self.w, self.h)
        rect_2 = pygame.rect.Rect(x, y, w, h)
        return rect_1.colliderect(rect_2)

    def clear(self):
        self.cleared = True

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
        if self.style.transparent and self.draw_parent:
            self.draw_parent.clear()
            self.draw_parent.set_redraw()

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
            self.draw_parent.dirty = self.dirty

    def get_color(self):
        if self.animation_ratio:
            return tuple(self._color_start[i] * self.animation_ratio + \
                         self._color_end[i] * (1 - self.animation_ratio) for i in range(4))
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
        if self.hover_pred(x, y):
            if not self.hovered:
                self.mouse_enter()
        elif self.hovered:
            self.mouse_leave()
        for element in self.elements:
            element_x, element_y = self.to_element_x(x), self.to_element_y(y)
            element.check_mouse(element_x, element_y)

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
        if self.hovered:
            if not self.clicked and self.hovered and self.queue_name:
                event = MouseEvent({'type': 'click', 'x': x, 'y': y, 'button': button, 'element': self})
                pub.sendMessage(self.queue_name, event=event)
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
        for element in self.elements:
            element.mouse_up(self.to_element_x(x), self.to_element_y(y))
        redraw = self.clicked and self.style.click_color
        color_start = self.get_color()
        if self.clicked and self.hovered and self.queue_name:
            event = MouseEvent({'type':'confirm-click', 'x': x, 'y': y, 'button': self.clicked, 'element': self})
            pub.sendMessage(self.queue_name, event=event)
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
        self.cleared = False

    def parent_draw(self):
        fbo, w_parent, h_parent, x, y = self.get_draw_parent_fbo()
        if self.texture:
            self.gl_draw_rectangle(self.get_color(), self.texture, fbo, w_parent, h_parent,
                                   off_x=x-self.x, off_y=y-self.y)
        else:
            self.draw_background(fbo, w_parent, h_parent, x, y)

    def draw_background(self, fbo, w_disp, h_disp, x_disp, y_disp):
        if self.style.border_color and self.style.border_line_w:
            self.gl_draw_rectangle(self.style.border_color, 0, fbo, w_disp, h_disp,
                                   off_x=x_disp-self.x, off_y=y_disp-self.y)
            border_w = self.style.border_line_w
            self.gl_draw_rectangle(self.get_color(), 0, fbo,
                                   w_disp, h_disp, border_w+x_disp, border_w+y_disp, -2*border_w, -2*border_w)
        else:
            self.gl_draw_rectangle(self.get_color(), 0, fbo,
                                   w_disp, h_disp, off_x=x_disp-self.x, off_y=y_disp-self.y)

    def gl_draw_rectangle(self, color, texture, fbo, viewort_w, viewport_h, off_x=0, off_y=0, off_w=0, off_h=0,
                          tex_x=0, tex_y=0, tex_w=None, tex_h=None):
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, viewort_w, viewport_h)
        x, y, w, h = (self.x + off_x) / viewort_w, 1 - (self.y + self.h + off_y + off_h) / viewport_h, \
                     (self.w + off_w) / viewort_w, (self.h + off_h) / viewport_h
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


class Options:
    def __init__(self):
        self.resolution = (1920, 1080)


MAGIC_NUMBER = 32


class RenderFont:
    def __init__(self, font_path, font_size):
        self.face = freetype.Face(font_path)
        self.face.set_pixel_sizes(font_size, font_size)
        self.char_to_tex = {}
        self.char_sizes = {}
        self.font_size = font_size
        self.cache_file = font_path[:-4] + f'_{font_size}.raw'
        self.line_height = 0
        self.min_top = None
        self.fill_char_index()
        full_binary = self.get_full_binary()
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.line_height * MAGIC_NUMBER,
                     len(full_binary) // (MAGIC_NUMBER * self.line_height * 4),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, full_binary)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        self.vbo = Vbo()

    def fill_char_index(self):
        for enum, my_char in enumerate(self.face.get_chars()):
            self.face.load_glyph(my_char[1])
            self.char_to_tex[my_char[1]] = enum
            self.char_sizes[my_char[1]] = (
                self.face.glyph.bitmap_left, self.face.glyph.bitmap_top, self.face.glyph.bitmap.width,
                self.face.glyph.bitmap.rows, self.face.glyph.advance.x >> 6)
            self.line_height = max(self.line_height, self.face.glyph.bitmap.rows)
            self.min_top = min(self.face.glyph.bitmap_top, self.min_top or self.face.glyph.bitmap_top)
        self.line_height -= self.min_top
        self.total_glyph = len(self.char_to_tex) + (-len(self.char_to_tex) % MAGIC_NUMBER)

    def get_full_binary(self):
        try:
            with open(self.cache_file, 'rb') as f:
                return f.read()
        except OSError:
            tex_array = []
            for enum, my_char in enumerate(self.face.get_chars()):
                self.face.load_glyph(my_char[1])
                bitmap = self.face.glyph.bitmap
                if enum % MAGIC_NUMBER == 0:
                    for i in range(self.line_height):
                        tex_array.append([])
                        for j in range(self.line_height * MAGIC_NUMBER):
                            tex_array[-1].append(bytes([0, 0, 0, 0]))
                start_i = (enum // MAGIC_NUMBER) * self.line_height
                start_j = (enum % MAGIC_NUMBER) * self.line_height
                for i in range(bitmap.width):
                    for j in range(bitmap.rows):
                        tex_array[start_i + j][start_j + i] = bytes(
                            4 * [bitmap.buffer[j * bitmap.width + i]])
            full_binary = b''.join(i for row in tex_array for i in row)
            with open(self.cache_file, 'wb') as f:
                f.write(full_binary)
            return full_binary


class Vbo:
    def __init__(self):
        self.tex_buffer = []
        self.vtx_buffer = []

    def push(self, tex_array, vtx_array):
        self.tex_buffer.extend(tex_array)
        self.vtx_buffer.extend(vtx_array)

    def flush(self, widget):
        if not self.vtx_buffer:
            return
        fbo, w_parent, h_parent, x_disp, y_disp = widget.get_draw_parent_fbo()

        glBindTexture(GL_TEXTURE_2D, widget.texture)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, w_parent, h_parent)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glColor4f(*widget.get_color())
        glVertexPointer(2, GL_FLOAT, 0, numpy.array(self.vtx_buffer, dtype=numpy.float32).tobytes())
        glTexCoordPointer(2, GL_FLOAT, 0, numpy.array(self.tex_buffer, dtype=numpy.float32).tobytes())
        indices = numpy.array(list(range(len(self.vtx_buffer))), dtype=numpy.uint32)
        glDrawElements(GL_TRIANGLES, len(self.vtx_buffer) // 2, GL_UNSIGNED_INT, indices.tobytes())
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glFlush()
        self.vtx_buffer = []
        self.tex_buffer = []


class RenderString(Widget):
    DEFAULT_STYLE = Style(color=(1, 1, 1, 1), transparent=True)

    def __init__(self, x, y, string, render_font, wrap=WRAP_WORDS, max_w=None, **kwargs):
        super().__init__(x, y, **kwargs)
        self.max_w = max_w
        self.wrap = wrap
        self.render_font = render_font
        self._string = None
        self._render = []
        self.string = string
        self.texture = render_font.texture
        self.direct_rendering = True
        self.dirty = 1

    @property
    def string(self):
        return self._string

    @string.setter
    def string(self, value):
        if value == self._string:
            return
        self._string = value
        max_x = self.x
        max_y = self.y
        for char, cur_x, cur_y, advance in self.iter_chars():
            max_x = max(max_x, cur_x + advance)
            max_y = cur_y
        self.w, self.h = max_x - self.x, max_y - self.y
        self.dirty = 1
        if self.draw_parent:
            self.draw_parent.clear()
            self.draw_parent.set_redraw()

    def iter_chars(self):
        cur_x, cur_y = self.x, self.y
        chunks = list(self._string) if self.wrap == WRAP_CHAR else self._string.split(' ')
        height = self.render_font.line_height
        for i, chunk in enumerate(chunks):
            if i > 0 and self.wrap == WRAP_WORDS:
                chunk = ' ' + chunk
            size_chunk = sum(
                self.render_font.char_sizes[self.render_font.face.get_char_index(char)][4] for char in chunk)
            if self.max_w is not None and cur_x != self.x and cur_x + size_chunk > self.max_w:
                cur_x = self.x
                cur_y += height
                chunk = chunk.strip()
            if cur_y == self.y:
                cur_y += height + self.render_font.min_top
            for char in chunk:
                if char == "\n":
                    cur_x = self.x
                    cur_y += height
                if char != ' ' and not char.strip():
                    continue
                char = self.render_font.face.get_char_index(char)
                advance = self.render_font.char_sizes[char][4]
                yield char, cur_x, cur_y, advance
                cur_x += advance

    def parent_draw(self):
        fbo, disp_w, disp_h, x_disp, y_disp = self.get_draw_parent_fbo()
        for char, cur_x, cur_y, advance in self.iter_chars():
            rect = pygame.rect.Rect(cur_x - (self.x - x_disp) + self.render_font.char_sizes[char][0],
                                    cur_y - (self.y - y_disp) - self.render_font.char_sizes[char][1],
                                    self.render_font.char_sizes[char][2], self.render_font.char_sizes[char][3])
            x, y = rect.x, rect.y
            x /= disp_w
            y /= disp_h
            w, h = rect.w, rect.h
            tex_i = self.render_font.char_to_tex[char]
            tex_x, tex_y = (tex_i % MAGIC_NUMBER) * self.render_font.line_height, \
                           (tex_i // MAGIC_NUMBER) * self.render_font.line_height
            w, h = self.render_font.line_height / disp_w, self.render_font.line_height / disp_h
            tex_x2, tex_y2 = tex_x + self.render_font.line_height, tex_y + self.render_font.line_height

            mul_x = 1.0 / (MAGIC_NUMBER * self.render_font.line_height)

            mul_y = MAGIC_NUMBER / (self.render_font.total_glyph * self.render_font.line_height)

            tex_x = tex_x * mul_x
            tex_y = tex_y * mul_y
            tex_x2 = tex_x2 * mul_x
            tex_y2 = tex_y2 * mul_y
            vtx_x = -1 + 2 * x
            vtx_y = 1 - 2 * y
            vtx_x2 = -1 + 2 * x + 2 * w
            vtx_y2 = 1 - (2 * y + 2 * h)
            tex_pointer = [tex_x, tex_y, tex_x2, tex_y2, tex_x, tex_y2] + [tex_x, tex_y, tex_x2, tex_y, tex_x2,
                                                                           tex_y2]
            vtx_pointer = [vtx_x, vtx_y, vtx_x2, vtx_y2, vtx_x, vtx_y2] + [vtx_x, vtx_y, vtx_x2, vtx_y, vtx_x2,
                                                                           vtx_y2]
            self.render_font.vbo.push(tex_pointer, vtx_pointer)
        self.render_font.vbo.flush(self)


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


class TextOverlay(GuiContainer):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 0))

    def __init__(self, x, y, text, font, **kwargs):
        self.render_string = RenderString(0, font.min_top, text, font, **kwargs)
        super().__init__(x, y, self.render_string.w, self.render_string.h)
        self.add_element(self.render_string)


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


class TextArea(GuiContainer):
    def __init__(self, x, y, w, h, font, placeholder='', **kwargs):
        super().__init__(x, y, w, h, **kwargs)
        self.string = ''
        self.placeholder = placeholder
        self.render_string = RenderString(0, font.min_top, placeholder, font, max_w=self.w)
        self.add_element(self.render_string)
        self.focus = False

    def key_down(self, keycode, key_char):
        if not self.focus:
            return
        if keycode == pygame.K_BACKSPACE:
            self.string = self.string[:-1]
        else:
            self.string = self.string + key_char
        self.render_string.string = self.string

    def mouse_down(self, x, y, button):
        if button != 1:
            return
        if self.hovered:
            self.focus = True
            if not self.string:
                self.render_string.string = self.string
        else:
            self.focus = False
            if not self.string:
                self.render_string.string = self.placeholder


class Button(GuiContainer):
    def __init__(self, x, y, w, h, text, font, padding_x=16, padding_y=8, **kwargs):
        self.caption = TextOverlay(padding_x, padding_y, text, font)
        super().__init__(x, y, w or self.caption.w + 2 * padding_x, h or self.caption.h + 2 * padding_y, **kwargs)
        self.add_element(self.caption)


class DropDown(GuiContainer):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 0))

    def __init__(self, x, y, w, h, top_text, option_list, font, queue_name=None, **kwargs):
        if 'style' not in kwargs:
            kwargs['style'] = self.DEFAULT_STYLE
        self.button = Button(0, 0, w, h, top_text, font, style=kwargs['style'])
        options_h = 0
        self.options = []
        for text in option_list:
            option = Button(0, 0, w, h, text, font, style=kwargs['style'], queue_name=queue_name)
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
        if button != 1 or self.drop_down._scrollbar.clicked:
            return
        if self.hovered and not self.focus:
            self.focus = True
            self.add_element(self.drop_down)
            self.clear()
            self.set_redraw()
        elif self.focus:
            self.elements.remove(self.drop_down)
            self.drop_down.unbind()
            self.focus = False
            self.clear()
            self.set_redraw()
            for option in self.options:
                option.reset()
            self.drop_down.reset()

    def hover_pred(self, x, y):
        if not self.focus:
            return self.button.hover_pred(self.to_element_x(x), self.to_element_y(y))
        return super().hover_pred(x, y)


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


class OptionsUIApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Options UI")
        self.options = Options()
        self.clock = pygame.time.Clock()
        self.window_surface = pygame.display.set_mode(self.options.resolution,
                                                      pygame.FULLSCREEN | pygame.OPENGL | pygame.DOUBLEBUF)
        # basic opengl configuration
        glViewport(0, 0, self.options.resolution[0], self.options.resolution[1])
        glDepthRange(0, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glShadeModel(GL_SMOOTH)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

        self.background_surface = None
        self.small_font = RenderFont("fonts/FiraCode-Regular.ttf", 14)
        self.window_ui = MainWindow(0, 0, self.options.resolution[0], self.options.resolution[1])
        panel_level1_style = Style(color=(0.05, 0.05, 0.05, 1))
        self.panel = GuiContainer(40, 40, 1920 - 80, 1000, style=panel_level1_style)
        self.window_ui.add_element(self.panel)
        self.load_display = TextOverlay(20, 10, '000.0 load', self.small_font)
        self.window_ui.add_element(self.load_display)
        panel_level2_style = Style(color=(0.1, 0.1, 0.1, 1))
        self.panel2 = GuiContainer(1540, 40, 150, 50, style=panel_level2_style)
        self.panel3 = GuiContainer(40, 40, 500, 920, style=panel_level2_style, overflow_h=8000)
        self.panel.add_element(self.panel2)
        self.panel.add_element(self.panel3)
        textarea = TextArea(580, 40, 200, 200, self.small_font, placeholder='Type here!', style=panel_level2_style)
        self.panel.add_element(textarea)
        btn_style = Style(color=(0, 0.2, 0, 1), hover_color=(0.2, 0.4, 0.2, 1), click_color=(0.5, 0.5, 0.5, 1),
                          fade_out_time=0.35, border_color=(0.5, 0.6, 0.5, 1), border_line_w=1)

        select_style = Style(color=(0, 0.2, 0, 1), hover_color=(0.25, 0.4, 0.25, 1),
                             fade_out_time=0.35, border_color=(0.5, 0.6, 0.5, 1), border_line_w=1)
        select = DropDown(800, 40, 160, 40, 'Select menu', [f"Option {i}" for i in range(1, 21)],
                          self.small_font, style=select_style, max_h=300, queue_name='Select_menu')

        image = Widget(600, 600, 1, 1)
        image.load_image('images/Other Load.png')


        def listener(event):
            print(event.__dict__)

        pub.subscribe(listener, 'callback-click')
        pub.subscribe(listener, 'Select_menu')
        self.panel.add_element(image)
        self.panel.add_element(select)
        self.panel2.add_element(Button(0, 0, 0, 0, "Click me", self.small_font, style=btn_style, queue_name='callback-click'))
        self.panel3.add_element(TextOverlay(10, 10, LOREM_IPSUM, self.small_font, max_w=self.panel3.w - 20))
        self.run()

    def run(self):
        t0 = time.time_ns()
        t1 = t0
        load_buff = []
        while self.window_ui.running:
            frame_time = t1 - t0
            t0 = time.time_ns()
            self.clock.tick(FRAMERATE)
            t_run_0 = time.time_ns()
            if load_buff:
                load = sum(load_buff) / len(load_buff)
                if len(load_buff) > FRAMERATE:
                    load_buff.pop(0)
                self.load_display.render_string.string = f'{load:.1f}% load'
            self.window_ui.process_events()
            self.window_ui.update(frame_time / 10**6)
            self.window_ui.draw()
            pygame.display.flip()
            t1 = time.time_ns()
            if frame_time:
                load_buff.append(100 * (t1 - t_run_0) / frame_time)


if __name__ == '__main__':
    app = OptionsUIApp()
