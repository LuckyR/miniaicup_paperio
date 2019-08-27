from algo import Bot
import json

bot = Bot()

while True:
    try:
        state = json.loads(input())
    except EOFError:
        break

    if state['type'] == 'start_game':
        bot.on_game_start(state['params'])
    elif state['type'] == 'tick':
        bot.on_tick(state['params'])
    elif state['type'] == 'end_game':
        break

