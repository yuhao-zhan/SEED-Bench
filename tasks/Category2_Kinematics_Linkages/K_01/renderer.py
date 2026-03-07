"""
K-01: The Walker task rendering module
Standardized for professional academic aesthetics.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, revoluteJoint

# Standard Academic Palette
COLOR_BG = (0, 0, 0)
COLOR_ENV = (230, 194, 41)    # Goldenrod Yellow (#E6C229)
COLOR_AGENT = (76, 175, 80)  # Material Green (#4CAF50)
COLOR_TEMPLATE = (90, 90, 90)
COLOR_JOINT = (255, 220, 100)

RENDER_SCALE = 1.5  # Slightly zoomed out for panoramic view


class K01Renderer(Renderer):
    """K-01: The Walker — standardized 2D side-view mechanism."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio
        if simulator.can_display:
            target_h = 600
            target_w = int(target_h * 16 / 9)  # ~1066
            if simulator.screen_width != target_w or simulator.screen_height != target_h:
                simulator.screen_width = target_w
                simulator.screen_height = target_h
                # Re-create screen surface for 16:9
                simulator.screen = pygame.Surface((target_w, target_h))

    def world_to_screen(self, world_x, world_y):
        """Apply scale and camera offset."""
        ppm = self.simulator.ppm * RENDER_SCALE
        screen_x = world_x * ppm - self.camera_offset_x
        screen_y = self.simulator.screen_height - (world_y * ppm) - self.camera_offset_y
        return (int(screen_x), int(screen_y))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        # Center camera on agent if it exists
        if agent_body:
            cx = agent_body.position.x
            # Keep vertical view balanced to show ground and build zone
            self.set_camera_offset(cx * ppm * RENDER_SCALE - sw / 2, -50)
        else:
            self.set_camera_offset(camera_offset_x, -50)
            
        self.clear(COLOR_BG)
        
        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body,
                             dynamic_color=COLOR_AGENT,
                             static_color=COLOR_ENV,
                             outline_color=COLOR_ENV,
                             outline_width=2)
        
        # Identify walker components
        torso_body = agent_body
        leg_bodies = set()
        
        if torso_body and hasattr(sandbox, '_joints'):
            for joint in sandbox._joints:
                if isinstance(joint, revoluteJoint):
                    if joint.bodyA == torso_body:
                        leg_bodies.add(joint.bodyB)
                    elif joint.bodyB == torso_body:
                        leg_bodies.add(joint.bodyA)
        
        # Draw dynamic objects (walker structure)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_template = False
                if hasattr(sandbox, '_walker_bodies'):
                    for key, value in sandbox._walker_bodies.items():
                        if 'template' in key and body == value:
                            is_template = True
                            break
                
                if is_template:
                    self.draw_body(body,
                                 dynamic_color=COLOR_TEMPLATE,
                                 static_color=COLOR_ENV,
                                 outline_color=COLOR_TEMPLATE,
                                 outline_width=1)
                else:
                    # All agent-created structures are Material Green
                    self.draw_body(body,
                                 dynamic_color=COLOR_AGENT,
                                 static_color=COLOR_ENV,
                                 outline_color=COLOR_AGENT,
                                 outline_width=2)
        
        # Joints: one small marker per unique anchor
        if hasattr(sandbox, '_joints'):
            seen = set()
            for joint in sandbox._joints:
                if not isinstance(joint, revoluteJoint) or not joint.bodyA or not joint.bodyB:
                    continue
                try:
                    if hasattr(joint, 'localAnchorA'):
                        local_anchor = joint.localAnchorA
                    elif hasattr(joint, 'anchorA'):
                        local_anchor = joint.anchorA
                    else:
                        continue
                    world_anchor = joint.bodyA.GetWorldPoint(local_anchor)
                    key = (round(world_anchor.x, 3), round(world_anchor.y, 3))
                    if key in seen:
                        continue
                    seen.add(key)
                    anchor_screen = self.world_to_screen(world_anchor.x, world_anchor.y)
                    pygame.draw.circle(self.simulator.screen, COLOR_JOINT, anchor_screen, 4)
                except Exception:
                    pass

        # Target line (Goldenrod Yellow as per environmental baseline)
        if target_x and target_x > 0:
            self.draw_line(target_x, 1.0, target_x, 10.0, COLOR_ENV, 3)
        
        # Build zone (Goldenrod Yellow)
        if hasattr(sandbox, 'BUILD_ZONE_X_MIN'):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENV, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENV, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENV, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENV, 1)
