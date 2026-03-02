"""
S-03: The Cantilever task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """Evaluation system for S-03: The Cantilever"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.target_reach = float(terrain_bounds.get("target_reach", 14.0))
        self.min_tip_height = float(terrain_bounds.get("min_tip_height", -2.5))
        self.load_hold_time = 10.0
        
        self.max_reach = 0.0
        self.min_tip_y = float('inf')  # Track lowest tip height (no sagging below this)
        self.load_attach_time = float(terrain_bounds.get("load_attach_time", 5.0))
        self.load2_attach_time = float(terrain_bounds.get("second_load_attach_time", 10.0))
        self.load_hold_start = None
        self.load2_hold_start = None
        self.anchor_broken = False
        self.tip_sagged = False
        self.initial_joint_count = 0
        self.initial_wall_joint_count = 0
        self.max_anchor_torque_seen = 0.0
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        # Use instance variables if available (for mutated tasks), otherwise fall back to class constants
        env_class = type(environment)
        try:
            # Try to use instance variables first (for mutated tasks with custom parameters)
            self.TARGET_REACH = getattr(environment, '_target_reach', env_class.TARGET_REACH)
            self.MAX_ANCHOR_POINTS = getattr(environment, '_max_anchor_points', env_class.MAX_ANCHOR_POINTS)
            self.MAX_ANCHOR_TORQUE = getattr(environment, '_max_anchor_torque', env_class.MAX_ANCHOR_TORQUE)
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate cantilever performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Track initial joint count
        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
            self.initial_wall_joint_count = len(self.environment._wall_joints)
        
        # Get structure reach
        current_reach = self.environment.get_structure_reach()
        self.max_reach = max(self.max_reach, current_reach)
        
        # Track tip height (rightmost point): use tip load body if attached, else rightmost structure body
        tip_y = None
        load_body = self.environment._terrain_bodies.get("load")
        if load_body:
            tip_y = load_body.position.y
        elif self.environment._bodies:
            rightmost = max(self.environment._bodies, key=lambda b: b.position.x)
            tip_y = rightmost.position.y
        if tip_y is not None:
            self.min_tip_y = min(self.min_tip_y, tip_y)
            if self.min_tip_y < self.min_tip_height:
                self.tip_sagged = True
        
        # Check if load is attached and track hold time
        time_step = TIME_STEP
        current_time = step_count * time_step
        
        # Track anchor torque
        current_max_torque = 0.0
        for joint in self.environment._wall_joints:
            if hasattr(joint, 'GetReactionTorque'):
                try:
                    torque = abs(joint.GetReactionTorque(time_step))
                    current_max_torque = max(current_max_torque, torque)
                except:
                    pass
        self.max_anchor_torque_seen = max(self.max_anchor_torque_seen, current_max_torque)
        
        # Get load information
        load_body = self.environment._terrain_bodies.get("load")
        load_position_x = None
        if load_body:
            load_position_x = load_body.position.x
        
        if current_time >= self.load_attach_time:
            if self.load_hold_start is None:
                self.load_hold_start = current_time
        if current_time >= self.load2_attach_time:
            if self.load2_hold_start is None:
                self.load2_hold_start = current_time
            
            # Check if anchor broke (compare current wall joints with initial count)
            if len(self.environment._wall_joints) < self.initial_wall_joint_count:
                self.anchor_broken = True
        
        # Check success: reach, both loads held 10s each, no anchor break
        reach_ok = self.max_reach >= self.target_reach
        load_ok = (self.load_hold_start is not None and
                  current_time >= self.load_hold_start + self.load_hold_time)
        load2_ok = (self.load2_hold_start is not None and
                   current_time >= self.load2_hold_start + self.load_hold_time)
        anchor_ok = not self.anchor_broken
        tip_height_ok = not self.tip_sagged  # Tip must not sag below min_tip_height
        
        success = reach_ok and load_ok and load2_ok and anchor_ok and tip_height_ok
        
        # Check failures
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Only check failures after load has been attached for a reasonable time
        # Give structure time to stabilize after load attachment
        min_check_time_after_load = 0.5  # Wait 0.5s after load attachment before checking failures
        
        if self.anchor_broken:
            failed = True
            failure_reason = f"Wall anchor broke (torque exceeded {self.MAX_ANCHOR_TORQUE} Nm)"
        elif self.tip_sagged:
            failed = True
            failure_reason = f"Structure sagged too much (tip dropped below {self.min_tip_height}m; min_tip_y={self.min_tip_y:.2f}m)"
        elif not reach_ok and current_time >= self.load_attach_time + min_check_time_after_load:
            failed = True
            failure_reason = f"Structure reach {self.max_reach:.2f}m does not meet {self.target_reach}m target"
        elif (self.load_hold_start is not None and
              current_time >= self.load_hold_start + self.load_hold_time and
              not load_ok):
            failed = True
            failure_reason = "Failed to hold tip load for 10s"
        elif (self.load2_hold_start is not None and
              current_time >= self.load2_hold_start + self.load_hold_time and
              not load2_ok):
            failed = True
            failure_reason = "Failed to hold mid-span load for 10s"
        
        # Calculate score
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            reach_score = min(self.max_reach / self.target_reach, 1.0) * 30
            load_score = 30.0 if load_ok else 0.0
            load2_score = 25.0 if load2_ok else 0.0
            tip_score = 15.0 if tip_height_ok else 0.0
            score = reach_score + load_score + load2_score + tip_score
        
        metrics = {
            'max_reach': self.max_reach,
            'min_tip_y': self.min_tip_y if self.min_tip_y != float('inf') else None,
            'min_tip_height': self.min_tip_height,
            'tip_sagged': self.tip_sagged,
            'current_reach': current_reach,
            'target_reach': self.target_reach,
            'load_attached': self.load_hold_start is not None,
            'load_hold_time': (current_time - self.load_hold_start) if self.load_hold_start else 0,
            'load2_attached': self.load2_hold_start is not None,
            'load2_hold_time': (current_time - self.load2_hold_start) if self.load2_hold_start else 0,
            'load_mass': getattr(self.environment, 'LOAD_MASS', 600.0),
            'load2_mass': getattr(self.environment, 'SECOND_LOAD_MASS', 400.0),
            'load_position_x': load_position_x,
            'anchor_broken': self.anchor_broken,
            'anchor_count': len(self.environment._wall_joints),
            'max_anchor_points': self.MAX_ANCHOR_POINTS,
            'max_anchor_torque': self.max_anchor_torque_seen,
            'max_anchor_torque_limit': self.MAX_ANCHOR_TORQUE,
            'structure_mass': self.environment.get_structure_mass(),
            'joint_count': len(self.environment._joints),
            'initial_joint_count': self.initial_joint_count,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        """Check design constraints"""
        violations = []
        
        if len(self.environment._wall_joints) > self.MAX_ANCHOR_POINTS:
            violations.append(f"Too many wall anchors: {len(self.environment._wall_joints)} > {self.MAX_ANCHOR_POINTS}")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-03: The Cantilever',
            'description': 'Construct a horizontal structure anchored to wall; two loads (tip + mid-span)',
            'target_reach': self.target_reach,
            'success_criteria': {
                'reach': f'Tip x >= {self.target_reach}m',
                'load': 'Hold tip load and mid-span load for 10s each',
                'anchor': 'No wall anchors break'
            }
        }
