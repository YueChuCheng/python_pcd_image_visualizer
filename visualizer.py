# ----------------------------------------------------------------------------
# -                        Open3D: www.open3d.org                            -
# ----------------------------------------------------------------------------
# The MIT License (MIT)
#
# Copyright (c) 2018-2021 www.open3d.org
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
# ----------------------------------------------------------------------------

from glob import glob
import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import glob
from natsort import natsorted
import threading

import time


# This example displays a point cloud and if you Ctrl-click on a point
# (Cmd-click on macOS) it will show the coordinates of the point.
# This example illustrates:
# - custom mouse handling on SceneWidget
# - getting a the depth value of a point (OpenGL depth)
# - converting from a window point + OpenGL depth to world coordinate
class ExampleApp:
    def __init__(self):
        # We will create a SceneWidget that fills the entire window, and then
        # a label in the lower left on top of the SceneWidget to display the
        # coordinate.
        app = gui.Application.instance
        self.window = app.create_window("Open3D - GetCoord Example", 1024, 768)
        # Since we want the label on top of the scene, we cannot use a layout,
        # so we need to manually layout the window's children.
        self.window.set_on_layout(self._on_layout)
        self.widget3d = gui.SceneWidget()
        self.window.add_child(self.widget3d)
        self.info = gui.Label("")
        self.info.visible = False
        self.window.add_child(self.info)

        self.widget3d.scene = rendering.Open3DScene(self.window.renderer)

        # change window bg color
        self.widget3d.scene.set_background([0, 0, 0, 0])

        self.mat = rendering.MaterialRecord()
        self.mat.shader = "defaultUnlit"
        # Point size is in native pixels, but "pixel" means different things to
        # different platforms (macOS, in particular), so multiply by Window scale
        # factor.
        self.mat.point_size = 1 * self.window.scaling

        bounds = self.widget3d.scene.bounding_box
        center = bounds.get_center()
        self.widget3d.setup_camera(60, bounds, center)
        self.widget3d.look_at(center, center - [0, 0, 3], [0, -1, 0])

        self.widget3d.set_on_mouse(self._on_mouse_widget3d)

        # get camera1 image
        self.camera1_img = []
        for path in natsorted(glob.glob("./data/img/*.jpg")):
            img = o3d.io.read_image(path)
            self.camera1_img.append(img)

        # set UI layout
        em = self.window.theme.font_size
        margin = 0.5 * em
        self.panel = gui.CollapsableVert("Camera 1", 0.5 * em, gui.Margins(margin))
        self.camera1 = gui.ImageWidget(self.camera1_img[0])
        self.panel.add_child(self.camera1)

        # get pcd file
        self.pcd = []
        for path in natsorted(glob.glob("./data/pcd/*.pcd")):
            cloud = o3d.io.read_point_cloud(path)
            cloud.paint_uniform_color([1.0, 1.0, 1.0])
            self.pcd.append(cloud)

        # change point cloud color
        self.widget3d.scene.add_geometry("Point Cloud", self.pcd[0], self.mat)

        # set play button
        self.playBtn = gui.Button("Play")
        self.playBtn.horizontal_padding_em = 0.5
        self.playBtn.vertical_padding_em = 0
        self.playBtn.set_on_clicked(self._on_start)
        self.panel.add_child(self.playBtn)

        self.window.add_child(self.panel)

        self.is_window_close = False

        self.is_play = False

        threading.Thread(target=self.update_frame).start()

        # close window => close thread
        self.window.set_on_close(self._on_close)

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
            time.sleep(1)
            # update frame
            if self.is_play:

                idx += 1
                # reset frame
                if idx >= len(self.camera1_img):
                    idx = 0

                def update():

                    # camera
                    camera1_frame = self.camera1_img[idx]
                    self.camera1.update_image(camera1_frame)

                    # pcd
                    pcd_frame = self.pcd[idx]
                    self.widget3d.scene.remove_geometry("Point Cloud")
                    self.widget3d.scene.add_geometry("Point Cloud", pcd_frame, self.mat)

                # update window
                gui.Application.instance.post_to_main_thread(self.window, update)

    def _on_layout(self, layout_context):
        contentRect = self.window.content_rect
        panel_width = 20 * layout_context.theme.font_size  # 15 ems wide

        self.widget3d.frame = gui.Rect(
            contentRect.x,
            contentRect.y,
            contentRect.width - panel_width,
            contentRect.height,
        )

        self.panel.frame = gui.Rect(
            self.widget3d.frame.get_right(),
            contentRect.y,
            panel_width,
            contentRect.height,
        )

    def _on_mouse_widget3d(self, event):
        # We could override BUTTON_DOWN without a modifier, but that would
        # interfere with manipulating the scene.
        if event.type == gui.MouseEvent.Type.BUTTON_DOWN and event.is_modifier_down(
            gui.KeyModifier.CTRL
        ):

            def depth_callback(depth_image):
                # Coordinates are expressed in absolute coordinates of the
                # window, but to dereference the image correctly we need them
                # relative to the origin of the widget. Note that even if the
                # scene widget is the only thing in the window, if a menubar
                # exists it also takes up space in the window (except on macOS).
                x = event.x - self.widget3d.frame.x
                y = event.y - self.widget3d.frame.y
                # Note that np.asarray() reverses the axes.
                depth = np.asarray(depth_image)[y, x]

                if depth == 1.0:  # clicked on nothing (i.e. the far plane)
                    text = ""
                else:
                    world = self.widget3d.scene.camera.unproject(
                        event.x,
                        event.y,
                        depth,
                        self.widget3d.frame.width,
                        self.widget3d.frame.height,
                    )
                    text = "({:.3f}, {:.3f}, {:.3f})".format(
                        world[0], world[1], world[2]
                    )

                # This is not called on the main thread, so we need to
                # post to the main thread to safely access UI items.
                def update_label():
                    self.info.text = text
                    self.info.visible = text != ""
                    # We are sizing the info label to be exactly the right size,
                    # so since the text likely changed width, we need to
                    # re-layout to set the new frame.
                    self.window.set_needs_layout()

                gui.Application.instance.post_to_main_thread(self.window, update_label)

            self.widget3d.scene.scene.render_to_depth_image(depth_callback)
            return gui.Widget.EventCallbackResult.HANDLED
        return gui.Widget.EventCallbackResult.IGNORED


def main():
    app = gui.Application.instance
    app.initialize()

    # This example will also work with a triangle mesh, or any 3D object.
    # If you use a triangle mesh you will probably want to set the material
    # shader to "defaultLit" instead of "defaultUnlit".

    ex = ExampleApp()

    app.run()


if __name__ == "__main__":
    main()
