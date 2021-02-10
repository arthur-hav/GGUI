from OpenGL.GL import *
from .widget import *
from .style import *
from .text import *
from .container import *
from .clickables import *
from .progress_bar import *


def init_gl(width, height):
    # basic opengl configuration
    glViewport(0, 0, width, height)
    glDepthRange(0, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glEnable(GL_TEXTURE_2D)
    glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)