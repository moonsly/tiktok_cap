# cap solver

MVP API для решения капчи Тиктока, актуальной на 2020 год. 

Пробив около 30-40%, без использования ML/AI/opencv/тяжелых вычислений.

Примеры капч на тот момент - в папке ./tiktok_cap 
![captcha example](https://raw.githubusercontent.com/moonsly/tiktok_cap_cv/main/cap.png)

Смысл в том, что несколько 3D-фигур с буквами/цифрами раскиданы по картинке, с небольшими вариантами (типа изменен поворот, цвет, освещение итд). Для решения капчи - пользователю нужно отметить мышкой 2 одинаковых фигурки (т.е. определить их области - 2 ограничивающих прямоугольника с координатами).

Для решения капчи используется такой алгоритм:
1) определяем области фигурок, методом обхода их границ (пока не вернемся в 1ю встреченную точку границы фигуры)
2) по каждой границе считаем ограничивающий прямоугольник, вырезаем для сравнения, считаем соотношения width/height, а также процент заполнения фигуры (переводим в монохром, считаем сколько % заполнено в прямоугольнике)
3) сортирует фигуры по width/height, отдельно по % заполнения
4) сравниваем ближайшие в отсортированных, дополнительно делаем попарное сравнение этих фигур - ресайзим меньшую до максимальной фигуры, смотрим какой % точек перекрывается
5) если в какой-то паре сходство выше threshold - помечаем эту пару как решение
6) на картинке-решении обводим одинаковые фигуры, возвращаем путь к картинке-решению (для визуального контроля на тестах пробива), возвращаем их координаты в JSON как ответ на капчу 

# Tests

По результатам тестирования на капчах из tiktok_cap - пробив был около 30-40%, время разгадывания 1й капчи в пределах 5-7 секунд (на слабой машине).

# TODO

Были планы докрутить и попробовать продать это как Antigate API, но только для арбитражников Тиктока (прикрутить платежный шлюз, ЛК, вынести задачи в очередь итд), но остались только в TODO.

1) TODO print -> logging
2) TODO move cap tasks to separate queue, multitask - NOT WORKING on RPS5.sh (5 req/seq)
3) TODO refactoring: move to lib, logging, gunicorn deploy
4) TODO add DB for users, tasks, API keys, img paths, area rectangles/bound pixels
5) TODO rucaptcha API for rechecking/testing/improving detect algorithm
6) TODO auth, balance (via shop?)
7) TODO API call for bad cap reports (dont' charge money)
8) TODO quality control (percent of bads from user VS system avg bads)

# запуск АПИ

python ./solve.py

mandatory param - api_id

# curl example 

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap3.jpg' -F "api_id=123" http://127.0.0.1:18757/solve 

{
  "res": [
    [
      74, 8, 126, 98
    ], 
    [
      179, 69, 230, 158
    ]
  ], 
  "result": "ok", 
  "timed": 4.483027935028076, 
  "uri": "/solved/solved_1601466994.3333046.png"
}

# autotests

cp ./caps_test/* ./

bash ./TEST_CAP5.sh
