"""
ClassifyBalls task evaluation module
"""
class Evaluator:
    """
    Evaluation system: Check if balls are correctly classified into corresponding bins
    """
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.red_balls_correct = 0  # Red balls correctly classified into red bin
        self.blue_balls_correct = 0  # Blue balls correctly classified into blue bin
        self.red_balls_wrong = 0  # Incorrectly classified red balls
        self.blue_balls_wrong = 0  # Incorrectly classified blue balls
        self.total_balls = 0
        
    def check_ball_in_basket(self, ball_data):
        """
        Check if ball is in basket
        Bins are now separated: Blue (x=1.0, width=2.0), Red (x=4.5, width=2.0)
        """
        ball = ball_data['body']
        ball_x = ball.position.x
        ball_y = ball.position.y
        color = ball_data['color']
        
        # Check the CORRECT basket first based on ball color
        # This ensures balls in overlapping area are classified correctly
        if color == 'red':
            # Check red basket first for red balls
            red_basket = self.sandbox.red_basket
            if (red_basket['x'] - red_basket['width']/2 <= ball_x <= red_basket['x'] + red_basket['width']/2 and
                red_basket['y'] - red_basket['height']/2 <= ball_y <= red_basket['y'] + red_basket['height']/2):
                if not ball_data['classified']:
                    self.red_balls_correct += 1
                    ball_data['classified'] = True
                    ball_data['in_basket'] = True
                return True
            # If not in red basket, check blue basket (wrong)
            blue_basket = self.sandbox.blue_basket
            if (blue_basket['x'] - blue_basket['width']/2 <= ball_x <= blue_basket['x'] + blue_basket['width']/2 and
                blue_basket['y'] - blue_basket['height']/2 <= ball_y <= blue_basket['y'] + blue_basket['height']/2):
                if not ball_data['classified']:
                    self.red_balls_wrong += 1
                    ball_data['classified'] = True
                    ball_data['in_basket'] = True
                return True
        else:  # color == 'blue'
            # Check blue basket first for blue balls
            blue_basket = self.sandbox.blue_basket
            if (blue_basket['x'] - blue_basket['width']/2 <= ball_x <= blue_basket['x'] + blue_basket['width']/2 and
                blue_basket['y'] - blue_basket['height']/2 <= ball_y <= blue_basket['y'] + blue_basket['height']/2):
                if not ball_data['classified']:
                    self.blue_balls_correct += 1
                    ball_data['classified'] = True
                    ball_data['in_basket'] = True
                return True
            # If not in blue basket, check red basket (wrong)
            red_basket = self.sandbox.red_basket
            if (red_basket['x'] - red_basket['width']/2 <= ball_x <= red_basket['x'] + red_basket['width']/2 and
                red_basket['y'] - red_basket['height']/2 <= ball_y <= red_basket['y'] + red_basket['height']/2):
                if not ball_data['classified']:
                    self.blue_balls_wrong += 1
                    ball_data['classified'] = True
                    ball_data['in_basket'] = True
                return True
        
        return False

    def evaluate(self, step_count, max_steps):
        """
        Evaluate classification performance
        Returns: (should_stop, score, metrics)
        """
        # Check if all balls are in baskets
        for ball_data in self.sandbox.balls:
            if not ball_data['in_basket']:
                self.check_ball_in_basket(ball_data)
        
        # Calculate totals
        total_red = sum(1 for b in self.sandbox.balls if b['color'] == 'red')
        total_blue = sum(1 for b in self.sandbox.balls if b['color'] == 'blue')
        self.total_balls = len(self.sandbox.balls)
        
        # Calculate accuracy
        correct = self.red_balls_correct + self.blue_balls_correct
        wrong = self.red_balls_wrong + self.blue_balls_wrong
        total_classified = correct + wrong
        
        if total_classified > 0:
            accuracy = correct / total_classified * 100.0
        else:
            accuracy = 0.0
        
        # Check if all balls spawned and classified
        all_spawned = self.sandbox.balls_spawned >= self.sandbox.balls_to_spawn
        all_classified = total_classified >= self.total_balls and self.total_balls > 0
        
        # Success condition: All balls correctly classified
        success = (all_classified and 
                  self.red_balls_correct == total_red and 
                  self.blue_balls_correct == total_blue and
                  self.red_balls_wrong == 0 and
                  self.blue_balls_wrong == 0)
        
        # Calculate score (0-100)
        if success:
            score = 100.0
        elif total_classified > 0:
            # Calculate score based on accuracy
            score = accuracy
        else:
            score = 0.0
        
        # Check if should stop (all balls spawned and classified, or timeout)
        should_stop = (all_classified and all_spawned) or (step_count >= max_steps)
        
        metrics = {
            'total_balls': self.total_balls,
            'total_red': total_red,
            'total_blue': total_blue,
            'red_balls_correct': self.red_balls_correct,
            'blue_balls_correct': self.blue_balls_correct,
            'red_balls_wrong': self.red_balls_wrong,
            'blue_balls_wrong': self.blue_balls_wrong,
            'accuracy': accuracy,
            'success': success,
            'all_spawned': all_spawned,
            'all_classified': all_classified
        }
        
        return should_stop, score, metrics

    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'Classify red and blue balls',
            'description': 'Design a device connected to conveyor end to put red balls into red bin, blue balls into blue bin',
            'requirements': {
                'sensor': 'Need raycast sensor to detect ball color',
                'actuator': 'Need piston or motor to control diversion device',
                'logic': 'Can use logic gates and delay to build control logic',
                'red_basket': f"Red balls should enter red bin (x={self.sandbox.red_basket['x']:.1f}, range {self.sandbox.red_basket['x'] - self.sandbox.red_basket['width']/2:.1f}-{self.sandbox.red_basket['x'] + self.sandbox.red_basket['width']/2:.1f}) - wider and closer for easier classification",
                'blue_basket': f"Blue balls should enter blue bin (x={self.sandbox.blue_basket['x']:.1f}, range {self.sandbox.blue_basket['x'] - self.sandbox.blue_basket['width']/2:.1f}-{self.sandbox.blue_basket['x'] + self.sandbox.blue_basket['width']/2:.1f}) - wider for easier classification",
                'build_zone': f"Agent can only build in build area ({self.sandbox.build_zone['min_x']}, {self.sandbox.build_zone['min_y']}) to ({self.sandbox.build_zone['max_x']}, {self.sandbox.build_zone['max_y']})"
            },
            'success_criteria': {
                'primary': 'All red balls enter red bin, all blue balls enter blue bin',
                'secondary': 'No balls enter wrong bin',
                'accuracy': 'Classification accuracy 100%'
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on classification accuracy',
                'failure_score': 0
            }
        }

