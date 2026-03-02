"""
K-02: The Climber task rendering module
2D side-view linkage mechanism: zoomed view, clear torso/legs, deduplicated joints.
"""
import sys
import os
import pygame
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, revoluteJoint

# Strong zoom so climber mechanism is clearly visible (not a tiny blob)
RENDER_SCALE = 3.0


class K02Renderer(Renderer):
    """K-02: The Climber — 2D side-view mechanism, zoomed for clarity."""

    def world_to_screen(self, world_x, world_y):
        """Apply zoom so mechanism appears larger."""
        ppm = self.simulator.ppm * RENDER_SCALE
        screen_x = world_x * ppm - self.camera_offset_x
        screen_y = self.simulator.screen_height - (world_y * ppm) - self.camera_offset_y
        return (int(screen_x), int(screen_y))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        if agent_body:
            center_world_x = 4.5
            center_world_y = agent_body.position.y
            cam_x = center_world_x * ppm * RENDER_SCALE - sw / 2
            cam_y = sh / 2 - center_world_y * ppm * RENDER_SCALE
            self.set_camera_offset(cam_x, cam_y)
        else:
            self.set_camera_offset(0, 0)
        self.clear((30, 30, 30))  # Dark background (match Category1_Statics_Equilibrium)
        
        # Draw static terrain (wall and ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Check if it's wall or ground
                is_wall = False
                if hasattr(sandbox, '_terrain_bodies'):
                    if body == sandbox._terrain_bodies.get("wall"):
                        is_wall = True
                
                if is_wall:
                    # Wall - rock color (unified with Category1)
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(120, 100, 60),
                                 outline_color=(200, 150, 100),
                                 outline_width=2)
                else:
                    # Ground - brown (unified with Category1)
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(150, 100, 50),
                                 outline_color=(200, 150, 100),
                                 outline_width=2)
        
        # Identify main body (agent_body) and other components
        main_body = agent_body
        other_bodies = set()
        
        # Find all bodies that are connected to main body via joints
        if main_body and hasattr(sandbox, '_joints'):
            for joint in sandbox._joints:
                if isinstance(joint, revoluteJoint):
                    if joint.bodyA == main_body:
                        other_bodies.add(joint.bodyB)
                    elif joint.bodyB == main_body:
                        other_bodies.add(joint.bodyA)
        
        # Draw dynamic objects (climber structure) with different colors
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if it's template
                is_template = False
                if hasattr(sandbox, '_climber_bodies'):
                    for key, value in sandbox._climber_bodies.items():
                        if 'template' in key and body == value:
                            is_template = True
                            break
                
                if is_template:
                    # Template - faded on dark background
                    self.draw_body(body,
                                 dynamic_color=(90, 90, 90),
                                 static_color=(150, 100, 50),
                                 outline_color=(140, 140, 140),
                                 outline_width=1)
                elif body == main_body:
                    # Main body - red (match Category1 vehicle style)
                    self.draw_body(body,
                                 dynamic_color=(255, 100, 100),
                                 static_color=(150, 100, 50),
                                 outline_color=(255, 150, 150),
                                 outline_width=3)
                elif body in other_bodies:
                    # Leg/gripper - green (match Category1 bridge/links style)
                    self.draw_body(body,
                                 dynamic_color=(100, 200, 100),
                                 static_color=(150, 100, 50),
                                 outline_color=(50, 150, 50),
                                 outline_width=2)
                    # Draw axis line so leg clearly looks like a rod (not a square)
                    px, py = body.position.x, body.position.y
                    ang = body.angle
                    half_len = 0.45  # ~leg half-length in world units
                    ax = px + half_len * math.cos(ang)
                    ay = py + half_len * math.sin(ang)
                    bx = px - half_len * math.cos(ang)
                    by = py - half_len * math.sin(ang)
                    p1 = self.world_to_screen(ax, ay)
                    p2 = self.world_to_screen(bx, by)
                    pygame.draw.line(self.simulator.screen, (50, 220, 80), p1, p2, 3)
                else:
                    # Other climber parts - blue
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(150, 100, 50),
                                 outline_color=(100, 150, 255),
                                 outline_width=2)
        
        # Torso emphasis: large "body" circle so main body is unmissable
        if main_body:
            pos = self.world_to_screen(main_body.position.x, main_body.position.y)
            r = max(14, int(0.38 * ppm * RENDER_SCALE))
            pygame.draw.circle(self.simulator.screen, (255, 100, 100), pos, r)
            pygame.draw.circle(self.simulator.screen, (255, 150, 150), pos, r, 3)

        # Joints: one small marker per unique anchor (no overlapping / flying dots)
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
                    pygame.draw.circle(self.simulator.screen, (255, 220, 100), anchor_screen, 4)
                except Exception:
                    pass

        # Draw target line (red) if target_x is provided (target_x represents target height)
        if target_x and target_x > 0:
            # Draw a red target line from wall to right
            wall_x = 5.0
            if hasattr(sandbox, '_wall_x'):
                wall_x = sandbox._wall_x
            self.draw_line(wall_x, target_x, wall_x + 2.0, target_x, (255, 0, 0), 3)
        
        # Draw build zone outline (yellow, semi-transparent)
        if hasattr(sandbox, 'BUILD_ZONE_X_MIN'):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            
            # Draw rectangle outline
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
