from collections import deque
from helpers import normalize_point_cords


def in_arena_bounds(point):
    x = point[0]
    y = point[1]
    return 0 <= x <= 30 and 0 <= y <= 30


def manhattan_distance(point1, point2):
    x1, y1 = point1[0], point1[1]
    x2, y2 = point2[0], point2[1]
    return abs(x1-x2) + abs(y1-y2)


def min_manhattan_distance(point, locations):
    distances = []
    for location in locations:
        distances.append(manhattan_distance(point, location))

    return min(distances)


def get_neighbors(point):
    x, y = point
    return (x+1, y), (x-1, y), (x, y+1), (x, y-1)


def initialize_map(x_count, y_count, initial_value=None):
    new_map = [[initial_value for _ in range(x_count)] for _ in range(y_count)]
    return new_map


def get_path_from_map(arena, start_point, end_points):
    """
    возвращается по локациям с цифрами, игнорируя None
    returns path [next_location, ..., ... territory_location]
    """

    current_location = start_point
    path = []

    while current_location not in end_points:

        best_neighbor = current_location
        for neighbor in get_neighbors(current_location):
            if not in_arena_bounds(neighbor):
                continue

            if arena[neighbor[0]][neighbor[1]] is None:
                continue

            x, y = neighbor
            best_x, best_y = best_neighbor
            if arena[x][y] < arena[best_x][best_y]:
                best_neighbor = (x, y)

        path.append(best_neighbor)
        current_location = best_neighbor

    return path


class MaxMin:
    def __init__(self, cord_seq):
        self.xmin = float('inf')
        self.ymin = float('inf')
        self.xmax = float('-inf')
        self.ymax = float('-inf')

        self.initialize(cord_seq)

    def initialize(self, cord_seq):
        for cords in cord_seq:
            self.update(cords)

    def update(self, point):
        x, y = point
        self.xmin = min(self.xmin, x)
        self.ymin = min(self.ymin, y)
        self.xmax = max(self.xmax, x)
        self.ymax = max(self.ymax, y)

    def is_in_range(self, point):
        """
        updates minmax
        :return: True if point in min_max range
        """
        prev = (self.xmin, self.ymin, self.xmax, self.ymax)
        self.update(point)
        new = (self.xmin, self.ymin, self.xmax, self.ymax)
        return prev == new


class ThreatsMap:
    """
    стартуя от шлейфа ищет ближайшего врага
    если враг не найден(враги отсутствуют на карте), то n_steps_to_enemy = None
    """
    def __init__(self, config, state):
        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']
        self.width = config['width']

        # changes inplace further
        self.visited_points = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['lines']}

        my_position = state['players']['i']['position']
        self.prev_location = normalize_point_cords(my_position, self.width)

        self.my_territory = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['territory']}

        self.enemy_points = set()
        for player_id, player_info in state['players'].items():
            if player_id != 'i':
                x, y = player_info['position']
                self.enemy_points.add(normalize_point_cords((x, y), self.width))

        self.n_steps_to_enemy = None
        self.map = initialize_map(self.x_cells_count, self.y_cells_count)

        self.run_bfs_from_enemies()

    def run_bfs_from_enemies(self):

        queue = deque(self.enemy_points)

        for x, y in self.enemy_points:
            self.map[x][y] = 0

        step_num = 0
        while queue:
            step_num += 1
            if step_num > 5:
                break
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not in_arena_bounds(neighbor):
                        continue

                    x, y = neighbor

                    if self.map[x][y] is None or self.map[x][y] > step_num:
                        self.map[x][y] = step_num
                        queue.append((x, y))

    def is_save_location(self, location, normalize=True):
        if normalize:
            x, y = normalize_point_cords(location, self.width)
        else:
            x, y = location

        if (x, y) in self.my_territory:
            return True

        if self.map[x][y] is not None and self.map[x][y] < 4:
            return False
        return True


class SavesMap:
    """
    инициализирует карту из None, координаты шлейфа(включая текущуюю координату) инициализируется None
    начиная с территории ищет мою текущую координату
    игнорирует локации с цифрами и шлейф (хотя шлейф и так с цифрами)
    все посещённые локации помечаются цифрами (кроме частного случая когда только вышли с территории в end_point)

    """
    def __init__(self, config, state):

        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']
        self.width = config['width']

        # changes inplace further
        self.start_points = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['territory']}
        my_position = state['players']['i']['position']
        self.end_point = normalize_point_cords(my_position, self.width)
        self.lines = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['lines']}

        self.map = initialize_map(self.x_cells_count, self.y_cells_count)

        for point in self.start_points:
            self.map[point[0]][point[1]] = 0

        self.path_to_territory = []
        self.n_steps_to_save = None

    def compute(self):
        """
        creates map of distances from territory to my location
        should be used outside my territory

        """
        queue = deque(self.start_points)

        if self.end_point in self.lines:
            self.lines.remove(self.end_point)

        n_steps = 0
        while queue:
            n_steps += 1

            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not self.is_valid_location(neighbor):
                        continue

                    if self.map[neighbor[0]][neighbor[1]] is not None:
                        continue

                    self.map[neighbor[0]][neighbor[1]] = n_steps

                    if neighbor == self.end_point:
                        # if just leaved territory, then n_steps should be at least 2, so leave this step
                        if len(self.lines) == 0 and n_steps == 1:
                            self.map[neighbor[0]][neighbor[1]] = None
                            continue
                        else:
                            self.n_steps_to_save = n_steps
                            self.lines.add(self.end_point)
                            return

                    queue.append(neighbor)

    def get_shortest_distance_to_territory(self):
        """
        returns None if current location in territory

        """
        return self.n_steps_to_save

    def get_path_to_territory(self):
        """
        возвращается по локациям с цифрами, игнорируя шлейф
        returns path [current_location, ..., ... territory_location]
        """
        if self.n_steps_to_save is None:
            return []

        min_max = MaxMin(self.lines)
        current_location = self.end_point
        path = []

        while current_location not in self.start_points:

            best_neighbor = current_location
            for neighbor in get_neighbors(current_location):
                if not self.is_valid_location(neighbor):
                    continue

                if self.map[neighbor[0]][neighbor[1]] is None:
                    continue

                x, y = neighbor
                best_x, best_y = best_neighbor
                if self.map[x][y] < self.map[best_x][best_y]:
                    best_neighbor = (x, y)
                elif self.map[x][y] == self.map[best_x][best_y] and best_neighbor != current_location:
                    if not min_max.is_in_range(neighbor):
                        best_neighbor = (x,y)

            path.append(best_neighbor)
            current_location = best_neighbor
            min_max.update(best_neighbor)

        return path

    def is_valid_location(self, location):
        return in_arena_bounds(location) and (location not in self.lines)

    def get_distance_from_point_to_territory(self, start_point):
        """
        ищет локацию с цифрой, если такая отсутствует
        """
        x, y = start_point

        if not self.is_valid_location(start_point):
            return None

        if self.map[x][y] is not None:
            return self.map[x][y]

        queue = deque([start_point])
        visited = {start_point}
        n_steps = 0

        while queue:
            n_steps += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not self.is_valid_location(neighbor):
                        continue

                    if neighbor in visited:
                        continue

                    x, y = neighbor[0], neighbor[1]
                    if self.map[x][y] is not None:
                        return n_steps + self.map[x][y]

                    queue.append(neighbor)
                    visited.add(neighbor)

        return None


class AttacksMap:
    def __init__(self, config, state):
        self.state = state
        self.width = config['width']
        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']

        my_position = state['players']['i']['position']
        self.start_point = normalize_point_cords(my_position, self.width)
        self.lines = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['lines']}
        self.territory = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['territory']}

        self.line_cords_to_id = {}
        for player_id, player_info in state['players'].items():
            if player_id != 'i':
                for x, y in player_info['lines']:
                    self.line_cords_to_id[normalize_point_cords((x, y), self.width)] = player_id

        self.enemy_id = None

        self.map = initialize_map(self.x_cells_count, self.y_cells_count)
        self.second_map = initialize_map(self.x_cells_count, self.y_cells_count)

        self.nearest_attack_point = None

        self.n_steps_to_enemy = None
        self.n_steps_for_enemy_save = None

        self.n_steps_from_attack_point = None
        self.path_to_enemy = None
        self.path_from_enemy = None

        self.final_point = None
        self.full_tail = None

        self.n_steps_to_second_enemy = None

    def get_next_location(self):
        #  bfs от меня до ближайшего соперника со шлейфом
        self.compute_my_distance_to_enemy()

        # если нет пути до шлейфа врага(возможно враг находится на базе)
        if self.n_steps_to_enemy is None:
            return

        self.compute_enemy_distance_to_territory()

        if self.n_steps_for_enemy_save is not None:
            # если противник вернётся на базу быстрее чем я проатачу или одновременно с моей атакой
            if self.n_steps_to_enemy >= self.n_steps_for_enemy_save:
                return
            # если у противника короче или такой же шлейф(то лучше не лезть)
            if len(self.lines) >= len(self.state['players'][self.enemy_id]['lines']):
                return

        self.compute_path_to_enemy()

        # если других врагов нет
        if len(self.state['players']) == 2:
            return self.path_to_enemy[0]

        self.run_bfs_from_attack_point()
        self.compute_path_from_enemy()

        # по идее такого быть не может, но всё же
        if not self.path_from_enemy:
            return

        self.full_tail = set(self.path_to_enemy) | set(self.path_from_enemy) | self.lines
        self.compute_distance_to_second_enemy()

        # с учётом шага на свою территорию
        attack_distance = len(self.path_to_enemy) + len(self.path_from_enemy)
        if self.n_steps_to_second_enemy is not None and self.n_steps_to_second_enemy < attack_distance:
            return None

        return self.path_to_enemy[0]

    def compute_my_distance_to_enemy(self):
        """
        start_point - моя позиция
        end_points - локации шлефов врагов
        заполняем карту цифрами (за исключением шлейфа) пока не достигнем ближайшего шлейфа противника
        """
        queue = deque([self.start_point])

        n_steps = 0
        while queue:
            n_steps += 1

            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not self.is_valid_location(neighbor):
                        continue

                    if self.map[neighbor[0]][neighbor[1]] is not None:
                        continue

                    self.map[neighbor[0]][neighbor[1]] = n_steps

                    if neighbor in self.line_cords_to_id:
                        self.n_steps_to_enemy = n_steps
                        self.nearest_attack_point = neighbor
                        return

                    queue.append(neighbor)

    def compute_enemy_distance_to_territory(self):
        """
        считаем расстояние от текущей локации врага до его территории минуя его шлейф

        """
        if self.n_steps_to_enemy is None:
            return None

        enemy_id = self.line_cords_to_id[self.nearest_attack_point]
        self.enemy_id = enemy_id

        start_point = normalize_point_cords(self.state['players'][enemy_id]['position'], self.width)
        end_points = {normalize_point_cords((x, y), self.width) for x, y in self.state['players'][enemy_id]['territory']}
        visited = {normalize_point_cords((x, y), self.width) for x, y in self.state['players'][enemy_id]['lines']}

        if start_point in end_points:
            self.n_steps_for_enemy_save = 0
            return

        queue = deque([start_point])
        n_steps = 0

        while queue:
            n_steps += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if neighbor in visited:
                        continue

                    if not in_arena_bounds(neighbor):
                        continue

                    if neighbor in end_points:
                        self.n_steps_for_enemy_save = n_steps
                        return

                    visited.add(neighbor)
                    queue.append(neighbor)

    def get_distance_to_enemy(self):
        return self.n_steps_to_enemy

    def get_enemy_save_distance(self):
        return self.n_steps_for_enemy_save

    def compute_path_to_enemy(self):
        self.map[self.start_point[0]][self.start_point[1]] = 0
        path_to_enemy = reversed(get_path_from_map(self.map, self.nearest_attack_point,{tuple(self.start_point)}))
        path_to_enemy = list(path_to_enemy)[1:] + [self.nearest_attack_point]
        self.path_to_enemy = path_to_enemy

    def compute_path_from_enemy(self):
        self.second_map[self.nearest_attack_point[0]][self.nearest_attack_point[1]] = 0
        # TODO разобраться почему внутри может быть x,y = None
        path_from_enemy = reversed(get_path_from_map(self.second_map, self.final_point, {self.nearest_attack_point}))
        path_from_enemy = list(path_from_enemy)
        self.path_from_enemy = path_from_enemy

    def run_bfs_from_attack_point(self):
        start_point = self.nearest_attack_point
        invalid_points = set(self.path_to_enemy) | self.lines
        end_points = self.territory

        queue = deque([start_point])
        n_steps = 0
        while queue:
            n_steps += 1

            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if neighbor in invalid_points or not in_arena_bounds(neighbor):
                        continue

                    if self.second_map[neighbor[0]][neighbor[1]] is not None:
                        continue

                    self.second_map[neighbor[0]][neighbor[1]] = n_steps

                    if neighbor in end_points:
                        self.n_steps_from_attack_point = n_steps
                        self.final_point = neighbor
                        return

                    queue.append(neighbor)

    def compute_distance_to_second_enemy(self):

        end_points = set()
        for player_id, player_info in self.state['players'].items():
            if player_id != 'i' and player_id != self.enemy_id:
                x, y = player_info['position']
                end_points.add(normalize_point_cords((x, y), width=self.width))

        queue = deque(self.full_tail)
        visited = self.full_tail
        n_steps = 0
        while queue:
            n_steps += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if neighbor in visited:
                        continue

                    if not in_arena_bounds(neighbor):
                        continue

                    if neighbor in end_points:
                        self.n_steps_to_second_enemy = n_steps
                        return

                    visited.add(neighbor)
                    queue.append(neighbor)

    def is_valid_location(self, location):
        return in_arena_bounds(location) and (location not in self.lines)


class TerritoryMovementsMap:
    """
    нужно вызывать с базы если есть враги
    """
    def __init__(self, config, state, prev_location):
        self.prev_location = prev_location
        self.state = state
        self.width = config['width']
        self.x_cells_count = config['x_cells_count']
        self.y_cells_count = config['y_cells_count']

        self.my_territory = {normalize_point_cords((x, y), self.width) for x, y in state['players']['i']['territory']}
        self.enemy_points = set()
        self.enemy_territory = set()

        my_position = state['players']['i']['position']
        self.curr_pos = normalize_point_cords(my_position, self.width)

        # карта для bfs от вражеской территории до меня и bfs от меня до границ
        self.map = initialize_map(self.x_cells_count, self.y_cells_count)

        for player_id, player_info in state['players'].items():
            if player_id != 'i':
                x, y = player_info['position']
                self.enemy_points.add(normalize_point_cords((x, y), self.width))
                for territory_point in player_info['territory']:
                    x_ter, y_ter = normalize_point_cords(territory_point, self.width)
                    self.map[x_ter][y_ter] = 0
                    self.enemy_territory.add((x_ter, y_ter))

        # карта для поиска ближайшего пути до лучшей точки
        self.second_map = initialize_map(self.x_cells_count, self.y_cells_count)
        self.bordering_points_set = set()
        self.best_point = None
        self.path_to_point = None

    def run_bfs_from_enemy_territory(self):

        queue = deque(self.enemy_territory)

        step_num = 0
        while queue:
            step_num += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not in_arena_bounds(neighbor):
                        continue

                    x, y = neighbor

                    if self.map[x][y] is None or self.map[x][y] > step_num:
                        self.map[x][y] = step_num
                        queue.append((x, y))

    def run_bfs_from_curr_pos(self):
        """
        обходим пока не посетили все точки, граничащие с территорией
        """
        required_count = len(self.bordering_points_set)
        visited_count = 0

        queue = deque([self.curr_pos])
        step_num = 0
        visited = {self.curr_pos}
        while queue:
            step_num += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not in_arena_bounds(neighbor):
                        continue

                    if neighbor == self.prev_location:
                        continue

                    if neighbor in visited:
                        continue

                    x, y = neighbor

                    self.map[x][y] = self.map[x][y] + step_num if self.map[x][y] is not None else step_num

                    if neighbor in self.bordering_points_set:
                        visited_count += 1
                        if visited_count == required_count:
                            return

                    visited.add(neighbor)
                    queue.append(neighbor)

    def find_territory_borders(self):
        locations = self.my_territory

        for point in locations:
            for neighbor in get_neighbors(point):
                if not in_arena_bounds(neighbor):
                    continue

                if neighbor not in self.my_territory:
                    self.bordering_points_set.add(neighbor)

    def find_best_point(self):
        """
        точка, которая прилегает к границе территории и имеет наибольший вес
        """
        locations = self.bordering_points_set

        max_weight = float('-inf')
        best_point = None
        for point in locations:

            distance_to_enemy = min_manhattan_distance(point, self.enemy_points)
            self.map[point[0]][point[1]] = -self.map[point[0]][point[1]] + distance_to_enemy

            if max_weight < self.map[point[0]][point[1]]:
                best_point = point
                max_weight = self.map[point[0]][point[1]]

        self.best_point = best_point

    def run_bfs_to_best_point(self):
        end_point = self.best_point
        queue = deque([self.curr_pos])
        self.second_map[self.curr_pos[0]][self.curr_pos[1]] = 0
        n_steps = 0
        while queue:
            n_steps += 1
            for _ in range(len(queue)):
                point = queue.popleft()

                for neighbor in get_neighbors(point):
                    if not in_arena_bounds(neighbor):
                        continue

                    if neighbor == self.prev_location:
                        continue

                    if self.second_map[neighbor[0]][neighbor[1]] is not None:
                        continue

                    self.second_map[neighbor[0]][neighbor[1]] = n_steps

                    if neighbor == end_point:
                        return

                    queue.append(neighbor)

    def compute_path_to_best_point(self):
        path_to_point = reversed(get_path_from_map(self.second_map, self.best_point, {tuple(self.curr_pos)}))
        path_to_point = list(path_to_point)[1:] + [self.best_point]
        self.path_to_point = path_to_point

    def get_next_point(self):
        # добавляются все соседи моей территории
        self.find_territory_borders()

        # начиная от территории врагов идти с +step_num пока вся карта не заполнится
        self.run_bfs_from_enemy_territory()

        # начиная с моей локации искать граничные локации, заполняя карту +step_num
        # можно заменить манхэтенским расстоянием
        self.run_bfs_from_curr_pos()

        # для каждой граничной локации взять с минусом вес
        # прибавить расстояние до врагов и выбрать точку с максимальным весом
        self.find_best_point()

        # предыдущая локация помечается как None
        if self.best_point != self.prev_location:
            self.run_bfs_to_best_point()
        else:
            return None

        self.compute_path_to_best_point()

        return self.path_to_point[0]
























