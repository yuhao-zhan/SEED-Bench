import Box2D
import pygame
import sys
import platform

def check():
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    try:
        import Box2D
        # Try to get version if available
        print(f"Box2D version: {getattr(Box2D, '__version__', 'unknown')}")
    except ImportError:
        print("Box2D not found")
    
    try:
        import pygame
        print(f"Pygame version: {pygame.__version__}")
    except ImportError:
        print("Pygame not found")

    # Test gravity stability
    world = Box2D.b2.world(gravity=(0, -60))
    ground = world.CreateStaticBody(position=(0, 0))
    ground.CreatePolygonFixture(box=(10, 1))
    
    body = world.CreateDynamicBody(position=(0, 2))
    body.CreatePolygonFixture(box=(0.5, 1), density=1.0)
    
    # Run 10 steps and see if it teleports
    print("Test simulation (10 steps at -60g):")
    for i in range(10):
        world.Step(1.0/60.0, 20, 20)
        print(f"  Step {i}: y={body.position.y:.6f}")

if __name__ == "__main__":
    check()
