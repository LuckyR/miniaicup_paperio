from constants import UP, DOWN, LEFT, RIGHT, opposite_directions
from constants import SIDE_DIRECTIONS


def follow_path(path):
    move = path[0]
    path = path[1:]
    return move, path


def get_side_directions(direction):
    return SIDE_DIRECTIONS[direction]


def get_prev_location(curr_position, prev_move, width, normalize=True):
    if prev_move is None:
        return None

    result = get_next_point(curr_position, opposite_directions[prev_move], width)
    if normalize:
        return normalize_point_cords(result, width)

    return result


def get_next_point(position, move, width):
    x, y = position

    if move == UP:
        return x, y + width

    if move == DOWN:
        return x, y - width

    if move == LEFT:
        return x - width, y

    if move == RIGHT:
        return x + width, y


def normalize_point_cords(point, width):
    return int(point[0] / width), int(point[1] / width)


def path_to_commands(path, curr_position, width):
    prev_point = normalize_point_cords(curr_position, width)
    commands = []
    for point in path:
        commands.append(get_command_from_points(prev_point, point))
        prev_point = point

    return commands


def get_command_from_points(prev_point, point):
    if point[0] == prev_point[0] + 1:
        return RIGHT
    elif point[0] == prev_point[0] - 1:
        return LEFT
    elif point[1] == prev_point[1] + 1:
        return UP
    else:
        return DOWN


