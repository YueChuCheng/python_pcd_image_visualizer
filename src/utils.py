from genericpath import exists
from glob import glob
from cv2 import imread
import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import glob
from natsort import natsorted
import threading

import time
import cv2
import math
import numpy as np


def camera_init(widget: o3d.visualization.gui, distance: float):
    bounds = widget.scene.bounding_box
    widget.setup_camera(distance, bounds, bounds.get_center())


def window_init(window_name: str, window_width: int, window_height: int):
    app = gui.Application.instance
    return app.create_window(window_name, window_width, window_height)


def set_layout(layout_context, window, widget3d, panel):
    contentRect = window.content_rect
    panel_width = 20 * layout_context.theme.font_size  # 15 ems wide

    widget3d.frame = gui.Rect(
        contentRect.x,
        contentRect.y,
        contentRect.width - panel_width,
        contentRect.height,
    )

    panel.frame = gui.Rect(
        widget3d.frame.get_right(),
        contentRect.y,
        panel_width,
        contentRect.height,
    )


def widget_init(window: o3d.visualization.gui, bg_color: list):

    widget = gui.SceneWidget()
    widget.scene = rendering.Open3DScene(window.renderer)
    widget.scene.set_background(bg_color)

    # add widget to window
    window.add_child(widget)

    return widget


def update_label(self, event):
    # ! need better calculation
    self.wheelCount += event.wheel_dy
    self.label.scale = max(self.text_ori_size - (0.1 * self.wheelCount), 0)


def material_init(
    shader_name: str,
    point_size: float = None,
    line_width: float = None,
    texture_image_path: str = None,
):
    mat = rendering.MaterialRecord()
    mat.shader = shader_name

    if point_size:
        mat.point_size = point_size

    if line_width:
        mat.line_width = line_width

    if texture_image_path:
        mat.albedo_img = o3d.io.read_image(texture_image_path)

    return mat


def get_files(folder_path: str, type: str = None):
    f = []

    if type == "image":
        for path in natsorted(glob.glob(folder_path)):
            img = o3d.io.read_image(path)
            f.append(img)

    elif type == "pcd":
        for path in natsorted(glob.glob(folder_path)):
            cloud = o3d.io.read_point_cloud(path)
            cloud.paint_uniform_color([1.0, 1.0, 1.0])
            f.append(cloud)

    return f


def panel_init(window, font_size, elements: list):

    panel = gui.CollapsableVert("Camera 1", font_size)

    for ele in elements:
        panel.add_child(ele)

    window.add_child(panel)

    return panel


def ground_image_init(
    path: str,
):

    im = imread(path)

    w = im.shape[0] / 2 * 0.18
    h = im.shape[1] / 2 * 0.18

    vert = [
        [-h, -w, -2],
        [-h, w, -2],
        [h, w, -2],
        [h, -w, -2],
    ]

    faces = [
        [0, 1, 2],
        [0, 2, 3],
    ]

    v_uv = [
        [0, 0],
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 1],
        [1, 0],
    ]

    v_uv = np.asarray(v_uv)

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(vert),
        o3d.utility.Vector3iVector(faces),
    )

    mesh.triangle_uvs = o3d.utility.Vector2dVector(v_uv)

    return mesh


def convert_row_boxs_to_point(row_boxs: list):

    # frame{
    #
    #       box{
    #
    #   }
    #
    #   box
    #   ...
    # }

    # box = frame_id,bbox_id,x,y,z,dx,dy,dz,heading

    total_frame_num = int(row_boxs[-1]["frame_id"]) + 1

    frame = [[] for i in range(0, total_frame_num)]

    for box in row_boxs:
        box_info = dict()
        points = []  # 8:3

        c_x = float(box["x"])
        c_y = float(box["y"])
        c_z = float(box["z"])

        dx = float(box["dx"]) / 2
        dy = float(box["dy"]) / 2
        dz = float(box["dz"]) / 2

        rotate = float(box["heading"])
        rotate_matrix = np.array(
            [
                [math.cos(math.degrees(rotate)), -math.sin(math.degrees(rotate)), 0.0],
                [math.sin(math.degrees(rotate)), math.cos(math.degrees(rotate)), 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        # print(math.degrees(rotate))

        # convert points
        p0 = [c_x - dx, c_y - dy, c_z - dz]
        p1 = [c_x + dx, c_y - dy, c_z - dz]
        p2 = [c_x + dx, c_y + dy, c_z - dz]
        p3 = [c_x - dx, c_y + dy, c_z - dz]
        p4 = [c_x - dx, c_y - dy, c_z + dz]
        p5 = [c_x + dx, c_y - dy, c_z + dz]
        p6 = [c_x + dx, c_y + dy, c_z + dz]
        p7 = [c_x - dx, c_y + dy, c_z + dz]

        points = np.array([p0, p1, p2, p3, p4, p5, p6, p7])

        # points = np.dot(points, rotate_matrix)

        box_info["points"] = points

        # append box point
        frame[int(box["frame_id"])].append(box_info)

    return frame


def draw_bbox(
    scene: o3d.visualization.gui,
    meterial,
    line_color: list,
    bboxs: list,
    bboxs_num,
):

    # clear bbox
    for i in range(bboxs_num):
        scene.remove_geometry(f"bbox{i}")

    line_indices = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
        [4, 5],
        [5, 6],
        [6, 7],
        [7, 4],
        [0, 4],
        [1, 5],
        [2, 6],
        [3, 7],
    ]

    for i, bbox in enumerate(bboxs):

        lines = o3d.geometry.LineSet()
        lines.points = o3d.utility.Vector3dVector(bbox["points"])
        lines.lines = o3d.utility.Vector2iVector(line_indices)

        lines.paint_uniform_color(line_color)

        scene.add_geometry(f"bbox{i}", lines, meterial)

    return len(bboxs)
