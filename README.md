# Mini AI Cup #4 , 22 место
https://aicups.ru/solution/21977/

## Общее описание логики

Бот может находиться в 2х состояниях: 
- на своей территории 
- вне своей территории

Находясь на своей территории, бот пытается покинуть территорию в той локации, которая:
- находится близко ко вражеской территории
- удалена от текущих позиций противников
- находится ближе всего к текущему положению бота  

Алгоритм реализован в классе TerritoryMovementsMap

Находясь вне своей территории бот перебирает все безопасные маршруты до базы и выбирает тот, 
который приносит наибольшее число очков.
Проверяются только маршруты, которые включают не больше 3х поворотов
Алгоритм реализован в классе RoutesMaker

Вне зависимости от текущего состояния бот пытется атаковать противника, если это можно безопасно сделать.

## Недоработки
При поиске пути до своей территории не учитывается сценарий, при котором противник закрашивает территорию 
бота, до которой бот выстроил маршрут. В таких ситуациях чаще всего бот оказывался в безвыходном положении и 
не успевал вернуться на базу. Это происходило почти во всех матчах, где бот занимал 5-6 места.

При расчёте локации для выхода с территории учитывается только близость вражеской территории,
но не учитывается как много клеток находится в окрестности. В итоге бот может проделать длинный путь через
свою территорию для того чтобы дозахватить всего лишь 1 вражескую клетку.

Время расчёта одного хода у бота составляло 10-60 мс, что являлось малой частью от доступного времени.
Таким образом скорее всего можно было добавить логики для расчёта очков на 2 закраски вперёд, 
не боясь при этом выйти за лимиты времени.