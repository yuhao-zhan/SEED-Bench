"""
C-03: The Seeker task rendering module
"""
import sys
import os
import importlib.util
import pygame
import math
import Box2D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody

_rdir = os.path.dirname(os.path.abspath(__file__))
_spec_vis = importlib.util.spec_from_file_location(
    "c03_environment_renderer", os.path.join(_rdir, "environment.py")
)
_c03_environment_renderer = importlib.util.module_from_spec(_spec_vis)
_spec_vis.loader.exec_module(_c03_environment_renderer)
TARGET_SENSOR_VISUAL_RADIUS = _c03_environment_renderer.TARGET_SENSOR_VISUAL_RADIUS


class C03Renderer(Renderer):
    """C-03: The Seeker. Draws ground, seeker, and the target at the delayed sensor reading (API-consistent)."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        # Ground length is 30m. Screen width 800px => ppm = 800/30 = 26.67
        self.simulator.ppm = 800.0 / 30.0
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Panoramic Viewport: x in [0, 30], y in [0, 16.875]
        # offset_x = 0
        # offset_y = 20 (to show a bit below y=0)
        self.set_camera_offset(0, 20)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        seeker = (
            sandbox._terrain_bodies.get("seeker")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )
        kinematic_type = getattr(Box2D.b2, "kinematicBody", 1)

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Environmental Baseline (Ground, Obstacles, Ice Zones)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == seeker:
                # Agent-Created Structure
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body.type == dynamicBody or body.type == kinematic_type:
                # Kinematic or other dynamic bodies (Obstacles)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )

        # Delayed/stale sensor reading — matches `get_target_position` without mutating sensor state.
        if hasattr(sandbox, "peek_target_position_sensor"):
            tx, ty = sandbox.peek_target_position_sensor()
        elif hasattr(sandbox, "get_target_position"):
            tx, ty = sandbox.get_target_position()
        elif hasattr(sandbox, "get_target_position_true"):
            tx, ty = sandbox.get_target_position_true()
        else:
            tx, ty = target_x, 0.0
        self.draw_circle(
            tx,
            ty,
            TARGET_SENSOR_VISUAL_RADIUS,
            ENVIRONMENT_COLOR,
            outline_color=OUTLINE_COLOR,
            outline_width=2,
        )
