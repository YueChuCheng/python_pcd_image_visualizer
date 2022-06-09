from glob import glob
from cv2 import imread
import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import glob
from natsort import natsorted
import numpy as np

from pathlib import Path


def camera_init(widget: o3d.visualization.gui, distance: float):
    bounds = widget.scene.bounding_box
    widget.setup_camera(distance, bounds, bounds.get_center())


def window_init(window_name: str, window_width: int, window_height: int):
    app = gui.Application.instance
    return app.create_window(window_name, window_width, window_height)


def set_layout(
    layout_context,
    window: o3d.visualization.gui,
    widget3d,
    panels_layout: o3d.visualization.gui,
):
    contentRect = window.content_rect
    panel_width = 20 * layout_context.theme.font_size  # 15 ems wide

    widget3d.frame = gui.Rect(
        contentRect.x,
        contentRect.y,
        contentRect.width - panel_width,
        contentRect.height,
    )

    panels_layout.frame = gui.Rect(
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


def get_files_sv(folder_path: str, type: str = None):
    f = []

    result = list(Path(".").rglob(folder_path))
    if type == "image":
        for path in natsorted(result):
            img = o3d.io.read_image(str(path))
            f.append(img)

    elif type == "pcd":
        for path in natsorted(result):

            cloud = o3d.io.read_point_cloud(str(path))
            cloud.paint_uniform_color([1.0, 1.0, 1.0])
            f.append(cloud)

    else:
        exit("no match file type")

    return f


def panel_init(
    window: o3d.visualization.gui, font_size: float, elements: list, name: str
):

    panel = gui.CollapsableVert(name, font_size)

    for ele in elements:
        panel.add_child(ele)

    return panel


def panel_layout_init(window: o3d.visualization.gui, margin: float, panels: list):

    layout = gui.Vert(
        margin * window.theme.font_size,
        gui.Margins(margin),
    )
    window.add_child(layout)

    for panel in panels:
        layout.add_child(panel)

    return layout


def ground_image_init(
    path: str,
):

    im = imread(path)

    w = im.shape[0] / 2 * 0.15
    h = im.shape[1] / 2 * 0.15

    vert = [
        [-h + 10, -w - 5, -1.5],
        [-h + 10, +w - 5, -1.5],
        [+h + 10, +w - 5, -1.5],
        [+h + 10, -w - 5, -1.5],
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

        heading = float(box["heading"])

        cos = np.cos(heading)
        sin = np.sin(heading)

        rot = np.array(
            [
                [cos, -sin, 0.0],
                [sin, cos, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )

        center = np.array([[c_x, c_y, c_z]] * 8)

        points = np.array(
            [
                [-dx, -dy, -dz],
                [+dx, -dy, -dz],
                [+dx, +dy, -dz],
                [-dx, +dy, -dz],
                [-dx, -dy, +dz],
                [+dx, -dy, +dz],
                [+dx, +dy, +dz],
                [-dx, +dy, +dz],
            ]
        )

        # convert points
        points = points @ rot.T + center

        box_info["points"] = points

        # append box point
        frame[int(box["frame_id"])].append(box_info)

    return frame


def json2point(frames: list):

    total_frame_num = len(frames)

    result_frames = [[] for i in range(0, total_frame_num)]

    for frame_id, f in enumerate(frames):

        for idx in range(len(f["figures"])):
            box_info = dict()
            points = []  # 8:3

            c_x = f["figures"][idx]["geometry"]["position"]["x"]
            c_y = f["figures"][idx]["geometry"]["position"]["y"]
            c_z = f["figures"][idx]["geometry"]["position"]["z"]

            dx = f["figures"][idx]["geometry"]["dimensions"]["x"] / 2
            dy = f["figures"][idx]["geometry"]["dimensions"]["y"] / 2
            dz = f["figures"][idx]["geometry"]["dimensions"]["z"] / 2

            heading = f["figures"][idx]["geometry"]["rotation"]["z"]

            cos = np.cos(heading)
            sin = np.sin(heading)

            rot = np.array(
                [
                    [cos, -sin, 0.0],
                    [sin, cos, 0.0],
                    [0.0, 0.0, 1.0],
                ]
            )

            center = np.array([[c_x, c_y, c_z]] * 8)

            points = np.array(
                [
                    [-dx, -dy, -dz],
                    [+dx, -dy, -dz],
                    [+dx, +dy, -dz],
                    [-dx, +dy, -dz],
                    [-dx, -dy, +dz],
                    [+dx, -dy, +dz],
                    [+dx, +dy, +dz],
                    [-dx, +dy, +dz],
                ]
            )

            # convert points
            points = points @ rot.T + center

            box_info["points"] = points

            # append box point
            result_frames[frame_id].append(box_info)

    return result_frames


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
