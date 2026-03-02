"""
D-03: Phase-Locked Gate — cart, rotating gate, build zone, target zone.
"""
import sys
import os
import pygame
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D03Renderer(Renderer):
    """D-03: Phase-Locked Gate — cart, gate rod, build zone, target zone."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((24, 28, 36))

        # Target zone (x >= 15)
        tx = getattr(sandbox, "_target_x_min", 15.0)
        self.draw_line(tx, 0.4, tx, 4.0, (80, 220, 120), 3)
        self.draw_line(tx + 2, 0.4, tx + 2, 4.0, (80, 220, 120), 1)

        # Mud zone [5.5, 7.5] and Brake zone [12, 15]
        if hasattr(sandbox, "_mud_zone_x_min"):
            m1, m2 = sandbox._mud_zone_x_min, sandbox._mud_zone_x_max
            self.draw_line(m1, 0.4, m1, 4.0, (120, 80, 40), 1)
            self.draw_line(m2, 0.4, m2, 4.0, (120, 80, 40), 1)
        if hasattr(sandbox, "_brake_zone_x_min"):
            b1, b2 = sandbox._brake_zone_x_min, sandbox._brake_zone_x_max
            self.draw_line(b1, 0.4, b1, 4.0, (80, 60, 120), 1)
            self.draw_line(b2, 0.4, b2, 4.0, (80, 60, 120), 1)

        # Build zone
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 220, 80), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 220, 80), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 220, 80), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 220, 80), 1)

        # Impulse zone [8, 9]
        if hasattr(sandbox, "_impulse_zone_x_min"):
            i1, i2 = sandbox._impulse_zone_x_min, sandbox._impulse_zone_x_max
            self.draw_line(i1, 0.4, i1, 4.0, (200, 80, 80), 1)
            self.draw_line(i2, 0.4, i2, 4.0, (200, 80, 80), 1)
        # Second impulse zone [10.5, 11] — backward kick after gate 1
        if hasattr(sandbox, "_impulse2_zone_x_min"):
            j1 = getattr(sandbox, "_impulse2_zone_x_min", 10.5)
            j2 = getattr(sandbox, "_impulse2_zone_x_max", 11.0)
            self.draw_line(j1, 0.4, j1, 4.0, (220, 60, 60), 2)
            self.draw_line(j2, 0.4, j2, 4.0, (220, 60, 60), 2)
        # Speed trap at x=9 (min speed required when crossing)
        if hasattr(sandbox, "_speed_trap_x"):
            sx = getattr(sandbox, "_speed_trap_x", 9.0)
            self.draw_line(sx, 0.4, sx, 4.0, (255, 180, 60), 2)
        # Decel zone [9.5, 11] — velocity profile constraint
        if hasattr(sandbox, "_decel_zone_x_min"):
            d1 = getattr(sandbox, "_decel_zone_x_min", 9.5)
            d2 = getattr(sandbox, "_decel_zone_x_max", 11.0)
            self.draw_line(d1, 0.4, d1, 4.0, (180, 100, 220), 2)
            self.draw_line(d2, 0.4, d2, 4.0, (180, 100, 220), 2)
        # Ground (exclude gate pivots)
        gate_pivot = sandbox._terrain_bodies.get("gate_pivot")
        gate_pivot_2 = sandbox._terrain_bodies.get("gate_pivot_2")
        gate_pivot_3 = sandbox._terrain_bodies.get("gate_pivot_3")
        gate_pivot_4 = sandbox._terrain_bodies.get("gate_pivot_4")
        for body in sandbox.world.bodies:
            if body.type == staticBody and body not in (gate_pivot, gate_pivot_2, gate_pivot_3, gate_pivot_4):
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(100, 85, 55),
                    outline_color=(140, 120, 80),
                    outline_width=2,
                )

        # Gate 1, 2, 3 & 4 pivots
        for key in ("gate_pivot", "gate_pivot_2", "gate_pivot_3", "gate_pivot_4"):
            pivot = sandbox._terrain_bodies.get(key)
            if pivot is not None:
                self.draw_body(
                    pivot,
                    dynamic_color=(80, 80, 80),
                    static_color=(60, 60, 60),
                    outline_color=(120, 120, 120),
                    outline_width=2,
                )

        # Gate rods (1, 2, 3 and 4)
        rod = sandbox._terrain_bodies.get("gate_rod")
        rod2 = sandbox._terrain_bodies.get("gate_rod_2")
        rod3 = sandbox._terrain_bodies.get("gate_rod_3")
        rod4 = sandbox._terrain_bodies.get("gate_rod_4")
        cabin = sandbox._terrain_bodies.get("vehicle_cabin")
        agent_bodies = set(getattr(sandbox, "_bodies", []))

        for body in sandbox.world.bodies:
            if body.type != dynamicBody:
                continue
            if body == cabin:
                self.draw_body(
                    body,
                    dynamic_color=(255, 90, 90),
                    static_color=(150, 100, 50),
                    outline_color=(255, 150, 150),
                    outline_width=3,
                )
            elif body in (rod, rod2, rod3, rod4):
                self.draw_body(
                    body,
                    dynamic_color=(200, 120, 255),
                    static_color=(100, 80, 120),
                    outline_color=(220, 160, 255),
                    outline_width=2,
                )
            elif body in agent_bodies:
                self.draw_body(
                    body,
                    dynamic_color=(80, 200, 120),
                    static_color=(150, 100, 50),
                    outline_color=(60, 160, 90),
                    outline_width=2,
                )
            else:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(150, 100, 50),
                    outline_color=(100, 150, 255),
                    outline_width=2,
                )
