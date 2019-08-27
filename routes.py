from helpers import get_next_point, opposite_directions, normalize_point_cords,\
    get_prev_location, get_side_directions
from constants import SIDE_DIRECTIONS
from maps import in_arena_bounds, get_neighbors, initialize_map
from collections import deque


def argmax(l):
    return max(list(range(len(l))), key=lambda x: l[x])


class MinMax:
    __slots__ = ['xmin', 'ymin', 'xmax', 'ymax']

    def __init__(self):
        self.xmin = float('inf')
        self.ymin = float('inf')
        self.xmax = float('-inf')
        self.ymax = float('-inf')

    def update(self, point):
        x, y = point
        self.xmin = min(self.xmin, x)
        self.ymin = min(self.ymin, y)
        self.xmax = max(self.xmax, x)
        self.ymax = max(self.ymax, y)

    def expand(self):
        self.xmax += 1
        self.ymax += 1
        self.xmin -= 1
        self.ymin -= 1


class RoutesMaker:
    def __init__(self, config, state, prev_move):
        self.state = state
        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']
        self.width = config['width']
        self.prev_move = prev_move

        self.slows = {normalize_point_cords(bonus['position'], self.width) for
                      bonus in state['bonuses'] if bonus['type'] == 's'}

        self.is_slow = any(bonus['type'] == 's' for bonus in state['players']['i']['bonuses'])

        self.remaining_ticks = ((2500 - self.state['tick_num']) / config['speed']) - 1
        # self.remaining_ticks = float('inf')

        my_position = state['players']['i']['position']
        self.curr_position = normalize_point_cords(my_position, self.width)

        min_max = MinMax()
        self.my_territory, self.x_set, self.y_set = set(), set(), set()

        for cords in state['players']['i']['territory']:
            x, y = normalize_point_cords(cords, self.width)
            self.my_territory.add((x, y))
            self.x_set.add(x)
            self.y_set.add(y)
            min_max.update((x, y))

        self.min_max = min_max
        self.lines = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['lines']}

        for point in self.lines:
            min_max.update(point)

        self.backward_direction = opposite_directions[self.prev_move]
        self.side_directions = SIDE_DIRECTIONS[prev_move]

        self.enemy_points = set()
        self.enemy_territory = set()
        for player_id, player_info in state['players'].items():
            if player_id != 'i':
                for x, y in player_info['territory']:
                    self.enemy_territory.add(normalize_point_cords((x, y), self.width))

                x, y = player_info['position']
                self.enemy_points.add(normalize_point_cords((x, y), self.width))

        if not self.enemy_points:
            self.map = initialize_map(self.x_cells_count, self.y_cells_count, initial_value=self.remaining_ticks)
        else:
            self.map = initialize_map(self.x_cells_count, self.y_cells_count)
            self.run_bfs_from_enemies()

        self.routes = []

    def get_next_step(self):
        """
        :returns: next move direction
        """
        stack = []
        min_weight = min([self.map[x][y] for x, y in self.lines]) if self.lines else float('inf')

        if self.curr_position in self.lines:
            self.lines.remove(self.curr_position)

        delta = 2 if self.is_slow else 1
        side_dir1, side_dir2 = get_side_directions(self.prev_move)
        # с помощью построения 3х сторон прямоугольника ищутся все безопасные пути до базы
        # снизу 3 разных начальных направления
        self.get_valid_routes(self.curr_position, self.prev_move, 0, 0, min_weight, stack, delta)
        self.get_valid_routes(self.curr_position, side_dir1, 0, 0, min_weight, stack, delta)
        self.get_valid_routes(self.curr_position, side_dir2, 0, 0, min_weight, stack, delta)

        self.lines.add(self.curr_position)

        estimations = self.estimate_valid_routes()
        if self.routes:
            return self.choose_best_route(estimations, self.routes)

    def is_valid_location(self, curr_pos, steps_count):
        if not in_arena_bounds(curr_pos) or curr_pos in self.lines:
            return False
        if self.map[curr_pos[0]][curr_pos[1]] - steps_count < 1:
            return False
        return True

    def check_location(self, curr_pos, steps_count, min_weight):
        if not in_arena_bounds(curr_pos) or curr_pos in self.lines:
            return False, min_weight

        min_weight = min(min_weight, self.map[curr_pos[0]][curr_pos[1]])
        if min_weight - steps_count < 1:
            return False, min_weight

        return True, min_weight

    def get_valid_routes(self, curr_pos, direction, switch_count, steps_count, min_weight, stack, delta=1):
        """
        stack contains current route and changes inplace
        """
        # если данный путь является возвратным, но не находится на одной линии с базой
        if switch_count == 2:
            if curr_pos[0] not in self.x_set and curr_pos[1] not in self.y_set:
                return

        dir1, dir2 = get_side_directions(direction)
        stack.append(curr_pos)
        i = 1
        while True:

            is_valid_location, min_weight = self.check_location(curr_pos, steps_count, min_weight)
            if not is_valid_location:
                break

            if curr_pos in self.my_territory:
                self.routes.append([pos for pos in stack])
                break

            # попробовать повернуть
            if switch_count < 2:
                for side_dir in (dir1, dir2):
                    next_pos = get_next_point(curr_pos, side_dir, 1)
                    self.get_valid_routes(next_pos, side_dir, switch_count+1, steps_count+delta, min_weight, stack)

            curr_pos = get_next_point(curr_pos, direction, 1)

            if curr_pos in self.slows:
                delta = 2

            stack.append(curr_pos)
            steps_count += delta
            i += 1

        # удаление текущей линии из стека
        for _ in range(i):
            stack.pop()

    def estimate_valid_routes(self):
        estimations = []
        for route in self.routes:
            route_set = set()
            curr_min_max = MinMax()
            for x, y in route:
                route_set.add((x, y))
                curr_min_max.update((x, y))

            curr_min_max.update((self.min_max.xmin, self.min_max.ymin))
            curr_min_max.update((self.min_max.xmax, self.min_max.ymax))

            curr_min_max.expand()

            estimation = 0
            # changes inplace
            visited = set()

            # подсчёт очков при закраске без учёта длинны шлейфа
            for x in range(int(curr_min_max.xmin+1), int(curr_min_max.xmax)):
                for y in range(int(curr_min_max.ymin+1), int(curr_min_max.ymax)):
                    if (x, y) in visited or (x, y) in self.my_territory or (x, y) in self.lines or (x, y) in route_set:
                        continue

                    estimation += self.filling_bfs((x, y), curr_min_max, visited, route_set)

            estimations.append(estimation)
        return estimations

    def filling_bfs(self, position, min_max, visited, route):
        queue = deque([position])
        visited.add(position)
        game_points = 5 if (position[0], position[1]) in self.enemy_territory else 1
        is_surrounded = True

        while queue:
            for _ in range(len(queue)):
                curr_pos = queue.popleft()

                for neighbor in get_neighbors(curr_pos):
                    x, y = neighbor

                    if neighbor in visited:
                        continue

                    if not (min_max.xmin < x < min_max.xmax and min_max.ymin < y < min_max.ymax):
                        is_surrounded = False
                        continue

                    if (x, y) in self.my_territory or (x, y) in self.lines or (x, y) in route:
                        continue

                    visited.add((x, y))
                    game_points += 5 if (x, y) in self.enemy_territory else 1
                    queue.append((x,y))

        if is_surrounded:
            return game_points
        return 0

    def choose_best_route(self, estimations, routes):
        best_estimation_index = argmax(estimations)
        # в случае если можно закрасить только с помощью шлейфа
        # (движение по соседним локациям вдоль своей территори)
        if estimations[best_estimation_index] == 0:
            longest_route_index = argmax([len(route) for route in routes])
            next_location = routes[longest_route_index][1]
        else:
            next_location = routes[best_estimation_index][1]
        return next_location

    def run_bfs_from_enemies(self):

        queue = deque(self.enemy_points)

        for x, y in self.enemy_points:
            self.map[x][y] = 0

        step_num = 0

        while queue:
            step_num += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not in_arena_bounds(neighbor):
                        continue

                    x, y = neighbor

                    if self.map[x][y] is None or self.map[x][y] > min(step_num, self.remaining_ticks):
                        self.map[x][y] = min(step_num, self.remaining_ticks)
                        queue.append((x, y))