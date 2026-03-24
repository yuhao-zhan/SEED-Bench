"""
C-02: The Lander task rendering module
"""
import sys
import os
import pygame
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
_c02_dir = os.path.dirname(os.path.abspath(__file__))
if _c02_dir not in sys.path:
    sys.path.insert(0, _c02_dir)
from environment import GROUND_SLAB_HEIGHT  # noqa: E402

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C02Renderer(Renderer):
    """C-02: The Lander task renderer. Draws ground, barrier, and lander."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # 16:9 viewport; ~22 m vertical span (covers default corridor ceiling + margin; mutated stages may use a lower ceiling).
        # World x span 30 m then uses ~655 px width at this ppm.
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        self.simulator.ppm = float(self.simulator.screen_height) / 22.0
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # World y visible ~[0, 22] m with small margin below y=0 via offset
        self.set_camera_offset(float(camera_offset_x), 12)
        _ = target_x  # shared render API passes world hint; C-02 uses fixed framing
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        lander = (
            sandbox._terrain_bodies.get("lander")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Environmental Baseline
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == lander:
                # Agent-Created Structure
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body.type == dynamicBody:
                # Any other dynamic objects are also considered agent-related
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
        
        # Draw no-fly zone (barrier): lower obstacle and upper ceiling if in view
        if hasattr(sandbox, "_barrier_x_left") and hasattr(sandbox, "_barrier_y_top"):
            bx_left = sandbox._barrier_x_left
            bx_right = sandbox._barrier_x_right
            by_top = sandbox._barrier_y_top
            ground_y = getattr(sandbox, "_ground_y_top", 1.0)
            # Lower obstacle: vertical strip from ground up to y=barrier_y_top (draw_rect uses center y)
            obs_width = bx_right - bx_left
            obs_height = by_top - ground_y
            if obs_height > 0:
                self.draw_rect(
                    bx_left, ground_y + obs_height / 2.0, obs_width, obs_height,
                    (180, 60, 60), outline_color=(255, 100, 100), outline_width=2
                )
            # Upper ceiling (if within typical view): horizontal band at barrier_y_bottom
            by_bottom = getattr(sandbox, "_barrier_y_bottom", 20.0)
            # Draw ceiling whenever a finite upper bound exists (no arbitrary cutoff)
            if by_bottom < 1e6:
                self.draw_line(bx_left, by_bottom, bx_right, by_bottom, (180, 60, 60), width=2)

        # Moving landing platform (visual only; physics is flat ground at ground_y_top + evaluator x-window)
        if hasattr(sandbox, "_sim_time") and hasattr(sandbox, "get_platform_center_at_time"):
            t = sandbox._sim_time
            tx = sandbox.get_platform_center_at_time(t)
            ty = sandbox._ground_y_top
            hw = sandbox._platform_half_width
            slab_h = float(
                getattr(sandbox, "_ground_slab_height", GROUND_SLAB_HEIGHT)
            )
            # draw_rect: world_y is the rectangle bottom; span [ty - slab_h, ty] so the band sits in the ground slab flush with the landing surface
            self.draw_rect(
                tx - hw,
                ty - slab_h,
                2.0 * hw,
                slab_h,
                (90, 90, 140),
                outline_color=(200, 200, 255),
                outline_width=2,
            )
            self.draw_line(tx - hw, ty + 0.02, tx + hw, ty + 0.02, (255, 255, 255), width=2)
