import os
import time
import re
import glob
from random import randint, choice
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename


REMOVE_TMP_FILES = True
API_ID = "0x52837abc348d3f8252826abde426262324"
THRESHOLD_GRAY = 9  # % for convert captcha to transparent png without shadows

"""
tests for different threshold:
6 -> time 3.4 sec ; percent 47.8% ; 33/69 ; больше подставки под фигурами, больше циклов get_area
7 -> time 2.7 sec ; percent 44.9% ; 31/69 ;
8 -> time 2.7 sec ; percent 44.9% ; 31/69 ;
9 -> time 2.65 sec; percent 49%   ; 34/69 ; 9 < ----- лучший процент + минимальное время разгадывания
10-> time 2.7 sec ; percent 47.8% ; 33/69 ; с 10 и выше начинаются артефакты типа фигуры с пиксель-дырками
"""


all_areas = []
def dump_rects():
    """ сдампить координаты прямоугольников областей/букв """
    with open("rects.txt", "w") as f:
        f.write("\n".join([str(i) for i in all_areas]))
        f.close()


def get_pxls(fname='cap.png', filtered=1):
    im = Image.open(fname)
    pixels = list(im.getdata())
    width, height = im.size
    pxls = [pixels[i * width:(i + 1) * width] for i in range(height)]
    for y in range(height):
        for x in range(width):
            if not isinstance(pxls[y][x], tuple) or len(pxls[y][x]) < 4:
                #print("ERROR PXLS {}, {}: {}".format(x, y, pxls[y][x]))
                pass
            if isinstance(pxls[y][x], int):
                pxls[y][x] = (250, 250, 250, 0)

    if filtered:
        for y in range(height-4):
            for x in range(width-4):
                if pxls[y][x][3] != 0 and pxls[y][x+1][3] == 0 and pxls[y][x+2][3] != 0:
                    pxls[y][x+1] = (200, 200, 200, 255)
                if pxls[y][x][3] != 0 and pxls[y][x+1][3] == 0 and\
                   pxls[y][x+2][3] == 0 and pxls[y][x+3][3] != 0:
                    pxls[y][x+1] = (200, 200, 200, 255)
                    pxls[y][x+2] = (200, 200, 200, 255)

                if pxls[y][x][3] != 0 and pxls[y+1][x][3] == 0 and pxls[y+2][x][3] != 0:
                    pxls[y+1][x] = (200, 200, 200, 255)
                if pxls[y][x][3] != 0 and pxls[y+1][x][3] == 0 and\
                   pxls[y+2][x][3] == 0 and pxls[y+3][x][3] != 0:
                    pxls[y+1][x] = (200, 200, 200, 255)
                    pxls[y+2][x] = (200, 200, 200, 255)

    return pxls


def img_print(xmin=205, ymin=35, xmax=250, ymax=100, fname='cap.png'):
    im = Image.open(fname)
    pixels = list(im.getdata())
    width, height = im.size
    pxls = [pixels[i * width:(i + 1) * width] for i in range(height)]
    for y in range(height):
        res = ""
        for x in range(width):
            if xmin<x<xmax and ymin<y<ymax:
                if pxls[y][x][3] != 0:
                    res += "X"
                else:
                    res += " "
        if ymin<y<ymax:
            print(res)


def crop_resize(rect, w, h, fname='cap.png'):
    orig_w, orig_h = rect[2] - rect[0], rect[3] - rect[1]
    outfile = "./tmp/{}_{}.png".format(time.time(), randint(1000,9999))
    # convert cap file -crop 34x54+212+40 -resize 100x100 -gravity Center tmp.png
    cmd = "convert {} -crop {}x{}+{}+{} -resize {}x{} -gravity Center {}".format(
        fname, orig_w, orig_h, rect[0], rect[1], w, h, outfile)
    print("CROP RESIZE ", cmd)
    os.system(cmd)
    time.sleep(0.1)
    px = get_pxls(outfile)
    REMOVE_TMP_FILES and os.system("rm {}".format(outfile))
    return px


def alike_perc_paired(rect1, rect2, alikes=None, pxls=None, fname=None):
    w1, h1 = rect1[2] - rect1[0], rect1[3] - rect1[1]
    w2, h2 = rect2[2] - rect2[0], rect2[3] - rect2[1]
    r1 = {w1: 1, h1: 1}
    r2 = {w2: 1, h2: 1}
    max_side = max(w1, h1, w2, h2)
    pxls = pxls or get_pxls(fname)
    # rect in main image, resize other
    rect_main = rect1 if max_side in r1 else rect2
    rect_resize = rect1 if rect_main == rect2 else rect2
    px2 = crop_resize(rect_resize, max_side, max_side, fname=fname)
    xbase, ybase = rect_main[0], rect_main[1]
    total_pix = min(h1, h2) * min(w1, w2)
    if alikes:
        total_pix = (sum(alikes) / 2) * total_pix
    white_pix = 0
    for y in range(min(h1, h2)):
        for x in range(min(w1, w2)):
            if px2[y][x][3] != 0 and pxls[ybase+y][xbase+x][3] != 0:
                white_pix += 1
    return white_pix / total_pix


def alike_perc(rect, pxls=None):
    """ определение коэф заполненности в monochrome области/фигуре капчи """
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    total_pix = w * h
    white_pix = 0
    pxls = pxls or get_pxls()
    for y in range(rect[1], rect[3]+1):
        for x in range(rect[0], rect[2]+1):
            if pxls[y][x][3] != 0:
                white_pix += 1
    res = white_pix/total_pix
    print("PERC ", res)
    return res


def alike_rects(frect='./rects.txt', fname='cap.png', pxls=None, rects=None):
    rs = rects or []
    alike = []
    if not rs:
        with open(frect) as f:
            lines = f.read().split("\n")
            for l in lines:
                rect_cur = [int(i) for i in l[1:-1].split(",")]
                #if is_doubled_rect(rect_cur, rs):
                rs.append(rect_cur)

    for r in rs:
        alike_wh = (r[2] - r[0]) / (r[3] - r[1])
        alike.append((alike_wh, alike_perc(r, pxls=pxls)))
    print(rs)
    print(alike)

    pairs = []
    for i in range(len(alike)-1):
        for k in range(i+1, len(alike)):
            d1 = abs(alike[i][0] - alike[k][0])  # by W/H alike
            d2 = abs(alike[i][1] - alike[k][1])  # by pixel percent
            pairs.append([(i, k), d1*d2, d1+d2, d2])
    top3 = set()
    sorted_d1 = sorted(pairs, key=lambda s: s[1])[:3]
    sorted_d2 = sorted(pairs, key=lambda s: s[2])[:3]
    for pr in sorted_d1 + sorted_d2:
        top3.add(pr[0])
    pairs_app = []
    for pr in top3:
        app = alike_perc_paired(rs[pr[0]], rs[pr[1]],
            alikes=[alike[pr[0]][1], alike[pr[1]][1]], pxls=pxls, fname=fname)
        print(pr, app)
        pairs_app.append((pr, app))
    sorted_app = sorted(pairs_app, key=lambda s: s[1], reverse=True)[:1]
    print(sorted_app)
    result_pair = sorted_app[0][0]

    solved_path = "./solved/solved_{}.png".format(time.time())
    cmd = """convert {} -fill none -stroke red -strokewidth 3 -draw 'rectangle {} {} {} {}' \\
        -draw 'rectangle {} {} {} {}' {}""".format(
            fname, *rs[result_pair[0]], *rs[result_pair[1]], solved_path)
    print(cmd)
    os.system(cmd)

    return [rs[result_pair[0]], rs[result_pair[1]]], solved_path


def img(fname='cap.png'):
    im = Image.open(fname)
    pixels = list(im.getdata())
    width, height = im.size
    pxls = get_pxls(fname)  # [pixels[i * width:(i + 1) * width] for i in range(height)]

    for y in range(height):
        for x in range(width):
            if pxls[y][x][3] != 0 and not in_area(pxls, x, y, all_areas):
                #print(x, y)
                try:
                    res = get_area(pxls, x-1, y)
                except Exception as e:
                    #print(e)
                    pass
                # if len(res) < 10:
                #     continue
                #print(res)
            if len(all_areas) > 10:
                return pxls, all_areas
    return pxls, all_areas


def in_area(pxls, x, y, all_areas):
    for rect in all_areas:
        if x >= rect[0] and x <= rect[2] and y >= rect[1] and y <= rect[3]:
            return True
    return False


def get_area(pxls, x, y):
    """ 
    определение пиксельной границы замкнутой фигуры (буква капчи)
    если зациклился в пикселях - выходим, фейл распознавания границы
    """
    area = set()
    area.add((x, y))
    x_start, y_start = x, y
    xc, yc = 0, 0

    total = 0
    delta_window = 1
    N = 0
    while total < 3000:
        if (abs(xc - x_start) <= 3 and abs(yc - y_start) <= 3) and total > 100:
            print("FINISHED {} {} total".format(xc, yc, total))
            break
        if xc * yc == 0:
            xc, yc = x, y
        #print("---C", xc, yc)

        try:
            for y_d in range(yc-delta_window, yc+delta_window+1):
                for x_d in range(xc-delta_window, xc+delta_window+1):
                    if pxls[y_d][x_d][3] != 0 and (x_d, y_d) not in area and has_neighbor(pxls, x_d, y_d):
                        #print("add", x_d, y_d)
                        area.add((x_d, y_d))
                        xc, yc = x_d, y_d
                        #print("---C2", xc, yc)
                        N = 0
                        total += 1
                        raise ValueError("next")

                    N += 1
                    if N > 30:
                        # print("N ", N)
                        raise Exception("Infinite Loop on ({}, {})".format(x_d, y_d))
        except ValueError:
            pass

    x_min, y_min = min([i[0] for i in area])-1, min([i[1] for i in area])-1
    x_max, y_max = max([i[0] for i in area])+1, max([i[1] for i in area])+1
    if is_doubled_rect([x_min, y_min, x_max, y_max], all_areas):
        print("DOUBLE AREA ({}, {}) - ({}, {}) total {}".format(x_min, y_min, x_max, y_max, total))
        return None
    else:
        print("AREA rect: ({}, {}) - ({}, {}) total {}".format(x_min, y_min, x_max, y_max, total))
        all_areas.append([x_min, y_min, x_max, y_max])
        dump_rects()
        return area


def is_doubled_rect(rect1, areas):
    for rect2 in areas:
        is_doubled = True
        for i in range(4):
            is_doubled = is_doubled and abs(rect2[i] - rect1[i]) <= 2
        if is_doubled:
            return is_doubled
    return False


def has_neighbor(pxls, x, y):
    res = False
    for y_d in range(y-1, y+2):
        for x_d in range(x-1, x+2):
            if not(y_d == y and x_d == x) and pxls[y_d][x_d][3] == 0:
                return True
    return False


def mass_test():
    global all_areas
    times = []
    os.system("rm ./solved/*")
    for f in glob.glob("tiktok_cap/*.jpg"):
        all_areas = []
        print(f)
        start = time.time()
        cmd = """convert {} \( +clone -colorspace HCL -channel G -separate +channel -threshold {}% \) -alpha off -compose CopyOpacity -composite {}"""
        cmd = cmd.format(f, THRESHOLD_GRAY, "./cap.png")
        print(cmd)
        os.system(cmd)
        time.sleep(0.1)
        img()
        alike_rects()
        times.append(time.time() - start - 0.1)

    print("AVERAGE SOLVE TIME {}".format(sum(times)/len(times)))


app = Flask(__name__, static_url_path='')
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.config['UPLOAD_FOLDER'] = uploads_dir
app.config['MAX_CONTENT_LENGTH'] = 1.5 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def solve_captcha(fname):
    global all_areas
    all_areas = []
    start = time.time()
    cmd = """convert {} \( +clone -colorspace HCL -channel G -separate +channel -threshold {}% \) -alpha off -compose CopyOpacity -composite {}"""
    cap_file = "./tmp/cap_{}_{}.png".format(time.time(), randint(1000, 9999))
    cmd = cmd.format(fname, THRESHOLD_GRAY, cap_file)
    print(cmd)
    os.system(cmd)
    time.sleep(0.1)
    pxls, rects = img(cap_file)
    print("CAP FILE ", cap_file)
    print(rects, all_areas)
    solved, uri = alike_rects(cap_file, pxls=pxls, rects=rects, fname=cap_file)
    timed = time.time() - start
    REMOVE_TMP_FILES and os.system("rm {}".format(cap_file))
    return solved, timed, uri


# TODO print -> logging
# TODO move cap tasks to separate queue, multitask - NOT WORKING on RPS5.sh (5 req/seq)
# TODO1 refactoring: move to lib, logging, gunicorn deploy
# TODO2 add DB for users, tasks, API keys, img paths, area rectangles/bound pixels
# TODO3 rucaptcha API
# TODO4 auth, balance (via shop?)
# TODO5 API call for bad cap reports (dont' charge money)
# TODO6 quality control (percent of bads from user VS system avg bads)


@app.route('/solve', methods = ['POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        api_id = (request.values.get('api_id', ''))
        if api_id != API_ID:
            return jsonify({"result": "error", "message": "not authed"})

        fname = secure_filename(f.filename)
        res, timed = [], 0
        if f and allowed_file(fname):
            ff, ext = re.findall(r"^(.*)(\.[^\.]+)$", fname)[0]
            fname = "{}_{}_{}{}".format(ff, time.time(), randint(1000, 9999), ext)
            fpath = os.path.join(uploads_dir, fname)
            f.save(fpath)
            res, timed, uri = solve_captcha(fpath)

        return jsonify({"result": "ok", "res": res, "timed": timed, "uri": uri[1:]})


@app.route('/solved/<path:filename>')
def send_js(filename):
    print(filename)
    return send_from_directory('solved', filename)


if __name__ == "__main__":
    #mass_test()

    app.run(debug=True, host="0.0.0.0", port=18757)

