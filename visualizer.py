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

import csv
from pathlib import Path

from src.utils import (
    window_init,
    set_layout,
    update_label,
    widget_init,
    material_init,
    get_files_sv,
    panel_init,
    ground_image_init,
    convert_row_boxs_to_point,
    draw_bbox,
    camera_init,
    panel_layout_init,
    get_files,
)


class App:
    def __init__(self):

        ##### window setting #####

        # init window
        self.window = window_init("pcd_img_visualizer", 1024, 768)

        # set window layout
        self.window.set_on_layout(self._on_layout)

        # widget init
        self.widget3d = widget_init(window=self.window, bg_color=[0, 0, 0, 0])
        self.widget3d.set_on_mouse(self._on_widget3d_event_control)

        ##### set materials #####
        self.materials = dict()
        self.materials["line"] = material_init(shader_name="unlitLine", line_width=1)

        self.materials["pcd"] = material_init(
            shader_name="defaultUnlit", point_size=1 * self.window.scaling
        )

        self.materials["ground"] = material_init(
            shader_name="defaultUnlit", texture_image_path="./data/bg/bg.jpg"
        )

        ##### get data files #####

        # get pcd files
        self.pcd = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/pointcloud/*.pcd", "pcd"
        )
        self.widget3d.scene.add_geometry(
            "Point Cloud", self.pcd[0], self.materials["pcd"]
        )

        # get camera1 images
        self.wayside_1_camera1_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_1_camera1.jpg",
            "image",
        )
        self.wayside_1_camera2_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_1_camera2.jpg",
            "image",
        )
        self.wayside_1_camera3_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_1_camera3.jpg",
            "image",
        )

        self.wayside_2_camera1_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_2_camera1.jpg",
            "image",
        )
        self.wayside_2_camera2_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_2_camera2.jpg",
            "image",
        )
        self.wayside_2_camera3_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_2_camera3.jpg",
            "image",
        )

        self.wayside_3_camera1_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_3_camera1.jpg",
            "image",
        )
        self.wayside_3_camera2_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_3_camera2.jpg",
            "image",
        )
        self.wayside_3_camera3_img = get_files_sv(
            "./data/exp/data-writer/0/pcd/dataset/related_images/*/wayside_3_camera3.jpg",
            "image",
        )

        ##### set UI layout #####

        # camera 1 widget
        self.wayside_1_camera1 = gui.ImageWidget(self.wayside_1_camera1_img[0])
        self.wayside_1_camera2 = gui.ImageWidget(self.wayside_1_camera2_img[0])
        self.wayside_1_camera3 = gui.ImageWidget(self.wayside_1_camera3_img[0])

        self.wayside_2_camera1 = gui.ImageWidget(self.wayside_2_camera1_img[0])
        self.wayside_2_camera2 = gui.ImageWidget(self.wayside_2_camera2_img[0])
        self.wayside_2_camera3 = gui.ImageWidget(self.wayside_2_camera3_img[0])

        self.wayside_3_camera1 = gui.ImageWidget(self.wayside_3_camera1_img[0])
        self.wayside_3_camera2 = gui.ImageWidget(self.wayside_3_camera2_img[0])
        self.wayside_3_camera3 = gui.ImageWidget(self.wayside_3_camera3_img[0])

        # set play button
        self.playBtn = gui.Button("Play")
        self.playBtn.horizontal_padding_em = 0.5
        self.playBtn.vertical_padding_em = 0
        self.playBtn.set_on_clicked(self._on_start)

        self.window.add_child(self.playBtn)

        # set panel
        self.panel_wayside1 = panel_init(
            window=self.window,
            font_size=self.window.theme.font_size * 0.5,
            elements=[
                self.wayside_1_camera1,
                self.wayside_1_camera2,
                self.wayside_1_camera3,
            ],
            name="Wayside 1",
        )

        self.panel_wayside2 = panel_init(
            window=self.window,
            font_size=self.window.theme.font_size * 0.5,
            elements=[
                self.wayside_2_camera1,
                self.wayside_2_camera2,
                self.wayside_2_camera3,
            ],
            name="Wayside 2",
        )

        self.panel_wayside3 = panel_init(
            window=self.window,
            font_size=self.window.theme.font_size * 0.5,
            elements=[
                self.wayside_3_camera1,
                self.wayside_3_camera2,
                self.wayside_3_camera3,
            ],
            name="Wayside 3",
        )

        # set panel layout
        self.panels_layout = panel_layout_init(
            window=self.window,
            margin=1.0,
            panels=[self.panel_wayside1, self.panel_wayside2, self.panel_wayside3],
        )

        ##### Player #####

        self.is_play = False
        self.is_window_close = False

        # start player
        threading.Thread(target=self.update_frame).start()

        # close window => close thread
        self.window.set_on_close(self._on_close)

        ##### bbox #####
        row_boxs = []
        with open("./data/exp/dataframe-writer/boxes.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row_boxs.append(row)

        # convert row boxs to point
        self.bboxs = convert_row_boxs_to_point(row_boxs)
        self.bboxs_num = 0

        self.bboxs_num = draw_bbox(
            scene=self.widget3d.scene,
            meterial=self.materials["line"],
            line_color=[1.0, 1.0, 0.0],
            bboxs=self.bboxs[0],
            bboxs_num=self.bboxs_num,
        )

        # setup camera
        camera_init(widget=self.widget3d, distance=15.0)

        # print(bboxs[0][0])

        ##### label #####

        # add label
        # self.text_ori_size = 4.0
        # self.wheelCount = 0.0

        # self.label = self.widget3d.add_3d_label([0.5, 0.5, 0.5], "test")
        # self.label.color = gui.Color(1.0, 1.0, 0.0)
        # self.label.scale = self.text_ori_size

        ##### set ground image #####

        # ground box
        ground = ground_image_init(path="./data/bg/bg.jpg")
        self.widget3d.scene.add_geometry("ground", ground, self.materials["ground"])

        # axes
        # self.widget3d.scene.show_axes(True)

    def _on_close(self):
        self.is_window_close = True
        return True  # False would cancel the close

    # animation button function
    def _on_start(self):
        self.playBtn.text = "Stop"
        self.playBtn.set_on_clicked(self._on_stop)
        self.is_play = True

    def _on_stop(self):
        self.playBtn.text = "Play"
        self.playBtn.set_on_clicked(self._on_start)
        self.is_play = False

    def update_frame(self):
        idx = 0
        while not self.is_window_close:
            time.sleep(0.1)
            # update frame
            if self.is_play:

                idx += 1
                # reset frame
                if idx >= len(self.wayside_1_camera1_img):
                    idx = 0

                def update():

                    # camera
                    self.wayside_1_camera1.update_image(self.wayside_1_camera1_img[idx])
                    self.wayside_1_camera2.update_image(self.wayside_1_camera2_img[idx])
                    self.wayside_1_camera3.update_image(self.wayside_1_camera3_img[idx])

                    self.wayside_2_camera1.update_image(self.wayside_2_camera1_img[idx])
                    self.wayside_2_camera2.update_image(self.wayside_2_camera2_img[idx])
                    self.wayside_2_camera3.update_image(self.wayside_2_camera3_img[idx])

                    self.wayside_3_camera1.update_image(self.wayside_3_camera1_img[idx])
                    self.wayside_3_camera2.update_image(self.wayside_3_camera2_img[idx])
                    self.wayside_3_camera3.update_image(self.wayside_3_camera3_img[idx])

                    # pcd
                    pcd_frame = self.pcd[idx]
                    self.widget3d.scene.remove_geometry("Point Cloud")
                    self.widget3d.scene.add_geometry(
                        "Point Cloud", pcd_frame, self.materials["pcd"]
                    )

                    # bbox
                    self.bboxs_num = draw_bbox(
                        scene=self.widget3d.scene,
                        meterial=self.materials["line"],
                        line_color=[1.0, 1.0, 0.0],
                        bboxs=self.bboxs[idx],
                        bboxs_num=self.bboxs_num,
                    )

                # update window
                gui.Application.instance.post_to_main_thread(self.window, update)

    def _on_layout(self, layout_context):
        set_layout(
            layout_context,
            self.window,
            self.widget3d,
            self.panels_layout,
        )

    def _on_widget3d_event_control(self, event):

        if event.type == gui.MouseEvent.Type.WHEEL:
            # update_label(self, event)
            return gui.Widget.EventCallbackResult.HANDLED

        return gui.Widget.EventCallbackResult.IGNORED


def main():
    app = gui.Application.instance
    app.initialize()

    ex = App()

    app.run()


if __name__ == "__main__":
    main()
