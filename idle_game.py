import pygame
from pubsub import pub
import ggui
from collections import OrderedDict

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


class Game:
    building_costs = {
        'power_plant': {'metal': 20}
    }

    def __init__(self):
        self.resources = OrderedDict({
            'metal': 10,
            'energy': 10,
            'wood': 10
        })
        self.buildings = OrderedDict({
            'power_plant': 0
        })
        self.current_action = None
        self.action_time_max = 0
        self.action_time = 0

    def update(self, frame_time):
        consumption = min(self.resources['wood'], self.buildings['power_plant'] * frame_time / 5000)
        self.resources['energy'] += consumption * 5
        self.resources['wood'] -= consumption
        if self.current_action:
            self.action_time += frame_time / 1000
            if self.action_time > self.action_time_max:
                self.current_action()
                self.current_action = None
                self.action_time_max = 0
                self.action_time = 0

    def check_resources(self, building):
        for resource, cost in self.building_costs[building].items():
            if self.resources[resource] < cost:
                return False
        return True

    def consume_resources(self, building):
        for resource, cost in self.building_costs[building].items():
            self.resources[resource] -= cost


class HexTile(ggui.Widget):
    master_texture = None

    def __init__(self, x, y):
        if not self.master_texture:
            HexTile.master_texture = self.load_image('images/Hex.png')
        self.hidden_style = ggui.Style(color=(0, 0, 0, 1))
        self.revealed_style = ggui.Style(color=(0.25, 0.25, 0.25, 1), hover_color=(0.5, 0.5, 0.5, 1), fade_out_time=0.2)
        self.revealed = False
        super().__init__(x, y, 56, 60, texture=self.master_texture, style=self.hidden_style)

    def hover_pred(self, x, y):
        t1 = - (y - self.y) + 0.5 * (x - self.x) + self.w * 3 / 4
        t2 = - (y - self.y) - 0.5 * (x - self.x) + 5 * self.w / 4
        t3 = x - self.x
        return 0 < t1 < self.h and 0 < t2 < self.h and 0 < t3 < self.w

    def reveal(self):
        self.style = self.revealed_style
        self.revealed = True


class Grid(ggui.GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for j in range(-46, self.h, 46):
            for i in range(-56, self.w, 56):
                if j % 4 == 0:
                    i += 28
                self.add_element(HexTile(i, j))
        center_cell = self.elements[len(self.elements)//2]
        self.player_cell = center_cell
        self.player = ggui.Widget(center_cell.w / 2 - 10, center_cell.h / 2 - 10, 20, 20)
        self.player.texture = self.player.load_image('images/Player.png')
        self.player_cell.add_element(self.player)
        self._moving_from = None
        self._moving_to = None
        self.scout()

    def dist(self, cell1, cell2):
        return ((cell1.x - cell2.x) ** 2 + (cell1.y - cell2.y) ** 2) ** 0.5 / cell1.w

    def get_clicked_element(self):
        for element in self.elements:
            if element.clicked:
                return element

    def mouse_down(self, x, y, button):
        super().mouse_down(x, y, button)
        cell = self.get_clicked_element()
        if not cell or cell == self.player_cell:
            return
        self.parent.game.current_action = lambda: self.move(cell)
        self.player_cell.elements.remove(self.player)
        self.player_cell.set_redraw()
        self._moving_from = (self.player_cell.x + self.player.x, self.player_cell.y + self.player.y)
        self._moving_to = (cell.x + self.player.x, cell.y + self.player.y)
        self.parent.game.action_time_max = self.dist(cell, self.player_cell)
        self.add_element(self.player)

    def scout(self):
        for cell in self.elements:
            if self.dist(self.player_cell, cell) < 1.5:
                cell.reveal()

    def move(self, cell):
        self.elements.remove(self.player)
        self.player_cell = cell
        cell.add_element(self.player)
        self.player.x = cell.w / 2 - 10
        self.player.y = cell.h / 2 - 10
        self.player_cell.clear()
        self.player_cell.set_redraw()
        self.scout()
        self._moving_to = None
        self._moving_from = None

    def update(self, frame_time):
        super(Grid, self).update(frame_time)
        if self._moving_from and self._moving_to:
            progress = self.parent.game.action_time / self.parent.game.action_time_max
            self.player.x = self._moving_from[0] * (1 - progress) + self._moving_to[0] * progress
            self.player.y = self._moving_from[1] * (1 - progress) + self._moving_to[1] * progress
            self.clear()
            self.set_redraw()

class ActionTab(ggui.GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.btn_style = ggui.Style(color=(0.075, 0.075, 0.075, 0.5),
                                    hover_color=(0.12, 0.12, 0.12, 0.5),
                                    click_color=(0.37, 0.0, 0.0, 0.5),
                                    border_line_w=1, border_color=(0.5, 0.5, 0.5, 0.5))
        gatherable_resources = ['wood', 'metal']

        self.gather_select = ggui.DropDown(20, 20, 210, 40, 'Gather...', gatherable_resources, SMALL_FONT,
                                           style=self.btn_style)

        self.build_select = ggui.DropDown(20, 80, 210, 40, 'Build...', ['Steam power plant'], SMALL_FONT,
                                          style=self.btn_style)
        for element in [self.gather_select, self.build_select]:
            self.add_element(element)
        pub.subscribe(self.gather_focus, f'{self.gather_select.uid}.focus')
        pub.subscribe(self.gather_unfocus, f'{self.gather_select.uid}.unfocus')

    def gather_focus(self, event):
        self.elements.remove(self.build_select)

    def gather_unfocus(self, event):
        self.add_element(self.build_select)


class ResourceTab(ggui.GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texts = []

    def bind(self, parent):
        super().bind(parent)
        for i, resources in enumerate(self.parent.game.resources.keys()):
            self.texts.append(ggui.TextOverlay(20, 20 + 50 * i, resources, SMALL_FONT, w=200))
        for element in self.texts:
            self.add_element(element)

    def update(self, frame_time):
        for i, (resource, amount) in enumerate(self.parent.game.resources.items()):
            self.texts[i].render_string.string = f"{amount:.1f} {resource.capitalize()}"
        super().update(frame_time)


class PlayScene(ggui.GuiContainer):
    def __init__(self):
        super().__init__(10, 10, 1900, 1060, style=ggui.Style(color=(0.05, 0.05, 0.05, 1)))

        self.panel_style = ggui.Style(color=(0.1, 0.1, 0.1, 0.25), hover_color=(0.1, 0.1, 0.1, 1))
        self.subpanel_style = ggui.Style(parent_styles=[self.panel_style],
                                         border_color=(0.5, 0.5, 0.5, 0.5),
                                         border_line_w=2)
        self.game = Game()

        self.actions = ActionTab(1650, 10, 250, 800, style=self.panel_style)
        self.resources = ResourceTab(10, 10, 250, 800, style=self.panel_style)
        self.progress_bar = ggui.ProgressBar(10, 80, 210, 15, style=ggui.Style(color=(0, 0, 0, 0.2), border_line_w=2,
                                                                               border_color=(0.5, 0.5, 0.5, 0.2)))
        self.grid = Grid(50, 40, 1800, 1000, style=ggui.Style(color=(0, 0, 0, 1)))
        self.add_element(self.grid)
        self.add_element(self.actions)
        self.add_element(self.resources)

        pub.subscribe(self.build_callback, f'{self.actions.build_select.uid}.select')
        pub.subscribe(self.gather_callback, f'{self.actions.gather_select.uid}.select')

    def update(self, frame_time):
        self.game.update(frame_time)
        if self.game.current_action:
            self.progress_bar.set_progress(self.game.action_time / self.game.action_time_max)
        super().update(frame_time)

    def build_callback(self, event):
        if event.index == 0:
            if not self.game.check_resources('power_plant'):
                return
            self.game.current_action = lambda: self.build_done('power_plant')
            self.game.consume_resources('power_plant')
            self.game.action_time_max = 5
        self.actions.elements.remove(self.actions.build_select)
        self.actions.add_element(self.progress_bar)
        self.progress_bar.x, self.progress_bar.y = self.actions.build_select.x, self.actions.build_select.y
        self.actions.disable()

    def build_done(self, building):
        self.game.buildings[building] += 1
        self.actions.add_element(self.actions.build_select)
        self.actions.elements.remove(self.progress_bar)
        self.actions.enable()

    def gather_callback(self, event):
        if event.index == 0:
            self.game.current_action = lambda: self.gather_done('wood')
        if event.index == 1:
            self.game.current_action = lambda: self.gather_done('metal')
        self.game.action_time_max = 5
        self.actions.elements.remove(self.actions.gather_select)
        self.actions.add_element(self.progress_bar)
        self.progress_bar.x, self.progress_bar.y = self.actions.gather_select.x, self.actions.gather_select.y
        self.actions.disable()

    def gather_done(self, resource):
        self.game.resources[resource] += 10
        self.actions.add_element(self.actions.gather_select)
        self.actions.elements.remove(self.progress_bar)
        self.actions.enable()


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
