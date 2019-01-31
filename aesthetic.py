#!/usr/bin/env python3

import sys, argparse, random, re, multiprocessing, time, timeit

from PIL import Image, ImageDraw, ImageFont
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('outfile')
parser.add_argument("-t", "--text", help="[x,y]glorious[x, y]text")
parser.add_argument("-s", "--text-size", help="size for text", type=int, default=50)
args = parser.parse_args()

class PrintTimer:
    def __init__(self, text, count=0):
        self.text, self.count = text, count

    def __enter__(self):
        self.start = timeit.default_timer()
        return self

    def __exit__(self, type, value, traceback):
        unit, elapsed = "s", timeit.default_timer()-self.start
        if elapsed<1:
            unit, elapsed = "ms", elapsed*1000
        if not type:
            print("{:15} {}/{} {:3}{:>2}".format(self.text, self.count, self.count, int(elapsed), unit))
        return False

def render_text(draw, x, y, font, text, newline=1, size=52, foreground=(255,255,255), background=(0,0,0)):
    cell_width, cell_height = font.getsize("█")

    x, y = x*cell_width, y*cell_height
    x_ofs, y_ofs = cell_width, cell_height

    cx, cy = x, y
    cf, cb = foreground, background

    prev_char = ""
    for char in text:
        # This is more or less how Minecraft does colours. Make of this what you will.
        if prev_char in ["§"]:
            cf = {"r": foreground, "c": (51, 69, 129), "9": (190, 30, 45)}[char]
            prev_char = char
            continue

        prev_char = char

        # Nondisplayable characters
        if char in ["§", "\r"]:
            continue
        # Null termination, for no particularly good reason
        if char in ["\0"]:
            break

        # Linebreak
        if char=="\n":
            cf = foreground
            # LTR horizontal
            if newline == 1:
                cx = x
                cy += y_ofs
            # RTL vertical
            elif newline == 2:
                cx -= x_ofs
                cy = y
            continue

        # Render background if we have one
        if cb:
            draw.rectangle((cx, cy, cx+x_ofs, cy+y_ofs), fill=cb)

        # Render char
        draw.text((cx, cy), char, font=font, fill=cf)

        # Set correct position for next char draw
        if newline in [1, 0]:
            cx += x_ofs
        elif newline == 2:
            cy += y_ofs

def convert_in_np(rgb_list):
    with PrintTimer("NP RGB->YUV", len(rgb_list)):
        m = np.array([[ 0.29900, -0.16874,  0.50000],
            [0.58700, -0.33126, -0.41869],
            [0.11400, 0.50000, -0.08131]])
        yuv_list = np.dot(rgb_list, m)
        yuv_list[:,1:]+=128.0
        yuv_list = yuv_list.astype(int)
    return yuv_list

def convert_out_np(yuv_list):
    with PrintTimer("NP YUV->RGB", len(yuv_list)):
        m = np.array([[ 1.0, 1.0, 1.0],
            [-0.000007154783816076815, -0.3441331386566162, 1.7720025777816772],
            [1.4019975662231445, -0.7141380310058594 , 0.00001542569043522235] ])
        rgb_list = np.dot(yuv_list, m)
        rgb_list[:,0]-=179.45477266423404
        rgb_list[:,1]+=135.45870971679688
        rgb_list[:,2]-=226.8183044444304
        rgb_list = rgb_list.astype(int)
    return rgb_list

def interfere_np(yuv_list):
    with PrintTimer("NP Static", len(yuv_list)):
        out = np.concatenate([yuv_list[:,:1]+np.random.randint(-7,8), yuv_list[:,1:]+np.random.randint(-10,11)], axis=1)
    return out

with PrintTimer("PI load") as pt:
    image = Image.open(args.file)
    image = image.convert("RGB")
    pt.count = len(image.getdata())

LUMINANCE_GHOST_WIDTH = round(image.width/150)
CHROMA_GHOST_WIDTH = 15

ll = image.width

if args.text:
    print("Applying dramatic slogans")
    pattern = re.compile(r"(\[(?:[+-]|0?\.)?\d+,\s?(?:[+-]|0?\.)?\d+\]|[^\[]+)")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", args.text_size)
    cx, cy = 0,0
    for token in pattern.findall(args.text):
        if token.startswith("["):
            if "," in token:
                split_token = token[1:-1].replace(" ", '').split(",")
                new_coords = []
                resolution_cells = [int(a/b) for a,b in zip(image.size, font.getsize("█"))]
                for original, update, resolution in zip([cx,cy], split_token, resolution_cells):
                    if update[0] in "+-":
                        new_coords.append(original+int(update))
                    elif "." in update:
                        new_coords.append(round(resolution*float(update)))
                    else:
                        new_coords.append(int(update))
                cx, cy = new_coords
        else:
            render_text(draw, cx, cy, font, token, newline=1)

total_length = len(image.getdata())

with PrintTimer("NP Array in", total_length):
    data = np.array(image.getdata())
with PrintTimer("NP Array copy", total_length):
    old_data = np.copy(data)

data = interfere_np(convert_in_np(data))
old_data = interfere_np(convert_in_np(old_data))

# Let's assume that the chroma carrier is larger than it really ought to be.
# We're looking further into it, so everything's shifted up - this gives us the cute purple aesthetic!
with PrintTimer("NP Chroma shift", total_length):
    data[:,1:]+np.random.randint(15,17)

# Dropping the luma by a fixed amount is a fairly lazy way to avoid ghost saturation
with PrintTimer("NP Luma floor", total_length):
    data[:,:1]-=40

start = time.time()

ghost_offset = 0
for i, (y,u,v) in enumerate(data):
    crosstalk_c, crosstalk_l = 0, 0

    # Artificially lower definition by reusing base pixels
    if i%ll > 1 and random.randrange(-2, 3)==1:
        # Have to replicate the floor, otherwise the result is overbright static
        y = old_data[i-1][0]-40
        u = old_data[i-1][1]
        v = old_data[i-1][2]

    # Oh no, the colour is slightly out of alignment!
    if i > 2:
        u = old_data[i-2][1]
        v = old_data[i-1][2]

    # Arbitrary number to recalculate ghost offset at - otherwise it looks too uniform
    if not i%70:
        ghost_offset = (ghost_offset+random.randrange(-1, 2))%3 #3

    # I ain't afraid of no ghosts
    if i%ll > LUMINANCE_GHOST_WIDTH:
        y += old_data[(i-LUMINANCE_GHOST_WIDTH)+ghost_offset][0]>>1
    else:
        # If we don't do this, there's a visible margin, which looks kinda bad
        y += old_data[i][0]>>1

    data[i] = (y, u, v)

    if not i%100:
        sys.stdout.write("\rIL Luma ghost   {}/{} {:3} s".format(i+1, total_length, int(time.time()-start)))
        sys.stdout.flush()

print("\rIL Ghost        {}/{} {:3} s".format(total_length, total_length, int(time.time()-start)))

with PrintTimer("NP Clip", total_length):
    # Overflow? In your program? It's more likely than you think
    data = data.clip(0,255)

data = convert_out_np(data)
with PrintTimer("IL Array out", total_length):
    image.putdata([tuple(x) for x in data])

with PrintTimer("PI save", total_length):
    image = image.convert("RGB")
    image.save(args.outfile)
