import pygame
from pubsub import pub
import ggui
from collections import OrderedDict
import random

FRAMERATE = 60
SMALL_FONT = None
MEDIUM_FONT = None
LARGE_FONT = None


class MainMenu(ggui.GuiContainer):

    def __init__(self):
        super().__init__(10, 10, 1900, 1060, style=ggui.Style(color=(0.05, 0.05, 0.05, 1)))
        btn = ggui.Button(900, 480, 120, 60, 'Play', LARGE_FONT, padding_y=10, padding_x=30,
                          style=ggui.Style(color=(0.25, 0.05, 0.05, 1),
                                           hover_color=(0.75, 0.5, 0.5, 1),
                                           click_color=(1, 1, 1, 1)))
        pub.subscribe(self.start, f'{btn.uid}.confirm-click')
        self.add_element(btn)

    def start(self, event):
        self.parent.elements.remove(self)
        self.parent.add_element(PlayScene())
        self.unbind()


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Game:
    building_costs = {
        'power_plant': {'iron': 20}
    }

    def __init__(self):
        self.resources = OrderedDict({
            'iron': 0,
            'wood': 0
        })
        self.buildings = OrderedDict({
            'power_plant': 0
        })
        self.current_action = None
        self.action_time_max = 0
        self.action_time = 0
        self.map = {}

    def update(self, frame_time):
        consumption = min(self.resources['wood'], self.buildings['power_plant'] * frame_time / 5000)
        # self.resources['energy'] += consumption * 5
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

    def __init__(self, x, y, revealed=False, resource=None):
        if not self.master_texture:
            HexTile.master_texture = self.load_image('images/Hex.png')
        self.hidden_style = ggui.Style(color=(0, 0, 0, 1))
        self.revealed_style = ggui.Style(color=(0.25, 0.25, 0.25, 1), hover_color=(0.5, 0.5, 0.5, 1), fade_out_time=0.2)
        self.revealed = revealed or resource

        super().__init__(x, y, 56, 60, texture=self.master_texture,
                         style=self.hidden_style if not self.revealed else self.revealed_style)
        if resource:
            self.add_element(Resource(12, 13, resource))
        if not revealed:
            self.disable()

    def hover_pred(self, x, y):
        t1 = - (y - self.y) + 0.5 * (x - self.x) + self.w * 3 / 4
        t2 = - (y - self.y) - 0.5 * (x - self.x) + 5 * self.w / 4
        t3 = x - self.x
        return 0 < t1 < self.h and 0 < t2 < self.h and 0 < t3 < self.w

    def reveal(self):
        if self.revealed:
            return None
        self.style = self.revealed_style
        element = 'empty'
        if random.random() < 0.06:
            element = 'wood'
        elif random.random() < 0.02:
            element = 'iron'
        if element != 'empty':
            self.add_element(Resource(12, 13, element))
        self.revealed = True
        self.enable()
        return element


class Resource(ggui.Widget):
    master_textures = {}
    name = ''

    def __init__(self, x, y, name):
        self.name = name
        if self.name not in self.master_textures:
            self.master_textures[self.name] = self.load_image(f'images/{self.name.capitalize()}.png')
        super().__init__(x, y, 32, 32, texture=self.master_textures[self.name])


class Grid(ggui.GuiContainer):
    STEPS = [(56, 0), (-56, 0), (28, 46), (-28, 46), (28, -46), (-28, -46), (0, 0)]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hexes = []
        self._moving_from = None
        self._moving_to = None
        self.player_coords = (0, 0)
        self.center_cell_coords = (840, 460)
        self.origin_shift = (0, 0)
        self.player = ggui.Widget(840 + 18, 460 + 20, 20, 20)
        self.player.texture = self.player.load_image('images/Player.png')
        self.drag_start = None
        self.add_element(self.player)

    def dist(self, cell1, cell2):
        return ((cell1.x - cell2.x) ** 2 + (cell1.y - cell2.y) ** 2) ** 0.5 / cell1.w

    def to_logical_coords(self, point):
        return (point.x - self.center_cell_coords[0] + self.origin_shift[0]), \
               (point.y - self.center_cell_coords[1] + self.origin_shift[1])

    def get_clicked_element(self):
        for element in self.elements:
            if element.clicked:
                return element

    def populate_from_game_dict(self, game_dict):
        for hex in self.hexes:
            if hex in self.elements:
                self.elements.remove(hex)
        self.hexes = []
        nb_steps_h = self.h // 46
        offset_h = self.origin_shift[1] % 46
        nb_step_w = self.w // 56
        offset_w = self.origin_shift[0] % 56
        if self.origin_shift[1] % 92 < 46:
            offset_w += 28
        for hex_count, j in enumerate(range(- offset_h, 46 * nb_steps_h, 46)):
            for i in range(- offset_w, 56 * nb_step_w, 56):
                if hex_count % 2 == 0:
                    i += 28
                x, y = self.to_logical_coords(Point(i, j))
                map_get = game_dict.get((x, y))
                if map_get:
                    resource = map_get if map_get != 'empty' else None
                    hex = HexTile(i, j, revealed=True, resource=resource)
                    self.hexes.append(hex)
                    self.add_element(hex, 0)

        if self.player in self.elements:
            self.elements.remove(self.player)
        self.add_element(self.player)
        self.player.x, self.player.y = self.to_screen_xy(Point(*self.player_coords), Point(18, 20))
        self.clear()
        self.set_redraw()

    def mouse_down(self, x, y, button):
        super().mouse_down(x, y, button)
        if button == 1 and not self._moving_to:
            cell = self.get_clicked_element()
            if not cell or self.to_logical_coords(cell) == self.player_coords:
                return
            self.parent.game.current_action = lambda: self.move(cell)
            self._moving_from = self.player_coords
            self._moving_to = self.to_logical_coords(cell)
            self.parent.game.action_time_max = self.dist(cell, Point(*self.player_coords)) / 46
        elif not self._moving_to:
            for element in self.elements:
                if element.hovered:
                    cell = element
                    break
            else:
                return
            self.drag_start = (x, y)

    def mouse_up(self, x, y):
        super().mouse_up(x, y)
        self.drag_start = None

    def check_mouse(self, x, y):
        super().check_mouse(x, y)
        if self.drag_start:
            self.origin_shift = self.origin_shift[0] - x + self.drag_start[0], \
                                self.origin_shift[1] - y + self.drag_start[1]
            self.drag_start = (x, y)
            self.populate_from_game_dict(self.parent.game.map)

    def get_hex_at_logical_xy(self, x, y):
        for element in self.hexes:
            if self.to_logical_coords(element) == (x, y):
                return element
        hex = HexTile(x + self.center_cell_coords[0] - self.origin_shift[0], y + self.center_cell_coords[1] - self.origin_shift[1])
        self.hexes.append(hex)
        self.add_element(hex, 0)
        return hex

    def to_screen_xy(self, point, point_center=None):
        if point_center is None:
            point_center = Point(0, 0)
        return point.x + self.center_cell_coords[0] - self.origin_shift[0] + point_center.x, \
               point.y + self.center_cell_coords[1] - self.origin_shift[1] + point_center.y

    def scout(self):
        for step in self.STEPS:
            x, y = self.player_coords[0] + step[0], self.player_coords[1] + step[1]
            cell = self.get_hex_at_logical_xy(x, y)
            retval = cell.reveal()
            if retval:
                self.parent.game.map[x, y] = retval

    def bind(self, parent):
        super().bind(parent)
        self.scout()

    def move(self, cell):
        self.player_coords = self.to_logical_coords(cell)
        self.player.x, self.player.y = self.to_screen_xy(Point(*self.player_coords), Point(18, 20))
        self.scout()
        self._moving_to = None
        self._moving_from = None

    def update(self, frame_time):
        super(Grid, self).update(frame_time)
        if self._moving_from and self._moving_to:
            progress = self.parent.game.action_time / self.parent.game.action_time_max
            from_xy = self.to_screen_xy(Point(*self._moving_from), Point(18, 20))
            to_xy = self.to_screen_xy(Point(*self._moving_to), Point(18, 20))
            self.player.x = from_xy[0] * (1 - progress) + to_xy[0] * progress
            self.player.y = from_xy[1] * (1 - progress) + to_xy[1] * progress
            self.clear()
            self.set_redraw()


class ActionTab(ggui.GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.btn_style = ggui.Style(color=(0.075, 0.075, 0.075, 0.5),
                                    hover_color=(0.12, 0.12, 0.12, 0.5),
                                    click_color=(0.37, 0.0, 0.0, 0.5),
                                    border_line_w=1, border_color=(0.5, 0.5, 0.5, 0.5))

        self.gather_btn = ggui.Button(20, 20, 210, 40, 'Gather Resource', MEDIUM_FONT, style=self.btn_style)

        self.build_select = ggui.DropDown(20, 80, 210, 40, 'Build...', ['Steam power plant'], MEDIUM_FONT,
                                          style=self.btn_style)
        for element in [self.gather_btn, self.build_select]:
            self.add_element(element)


class ResourceTab(ggui.GuiContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texts = {}
        self.icons = {}

    def bind(self, parent):
        super().bind(parent)
        for resource, value in self.parent.game.resources.items():
            self.texts[resource] = ggui.TextOverlay(25, 40, resource, SMALL_FONT, w=27, style=ggui.Style(color=(0, 0, 0, 0.5)))
            self.icons[resource] = Resource(20, 20, resource)

    def update(self, frame_time):
        i = 0
        for resource, amount in self.parent.game.resources.items():
            if amount <= 0:
                if self.texts[resource] in self.elements:
                    self.elements.remove(self.texts[resource])
                    self.elements.remove(self.icons[resource])
                    self.texts[resource].unbind()
                    self.icons[resource].unbind()
                continue
            self.texts[resource].render_string.string = f"{amount:.0f}"
            self.texts[resource].y = 40 + 50 * i
            self.icons[resource].y = 20 + 50 * i
            i += 1
            if self.texts[resource] not in self.elements:
                self.add_element(self.icons[resource])
                self.add_element(self.texts[resource])
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
        pub.subscribe(self.gather_callback, f'{self.actions.gather_btn.uid}.confirm-click')

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
        self.game.current_action = self.gather_done
        self.game.action_time_max = 5
        self.actions.elements.remove(self.actions.gather_btn)
        self.actions.add_element(self.progress_bar)
        self.progress_bar.x, self.progress_bar.y = self.actions.gather_btn.x, self.actions.gather_btn.y
        self.actions.disable()

    def gather_done(self):
        player_pos = self.grid.player_coords
        resource = self.game.map.get(player_pos)
        if not resource or resource == 'empty':
            print('WARNING empty resource gather')
            return
        self.game.resources[resource] += 10
        self.actions.add_element(self.actions.gather_btn)
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
        SMALL_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 10)
        global MEDIUM_FONT
        MEDIUM_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 14)
        global LARGE_FONT
        LARGE_FONT = ggui.RenderFont("fonts/FiraCode-Regular.ttf", 23)
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
