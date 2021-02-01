import pygame
from OpenGL.GL import *
import freetype
import numpy

from .widget import Widget
from .style import Style
from .container import GuiContainer


MAGIC_NUMBER = 32
WRAP_CHAR = 'char'
WRAP_WORDS = 'words'


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


class TextOverlay(GuiContainer):
    DEFAULT_STYLE = Style(color=(0, 0, 0, 0))

    def __init__(self, x, y, text, font, w=0, h=0, text_style=None, style=None, **kwargs):
        self.render_string = RenderString(0, font.min_top, text, font, style=text_style, **kwargs)
        super().__init__(x, y, w or self.render_string.w, h or self.render_string.h, style=style)
        self.add_element(self.render_string)


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
