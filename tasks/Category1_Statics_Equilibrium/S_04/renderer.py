"""
S-04: The Balancer task rendering module
Zoomed and centered so the pivot + beam + load fill the frame.
The 200kg load is drawn in a distinct color and the weld to the structure is shown so it doesn't look like it's floating.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody

# Zoom: smaller = camera further away
RENDER_SCALE = 1.2
# World position to place at screen center
CENTER_WORLD_X = 0.0
CENTER_WORLD_Y = 1.5

class S04Renderer(Renderer):
    """S-04: The Balancer task specific renderer — zoomed and centered."""

    def world_to_screen(self, world_x, world_y):
        """Apply zoom so the balancer appears larger and centered."""
        ppm = self.simulator.ppm * RENDER_SCALE
        screen_x = world_x * ppm - self.camera_offset_x
        screen_y = self.simulator.screen_height - (world_y * ppm) - self.camera_offset_y
        return (int(screen_x), int(screen_y))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render scene with fixed camera: center on balancer and zoom in."""
        ppm = self.simulator.ppm * RENDER_SCALE
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        # Fix camera so CENTER_WORLD is at screen center
        cam_x = CENTER_WORLD_X * ppm - sw / 2
        cam_y = sh / 2 - CENTER_WORLD_Y * ppm
        self.set_camera_offset(cam_x, cam_y)
        self.clear((30, 30, 30))

        load_body = getattr(sandbox, "_terrain_bodies", {}).get("load")

        # Draw pivot and structure (skip load so we draw it separately with distinct color)
        for body in sandbox.world.bodies:
            if body is load_body:
                continue
            if body.type == staticBody:
                self.draw_body(body, static_color=(255, 200, 0), outline_color=(255, 255, 0), outline_width=3)
            elif body.type == dynamicBody:
                self.draw_body(body, dynamic_color=(100, 200, 100), outline_color=(50, 150, 50), outline_width=2)

        # Draw weld line from load to the structure body it's welded to (so the line clearly connects orange load to green structure)
        if load_body is not None and getattr(sandbox, "_bodies", None):
            lx, ly = load_body.position.x, load_body.position.y
            best = None
            best_d = float("inf")
            for b in sandbox._bodies:
                if b is load_body:
                    continue
                d = (b.position.x - lx) ** 2 + (b.position.y - ly) ** 2
                if d < best_d:
                    best_d = d
                    best = b
            if best is not None:
                self.draw_line(best.position.x, best.position.y, lx, ly, (180, 180, 180), width=2)

        if load_body is not None:
            self.draw_body(
                load_body,
                dynamic_color=(255, 140, 60),
                outline_color=(255, 180, 100),
                outline_width=2,
            )
