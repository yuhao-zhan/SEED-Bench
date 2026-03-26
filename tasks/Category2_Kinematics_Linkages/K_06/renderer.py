"""
K-06: The Wiper task rendering module
Standardized for professional academic aesthetics.
正面视角 (front view): 面对玻璃，雨刮杆左右大幅度摆动“刷”玻璃。
"""
import sys
import os
import math
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, revoluteJoint, polygonShape

# Standard Academic Palette
COLOR_BG = (0, 0, 0)
COLOR_ENV = (230, 194, 41)    # Goldenrod Yellow (#E6C229)
COLOR_AGENT = (76, 175, 80)  # Material Green (#4CAF50)
COLOR_TEMPLATE = (90, 90, 90)
COLOR_JOINT = (255, 220, 100)
COLOR_GLASS = (40, 45, 55)    # Muted dark blue-gray for glass transparency feel
COLOR_GLASS_OUTLINE = (180, 200, 220)


class K06Renderer(Renderer):
    """K-06: The Wiper — standardized front-view mechanism."""

    PIVOT_X = 6.0
    PIVOT_Y = 2.08
    GLASS_Y = 2.0
    GLASS_X_MIN, GLASS_X_MAX = 0.5, 11.5
    BAR_HALF_LEN = 5.0
    SCALE_X = 60.0
    SCALE_Y = 80.0
    # Physically accurate radius: 0.08m * 60px/m = 4.8px -> use 5px for better visibility
    PARTICLE_RADIUS_PX = 6 
    BIN_LEFT_X = 0.3
    BIN_RIGHT_X = 11.7
    BIN_Y_OFFSET = 0.3

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio
        if simulator.can_display:
            target_h = 600
            target_w = int(target_h * 16 / 9)
            if simulator.screen_width != target_w or simulator.screen_height != target_h:
                simulator.screen_width = target_w
                simulator.screen_height = target_h
                simulator.screen = pygame.Surface((target_w, target_h))

    def _on_glass(self, sandbox, particle):
        """Check if particle is on glass."""
        # Use values from sandbox if available for better sync
        gx_min = getattr(sandbox, 'GLASS_X_MIN', 0.5)
        gx_max = getattr(sandbox, 'GLASS_X_MAX', 11.5)
        # Wait, environment.py uses hardcoded 0.5 and 11.5 in get_particle_count
        gx_min, gx_max = 0.5, 11.5
        glass_y = getattr(sandbox, '_glass_y', 2.0)
        x, y = particle.position.x, particle.position.y
        return (gx_min <= x <= gx_max and abs(y - glass_y) < 0.5)

    def _to_screen(self, px, py):
        """Front view coordinate transformation."""
        w = self.simulator.screen_width
        h = self.simulator.screen_height
        sx, sy = self.SCALE_X, self.SCALE_Y
        cx, cy = self.PIVOT_X, self.GLASS_Y
        screen_x = int((px - cx) * sx + w / 2)
        screen_y = int(h / 2 - (py - cy) * sy)
        return (screen_x, screen_y)

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        if not self.simulator.can_display:
            return

        self.clear(COLOR_BG)

        # 1) Glass Panel (Environmental Baseline)
        gx0, gx1 = 0.0, 12.0 # Total length from environment.py
        gy = getattr(sandbox, "_glass_y", self.GLASS_Y)
        # Physical glass height is 0.1, top at y=2.0.
        # We render it slightly thicker for visibility but aligned with top.
        glass_render_height = 0.2 
        pts_glass = [
            self._to_screen(gx0, gy - glass_render_height),
            self._to_screen(gx1, gy - glass_render_height),
            self._to_screen(gx1, gy),
            self._to_screen(gx0, gy),
        ]
        pygame.draw.polygon(self.simulator.screen, COLOR_GLASS, pts_glass)
        pygame.draw.polygon(self.simulator.screen, COLOR_ENV, pts_glass, 2)

        # 2) Agent Bodies (The actual wiper structure)
        # Draw all beams created by the agent
        for body in (sandbox.bodies or []):
            if body.type == dynamicBody:
                for fixture in body.fixtures:
                    shape = fixture.shape
                    if isinstance(shape, polygonShape):
                        vertices_world = [body.transform * v for v in shape.vertices]
                        vertices_screen = [self._to_screen(v.x, v.y) for v in vertices_world]
                        pygame.draw.polygon(self.simulator.screen, COLOR_AGENT, vertices_screen)
                        pygame.draw.polygon(self.simulator.screen, (255, 255, 255), vertices_screen, 1)

        # 3) Particles (Goldenrod Yellow as environmental markers)
        if hasattr(sandbox, '_particles'):
            left_bin_count = 0
            right_bin_count = 0
            for particle in sandbox._particles:
                px, py = particle.position.x, particle.position.y
                if self._on_glass(sandbox, particle):
                    pos = self._to_screen(px, py)
                    # Use Goldenrod for targets to be cleaned
                    pygame.draw.circle(self.simulator.screen, COLOR_ENV, pos, self.PARTICLE_RADIUS_PX)
                    pygame.draw.circle(self.simulator.screen, (255, 255, 255), pos, self.PARTICLE_RADIUS_PX, 1)
                else:
                    # Collected particles
                    r_small = 4
                    if px < 0.5: # Boundary from environment.py
                        left_bin_count += 1
                        by = self.GLASS_Y + self.BIN_Y_OFFSET * (left_bin_count % 3 - 1)
                        pos = self._to_screen(self.BIN_LEFT_X, by)
                    else:
                        right_bin_count += 1
                        by = self.GLASS_Y + self.BIN_Y_OFFSET * (right_bin_count % 3 - 1)
                        pos = self._to_screen(self.BIN_RIGHT_X, by)
                    pygame.draw.circle(self.simulator.screen, (50, 50, 50), pos, r_small)
                    pygame.draw.circle(self.simulator.screen, COLOR_ENV, pos, r_small, 1)

        # 4) Wiper Arm Indicator (Conceptual line for the motor joint)
        joint = getattr(sandbox, '_wiper_motor_joint', None)
        if joint is None and hasattr(sandbox, '_joints'):
            from Box2D.b2 import revoluteJoint
            search_list = getattr(sandbox, '_wiper_joints', sandbox._joints)
            for j in search_list:
                if isinstance(j, revoluteJoint) and getattr(j, 'motorEnabled', False):
                    joint = j
                    break
        
        if joint is not None:
            try:
                angle = joint.angle
                pivot_x, pivot_y = joint.anchorA
            except Exception:
                angle = joint.bodyB.angle
                pivot_x, pivot_y = self.PIVOT_X, self.PIVOT_Y
            
            # Draw a faint indicator of the sweep arm if requested
            half_len = self.BAR_HALF_LEN
            dx = half_len * math.cos(angle)
            dy = half_len * math.sin(angle)
            p1 = self._to_screen(pivot_x - dx, pivot_y - dy)
            p2 = self._to_screen(pivot_x + dx, pivot_y + dy)
            
            # Thinner, more transparent-looking line for the indicator
            pygame.draw.line(self.simulator.screen, (100, 200, 100), p1, p2, 2)

            # Pivot point at actual joint location
            pivot_pos = self._to_screen(pivot_x, pivot_y)
            pygame.draw.circle(self.simulator.screen, COLOR_JOINT, pivot_pos, 6)
            pygame.draw.circle(self.simulator.screen, (255, 255, 255), pivot_pos, 6, 1)
        else:
            # Default pivot point if no joint found
            pivot_pos = self._to_screen(self.PIVOT_X, self.PIVOT_Y)
            pygame.draw.circle(self.simulator.screen, COLOR_JOINT, pivot_pos, 6)
            pygame.draw.circle(self.simulator.screen, (255, 255, 255), pivot_pos, 6, 1)

