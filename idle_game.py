import pygame
import time
from pubsub import pub
import ggui

FRAMERATE = 60
SMALL_FONT = None
MEDIUM_FONT = None
TITLE_FONT = None


class MainMenu(ggui.GuiContainer):

    def __init__(self):
        super().__init__(10, 10, 1900, 1060, style=ggui.Style(color=(0.05, 0.05, 0.05, 1)))
        btn = ggui.Button(900, 480, 120, 60, 'Play', MEDIUM_FONT, padding_y=10, padding_x=30,
                          style=ggui.Style(color=(0.25, 0.05, 0.05, 1),
                                           hover_color=(0.75, 0.5, 0.5, 1),
                                           click_color=(1, 1, 1, 1)))
        pub.subscribe(self.start, f'{btn.uid}.confirm-click')
        self.add_element(btn)

    def start(self, event):
        self.parent.elements.remove(self)
        self.parent.add_element(PlayScene())
        self.unbind()


class PlayScene(ggui.GuiContainer):
    def __init__(self):
        super().__init__(10, 10, 1900, 1060, style=ggui.Style(color=(0.05, 0.05, 0.05, 1)))
        self.btn_style = ggui.Style(color=(0.075, 0.075, 0.075, 0.5),
                                           hover_color=(0.12, 0.12, 0.12, 0.5),
                                           click_color=(0.37, 0.37, 0.37, 0.5),
                                    border_line_w=1, border_color=(0.5, 0.5, 0.5, 0.5))

        self.panel_style = ggui.Style(color=(0.1, 0.1, 0.1, 0.10))
        self.subpanel_style = ggui.Style(parent_styles=[self.panel_style],
                                         border_color=(0.5, 0.5, 0.5, 0.5),
                                         border_line_w=2)
        self.metal_text = ggui.TextOverlay(20, 20, '100 Metal', MEDIUM_FONT, w=200)
        self.energy_text = ggui.TextOverlay(20, 80, '100 Energy', MEDIUM_FONT, w=200)
        self.wood_text = ggui.TextOverlay(20, 140, '100 Wood', MEDIUM_FONT, w=200)

        self.actions = ggui.GuiContainer(1650, 10, 250, 800, style=self.panel_style)
        self.ressources = ggui.GuiContainer(10, 10, 250, 800, style=self.panel_style)

        self.gather_wood = ggui.Button(20, 20, 140, 40, 'Gather wood', SMALL_FONT, style=self.btn_style)
        self.gather_metal = ggui.Button(20, 80, 140, 40, 'Gather metal', SMALL_FONT, style=self.btn_style)

        self.build_menu = ggui.GuiContainer(10, 200, 230, 200, overflow_h=200, style=self.subpanel_style)

        self.power_plant = ggui.Button(10, 20, 180, 40, 'Steam power plant', SMALL_FONT, style=self.btn_style)

        self.progress_bar = ggui.ProgressBar(10, 80, 180, 20, style=ggui.Style(color=(0, 0, 0, 0.2), border_line_w=2,
                                                                               border_color=(1, 1, 1, 0.2)))
        for element in [self.metal_text, self.energy_text, self.wood_text]:
            self.ressources.add_element(element)
        for element in [self.gather_wood, self.gather_metal, self.build_menu]:
            self.actions.add_element(element)
        for element in [self.power_plant, self.progress_bar]:
            self.build_menu.add_element(element)
        self.add_element(self.actions)
        self.add_element(self.ressources)
        self.timer = 0

    def update(self, frame_time):
        self.timer += frame_time / 1000
        if self.timer > 10:
            self.timer = 0
        self.progress_bar.set_progress(self.timer/10)

class IdleGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Options UI")
        self.clock = pygame.time.Clock()
        self.window_surface = pygame.display.set_mode((1920, 1080),
                                                      pygame.FULLSCREEN | pygame.OPENGL | pygame.DOUBLEBUF)

        ggui.init_gl(1920, 1080)
        global SMALL_FONT
        SMALL_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 14)
        global MEDIUM_FONT
        MEDIUM_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 23)
        global TITLE_FONT
        TITLE_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 40)
        self.window_ui = ggui.MainWindow(0, 0, 1920, 1080)
        self.main_menu = MainMenu()
        self.window_ui.add_element(self.main_menu)

    def run(self):
        while self.window_ui.running:
            update_time = self.clock.tick(FRAMERATE)
            self.window_ui.process_events()
            self.window_ui.update(update_time)
            self.window_ui.draw(True)
            pygame.display.flip()

if __name__ == '__main__':
    app = IdleGame()
    app.run()