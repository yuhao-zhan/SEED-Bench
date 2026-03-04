"""
K-06: The Wiper task rendering module
正面视角 (front view): 面对玻璃，雨刮杆左右大幅度摆动“刷”玻璃，红点=待清扫粒子。
"""
import sys
import os
import math
import json
import time
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody

DEBUG_LOG = "/home/test/test1709/THUNLP/.cursor/debug.log"
_render_call_count = 0

class K06Renderer(Renderer):
    """
    K-06 正面视角：面对玻璃，雨刮杆绕中心左右大幅度摆动（明显“刷”的感觉），
    红点=玻璃上的粒子，扫走后画到两侧收纳区。
    """

    PIVOT_X = 6.0
    PIVOT_Y = 2.08
    GLASS_Y = 2.0
    GLASS_X_MIN, GLASS_X_MAX = 0.5, 11.5
    BAR_HALF_LEN = 5.0
    SCALE_X = 60.0
    SCALE_Y = 80.0
    PARTICLE_RADIUS_PX = 12
    BIN_LEFT_X = 0.3
    BIN_RIGHT_X = 11.7
    BIN_Y_OFFSET = 0.3

    def _on_glass(self, sandbox, particle):
        """与 evaluator 一致：仍在玻璃上 = 0.5<=x<=11.5 且 |y - glass_y| < 0.5"""
        glass_y = getattr(sandbox, '_glass_y', 2.0)
        x, y = particle.position.x, particle.position.y
        return (self.GLASS_X_MIN <= x <= self.GLASS_X_MAX and
                abs(y - glass_y) < 0.5)

    def _to_screen(self, px, py):
        """正面视角：物理 (x, y) → 屏幕坐标，y 向上为屏幕向上"""
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

        w = self.simulator.screen_width
        h = self.simulator.screen_height

        self.simulator.screen.fill((30, 30, 30))

        # 1) 玻璃 - 正面看是一块明显的矩形面板（像挡风玻璃），不是细条
        gx0, gx1 = self.GLASS_X_MIN, self.GLASS_X_MAX
        gy = self.GLASS_Y
        glass_half_height = 0.7   # 视觉上玻璃面板高度 ±0.7，整块约 1.4 高，像一块真正的玻璃
        pts_glass = [
            self._to_screen(gx0, gy - glass_half_height),
            self._to_screen(gx1, gy - glass_half_height),
            self._to_screen(gx1, gy + glass_half_height),
            self._to_screen(gx0, gy + glass_half_height),
        ]
        pygame.draw.polygon(self.simulator.screen, (100, 115, 140), pts_glass)
        pygame.draw.polygon(self.simulator.screen, (180, 200, 220), pts_glass, 3)

        # 2) 粒子：在玻璃上 = 红点；已扫走 = 两侧收纳区
        if hasattr(sandbox, '_particles'):
            left_bin_count = 0
            right_bin_count = 0
            for particle in sandbox._particles:
                px, py = particle.position.x, particle.position.y
                if self._on_glass(sandbox, particle):
                    pos = self._to_screen(px, py)
                    pygame.draw.circle(
                        self.simulator.screen, (255, 100, 100), pos,
                        self.PARTICLE_RADIUS_PX,
                    )
                    pygame.draw.circle(
                        self.simulator.screen, (255, 180, 180), pos,
                        self.PARTICLE_RADIUS_PX, 2,
                    )
                else:
                    r_small = 6
                    if px < self.GLASS_X_MIN:
                        left_bin_count += 1
                        by = self.GLASS_Y + self.BIN_Y_OFFSET * (left_bin_count % 3 - 1)
                        pos = self._to_screen(self.BIN_LEFT_X, by)
                        color = (120, 80, 70)
                    else:
                        right_bin_count += 1
                        by = self.GLASS_Y + self.BIN_Y_OFFSET * (right_bin_count % 3 - 1)
                        pos = self._to_screen(self.BIN_RIGHT_X, by)
                        color = (120, 80, 70)
                    pygame.draw.circle(self.simulator.screen, color, pos, r_small)
                    pygame.draw.circle(self.simulator.screen, (200, 150, 100), pos, r_small, 1)

        # 3) 雨刮杆 - 正面视角下用真实角度画整根杆，大幅度左右“刷”非常明显
        global _render_call_count
        _render_call_count += 1
        
        # Robustly find a motor-driven joint to determine wiper angle
        joint = getattr(sandbox, '_wiper_motor_joint', None)
        if joint is None and hasattr(sandbox, '_joints'):
            from Box2D.b2 import revoluteJoint
            # Prefer joints in _wiper_joints if they exist
            search_list = getattr(sandbox, '_wiper_joints', sandbox._joints)
            for j in search_list:
                if isinstance(j, revoluteJoint) and getattr(j, 'motorEnabled', False):
                    joint = j
                    break
        
        if joint is not None:
            try:
                angle = joint.angle
            except Exception:
                angle = joint.bodyB.angle
            n_bodies = len(sandbox._bodies)
            half_len = 3.0 if n_bodies <= 4 else self.BAR_HALF_LEN
            # 杆端点：绕 pivot (6, 2.08) 旋转，用真实物理坐标
            dx = half_len * math.cos(angle)
            dy = half_len * math.sin(angle)
            p1 = self._to_screen(self.PIVOT_X - dx, self.PIVOT_Y - dy)
            p2 = self._to_screen(self.PIVOT_X + dx, self.PIVOT_Y + dy)
            # #region agent log
            if _render_call_count % 200 == 1:
                try:
                    with open(DEBUG_LOG, "a") as f:
                        f.write(json.dumps({"timestamp": int(time.time() * 1000), "location": "K_06/renderer.py:render", "message": "bar draw sample", "data": {"render_call": _render_call_count, "angle": angle, "p1": p1, "p2": p2}, "hypothesisId": "H2_H4"}) + "\n")
                except Exception:
                    pass
            # #endregion
            pygame.draw.line(self.simulator.screen, (80, 220, 80), p1, p2, 10)
            pygame.draw.line(self.simulator.screen, (40, 160, 40), p1, p2, 6)

        pivot_pos = self._to_screen(self.PIVOT_X, self.PIVOT_Y)
        pygame.draw.circle(self.simulator.screen, (180, 120, 40), pivot_pos, 10)
        pygame.draw.circle(self.simulator.screen, (220, 180, 100), pivot_pos, 10, 2)
