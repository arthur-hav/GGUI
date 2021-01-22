import pygame
from OpenGL.GL import *
import freetype
import numpy
from collections import defaultdict

WRAP_CHAR = 'char'
WRAP_WORDS = 'words'
LOREM_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec risus enim, congue nec eleifend vitae, placerat quis sapien. Nunc felis erat, blandit at turpis in, tincidunt varius lacus. Duis elementum molestie erat nec faucibus. Aliquam erat volutpat. Aliquam erat volutpat. Fusce dapibus tortor purus, ut fringilla tortor pharetra nec. Sed efficitur nunc quis mauris pellentesque pellentesque. Fusce laoreet pretium odio eget dictum. Aliquam consectetur ligula eu odio iaculis, nec venenatis sapien iaculis. Suspendisse a mi massa. Maecenas quis finibus nulla. Ut fermentum tortor id venenatis maximus.
Donec ut laoreet quam, in tincidunt ipsum. Sed in faucibus est, eu ultrices velit. Sed egestas elit eget ipsum interdum, non pharetra libero porta. Duis condimentum, elit vitae tempus varius, lacus turpis convallis nunc, ac mollis dui justo eget ipsum. Aliquam nec convallis lorem. Pellentesque mollis semper ante, eget ornare arcu ultricies eget. In vel purus gravida, ultricies mauris vel, pretium urna. Quisque tincidunt rutrum lacinia. Morbi et augue at metus tempus vehicula non non est. Morbi sed sagittis leo. Aliquam non bibendum mi. Duis in ex neque. Donec sit amet ante leo.
Nullam rhoncus massa nec felis luctus hendrerit. Ut rhoncus vehicula diam eu tincidunt. Etiam tempor lobortis sodales. Aliquam volutpat et elit ut rhoncus. Nunc facilisis, sapien ac laoreet auctor, tellus enim ornare risus, at tincidunt ligula neque non lectus. Morbi rhoncus ex malesuada libero dictum auctor. Pellentesque vitae arcu eget felis facilisis tempus eu sit amet diam. Donec sem ipsum, molestie ut tempor a, ultrices pulvinar erat. Mauris lacinia augue quis luctus rutrum. Mauris consequat orci at magna tincidunt, vel lacinia magna molestie. Nam vulputate faucibus urna, vel auctor nibh vulputate vel. Aliquam bibendum nisl in euismod mattis.
Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Vivamus bibendum magna justo, consequat sollicitudin risus tincidunt at. Etiam blandit finibus elit, ut facilisis ipsum vehicula eget. Maecenas ultricies erat sed hendrerit condimentum. Aenean semper bibendum elit. Cras molestie posuere metus a euismod. Nunc nec ligula metus. Nam pellentesque, nulla id faucibus interdum, nunc dui molestie turpis, nec semper nulla tortor at nibh. Quisque tempus fermentum egestas. Donec feugiat turpis et dolor vehicula, sed convallis nunc ultricies. Nulla vestibulum odio et sapien facilisis, eget ultrices elit blandit. Nullam a justo porttitor, luctus ex a, venenatis augue. Ut et leo sit amet felis mattis ultricies. Quisque sollicitudin, lorem vitae sagittis viverra, nunc erat finibus tellus, in pharetra felis diam ut elit.
Cras blandit eget arcu sed maximus. Suspendisse faucibus, quam nec hendrerit placerat, ipsum dolor gravida diam, vitae posuere enim justo nec quam. Fusce arcu neque, lacinia vitae magna nec, finibus maximus urna. Phasellus congue varius nibh. Morbi vestibulum a nisl eget luctus. Quisque condimentum nulla ut turpis rutrum, ut pharetra eros rutrum. Nam vel pulvinar ex. Lorem ipsum dolor sit amet, consectetur adipiscing elit. """
FRAMERATE = 60.0

class Widget:
    def __init__(self, x, y, w=0, h=0, *args, **kwargs):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dirty = True
        self.hovered = False
        self.elements = []

    def __str__(self):
        return f'{(self.x, self.y, self.w, self.h, self.color)}'

    def update(self, run_time, idle_time):
        for element in self.elements:
            self.dirty = self.dirty or element.update(run_time, idle_time)
        return self.dirty

    def to_element_x(self, x):
        return x - self.x

    def to_element_y(self, y):
        return y - self.y

    def check_mouse(self, x, y):
        if self.x < x < self.x + self.w and self.y < y < self.y + self.h:
            if not self.hovered:
                self.mouse_enter()
            self.hovered = True
        elif self.hovered:
            self.mouse_leave()
            self.hovered = False
        for element in self.elements:
            element_x, element_y = self.to_element_x(x), self.to_element_y(y)
            element.check_mouse(element_x, element_y)

    def mouse_enter(self):
        pass

    def mouse_leave(self):
        pass

    def mouse_wheel(self, relative_y):
        pass

    def mouse_down(self, x, y, buttons):
        if self.hovered:
            for element in self.elements:
                element.mouse_down(self.to_element_x(x), self.to_element_y(y), buttons)

    def mouse_up(self, x, y):
        for element in self.elements:
            element.mouse_up(self.to_element_x(x), self.to_element_y(y))

    def draw(self, vbo, fbo, force=False):
        pass

    def add_element(self, element):
        self.elements.append(element)
        element.parent = self


class OverflowWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overflow_w = kwargs.get('overflow_w', 0)
        self.overflow_h = kwargs.get('overflow_h', 0)
        self.offset_x = 0
        self.offset_y = kwargs.get('overflow_h', 0)
        self._parent = None
        self._scrollbar = None

    @property
    def total_w(self):
        return self.w + self.overflow_w

    @property
    def total_h(self):
        return self.h + self.overflow_h

    @property
    def parent(self):
        return self._parent

    def mouse_wheel(self, relative_y):
        if self.hovered:
            for element in self.elements:
                element.mouse_wheel(relative_y)
            if self._scrollbar:
                self._scrollbar.y -= 30 * relative_y * self.h / self.total_h
                self._scrollbar.scroll()

    @parent.setter
    def parent(self, parent):
        if not self.overflow_h and not self.overflow_w:
            self._parent = parent
            return
        if self._parent:
            self._parent.elements.remove(self._scrollbar)
        else:
            self._scrollbar = ScrollBar(window=self)
        parent.elements.append(self._scrollbar)
        self._scrollbar.parent = parent
        self._parent = parent

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
        self.id_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.id_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.line_height * MAGIC_NUMBER,
                     len(full_binary) // (MAGIC_NUMBER * self.line_height * 4),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, full_binary)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

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
    def __init__(self, tex):
        self.tex_buffer = defaultdict(list)
        self.vtx_buffer = defaultdict(list)
        self.tex = tex

    def push(self, tex_array, vtx_array, fbo):
        self.tex_buffer[fbo].extend(tex_array)
        self.vtx_buffer[fbo].extend(vtx_array)

    def flush(self, fbo):
        if not self.vtx_buffer[fbo]:
            return
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glColor3f(1,1,1)
        glVertexPointer(2, GL_FLOAT, 0, numpy.array(self.vtx_buffer[fbo], dtype=numpy.float32).tobytes())
        glTexCoordPointer(2, GL_FLOAT, 0, numpy.array(self.tex_buffer[fbo], dtype=numpy.float32).tobytes())
        indices = numpy.array(list(range(len(self.vtx_buffer[fbo]))), dtype=numpy.uint32)
        glDrawElements(GL_TRIANGLES, len(self.vtx_buffer[fbo]) // 2, GL_UNSIGNED_INT, indices.tobytes())
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glFlush()
        self.vtx_buffer[fbo] = []
        self.tex_buffer[fbo] = []


class RenderString(Widget):
    def __init__(self, x, y, string, render_font, wrap=WRAP_WORDS, max_w=None):
        super().__init__(x, y)
        self.max_w = max_w
        self.wrap = wrap
        self.render_font = render_font
        self._string = None
        self._render = []
        self.string = string

    @property
    def string(self):
        return self._string

    @string.setter
    def string(self, value):
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
            size_chunk = sum(self.render_font.char_sizes[self.render_font.face.get_char_index(char)][4] for char in chunk)
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

    def draw(self, vbo, fbo, force=False):
        if not self.dirty and not force:
            return False
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
            vbo.push(tex_pointer, vtx_pointer, fbo)
        self.dirty = False
        return True


class GuiContainer(OverflowWidget):
    def __init__(self, *args, **kwargs):
        self.color = kwargs.get('color', (0, 0, 0, 0))
        super().__init__(*args, **kwargs)
        self.fbo, self.fbo_tex = self.create_fbo(self.total_w, self.total_h)
        self.cleared = False
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
        return GL_RGBA if self.color[3] != 1 else GL_RGB

    def clear(self, color=None):
        glBindTexture(GL_TEXTURE_2D, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        if color is None:
            color = self.color
        glClearColor(color[0], color[1], color[2], color[3])
        glClear(GL_COLOR_BUFFER_BIT)
        self.cleared = True

    def draw(self, vbo, fbo, force=False):
        dirty = False
        for element in self.elements:
            dirty = element.draw(vbo, self.fbo, self.cleared) or dirty
        if dirty or self.dirty or force or self.cleared:
            self.parent_draw(vbo)
        retval = dirty or self.dirty
        self.dirty = False
        self.cleared = False
        return retval

    def parent_draw(self, vbo):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.total_w, self.total_h)
        vbo.flush(self.fbo)
        glBindTexture(GL_TEXTURE_2D, self.fbo_tex)
        glBindFramebuffer(GL_FRAMEBUFFER, self.parent.fbo if self.parent is not None else 0)
        glViewport(0, 0, self.parent.total_w if self.parent else self.total_w, self.parent.total_h if self.parent else self.total_h)

        x, y, w, h = self.x / (self.parent.total_w if self.parent else self.total_w), 1 - (self.y + self.h) / (self.parent.total_h if self.parent else self.total_h), \
                     self.w / (self.parent.total_w if self.parent else self.total_w), self.h / (self.parent.total_h if self.parent else self.total_h)
        x1, y1, x2, y2 = -1 + 2 * x, -1 + 2 * y, -1 + 2 * x + 2 * w, -1 + (2 * y + 2 * h)
        tex_x0, tex_y0, tex_x1, tex_y1 = self.offset_x/self.total_w, \
                                         self.offset_y/self.total_h,\
                                         (self.offset_x+self.w)/self.total_w, \
                                         (self.offset_y+self.h)/self.total_h,
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
    def __init__(self, x, y, text, font, color=(0,0,0,0)):
        self.render_string = RenderString(0, font.min_top, text, font)
        super().__init__(x, y, self.render_string.w, self.render_string.h, color=color)
        self.add_element(self.render_string)


class LoadDisplay(TextOverlay):
    def __init__(self, x, y, font):
        super().__init__(x, y, '00.0% load', font)
        self.delay_buffer = []
        self.last_update = 0

    def update(self, run_time, idle_time):
        val_in = self.delay_buffer.append(min(run_time * FRAMERATE / 1000.0, 1))
        if len(self.delay_buffer) > 200:
            val_out = self.delay_buffer.pop(0)
            if val_in == val_out:
                return False
        if self.last_update < 100:
            self.last_update += run_time + idle_time
            return False
        load = 100 * sum(self.delay_buffer) / len(self.delay_buffer)
        self.clear()
        self.render_string.string = f'{load:.1f}% load'
        self.last_update = 0
        super().update(run_time, idle_time)
        return True


class ScrollBar(GuiContainer):
    def __init__(self, window):
        super().__init__(window.x + window.w - 8, window.y, 8, window.h ** 2 // window.total_h)
        self.drag_start = None
        self.window = window
        self.hovered = False
        self.color = (1, 1, 1, 0.1)

    def parent_draw(self, vbo):
        glBindTexture(GL_TEXTURE_2D, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, self.parent.fbo)
        glViewport(0, 0, self.parent.total_w, self.parent.total_h)

        x, y, w, h = self.x / (self.parent.total_w if self.parent else self.w), 1 - (self.y + self.h) / (self.parent.total_h if self.parent else self.h), \
                     self.w / (self.parent.total_w if self.parent else self.w), self.h / (self.parent.total_h if self.parent else self.h)
        x1, y1, x2, y2 = -1 + 2 * x, -1 + 2 * y, -1 + 2 * x + 2 * w, -1 + (2 * y + 2 * h)
        glColor4f(*self.color)
        glBegin(GL_TRIANGLES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glVertex2f(x1, y2)

        glVertex2f(x1, y1)
        glVertex2f(x2, y1)
        glVertex2f(x2, y2)
        glColor4f(1, 1, 1, 1)
        glEnd()

    def check_mouse(self, x, y):
        if self.x < x < self.x + self.w and self.window.y < y < self.y + self.window.h:
            if not self.hovered:
                self.mouse_enter()
            self.hovered = True
        elif self.hovered:
            self.mouse_leave()
            self.hovered = False
        if self.drag_start:
            self.y -= self.drag_start[1] - y
            self.drag_start = (x, y)
            self.scroll()

    def scroll(self):
        self.y = min(max(self.y, self.window.y), self.window.y + self.window.h - self.h)
        self.window.offset_y = self.window.overflow_h - (self.y - self.window.y) * (
                self.window.total_h / self.h)
        self.window.dirty = True
        self.dirty = True

    def mouse_down(self, x, y, buttons):
        if not buttons[0]:
            return
        if self.hovered:
            self.drag_start = (x, y)
            if not self.y < y < self.y + self.h:   # Jump click
                self.y = y - self.h // 2
                self.scroll()

    def mouse_enter(self):
        self.dirty = True
        self.window.dirty = True
        self.color = (1, 1, 1, 1)

    def mouse_leave(self):
        if self.drag_start:
            return
        self.dirty = True
        self.window.dirty = True
        self.color = (1, 1, 1, 0.1)

    def mouse_up(self, x, y):
        self.drag_start = None
        if not self.hovered:
            self.mouse_leave()

class Button(GuiContainer):
    def __init__(self, x, y, text, font, padding_x=16, padding_y=8, color=(0,0,0,0)):
        self.overflow_w, self.overflow_h = 0, 0
        self.caption = TextOverlay(padding_x, padding_y, text, font)
        super().__init__(x, y, self.caption.w + 2 * padding_x, self.caption.h + 2 * padding_y, color=color)
        self.hover_color = (0.8, 0.5, 0.5, 1.)
        self.default_color = self.color
        self.click_color = (0.2, 0, 0, 1)
        self.animate_time = 0
        self.animation_start = None
        self.animation_end = None
        self.click = False
        self._parent = None

    def mouse_enter(self):
        self.animation_start = self.color
        self.animation_end = self.hover_color
        self.animate_time = 0

    def mouse_leave(self):
        self.animation_start = self.color
        self.animation_end = self.default_color
        self.click = False

    def mouse_down(self, x, y, buttons):
        if not buttons[0]:
            return
        if self.hovered:
            self.animation_start = self.color
            self.animation_end = self.click_color
            self.animate_time = 0
            self.click = True

    def mouse_up(self, x, y):
        self.dirty = self.click
        self.animation_start = self.color
        self.animation_end = self.hover_color if self.hovered else self.default_color
        self.animate_time = 0
        self.click = False

    def update(self, run_time, idle_time):
        super().update(run_time, idle_time)
        if self.animation_start and self.animation_end:
            self.animate_time += (run_time + idle_time) / 100
            if self.animate_time >= 1.0:
                self.color = self.animation_end
                self.animation_start, self.animation_end = None, None
            else:
                self.color = tuple(self.animation_start[i] * (1 - self.animate_time) + \
                                   self.animation_end[i] * self.animate_time for i in range(4))
            self.clear()
            self.caption.dirty = True
        else:
            self.animate_time = 0
        return self.dirty


class MainWindow(GuiContainer):
    def get_mode(self):
        return GL_RGB

    def update(self, run_time, idle_time):
        ret = super().update(run_time, idle_time)
        if ret:
            self.clear()
        self.dirty = True


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
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA, GL_ONE)

        self.background_surface = None
        self.small_font = RenderFont("FiraCode-Regular.ttf", 14)
        self.window_ui = MainWindow(0, 0, self.options.resolution[0], self.options.resolution[1], color=(0, 0, 0, 1))
        self.panel = GuiContainer(40, 40, 1920 - 80, 1000, color=(0.05, 0.05, 0.05, 1))
        self.window_ui.add_element(self.panel)
        self.fps_display = LoadDisplay(20, 10, self.small_font)
        self.window_ui.add_element(self.fps_display)
        self.panel2 = GuiContainer(1540, 40, 150, 50, color=(0.1, 0.1, 0.1, 1))
        self.panel3 = GuiContainer(40, 40, 500, 920, color=(0.1, 0.1, 0.1, 1), overflow_h=800)
        self.panel.add_element(self.panel2)
        self.panel.add_element(self.panel3)
        self.panel.add_element(GuiContainer(580, 40, 200, 200, color=(0.1, 0.1, 0.1, 1)))
        btn = Button(15, 5, 'LOREM IPSUM', self.small_font, color=(0.6, 0.2, 0.2, 1))
        self.panel2.add_element(btn)
        btn.add_element(btn.caption)
        self.panel3.add_element(RenderString(10, 10, LOREM_IPSUM, self.small_font, max_w=self.panel3.w))
        self.vbo = Vbo(self.small_font.id_tex)
        self.running = True
        self.show_fps = True
        self.toggle_click = False
        self.run()

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.window_ui.mouse_down(*pygame.mouse.get_pos(), pygame.mouse.get_pressed(num_buttons=5))
            if event.type == pygame.MOUSEWHEEL:
                self.window_ui.mouse_wheel(event.y)
            if event.type == pygame.MOUSEBUTTONUP:
                self.window_ui.mouse_up(*pygame.mouse.get_pos())
            if event.type == pygame.MOUSEMOTION:
                self.window_ui.check_mouse(*pygame.mouse.get_pos())

    def run(self):
        while self.running:
            runtime = self.clock.tick()
            idle_time = self.clock.tick(FRAMERATE)
            self.process_events()
            self.window_ui.update(runtime, idle_time)
            self.window_ui.draw(self.vbo, 0)
            pygame.display.flip()

if __name__ == '__main__':
    app = OptionsUIApp()
    app.run()
