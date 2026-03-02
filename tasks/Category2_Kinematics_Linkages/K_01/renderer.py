"""
K-01: The Walker task rendering module
2D side-view linkage mechanism: zoomed view, clear torso/legs, deduplicated joints.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, revoluteJoint

RENDER_SCALE = 2.0  # Zoom so mechanism is clearly visible


class K01Renderer(Renderer):
    """K-01: The Walker — 2D side-view mechanism, zoomed for clarity."""

    def world_to_screen(self, world_x, world_y):
        """Apply zoom so mechanism appears larger."""
        ppm = self.simulator.ppm * RENDER_SCALE
        screen_x = world_x * ppm - self.camera_offset_x
        screen_y = self.simulator.screen_height - (world_y * ppm) - self.camera_offset_y
        return (int(screen_x), int(screen_y))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        if agent_body:
            cx = agent_body.position.x
            self.set_camera_offset(cx * ppm * RENDER_SCALE - sw / 2, 0)
        else:
            self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))  # Dark background (match Category1_Statics_Equilibrium)
        
        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Ground - brown/rock color (unified with Category1)
                self.draw_body(body,
                             dynamic_color=(100, 150, 240),
                             static_color=(150, 100, 50),
                             outline_color=(200, 150, 100),
                             outline_width=2)
        
        # Identify torso (agent_body) and legs
        torso_body = agent_body
        leg_bodies = set()
        
        # Find all bodies that are connected to torso via joints (these are legs)
        if torso_body and hasattr(sandbox, '_joints'):
            for joint in sandbox._joints:
                if isinstance(joint, revoluteJoint):
                    if joint.bodyA == torso_body:
                        leg_bodies.add(joint.bodyB)
                    elif joint.bodyB == torso_body:
                        leg_bodies.add(joint.bodyA)
        
        # Also check if we can identify legs from the walker structure
        # In our design, legs are all bodies except torso
        if torso_body:
            for body in sandbox.world.bodies:
                if body.type == dynamicBody and body != torso_body:
                    # Check if it's connected to torso (it's a leg)
                    if body not in leg_bodies:
                        # Check if connected via any joint
                        for joint in sandbox._joints:
                            if (joint.bodyA == torso_body and joint.bodyB == body) or \
                               (joint.bodyB == torso_body and joint.bodyA == body):
                                leg_bodies.add(body)
                                break
        
        # Draw dynamic objects (walker structure) with different colors
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if it's template
                is_template = False
                if hasattr(sandbox, '_walker_bodies'):
                    for key, value in sandbox._walker_bodies.items():
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
                elif body == torso_body:
                    # Torso - red (match Category1 vehicle style)
                    self.draw_body(body,
                                 dynamic_color=(255, 100, 100),
                                 static_color=(150, 100, 50),
                                 outline_color=(255, 150, 150),
                                 outline_width=3)
                elif body in leg_bodies:
                    # Legs - green (match Category1 bridge/links style)
                    self.draw_body(body,
                                 dynamic_color=(100, 200, 100),
                                 static_color=(150, 100, 50),
                                 outline_color=(50, 150, 50),
                                 outline_width=2)
                else:
                    # Other walker parts - blue
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(150, 100, 50),
                                 outline_color=(100, 150, 255),
                                 outline_width=2)
        
        # Torso emphasis: clear "body" circle so main body is obvious
        if torso_body:
            pos = self.world_to_screen(torso_body.position.x, torso_body.position.y)
            r = max(8, int(0.22 * ppm * RENDER_SCALE))
            pygame.draw.circle(self.simulator.screen, (255, 100, 100), pos, r)
            pygame.draw.circle(self.simulator.screen, (255, 150, 150), pos, r, 2)

        # Joints: one small marker per unique anchor (no overlapping circles / flying dots)
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

        if target_x and target_x > 0:
            self.draw_line(target_x, 1.0, target_x, 10.0, (255, 0, 0), 3)
        
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
