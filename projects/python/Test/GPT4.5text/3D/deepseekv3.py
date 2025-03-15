import pygame
import math
import sys

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bouncing Ball in Spinning Hexagon")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Clock
clock = pygame.time.Clock()

# Physics constants
GRAVITY = 0.5
FRICTION = 0.99
BALL_RADIUS = 15
BALL_SPEED_X = 5
BALL_SPEED_Y = 0
HEXAGON_RADIUS = 200
HEXAGON_SPEED = 1  # Degrees per frame

# Ball properties
ball_pos = [WIDTH // 2, HEIGHT // 2]
ball_vel = [BALL_SPEED_X, BALL_SPEED_Y]

# Hexagon properties
hexagon_angle = 0  # Current rotation angle in degrees

def rotate_point(point, angle, center):
    """Rotate a point around a center by a given angle."""
    angle_rad = math.radians(angle)
    x, y = point
    cx, cy = center
    dx = x - cx
    dy = y - cy
    new_x = cx + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
    new_y = cy + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
    return (new_x, new_y)

def get_hexagon_points(center, radius, angle):
    """Get the vertices of a hexagon centered at `center` with a given radius and rotation angle."""
    points = []
    for i in range(6):
        x = center[0] + radius * math.cos(math.radians(60 * i + angle))
        y = center[1] + radius * math.sin(math.radians(60 * i + angle))
        points.append((x, y))
    return points

def line_intersection(line1, line2):
    """Find the intersection point of two lines."""
    x1, y1 = line1[0]
    x2, y2 = line1[1]
    x3, y3 = line2[0]
    x4, y4 = line2[1]

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None  # Lines are parallel

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    return (px, py)

def closest_point_on_line(point, line):
    """Find the closest point on a line to a given point."""
    x1, y1 = line[0]
    x2, y2 = line[1]
    px, py = point

    dx = x2 - x1
    dy = y2 - y1
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return (x1 + t * dx, y1 + t * dy)

def reflect_velocity(vel, normal):
    """Reflect the velocity vector off a surface with a given normal."""
    dot = vel[0] * normal[0] + vel[1] * normal[1]
    new_x = vel[0] - 2 * dot * normal[0]
    new_y = vel[1] - 2 * dot * normal[1]
    return [new_x, new_y]

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Update hexagon rotation
    hexagon_angle += HEXAGON_SPEED
    if hexagon_angle >= 360:
        hexagon_angle -= 360

    # Update ball position and velocity
    ball_vel[1] += GRAVITY
    ball_pos[0] += ball_vel[0]
    ball_pos[1] += ball_vel[1]

    # Apply friction
    ball_vel[0] *= FRICTION
    ball_vel[1] *= FRICTION

    # Get hexagon points
    hexagon_points = get_hexagon_points((WIDTH // 2, HEIGHT // 2), HEXAGON_RADIUS, hexagon_angle)

    # Check for collisions with hexagon walls
    for i in range(6):
        p1 = hexagon_points[i]
        p2 = hexagon_points[(i + 1) % 6]
        line = [p1, p2]

        # Find the closest point on the line to the ball
        closest = closest_point_on_line(ball_pos, line)
        distance = math.hypot(ball_pos[0] - closest[0], ball_pos[1] - closest[1])

        if distance <= BALL_RADIUS:
            # Calculate the normal vector of the line
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            normal = [-dy, dx]
            length = math.hypot(normal[0], normal[1])
            normal = [normal[0] / length, normal[1] / length]

            # Reflect the ball's velocity
            ball_vel = reflect_velocity(ball_vel, normal)

            # Move the ball outside the wall to prevent sticking
            overlap = BALL_RADIUS - distance
            ball_pos[0] += normal[0] * overlap
            ball_pos[1] += normal[1] * overlap

    # Clear the screen
    screen.fill(WHITE)

    # Draw the hexagon
    pygame.draw.polygon(screen, BLACK, hexagon_points, 2)

    # Draw the ball
    pygame.draw.circle(screen, RED, (int(ball_pos[0]), int(ball_pos[1])), BALL_RADIUS)

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

# Quit Pygame
pygame.quit()
sys.exit()