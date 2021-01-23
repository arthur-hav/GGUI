import pygame
from OpenGL.GL import *
import freetype
import numpy
import time
from collections import defaultdict

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
                 fade_in_time=0,
                 fade_out_time=0):
        self.default_color = color
        self.hover_color = hover_color
        self.click_color = click_color
        self.fade_in_time = fade_in_time
        self.fade_out_time = fade_out_time
        self.border_color = border_color
        self.border_line_w = border_line_w

    @property
    def background(self):
        return self.hover_color or self.border_color

    def __str__(self):
        return f'#{int(255 * self.default_color[0]):02X}{int(255 * self.default_color[1]):02X}' \
               f'{int(255 * self.default_color[2]):02X}{int(255 * self.default_color[3]):02X}'


class Widget:
    def __init__(self, x, y, w=0, h=0, style_args=None, *args, **kwargs):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dirty = True
        self.hovered = False
        self.parent = None
        self.elements = []
        self.style = Style(**(style_args or {}))
        self.clicked = False
        self.fade_timer = 0
        self.animation_ratio = 0
        self._color_start = self.style.default_color
        self._color_end = self.style.default_color
        self.cleared = False
        self.texture = 0

    def clear(self):
        self.cleared = True

    def __repr__(self):
        return f'{(self.x, self.y, self.w, self.h, str(self.style))}'

    def update(self, frame_time):
        for element in self.elements:
            self.dirty = self.dirty or element.update(frame_time)
        if self.animation_ratio:
            self.animation_ratio = max(0, self.animation_ratio - frame_time / (1000 * self.fade_timer))
            self.dirty = True
        return self.dirty

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

    def mouse_enter(self):
        if not self.hovered and not self.clicked and self.style.hover_color:
            self._color_start = self.get_color()
            self.fade_timer = self.style.fade_in_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self._color_end = self.style.hover_color
            self.dirty = True
        self.hovered = True

    def mouse_leave(self):
        if not self.clicked and self.style.hover_color:
            self._color_start = self.get_color()
            self.fade_timer = self.style.fade_out_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self._color_end = self.style.default_color
            self.dirty = True
        self.hovered = False

    def mouse_wheel(self, relative_y):
        pass

    def mouse_down(self, x, y, button):
        if self.hovered:
            for element in self.elements:
                element.mouse_down(self.to_element_x(x), self.to_element_y(y), button)
            if not self.clicked and self.style.click_color:
                self._color_start = self.get_color()
                self.fade_timer = self.style.fade_in_time
                self.animation_ratio = 1.0 if self.fade_timer else 0
                self._color_end = self.style.click_color
                self.dirty = True
            self.clicked = True

    def mouse_up(self, x, y):
        for element in self.elements:
            element.mouse_up(self.to_element_x(x), self.to_element_y(y))
        if self.clicked and self.style.click_color:
            self._color_start = self.get_color()
            self._color_end = self.style.hover_color if self.hovered else self.style.default_color
            self.fade_timer = self.style.fade_out_time
            self.animation_ratio = 1.0 if self.fade_timer else 0
            self.clicked = False
            self.dirty = True
        self.clicked = False

    def key_down(self, keycode, key_char):
        for element in self.elements:
            element.key_down(keycode, key_char)

    def draw(self, force=False):
        dirty = False
        for element in self.elements:
            dirty = element.draw(self.cleared) or dirty
        if dirty or self.dirty or force or self.cleared:
            self.parent_draw()
        retval = dirty or self.dirty or self.cleared
        self.dirty = False
        self.cleared = False
        return retval

    def parent_draw(self):
        self.draw_background(self.parent)

    def draw_background(self, container):
        if self.style.border_color and self.style.border_line_w:
            self.gl_draw_rectangle(self.style.border_color, self.texture, container.fbo,
                                   container.total_w, container.total_h)
            self.x += self.style.border_line_w
            self.y += self.style.border_line_w
            self.w -= self.style.border_line_w * 2
            self.h -= self.style.border_line_w * 2
            self.gl_draw_rectangle(self.get_color(), self.texture, container.fbo,
                                   container.total_w, container.total_h)
            self.x -= self.style.border_line_w
            self.y -= self.style.border_line_w
            self.w += self.style.border_line_w * 2
            self.h += self.style.border_line_w * 2
        else:
            self.gl_draw_rectangle(self.get_color(), self.texture, container.fbo,
                                   container.total_w, container.total_h)

    def gl_draw_rectangle(self, color, texture, fbo, viewort_w, viewport_h):
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, viewort_w, viewport_h)
        x, y, w, h = self.x / viewort_w, 1 - (self.y + self.h) / viewport_h, \
                     self.w / viewort_w, self.h / viewport_h
        x1, y1, x2, y2 = -1 + 2 * x, -1 + 2 * y, -1 + 2 * x + 2 * w, -1 + (2 * y + 2 * h)
        glColor4f(*color)
        glBegin(GL_TRIANGLES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glVertex2f(x1, y2)

        glVertex2f(x1, y1)
        glVertex2f(x2, y1)
        glVertex2f(x2, y2)

        glEnd()

    def add_element(self, element):
        self.elements.append(element)
        element.bind(self)


class OverflowWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overflow_w = kwargs.get('overflow_w', 0)
        self.overflow_h = kwargs.get('overflow_h', 0)
        self.offset_x = 0
        self.offset_y = kwargs.get('overflow_h', 0)
        self._scrollbar = None

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
            if self._scrollbar:
                self._scrollbar.y -= 30 * relative_y * self.h / self.total_h
                self._scrollbar.scroll()

    def bind(self, parent):
        if not self.overflow_h and not self.overflow_w:
            self.parent = parent
            return
        if self.parent:
            self.parent.elements.remove(self._scrollbar)
        else:
            self._scrollbar = ScrollBar(window=self)
        parent.elements.append(self._scrollbar)
        self._scrollbar.bind(parent)
        self.parent = parent

    def to_element_x(self, x):
        return x - self.x - self.offset_x

    def to_element_y(self, y):
        return y - self.offset_y + self.overflow_h - self.y


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
                            tex_array[-1].append(bytes([255, 255, 255, 0]))
                start_i = (enum // MAGIC_NUMBER) * self.line_height
                start_j = (enum % MAGIC_NUMBER) * self.line_height
                for i in range(bitmap.width):
                    for j in range(bitmap.rows):
                        tex_array[start_i + j][start_j + i] = bytes(
                            [255, 255, 255, bitmap.buffer[j * bitmap.width + i]])
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
        glBindTexture(GL_TEXTURE_2D, widget.texture)
        glBindFramebuffer(GL_FRAMEBUFFER, widget.parent.fbo)
        glViewport(0, 0, widget.parent.total_w, widget.parent.total_h)
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
    def __init__(self, x, y, string, render_font, wrap=WRAP_WORDS, max_w=None, **kwargs):
        super().__init__(x, y, **kwargs)
        self.max_w = max_w
        self.wrap = wrap
        self.render_font = render_font
        self._string = None
        self._render = []
        self.string = string
        self.texture = render_font.texture

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
        self.dirty = True

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

    def parent_draw(self, force=False):
        for char, cur_x, cur_y, advance in self.iter_chars():
            rect = pygame.rect.Rect(cur_x + self.render_font.char_sizes[char][0],
                                    cur_y - self.render_font.char_sizes[char][1],
                                    self.render_font.char_sizes[char][2], self.render_font.char_sizes[char][3])
            x, y = rect.x, rect.y
            x /= self.parent.total_w
            y /= self.parent.total_h
            w, h = rect.w, rect.h
            tex_i = self.render_font.char_to_tex[char]
            tex_x, tex_y = (tex_i % MAGIC_NUMBER) * self.render_font.line_height, \
                           (tex_i // MAGIC_NUMBER) * self.render_font.line_height
            w, h = self.render_font.line_height / self.parent.total_w, self.render_font.line_height / self.parent.total_h
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fbo, self.fbo_tex = self.create_fbo(self.total_w, self.total_h)
        self.clear()

    def create_fbo(self, w, h):
        texID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texID)
        glTexImage2D(GL_TEXTURE_2D, 0, self.get_mode(), w, h, 0, self.get_mode(), GL_UNSIGNED_BYTE, b'\xff' * 4 * w * h)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        fb_id = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fb_id)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, texID, 0)
        glDrawBuffers(1, GL_COLOR_ATTACHMENT0)
        return fb_id, texID

    def get_mode(self):
        return GL_RGBA

    def clear(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glClearColor(*self.get_color())
        glClear(GL_COLOR_BUFFER_BIT)
        if self.style.background:
            x, y, w, h = self.x, self.y, self.w, self.h
            self.x, self.y, self.w, self.h = 0, self.overflow_h, self.total_w, self.total_h
            self.draw_background(self)
            self.x, self.y, self.w, self.h = x, y, w, h
        super().clear()

    def parent_draw(self):
        glBindTexture(GL_TEXTURE_2D, self.fbo_tex)
        glBindFramebuffer(GL_FRAMEBUFFER, self.parent.fbo if self.parent is not None else 0)
        w_disp = self.parent.total_w if self.parent else self.total_w
        h_disp = self.parent.total_h if self.parent else self.total_h
        glViewport(0, 0, w_disp, h_disp)

        x, y, w, h = self.x / w_disp, 1 - (self.y + self.h) / h_disp, self.w / w_disp, self.h / h_disp
        x1, y1, x2, y2 = -1 + 2 * x, -1 + 2 * y, -1 + 2 * x + 2 * w, -1 + (2 * y + 2 * h)
        tex_x0 = self.offset_x / self.total_w
        tex_y0 = self.offset_y / self.total_h
        tex_x1 = (self.offset_x + self.w) / self.total_w
        tex_y1 = (self.offset_y + self.h) / self.total_h
        glColor4f(1, 1, 1, 1)
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


class TextOverlay(GuiContainer):
    def __init__(self, x, y, text, font, **kwargs):
        if 'style_args' not in kwargs:
            kwargs['style_args'] = {
                'color': (1, 1, 1, 1)
            }
        self.render_string = RenderString(0, font.min_top, text, font, **kwargs)
        super().__init__(x, y, self.render_string.w, self.render_string.h)
        self.add_element(self.render_string)


class ScrollBar(Widget):
    def __init__(self, window):
        style_args = {
            'color': (1, 1, 1, 0.1),
            'hover_color': (1, 1, 1, 0.2),
            'click_color': (1, 1, 1, 1)
        }
        super().__init__(window.x + window.w - 8, window.y, 8, window.h ** 2 // window.total_h, style_args=style_args)
        self.drag_start = None
        self.window = window
        self.hovered = False

    def hover_pred(self, x, y):
        return self.x < x < self.x + self.w and self.window.y < y < self.y + self.window.h

    def check_mouse(self, x, y):
        super().check_mouse(x, y)
        if self.drag_start:
            self.y -= self.drag_start[1] - y
            self.drag_start = (x, y)
            self.scroll()

    def scroll(self):
        self.y = min(max(self.y, self.window.y), self.window.y + self.window.h - self.h)
        self.window.offset_y = self.window.overflow_h - (self.y - self.window.y) * (self.window.total_h / self.window.h)
        self.window.dirty = True
        self.dirty = True

    def mouse_down(self, x, y, button):
        super().mouse_down(x, y, button)
        if button != 1:
            return
        if self.hovered:
            self.drag_start = (x, y)
            if not self.y < y < self.y + self.h:  # Jump click
                self.y = y - self.h // 2
                self.scroll()

    def mouse_enter(self):
        super().mouse_enter()
        self.window.dirty = True

    def mouse_leave(self):
        super().mouse_leave()
        if self.drag_start:
            return
        self.window.dirty = True

    def mouse_up(self, x, y):
        super().mouse_up(x, y)
        self.drag_start = None
        if not self.hovered:
            self.mouse_leave()


class TextArea(GuiContainer):
    def __init__(self, x, y, w, h, font, **kwargs):
        super().__init__(x, y, w, h, **kwargs)
        self.render_string = RenderString(0, font.min_top, '', font, max_w=self.w, style_args={'color': (1, 1, 1, 1)})
        self.add_element(self.render_string)
        self.focus = False

    def key_down(self, keycode, key_char):
        if not self.focus:
            return
        if keycode == pygame.K_BACKSPACE:
            self.render_string.string = self.render_string.string[:-1]
        else:
            self.render_string.string = self.render_string.string + key_char
        self.clear()

    def mouse_down(self, x, y, button):
        if button != 1:
            return
        if self.hovered:
            self.focus = True
        else:
            self.focus = False


class Button(GuiContainer):
    def __init__(self, x, y, text, font, padding_x=16, padding_y=8):
        self.overflow_w, self.overflow_h = 0, 0
        self.caption = TextOverlay(padding_x, padding_y, text, font)
        style_args = {
            'color': (0.6, 0.2, 0.2, 1),
            'hover_color': (0.7, 0.3, 0.3, 1),
            'click_color': (0.0, 1, 0, 1),
            'fade_out_time': 0.35,
            'border_color': (1, 1, 1, 1),
            'border_line_w': 1
        }
        super().__init__(x, y, self.caption.w + 2 * padding_x, self.caption.h + 2 * padding_y)
        self.bg = Widget(0, 0, self.w, self.h, style_args=style_args)
        self.add_element(self.bg)
        self.add_element(self.caption)

    def update(self, frame_time):
        super().update(frame_time)
        if self.bg.dirty:
            self.clear()
        return self.dirty or self.cleared


class MainWindow(GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True

    def get_mode(self):
        return GL_RGB

    def update(self, frame_time):
        super().update(frame_time)
        self.clear()
        return True

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
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE)

        self.background_surface = None
        self.small_font = RenderFont("fonts/FiraCode-Regular.ttf", 14)
        self.window_ui = MainWindow(0, 0, self.options.resolution[0], self.options.resolution[1], style_args=dict(color=(0.05, 0.05, 0.05, 1)))
        self.panel = GuiContainer(40, 40, 1920 - 80, 1000, style_args=dict(color=(0.05, 0.05, 0.05, 1)))
        self.window_ui.add_element(self.panel)
        self.load_display = TextOverlay(20, 10, '000.0 load', self.small_font)
        self.window_ui.add_element(self.load_display)

        panel_level2_style = dict(color=(0.1, 0.1, 0.1, 1))
        self.panel2 = GuiContainer(1540, 40, 150, 50, style_args=panel_level2_style)
        self.panel3 = GuiContainer(40, 40, 500, 920, style_args=panel_level2_style, overflow_h=800)
        self.panel.add_element(self.panel2)
        self.panel.add_element(self.panel3)
        textarea = TextArea(580, 40, 200, 200, self.small_font, style_args=panel_level2_style)
        self.panel.add_element(textarea)
        btn = Button(15, 5, 'LOREM IPSUM', self.small_font)
        self.panel2.add_element(btn)
        self.panel3.add_element(RenderString(10, 10, LOREM_IPSUM, self.small_font, max_w=self.panel3.w, style_args={
            'color': (1, 1, 1, 1),
        }))
        self.running = True
        self.show_fps = True
        self.toggle_click = False
        self.run()

    def run(self):
        t0 = time.time_ns()
        t1 = t0
        load_buff = []
        pygame.display.flip()
        while self.window_ui.running:
            frame_time = t1 - t0
            t0 = time.time_ns()
            self.clock.tick(FRAMERATE)
            t_run_0 = time.time_ns()
            if load_buff:
                self.load_display.clear()
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
