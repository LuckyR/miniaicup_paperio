from constants import LEFT, RIGHT, UP, DOWN, opposite_directions
from helpers import get_next_point, normalize_point_cords, path_to_commands, \
    follow_path, get_prev_location, get_command_from_points
import random
import json
from maps import ThreatsMap, SavesMap, AttacksMap, TerritoryMovementsMap
import time
from routes import RoutesMaker


class Bot:
    def __init__(self):
        self.width = None
        self.x_cells_count = None
        self.y_cells_count = None
        self.curr_position = None
        self.curr_territory = None
        self.have_enemies = False
        self.config = None
        self.state = None
        self.risky_location = None

        self.return_commands = None
        self.prev_move = None
        self.move = None

    def on_game_start(self, config):
        self.config = config
        self.width = config['width']
        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']

    def on_tick(self, state):
        start_time = time.time()
        self.state = state
        self.risky_location = None
        self.move = None
        self.curr_position = state['players']['i']['position']
        self.curr_territory = state['players']['i']['territory']
        self.have_enemies = True if len(state['players']) > 1 else False

        moves = self.get_valid_moves()

        if self.in_territory_bounds():
            self.move = self.attack_attempt()
            if not self.move:
                self.move = self.leave_territory()
                # если следующая локация находится вне границ территории
                if self.risky_location:
                    threats_map = ThreatsMap(self.config, self.state)
                    if not threats_map.is_save_location(self.risky_location, normalize=False):
                        moves = self.filter_dangerous_moves(moves, threats_map)
                        self.move = None
                # попытаться сделать случайный шаг в пределах своей территории
                if not self.move:
                    self.move = random.choice(moves) if moves else LEFT
        else:
            self.move = self.attack_attempt()
            if not self.move:
                routes_maker = RoutesMaker(self.config, self.state, self.prev_move)

                next_location = routes_maker.get_next_step()
                if next_location:
                    self.move = get_command_from_points(normalize_point_cords(self.curr_position, self.width),
                                                        next_location)
                if not self.move or self.move not in moves:
                    saves_map = SavesMap(self.config, self.state)
                    saves_map.compute()
                    path_to_territory = saves_map.get_path_to_territory()
                    return_commands = path_to_commands(path_to_territory, self.curr_position, self.width)
                    if return_commands:
                        self.move, return_commands = follow_path(return_commands)
                    if not self.move:
                        self.move = self.choose_arbitrary_move(moves, saves_map)

        self.prev_move = self.move
        print(json.dumps({"command": self.move, "debug": f"time = {time.time()-start_time}"}))

    def leave_territory(self):
        if not self.have_enemies:
            return

        prev_location = get_prev_location(self.curr_position, self.prev_move, self.width)

        territory_movements_map = TerritoryMovementsMap(self.config, self.state, prev_location)
        next_point = territory_movements_map.get_next_point()
        if next_point not in territory_movements_map.my_territory:
            self.risky_location = next_point
        if next_point:
            return path_to_commands([next_point], self.curr_position, self.width)[0]

    def attack_attempt(self):
        if not self.have_enemies:
            return

        attack_map = AttacksMap(self.config, self.state)
        next_point = attack_map.get_next_location()
        if next_point:
            return path_to_commands([next_point], self.curr_position, self.width)[0]

    def choose_arbitrary_move(self, moves, saves_map):
        moves_info = {}
        for move in moves:
            next_point = get_next_point(self.curr_position, move, self.width)
            next_point = normalize_point_cords(next_point, self.width)
            moves_info[move] = saves_map.get_distance_from_point_to_territory(next_point)

        move_chosen = False

        while not move_chosen:
            move = random.choice(moves)
            if moves_info[move] is not None:
                move_chosen = True

        return move

    def in_territory_bounds(self):
        return self.curr_position in self.curr_territory

    def filter_dangerous_moves(self, moves, threats_map):
        save_moves = []
        for move in moves:
            next_point = get_next_point(self.curr_position, move, self.width)
            if threats_map.is_save_location(next_point):
                save_moves.append(move)
        return save_moves

    def in_arena_bounds(self, point):
        x, y = point
        valid_x = round(self.width / 2) - 1 < x < self.x_cells_count * self.width - round(self.width / 2) + 1
        valid_y = round(self.width / 2) - 1 < y < self.y_cells_count * self.width - round(self.width / 2) + 1
        return valid_x and valid_y

    def get_valid_moves(self):
        moves = []
        invalid_move = opposite_directions[self.prev_move] if self.prev_move else None
        for move in [LEFT, RIGHT, UP, DOWN]:
            if self.in_arena_bounds(get_next_point(self.curr_position, move, self.width)) and move != invalid_move:
                moves.append(move)
        return moves





