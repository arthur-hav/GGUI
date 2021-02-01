import pygame
import time
from pubsub import pub
import ggui


LOREM_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec risus enim, congue nec eleifend vitae, 
placerat quis sapien. Nunc felis erat, blandit at turpis in, tincidunt varius lacus. Duis elementum molestie erat nec 
faucibus. Aliquam erat volutpat. Aliquam erat volutpat. Fusce dapibus tortor purus, ut fringilla tortor pharetra nec. 
Sed efficitur nunc quis mauris pellentesque pellentesque. Fusce laoreet pretium odio eget dictum. Aliquam consectetur 
ligula eu odio iaculis, nec venenatis sapien iaculis. Suspendisse a mi massa. Maecenas quis finibus nulla. Ut fermentum
tortor id venenatis maximus.

Donec ut laoreet quam, in tincidunt ipsum. Sed in faucibus est, eu ultrices velit. Sed egestas elit eget ipsum interdum, 
non pharetra libero porta. Duis condimentum, elit vitae tempus varius, lacus turpis convallis nunc, ac mollis dui justo 
eget ipsum. Aliquam nec convallis lorem. Pellentesque mollis semper ante, eget ornare arcu ultricies eget. In vel purus 
gravida, ultricies mauris vel, pretium urna. Quisque tincidunt rutrum lacinia. Morbi et augue at metus tempus vehicula 
non non est. Morbi sed sagittis leo. Aliquam non bibendum mi. Duis in ex neque. Donec sit amet ante leo."""
FRAMERATE = 60


def listener(event):
    print(event.__dict__)


class ExampleApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Options UI")
        self.clock = pygame.time.Clock()
        self.window_surface = pygame.display.set_mode((1280, 800), pygame.OPENGL | pygame.DOUBLEBUF)

        ggui.init_gl(1280, 800)
        self.background_surface = None
        self.small_font = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 14)
        self.window_ui = ggui.MainWindow(0, 0, 1280, 800)
        panel_level1_style = ggui.Style(color=(0.05, 0.05, 0.05, 1))
        self.panel = ggui.GuiContainer(40, 40, 1200, 720, style=panel_level1_style)
        self.window_ui.add_element(self.panel)
        self.load_display = ggui.TextOverlay(20, 10, '000.0 load', self.small_font)
        self.window_ui.add_element(self.load_display)
        panel_level2_style = ggui.Style(color=(0.1, 0.1, 0.1, 1))
        self.panel2 = ggui.GuiContainer(980, 40, 150, 50, style=panel_level2_style)
        self.panel3 = ggui.GuiContainer(40, 40, 500, 640, style=panel_level2_style, overflow_h=800)
        self.panel.add_element(self.panel2)
        self.panel.add_element(self.panel3)
        textarea = ggui.TextArea(580, 40, 200, 200, self.small_font, placeholder='Type here!', style=panel_level2_style)
        self.panel.add_element(textarea)
        btn_style = ggui.Style(color=(0, 0.2, 0, 1), hover_color=(0.2, 0.4, 0.2, 1), click_color=(0.5, 0.5, 0.5, 1),
                          fade_out_time=0.35, border_color=(0.5, 0.6, 0.5, 1), border_line_w=1)

        select_style = ggui.Style(color=(0, 0.2, 0, 1), hover_color=(0.25, 0.4, 0.25, 1),
                             fade_out_time=0.35, border_color=(0.5, 0.6, 0.5, 1), border_line_w=1)
        select = ggui.DropDown(800, 40, 160, 40, 'Select menu', [f"Option {i}" for i in range(1, 21)],
                          self.small_font, style=select_style, max_h=300)

        image = ggui.Widget(600, 600, 28, 30)
        image.texture = image.load_image('images/Hex.png')

        pub.subscribe(listener, f'{select.uid}.select')
        self.panel.add_element(image)
        self.panel.add_element(select)
        self.panel2.add_element(ggui.Button(0, 0, 0, 0, "Click me", self.small_font, style=btn_style))
        self.panel3.add_element(ggui.TextOverlay(10, 10, LOREM_IPSUM, self.small_font, max_w=self.panel3.w - 20))

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
    app = ExampleApp()
    app.run()