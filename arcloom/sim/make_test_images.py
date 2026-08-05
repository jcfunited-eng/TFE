#!/usr/bin/env python3
"""
Generate realistic test images for vision simulation.
Not geometric primitives — objects with texture, irregular outlines, shading.
"""

import numpy as np
from PIL import Image, ImageDraw

def make_teddy_bear(size=128):
    """Brown teddy bear — irregular outline, fur texture, ears, body."""
    img = Image.new('RGB', (size, size), (220, 215, 210))  # off-white background
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2 + 5

    # Body (oval, not circle)
    body_color = (139, 90, 43)
    draw.ellipse([cx-22, cy-18, cx+22, cy+25], fill=body_color)

    # Head (smaller circle on top)
    head_y = cy - 25
    draw.ellipse([cx-16, head_y-16, cx+16, head_y+16], fill=body_color)

    # Ears
    draw.ellipse([cx-22, head_y-22, cx-10, head_y-10], fill=body_color)
    draw.ellipse([cx+10, head_y-22, cx+22, head_y-10], fill=body_color)
    # Inner ears (lighter)
    draw.ellipse([cx-19, head_y-19, cx-13, head_y-13], fill=(170, 120, 70))
    draw.ellipse([cx+13, head_y-19, cx+19, head_y-13], fill=(170, 120, 70))

    # Eyes
    draw.ellipse([cx-8, head_y-5, cx-4, head_y-1], fill=(20, 20, 20))
    draw.ellipse([cx+4, head_y-5, cx+8, head_y-1], fill=(20, 20, 20))

    # Nose
    draw.ellipse([cx-3, head_y+3, cx+3, head_y+7], fill=(40, 30, 20))

    # Arms (short ovals)
    draw.ellipse([cx-30, cy-5, cx-20, cy+12], fill=body_color)
    draw.ellipse([cx+20, cy-5, cx+30, cy+12], fill=body_color)

    # Legs
    draw.ellipse([cx-18, cy+18, cx-6, cy+32], fill=body_color)
    draw.ellipse([cx+6, cy+18, cx+18, cy+32], fill=body_color)

    # Belly patch (lighter)
    draw.ellipse([cx-10, cy-5, cx+10, cy+15], fill=(180, 140, 90))

    # Add fur texture noise
    arr = np.array(img)
    fur_noise = np.random.randint(-8, 9, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + fur_noise, 0, 255).astype(np.uint8)

    return arr


def make_red_cup(size=128):
    """Red coffee cup — rectangular body, handle, smooth surface."""
    img = Image.new('RGB', (size, size), (220, 215, 210))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    cup_color = (200, 35, 30)

    # Cup body (trapezoid - wider at top)
    points = [(cx-18, cy-22), (cx+18, cy-22), (cx+15, cy+22), (cx-15, cy+22)]
    draw.polygon(points, fill=cup_color)

    # Rim (lighter red at top)
    draw.rectangle([cx-18, cy-22, cx+18, cy-18], fill=(220, 60, 50))

    # Handle (arc on right side)
    draw.arc([cx+14, cy-12, cx+30, cy+12], 270, 90, fill=cup_color, width=3)

    # Slight shadow/shading on left side
    for x in range(cx-18, cx-12):
        for y in range(cy-22, cy+22):
            if 0 <= x < size and 0 <= y < size:
                r, g, b = img.getpixel((x, y))
                if (r, g, b) == cup_color:
                    img.putpixel((x, y), (180, 25, 25))

    # Smooth surface - minimal noise
    arr = np.array(img)
    noise = np.random.randint(-2, 3, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return arr


def make_white_bunny(size=128):
    """White stuffed bunny — long ears, round body, pink inner ears."""
    img = Image.new('RGB', (size, size), (220, 215, 210))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2 + 5

    bunny_color = (245, 242, 238)

    # Body
    draw.ellipse([cx-20, cy-10, cx+20, cy+25], fill=bunny_color)

    # Head
    head_y = cy - 20
    draw.ellipse([cx-14, head_y-12, cx+14, head_y+12], fill=bunny_color)

    # Long ears (tall ovals)
    draw.ellipse([cx-12, head_y-38, cx-4, head_y-8], fill=bunny_color)
    draw.ellipse([cx+4, head_y-38, cx+12, head_y-8], fill=bunny_color)
    # Pink inner ears
    draw.ellipse([cx-10, head_y-34, cx-6, head_y-12], fill=(240, 180, 180))
    draw.ellipse([cx+6, head_y-34, cx+10, head_y-12], fill=(240, 180, 180))

    # Eyes (pink/red)
    draw.ellipse([cx-7, head_y-3, cx-3, head_y+1], fill=(180, 50, 50))
    draw.ellipse([cx+3, head_y-3, cx+7, head_y+1], fill=(180, 50, 50))

    # Nose (pink)
    draw.ellipse([cx-2, head_y+4, cx+2, head_y+7], fill=(240, 150, 150))

    # Paws
    draw.ellipse([cx-25, cy+2, cx-18, cy+14], fill=bunny_color)
    draw.ellipse([cx+18, cy+2, cx+25, cy+14], fill=bunny_color)

    # Feet
    draw.ellipse([cx-16, cy+20, cx-4, cy+30], fill=bunny_color)
    draw.ellipse([cx+4, cy+20, cx+16, cy+30], fill=bunny_color)

    # Tail (small circle on back)
    draw.ellipse([cx-5, cy+22, cx+5, cy+28], fill=(250, 248, 245))

    # Soft fur texture
    arr = np.array(img)
    fur_noise = np.random.randint(-4, 5, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + fur_noise, 0, 255).astype(np.uint8)

    return arr


def make_blue_ball(size=128):
    """Blue rubber ball — smooth, circular, shiny highlight."""
    img = Image.new('RGB', (size, size), (220, 215, 210))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2
    r = 25

    # Ball body
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(30, 60, 200))

    # Gradient shading (darker at bottom-right)
    arr = np.array(img)
    for y in range(cy-r, cy+r+1):
        for x in range(cx-r, cx+r+1):
            dx, dy = x-cx, y-cy
            if dx*dx + dy*dy < r*r:
                # Shading: lighter top-left, darker bottom-right
                shade = 0.7 + 0.3 * (-dx - dy) / (2*r)
                shade = max(0.4, min(1.2, shade))
                arr[y, x, 0] = min(255, int(30 * shade))
                arr[y, x, 1] = min(255, int(60 * shade))
                arr[y, x, 2] = min(255, int(200 * shade))

    # Highlight spot (top-left)
    for y in range(cy-r//2-3, cy-r//2+3):
        for x in range(cx-r//2-3, cx-r//2+3):
            dx, dy = x-(cx-r//3), y-(cy-r//3)
            if dx*dx + dy*dy < 9 and 0 <= x < size and 0 <= y < size:
                arr[y, x] = [200, 210, 255]

    noise = np.random.randint(-2, 3, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return arr


def make_green_book(size=128):
    """Green hardcover book — rectangular, spine detail, text lines."""
    img = Image.new('RGB', (size, size), (220, 215, 210))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    # Book cover
    draw.rectangle([cx-22, cy-28, cx+22, cy+28], fill=(30, 120, 45))

    # Spine (darker green on left)
    draw.rectangle([cx-22, cy-28, cx-18, cy+28], fill=(20, 80, 30))

    # Title area (lighter rectangle)
    draw.rectangle([cx-14, cy-20, cx+18, cy-10], fill=(40, 140, 55))

    # Text lines (dark marks)
    for ly in range(cy-18, cy-12, 3):
        draw.line([(cx-12, ly), (cx+16, ly)], fill=(20, 60, 25), width=1)

    # Author area
    draw.rectangle([cx-14, cy+14, cx+18, cy+20], fill=(40, 140, 55))
    draw.line([(cx-10, cy+17), (cx+14, cy+17)], fill=(20, 60, 25), width=1)

    arr = np.array(img)
    noise = np.random.randint(-3, 4, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return arr


if __name__ == '__main__':
    import os
    out_dir = 'arcloom/sim/test_images'
    os.makedirs(out_dir, exist_ok=True)

    images = {
        'teddy_bear': make_teddy_bear(),
        'red_cup': make_red_cup(),
        'white_bunny': make_white_bunny(),
        'blue_ball': make_blue_ball(),
        'green_book': make_green_book(),
    }

    for name, arr in images.items():
        Image.fromarray(arr).save(f'{out_dir}/{name}.png')
        print(f"Saved {name}.png ({arr.shape})")

    print(f"\nAll images saved to {out_dir}/")
