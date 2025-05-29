# borrowed from https://github.com/TencentARC/MotionCtrl/blob/main/app.py

import argparse
import gc
import os
import tempfile
import threading
import time

import cv2
import gradio as gr
import imageio
import numpy as np
import torch


tempfile_dir = "/tmp/Tora"
os.makedirs(tempfile_dir, exist_ok=True)
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
SPACE_ID = os.environ.get("SPACE_ID", "")


#### Description ####
title = r"""<h1 align="center">Tora: Trajectory-oriented Diffusion Transformer for Video Generation</h1>"""

description = r""""""
article = r"""
---

📝 **Citation**
<br>
```bibtex
@misc{zhang2024toratrajectoryorienteddiffusiontransformer,
      title={Tora: Trajectory-oriented Diffusion Transformer for Video Generation},
      author={Zhenghao Zhang and Junchao Liao and Menghao Li and Zuozhuo Dai and Bingxue Qiu and Siyu Zhu and Long Qin and Weizhi Wang},
      year={2024},
      eprint={2407.21705},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2407.21705},
}
```
"""
css = """
.gradio-container {width: 85% !important}
.gr-monochrome-group {border-radius: 5px !important; border: revert-layer !important; border-width: 2px !important; color: black !important;}
span.svelte-s1r2yt {font-size: 17px !important; font-weight: bold !important; color: #d30f2f !important;}
button {border-radius: 8px !important;}
.add_button {background-color: #4CAF50 !important;}
.remove_button {background-color: #f44336 !important;}
.clear_button {background-color: gray !important;}
.mask_button_group {gap: 10px !important;}
.video {height: 300px !important;}
.image {height: 300px !important;}
.video .wrap.svelte-lcpz3o {display: flex !important; align-items: center !important; justify-content: center !important;}
.video .wrap.svelte-lcpz3o > :first-child {height: 100% !important;}
.margin_center {width: 50% !important; margin: auto !important;}
.jc_center {justify-content: center !important;}
"""

traj_list = []
traj_list_range_256 = []

canvas_width, canvas_height = 256, 256


# Note that the coordinates passed to the model must not exceed 256.
# xy range 256
PROVIDED_TRAJS = {
    "circle": [
        [120, 194],
        [144, 193],
        [155, 189],
        [158, 170],
        [160, 153],
        [159, 123],
        [152, 113],
        [136, 100],
        [124, 100],
        [108, 100],
        [101, 106],
        [90, 110],
        [84, 129],
        [79, 146],
        [78, 165],
        [83, 182],
        [87, 189],
        [94, 192],
        [100, 194],
        [106, 194],
        [112, 194],
        [118, 195],
    ],
    "spiral": [
        [100, 127],
        [105, 117],
        [122, 117],
        [132, 129],
        [133, 158],
        [125, 181],
        [108, 189],
        [92, 185],
        [84, 179],
        [79, 163],
        [75, 142],
        [73, 118],
        [75, 82],
        [91, 63],
        [115, 52],
        [139, 46],
        [154, 55],
        [167, 93],
        [175, 112],
        [177, 137],
        [177, 158],
        [177, 171],
        [175, 188],
        [173, 204],
    ],
    "coaster": [
        [40, 208],
        [40, 148],
        [40, 100],
        [52, 58],
        [60, 57],
        [74, 68],
        [78, 90],
        [84, 123],
        [88, 148],
        [96, 168],
        [100, 181],
        [102, 188],
        [105, 192],
        [113, 118],
        [119, 80],
        [128, 68],
        [145, 109],
        [149, 155],
        [157, 175],
        [161, 184],
        [164, 184],
        [172, 166],
        [183, 107],
        [189, 84],
        [198, 76],
    ],
    "dance": [
        [81, 112],
        [86, 112],
        [92, 112],
        [100, 113],
        [102, 114],
        [97, 115],
        [92, 114],
        [86, 112],
        [81, 112],
        [80, 112],
        [84, 113],
        [89, 114],
        [95, 114],
        [101, 114],
        [102, 114],
        [103, 124],
        [105, 137],
        [109, 156],
        [114, 172],
        [119, 180],
        [124, 184],
        [131, 181],
        [140, 168],
        [146, 152],
        [150, 128],
        [151, 117],
        [152, 116],
        [156, 116],
        [163, 115],
        [169, 116],
        [175, 116],
        [173, 116],
        [167, 116],
        [162, 114],
        [157, 114],
        [152, 115],
        [156, 115],
        [163, 115],
        [168, 115],
        [174, 116],
        [175, 116],
        [168, 116],
        [162, 116],
        [152, 114],
        [149, 134],
        [145, 156],
        [139, 168],
        [130, 183],
        [118, 180],
        [112, 170],
        [107, 151],
        [102, 128],
        [103, 117],
        [96, 113],
        [88, 113],
        [83, 112],
        [80, 112],
    ],
    "infinity": [
        [60, 141],
        [71, 127],
        [92, 120],
        [112, 123],
        [130, 145],
        [145, 163],
        [167, 178],
        [189, 187],
        [206, 176],
        [213, 147],
        [208, 124],
        [190, 112],
        [176, 111],
        [158, 124],
        [145, 147],
        [125, 172],
        [104, 189],
        [72, 189],
        [59, 184],
        [55, 153],
        [57, 140],
        [75, 119],
        [112, 118],
        [129, 142],
        [149, 163],
        [168, 180],
        [194, 186],
        [206, 175],
        [211, 159],
        [212, 149],
        [212, 134],
        [206, 122],
        [180, 112],
        [163, 116],
        [149, 138],
        [128, 170],
        [108, 184],
        [86, 190],
        [63, 181],
        [57, 152],
        [57, 139],
    ],
    "pause": [
        [98, 186],
        [100, 188],
        [98, 186],
        [100, 188],
        [101, 187],
        [104, 187],
        [111, 184],
        [116, 176],
        [125, 162],
        [132, 140],
        [136, 119],
        [137, 104],
        [138, 96],
        [139, 94],
        [140, 94],
        [140, 96],
        [138, 98],
        [138, 96],
        [136, 94],
        [137, 92],
        [140, 92],
        [144, 92],
        [149, 92],
        [152, 92],
        [151, 92],
        [147, 92],
        [142, 92],
        [140, 92],
        [139, 95],
        [139, 105],
        [141, 122],
        [142, 143],
        [140, 167],
        [136, 184],
        [135, 188],
        [132, 195],
        [132, 192],
        [131, 192],
        [131, 192],
        [130, 192],
        [130, 195],
    ],
    "shake": [
        [103, 89],
        [104, 89],
        [106, 89],
        [107, 89],
        [108, 89],
        [109, 89],
        [110, 89],
        [111, 89],
        [112, 89],
        [113, 89],
        [114, 89],
        [115, 89],
        [116, 89],
        [117, 89],
        [118, 89],
        [119, 89],
        [120, 89],
        [122, 89],
        [123, 89],
        [124, 89],
        [125, 89],
        [126, 89],
        [127, 88],
        [128, 88],
        [129, 88],
        [130, 88],
        [131, 88],
        [133, 87],
        [136, 86],
        [137, 86],
        [138, 86],
        [139, 86],
        [140, 86],
        [141, 86],
        [142, 86],
        [143, 86],
        [144, 86],
        [145, 86],
        [146, 87],
        [147, 87],
        [148, 87],
        [149, 87],
        [148, 87],
        [146, 87],
        [145, 88],
        [144, 88],
        [142, 89],
        [141, 89],
        [140, 90],
        [140, 91],
        [138, 91],
        [137, 92],
        [136, 92],
        [136, 93],
        [135, 93],
        [134, 93],
        [133, 93],
        [132, 93],
        [131, 93],
        [130, 93],
        [129, 93],
        [128, 93],
        [127, 92],
        [125, 92],
        [124, 92],
        [123, 92],
        [122, 92],
        [121, 92],
        [120, 92],
        [119, 92],
        [118, 92],
        [117, 92],
        [116, 92],
        [115, 92],
        [113, 92],
        [112, 92],
        [111, 92],
        [110, 92],
        [109, 92],
        [108, 92],
        [108, 91],
        [108, 90],
        [109, 90],
        [110, 90],
        [111, 89],
        [112, 89],
        [113, 89],
        [114, 89],
        [115, 89],
        [115, 88],
        [116, 88],
        [117, 88],
        [118, 88],
        [118, 87],
        [119, 87],
        [120, 87],
        [121, 87],
        [122, 86],
        [123, 86],
        [124, 86],
        [125, 86],
        [126, 85],
        [127, 85],
        [128, 85],
        [129, 85],
        [130, 85],
        [131, 85],
        [132, 85],
        [133, 85],
        [134, 85],
        [135, 85],
        [136, 85],
        [137, 85],
        [138, 85],
        [139, 85],
        [140, 85],
        [141, 85],
        [142, 85],
        [143, 85],
        [143, 84],
        [144, 84],
        [145, 84],
        [146, 84],
        [147, 84],
        [148, 84],
        [149, 84],
        [148, 84],
        [147, 84],
        [145, 84],
        [144, 84],
        [143, 84],
        [142, 84],
        [141, 84],
        [140, 85],
        [139, 85],
        [138, 85],
        [137, 86],
        [136, 86],
        [136, 87],
        [135, 87],
        [134, 87],
        [133, 87],
        [132, 88],
        [131, 88],
        [130, 88],
        [129, 88],
        [129, 89],
        [128, 89],
        [127, 89],
        [126, 89],
        [125, 89],
        [124, 90],
        [123, 90],
        [122, 90],
        [121, 90],
        [120, 91],
        [119, 91],
        [118, 91],
        [117, 91],
        [116, 91],
        [115, 91],
        [114, 91],
        [113, 91],
        [112, 91],
        [111, 91],
        [110, 91],
        [109, 91],
        [109, 90],
        [108, 90],
        [110, 90],
        [111, 90],
        [113, 90],
        [114, 90],
        [115, 90],
        [116, 90],
        [118, 90],
        [120, 90],
        [121, 90],
        [122, 90],
        [123, 90],
        [124, 90],
        [126, 90],
        [127, 90],
        [128, 90],
        [129, 90],
        [130, 90],
        [131, 90],
        [132, 90],
        [133, 90],
        [134, 90],
        [135, 90],
        [136, 90],
        [137, 90],
        [138, 90],
        [139, 90],
        [140, 90],
        [141, 89],
        [142, 89],
        [143, 89],
        [144, 89],
        [145, 89],
        [146, 89],
        [147, 89],
        [147, 89],
        [147, 89],
    ],
    "wave": [
        [16, 152],
        [23, 138],
        [39, 122],
        [54, 115],
        [75, 118],
        [88, 130],
        [93, 150],
        [89, 176],
        [75, 184],
        [63, 177],
        [65, 152],
        [77, 135],
        [98, 121],
        [116, 120],
        [135, 127],
        [148, 136],
        [156, 145],
        [160, 165],
        [158, 176],
        [138, 187],
        [133, 185],
        [129, 148],
        [140, 133],
        [156, 120],
        [177, 118],
        [197, 118],
        [214, 119],
        [225, 118],
    ],
}


PROVIDED_PROMPTS = {
    "dandelion": "A dandelion puff sways gently in the wind, its seeds ready to take flight and spread into the world. The animation style highlights the delicate fibers of the puff, with soft, glowing light surrounding it. The background showcases a lush, green field, hinting at the beauty of nature. As the wind blows, the seeds dance and float away, creating an enchanting visual narrative. The gentle sounds of nature, alongside soft whispers of the breeze, enrich the overall ambiance. This serene scene invites viewers to embrace the moment of letting go, celebrating the cycle of life and new beginnings.",
    "golden retriever": "A golden retriever, sporting sleek black sunglasses, with its lengthy fur flowing in the breeze, sprints playfully across a rooftop terrace, recently refreshed by a light rain. The scene unfolds from a distance, the dog's energetic bounds growing larger as it approaches the camera, its tail wagging with unrestrained joy, while droplets of water glisten on the concrete behind it. The overcast sky provides a dramatic backdrop, emphasizing the vibrant golden coat of the canine as it dashes towards the viewer.",
    "rubber duck": "A cheerful rubber duck floats serenely in a bathtub filled with bubbles, the soft foam creating an inviting atmosphere. The bathroom setting is warm with bright tiles reflecting soft light. The camera captures playful angles, zeroing in on the duck's bright yellow color and big eyes. Sounds of water gently splashing and laughter fill the background, enhancing the joyous ambiance. This moment invites viewers to embrace nostalgia and childhood fun, evoking a sense of playfulness and relaxation.",
    "squirrel": "A squirrel gathering nuts.",
}


#############################
def pdf2(sigma_matrix, grid):
    """Calculate PDF of the bivariate Gaussian distribution.
    Args:
        sigma_matrix (ndarray): with the shape (2, 2)
        grid (ndarray): generated by :func:`mesh_grid`,
            with the shape (K, K, 2), K is the kernel size.
    Returns:
        kernel (ndarrray): un-normalized kernel.
    """
    inverse_sigma = np.linalg.inv(sigma_matrix)
    kernel = np.exp(-0.5 * np.sum(np.dot(grid, inverse_sigma) * grid, 2))
    return kernel


def mesh_grid(kernel_size):
    """Generate the mesh grid, centering at zero.
    Args:
        kernel_size (int):
    Returns:
        xy (ndarray): with the shape (kernel_size, kernel_size, 2)
        xx (ndarray): with the shape (kernel_size, kernel_size)
        yy (ndarray): with the shape (kernel_size, kernel_size)
    """
    ax = np.arange(-kernel_size // 2 + 1.0, kernel_size // 2 + 1.0)
    xx, yy = np.meshgrid(ax, ax)
    xy = np.hstack(
        (
            xx.reshape((kernel_size * kernel_size, 1)),
            yy.reshape(kernel_size * kernel_size, 1),
        )
    ).reshape(kernel_size, kernel_size, 2)
    return xy, xx, yy


def sigma_matrix2(sig_x, sig_y, theta):
    """Calculate the rotated sigma matrix (two dimensional matrix).
    Args:
        sig_x (float):
        sig_y (float):
        theta (float): Radian measurement.
    Returns:
        ndarray: Rotated sigma matrix.
    """
    d_matrix = np.array([[sig_x**2, 0], [0, sig_y**2]])
    u_matrix = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    return np.dot(u_matrix, np.dot(d_matrix, u_matrix.T))


def bivariate_Gaussian(kernel_size, sig_x, sig_y, theta, grid=None, isotropic=True):
    """Generate a bivariate isotropic or anisotropic Gaussian kernel.
    In the isotropic mode, only `sig_x` is used. `sig_y` and `theta` is ignored.
    Args:
        kernel_size (int):
        sig_x (float):
        sig_y (float):
        theta (float): Radian measurement.
        grid (ndarray, optional): generated by :func:`mesh_grid`,
            with the shape (K, K, 2), K is the kernel size. Default: None
        isotropic (bool):
    Returns:
        kernel (ndarray): normalized kernel.
    """
    if grid is None:
        grid, _, _ = mesh_grid(kernel_size)
    if isotropic:
        sigma_matrix = np.array([[sig_x**2, 0], [0, sig_x**2]])
    else:
        sigma_matrix = sigma_matrix2(sig_x, sig_y, theta)
    kernel = pdf2(sigma_matrix, grid)
    kernel = kernel / np.sum(kernel)
    return kernel


size = 99
sigma = 10
blur_kernel = bivariate_Gaussian(size, sigma, sigma, 0, grid=None, isotropic=True)
blur_kernel = blur_kernel / blur_kernel[size // 2, size // 2]
#############################


def get_flow(points, optical_flow, video_len):
    for i in range(video_len - 1):
        p = points[i]
        p1 = points[i + 1]
        optical_flow[i + 1, p[1], p[0], 0] = p1[0] - p[0]
        optical_flow[i + 1, p[1], p[0], 1] = p1[1] - p[1]

    return optical_flow


def process_points(points, frames=49):
    defualt_points = [[128, 128]] * frames

    if len(points) < 2:
        return defualt_points

    elif len(points) >= frames:
        skip = len(points) // frames
        return points[::skip][: frames - 1] + points[-1:]
    else:
        insert_num = frames - len(points)
        insert_num_dict = {}
        interval = len(points) - 1
        n = insert_num // interval
        m = insert_num % interval
        for i in range(interval):
            insert_num_dict[i] = n
        for i in range(m):
            insert_num_dict[i] += 1

        res = []
        for i in range(interval):
            insert_points = []
            x0, y0 = points[i]
            x1, y1 = points[i + 1]

            delta_x = x1 - x0
            delta_y = y1 - y0
            for j in range(insert_num_dict[i]):
                x = x0 + (j + 1) / (insert_num_dict[i] + 1) * delta_x
                y = y0 + (j + 1) / (insert_num_dict[i] + 1) * delta_y
                insert_points.append([int(x), int(y)])

            res += points[i : i + 1] + insert_points
        res += points[-1:]
        return res


def read_points_from_list(traj_list, video_len=16, reverse=False):
    points = []
    for point in traj_list:
        if isinstance(point, str):
            x, y = point.strip().split(",")
        else:
            x, y = point[0], point[1]
        points.append((int(x), int(y)))
    if reverse:
        points = points[::-1]

    if len(points) > video_len:
        skip = len(points) // video_len
        points = points[::skip]
    points = points[:video_len]

    return points


def read_points_from_file(file, video_len=16, reverse=False):
    with open(file, "r") as f:
        lines = f.readlines()
    points = []
    for line in lines:
        x, y = line.strip().split(",")
        points.append((int(x), int(y)))
    if reverse:
        points = points[::-1]

    if len(points) > video_len:
        skip = len(points) // video_len
        points = points[::skip]
    points = points[:video_len]

    return points


def process_traj(trajs_list, num_frames, video_size, device="cpu"):
    if trajs_list and trajs_list[0] and (not isinstance(trajs_list[0][0], (list, tuple))):
        tmp = trajs_list
        trajs_list = [tmp]

    optical_flow = np.zeros((num_frames, video_size[0], video_size[1], 2), dtype=np.float32)
    processed_points = []
    for traj_list in trajs_list:
        points = read_points_from_list(traj_list, video_len=num_frames)
        xy_range = 256
        h, w = video_size
        points = process_points(points, num_frames)
        points = [[int(w * x / xy_range), int(h * y / xy_range)] for x, y in points]
        optical_flow = get_flow(points, optical_flow, video_len=num_frames)
        processed_points.append(points)

    print(f"received {len(trajs_list)} trajectorie(s)")

    for i in range(1, num_frames):
        optical_flow[i] = cv2.filter2D(optical_flow[i], -1, blur_kernel)

    optical_flow = torch.tensor(optical_flow).to(device)

    return optical_flow, processed_points


def fn_vis_realtime_traj(traj_list):
    points = process_points(traj_list)
    img = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
    for i in range(len(points) - 1):
        p = points[i]
        p1 = points[i + 1]
        cv2.line(img, p, p1, (255, 0, 0), 2)
    return img


def fn_vis_traj(traj_list):
    # global traj_list
    points = process_points(traj_list)
    imgs = []
    for idx in range(len(points)):
        bg_img = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
        for i in range(len(points) - 1):
            p = points[i]
            p1 = points[i + 1]
            cv2.line(bg_img, p, p1, (255, 0, 0), 2)

            if i == idx:
                cv2.circle(bg_img, p, 2, (0, 255, 0), 20)

        if idx == (len(points) - 1):
            cv2.circle(bg_img, points[-1], 2, (0, 255, 0), 20)

        imgs.append(bg_img.astype(np.uint8))

    fps = 8
    with tempfile.NamedTemporaryFile(dir=tempfile_dir, suffix=".mp4", delete=False) as f:
        path = f.name
    writer = imageio.get_writer(path, format="mp4", mode="I", fps=fps)
    for img in imgs:
        writer.append_data(img)

    writer.close()

    return path


def create_grid_image(width, height, grid_size):
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)

    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)

    return img


def add_provided_traj(traj_list, traj_name):
    traj_list.clear()
    traj_list += PROVIDED_TRAJS[traj_name]
    traj_str = [f"{traj}" for traj in traj_list]
    img = fn_vis_realtime_traj(traj_list)
    return img, ", ".join(traj_str), gr.update(visible=True)


def add_provided_prompt(prompt_name):
    return PROVIDED_PROMPTS[prompt_name]


def add_traj_point(
    traj_list,
    evt: gr.SelectData,
):
    # global traj_list
    traj_list.append(evt.index)
    traj_list[-1][0], traj_list[-1][1] = int(traj_list[-1][0]), int(traj_list[-1][1])
    img = fn_vis_realtime_traj(traj_list)
    traj_str = [f"{traj}" for traj in traj_list]
    return img, ", ".join(traj_str)


def fn_traj_droplast(traj_list):
    # global traj_list

    if traj_list:
        traj_list.pop()

    if traj_list:
        img = fn_vis_realtime_traj(traj_list)
        traj_str = [f"{traj}" for traj in traj_list]

        return img, ", ".join(traj_str), gr.update(visible=True)
    else:
        return (
            np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255,
            "Click to specify trajectory",
            gr.update(visible=True),
        )


def fn_traj_reset(traj_list):
    # global traj_list
    traj_list.clear()
    # traj_list = []
    return (
        np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255,
        "Click to specify trajectory",
        gr.update(visible=True),
    )


def scale_traj_list_to_256(traj_list, canvas_width, canvas_height):
    scale_x = 256 / canvas_width
    scale_y = 256 / canvas_height
    scaled_traj_list = [[int(x * scale_x), int(y * scale_y)] for x, y in traj_list]
    return scaled_traj_list


###########################################

import math
from typing import List, Union

from diffusion_video import SATVideoDiffusionEngine
from einops import rearrange, repeat
from omegaconf import ListConfig
from PIL import Image, ImageDraw
from torchvision.io import write_video
from torchvision.utils import flow_to_image

from sat.arguments import set_random_seed
from sat.model.base_model import get_model

def load_checkpoint(model, args, load_path=None, prefix='', specific_iteration=None):
    """Load a model checkpoint without relying on 'latest' metadata."""
    import os
    import torch
    import random
    import numpy as np
    from sat import mpu
    from sat.helpers import print_rank0, print_all

    if load_path is None:
        load_path = args.load

    # fallback inference mode
    if not hasattr(args, 'mode'):
        from copy import deepcopy
        args = deepcopy(args)
        args.mode = 'inference'

    # Bypass 'latest' logic, directly construct checkpoint path
    checkpoint_name = os.path.join(load_path, f'mp_rank_{mpu.get_model_parallel_rank():02d}_model_states.pt')
    iteration = 0

    if mpu.get_data_parallel_rank() == 0:
        print_all(f'[INFO] Loading checkpoint: {checkpoint_name}')

    sd = torch.load(checkpoint_name, map_location='cpu')

    # load submodule only
    new_sd = {'module': {}}
    for k in sd:
        if k != 'module':
            new_sd[k] = sd[k]
    for k in sd['module']:
        if k.startswith(prefix):
            new_sd['module'][k[len(prefix):]] = sd['module'][k]
    sd = new_sd

    module = model.module if hasattr(model, 'module') else model
    missing_keys, unexpected_keys = module.load_state_dict(sd['module'], strict=False)

    if len(unexpected_keys) > 0:
        print_rank0(f'[WARN] Unexpected keys in checkpoint: {unexpected_keys}')
    if len(missing_keys) > 0:
        if args.mode == 'inference':
            if getattr(args, 'force_inference', False):
                print_rank0(f'[WARN] Missing keys in inference: {missing_keys}')
            else:
                raise ValueError(f'[ERROR] Missing keys: {missing_keys}.\nUse --force_inference to skip this check.')

    if args.mode == 'inference':
        module.eval()

    if mpu.get_data_parallel_rank() == 0:
        print_all(f'[SUCCESS] Loaded checkpoint from: {checkpoint_name}')

    del sd
    return iteration



model = None


def get_batch(keys, value_dict, N: Union[List, ListConfig], T=None, device="cuda"):
    batch = {}
    batch_uc = {}

    for key in keys:
        if key == "txt":
            batch["txt"] = np.repeat([value_dict["prompt"]], repeats=math.prod(N)).reshape(N).tolist()
            batch_uc["txt"] = np.repeat([value_dict["negative_prompt"]], repeats=math.prod(N)).reshape(N).tolist()
        else:
            batch[key] = value_dict[key]

    if T is not None:
        batch["num_video_frames"] = T

    for key in batch.keys():
        if key not in batch_uc and isinstance(batch[key], torch.Tensor):
            batch_uc[key] = torch.clone(batch[key])
    return batch, batch_uc


def get_unique_embedder_keys_from_conditioner(conditioner):
    return list({x.input_key for x in conditioner.embedders})


def draw_points(video, points):
    """
    Draw points onto video frames.

    Parameters:
        video (torch.tensor): Video tensor with shape [T, H, W, C], where T is the number of frames,
                            H is the height, W is the width, and C is the number of channels.
        points (list): Positions of points to be drawn as a tensor with shape [T, 2],
                            each point contains x and y coordinates.

    Returns:
        torch.tensor: The video tensor after drawing points, maintaining the same shape [T, H, W, C].
    """

    T = video.shape[0]
    N = len(points)
    device = video.device
    dtype = video.dtype
    video = video.cpu().numpy().copy()
    traj = np.zeros(video.shape[-3:], dtype=np.uint8)  # [H, W, C]
    for t in range(1, T):
        cv2.line(traj, tuple(points[t - 1]), tuple(points[t]), (255, 1, 1), 2)
    for t in range(T):
        mask = traj[..., -1] > 0
        mask = repeat(mask, "h w -> h w c", c=3)
        alpha = 0.7
        video[t][mask] = video[t][mask] * (1 - alpha) + traj[mask] * alpha
        cv2.circle(video[t], tuple(points[t]), 3, (160, 230, 100), -1)
    video = torch.from_numpy(video).to(device, dtype)
    return video


def save_video_as_grid_and_mp4(video_batch: torch.Tensor, fps: int = 8, args=None, key=None, traj_points=None):
    with tempfile.NamedTemporaryFile(dir=tempfile_dir, suffix=".mp4", delete=False) as f:
        path = f.name
    vid = video_batch[0]
    x = rearrange(vid, "t c h w -> t h w c")
    x = x.mul(255).add(0.5).clamp(0, 255).to("cpu", torch.uint8)  # [T H W C]

    if traj_points is not None:
        # traj video
        x = draw_points(x, traj_points)
        with tempfile.NamedTemporaryFile(dir=tempfile_dir, suffix=".mp4", delete=False) as f:
            traj_path = f.name
        write_video(
            traj_path,
            x,
            fps=fps,
            video_codec="libx264",
            options={"crf": "23"},
        )
        print("write video success.")
        return [path, traj_path]

    return [path]


def delete_old_files(folder_path="/tmp/Tora", hours=48, check_interval=3600 * 24):
    """
    Periodically checks and deletes files in the specified folder that were created more than the specified number of hours ago.

    :param folder_path: The path of the folder to check
    :param hours: The number of hours after which files will be deleted (default 48 hours)
    :param check_interval: The interval (in seconds) at which to check for files (default once per day)
    """
    while True:
        print("Checking temporary files...")
        try:
            # Get the current time in seconds since the epoch
            now = time.time()
            # Calculate the cutoff time in seconds
            cutoff_time = now - hours * 3600

            # Iterate over all files in the folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)

                # Ensure it is a file and not a directory
                if os.path.isfile(file_path):
                    # Get the creation time of the file
                    creation_time = os.path.getctime(file_path)

                    # Check if the file is older than the specified time
                    if creation_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            print(f"Deleted file: {file_path}, creation time: {creation_time}")
                        except Exception as e:
                            print(f"Error deleting file: {file_path}. Error: {e}")
        except Exception as e:
            print(f"Error checking files: {e}")

        # Sleep for the specified interval before checking again
        time.sleep(check_interval)


def cold_start(args):
    global model

    if "OMPI_COMM_WORLD_LOCAL_RANK" in os.environ:
        os.environ["LOCAL_RANK"] = os.environ["OMPI_COMM_WORLD_LOCAL_RANK"]
        os.environ["WORLD_SIZE"] = os.environ["OMPI_COMM_WORLD_SIZE"]
        os.environ["RANK"] = os.environ["OMPI_COMM_WORLD_RANK"]

    model_cls = SATVideoDiffusionEngine
    if isinstance(model_cls, type):
        model = get_model(args, model_cls)
    else:
        model = model_cls

    load_checkpoint(model, args)
    model.eval()


def model_run_v2(prompt, seed, traj_list, n_samples=1):
    global model

    image_size = [480, 720]
    sampling_num_frames = 13  # Must be 13, 11 or 9
    latent_channels = 16
    sampling_fps = 8

    sample_func = model.sample
    T, H, W, C, F = sampling_num_frames, image_size[0], image_size[1], latent_channels, 8
    num_samples = [1]
    force_uc_zero_embeddings = ["txt"]
    device = model.device

    # global traj_list
    global canvas_width, canvas_height
    traj_list_range_video = traj_list.copy()
    traj_list_range_256 = scale_traj_list_to_256(traj_list, canvas_width, canvas_height)

    with torch.no_grad():
        set_random_seed(seed)
        total_num_frames = (T - 1) * 4 + 1  # T is the video latent size, 13 * 4 = 52

        video_flow, points = process_traj(traj_list_range_256, total_num_frames, image_size, device=device)
        video_flow = video_flow.unsqueeze_(0)

        if video_flow is not None:
            model.to("cpu")  # move model to cpu, run vae on gpu only.
            tmp = rearrange(video_flow[0], "T H W C -> T C H W")
            video_flow = flow_to_image(tmp).unsqueeze_(0).to("cuda")  # [1 T C H W]

            del tmp
            video_flow = (
                rearrange(video_flow / 255.0 * 2 - 1, "B T C H W -> B C T H W").contiguous().to(torch.bfloat16)
            )
            torch.cuda.empty_cache()
            video_flow = video_flow.repeat(2, 1, 1, 1, 1).contiguous()  # for uncondition
            model.first_stage_model.to(device)
            video_flow = model.encode_first_stage(video_flow, None)
            video_flow = video_flow.permute(0, 2, 1, 3, 4).contiguous()
            model.to(device)

        value_dict = {
            "prompt": prompt,
            "negative_prompt": "",
            "num_frames": torch.tensor(T).unsqueeze(0),
        }

        batch, batch_uc = get_batch(
            get_unique_embedder_keys_from_conditioner(model.conditioner), value_dict, num_samples
        )

        c, uc = model.conditioner.get_unconditional_conditioning(
            batch,
            batch_uc=batch_uc,
            force_uc_zero_embeddings=force_uc_zero_embeddings,
        )

        for k in c:
            if not k == "crossattn":
                c[k], uc[k] = map(lambda y: y[k][: math.prod(num_samples)].to("cuda"), (c, uc))

        for index in range(1):  # num_samples
            # reload model on GPU
            model.to(device)

            samples_z = sample_func(
                c,
                uc=uc,
                batch_size=1,
                shape=(T, C, H // F, W // F),
                video_flow=video_flow,
            )
            samples_z = samples_z.permute(0, 2, 1, 3, 4).contiguous()

            # Unload the model from GPU to save GPU memory
            model.to("cpu")
            torch.cuda.empty_cache()
            first_stage_model = model.first_stage_model
            first_stage_model = first_stage_model.to(device)

            latent = 1.0 / model.scale_factor * samples_z

            # Decode latent serial to save GPU memory
            recons = []
            loop_num = (T - 1) // 2
            for i in range(loop_num):
                if i == 0:
                    start_frame, end_frame = 0, 3
                else:
                    start_frame, end_frame = i * 2 + 1, i * 2 + 3
                if i == loop_num - 1:
                    clear_fake_cp_cache = True
                else:
                    clear_fake_cp_cache = False
                with torch.no_grad():
                    recon = first_stage_model.decode(
                        latent[:, :, start_frame:end_frame].contiguous(), clear_fake_cp_cache=clear_fake_cp_cache
                    )

                recons.append(recon)

            recon = torch.cat(recons, dim=2).to(torch.float32)
            samples_x = recon.permute(0, 2, 1, 3, 4).contiguous()
            samples = torch.clamp((samples_x + 1.0) / 2.0, min=0.0, max=1.0).cpu()
            # [b, f, c, h, w]
            file_path_list = save_video_as_grid_and_mp4(
                samples,
                fps=sampling_fps,
                traj_points=process_points(traj_list_range_video),  # interpolate to 49 points
            )
            print(file_path_list)

        del samples_z, samples_x, samples, video_flow, latent, recon, recons, c, uc, batch, batch_uc
        gc.collect()
        torch.cuda.empty_cache()

        return gr.update(value=file_path_list[1], height=image_size[0], width=image_size[1])


def main():
    global canvas_width, canvas_height
    canvas_width, canvas_height, grid_size = 720, 480, 120
    grid_image = create_grid_image(canvas_width, canvas_height, grid_size)

    global PROVIDED_TRAJS
    # scale provided trajs
    PROVIDED_TRAJS = {
        name: [[int(x * (canvas_width / 256)), int(y * (canvas_height / 256))] for x, y in points]
        for name, points in PROVIDED_TRAJS.items()
    }

    demo = gr.Blocks()
    with demo:
        gr.Markdown("""
            <div style="text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 20px;">
                Tora
            </div>
            <div style="text-align: center;font-size: 20px;">
                <a href="https://github.com/alibaba/Tora">Github</a> |
                <a href="https://ali-videoai.github.io/tora_video/">Project Page</a> |
                <a href="https://arxiv.org/abs/2407.21705">arXiv</a>
            </div>
        """)

        with gr.Column():
            with gr.Row():
                with gr.Column():
                    gr.Markdown("---\n## Step 1/2: Draw A Trajectory", show_label=False)
                    gr.Markdown(
                        "\n 1. **Click on the `Canvas` to create a trajectory.** Each click adds a new point. \
                        \n 2. Click `Visualize Trajectory` to view the video; \
                        \n 3. Click `Reset Trajectory` to clear.",
                        show_label=False,
                    )
                    traj_args = gr.Textbox(value="", label="Points of Trajectory")
                    traj_list = gr.State([])
                    with gr.Row():
                        traj_vis = gr.Button(value="Visualize Trajectory")
                        traj_reset = gr.Button(value="Reset Trajectory")
                        traj_droplast = gr.Button(value="Drop Last Point")

                with gr.Column():
                    traj_input = gr.Image(
                        grid_image,
                        width=canvas_width // 2,
                        height=canvas_height // 2,
                        label="Canvas for Drawing",
                    )
                    vis_traj = gr.Video(
                        value=None,
                        label="Trajectory",
                        width=canvas_width // 2,
                        height=canvas_height // 2,
                    )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("---\n## Step 2/2: Add Prompt", show_label=False)
                    prompt = gr.Textbox(value="", label="Prompt", interactive=True)
                    n_samples = gr.Number(value=1, precision=0, interactive=True, label="n_samples", visible=False)
                    seed = gr.Number(value=1234, precision=0, interactive=True, label="Seed")
                    start = gr.Button(value="Generate")
                with gr.Column():
                    gen_video = gr.Video(value=None, label="Generated Video")

            with gr.Column():
                gr.Markdown("---\n## Trajectory Examples", show_label=False)
                with gr.Row():
                    traj_1 = gr.Button(value="circle")
                    traj_2 = gr.Button(value="spiral")
                    traj_3 = gr.Button(value="coaster")
                    traj_4 = gr.Button(value="dance")
                with gr.Row():
                    traj_5 = gr.Button(value="infinity")
                    traj_6 = gr.Button(value="pause")
                    traj_7 = gr.Button(value="shake")
                    traj_8 = gr.Button(value="wave")

            with gr.Column():
                gr.Markdown("---\n## Prompt Examples", show_label=False)
                with gr.Row():
                    prompt_1 = gr.Button(value="rubber duck")
                    prompt_2 = gr.Button(value="dandelion")
                    prompt_3 = gr.Button(value="golden retriever")
                    prompt_4 = gr.Button(value="squirrel")

        for idx, traj_btn in enumerate(
            [traj_1, traj_2, traj_3, traj_4, traj_5, traj_6, traj_7, traj_8]
        ):
            traj_btn.click(fn=add_provided_traj, inputs=[traj_list, traj_btn], outputs=[traj_input, traj_args, traj_input])

        for prompt_btn in [prompt_1, prompt_2, prompt_3, prompt_4]:
            prompt_btn.click(fn=add_provided_prompt, inputs=prompt_btn, outputs=prompt)

        traj_vis.click(fn=fn_vis_traj, inputs=traj_list, outputs=[vis_traj])
        traj_input.select(fn=add_traj_point, inputs=traj_list, outputs=[traj_input, traj_args])
        traj_droplast.click(fn=fn_traj_droplast, inputs=traj_list, outputs=[traj_input, traj_args, traj_input])
        traj_reset.click(fn=fn_traj_reset, inputs=traj_list, outputs=[traj_input, traj_args, traj_input])

        start.click(fn=model_run_v2, inputs=[prompt, seed, traj_list, n_samples], outputs=gen_video)

        gr.Markdown(article)

    # Colab-friendly launch with share=True
    demo.queue(max_size=32).launch(share=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("--username", type=str, default="")
    parser.add_argument("--password", type=str, default="")
    parser.add_argument("--server_port", type=int, default=0)
    parser.add_argument("--inbrowser", action="store_true")
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--base", type=str, default="configs/tora/model/cogvideox_5b_tora.yaml configs/tora/inference_sparse.yaml")
    parser.add_argument("--load", type=str, default="ckpts/tora/t2v/")

    args = parser.parse_args()

    from arguments import get_args
    tora_args_list = [
        "--base", "configs/tora/model/cogvideox_5b_tora.yaml",
        "configs/tora/inference_sparse.yaml",
        "--load", args.load,
    ]
    tora_args = get_args(tora_args_list)
    tora_args = argparse.Namespace(**vars(tora_args))

    tora_args.model_config.first_stage_config.params.cp_size = 1
    tora_args.model_config.network_config.params.transformer_args.model_parallel_size = 1
    tora_args.model_config.network_config.params.transformer_args.checkpoint_activations = False
    tora_args.model_config.loss_fn_config.params.sigma_sampler_config.params.uniform_sampling = False
    tora_args.model_config.en_and_decode_n_samples_a_time = 1

    cold_start(args=tora_args)
    print("******************** model loaded ********************")

    threading.Thread(target=delete_old_files, args=("/tmp/Tora", 48, 3600 * 24), daemon=True).start()

    # No args passed since launch is handled in `main()`
    main()

