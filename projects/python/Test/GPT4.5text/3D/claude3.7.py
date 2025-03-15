import pygame
import sys
import math
import numpy as np

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Physics constants
GRAVITY = 0.5
FRICTION = 0.97
ROTATION_SPEED = 0.01
ELASTICITY = 0.8

class Ball:
    def __init__(self, x, y, radius=15):
        self.x = x
        self.y = y
        self.radius = radius
        self.vel_x = 0
        self.vel_y = 0
        self.color = RED
    
    def update(self):
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Update position
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Apply friction
        self.vel_x *= FRICTION
        self.vel_y *= FRICTION
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Hexagon:
    def __init__(self, center_x, center_y, radius=200):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.angle = 0
        self.vertices = self.calculate_vertices()
    
    def calculate_vertices(self):
        vertices = []
        for i in range(6):
            angle = self.angle + i * math.pi / 3
            x = self.center_x + self.radius * math.cos(angle)
            y = self.center_y + self.radius * math.sin(angle)
            vertices.append((x, y))
        return vertices
    
    def rotate(self):
        self.angle += ROTATION_SPEED
        self.vertices = self.calculate_vertices()
    
    def draw(self, screen):
        pygame.draw.polygon(screen, BLUE, self.vertices, 2)

def line_intersection(line1, line2):
    # Calculate the direction vectors
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        return None  # Lines are parallel

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    
    # Check if the intersection point is on both line segments
    def is_between(p, a, b):
        # Check if p is between a and b
        return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and 
                min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))
    
    if (is_between((x, y), line1[0], line1[1]) and 
        is_between((x, y), line2[0], line2[1])):
        return (x, y)
    return None

def reflect_velocity(ball, wall_p1, wall_p2):
    # Calculate the wall normal vector
    wall_vec = (wall_p2[0] - wall_p1[0], wall_p2[1] - wall_p1[1])
    wall_norm = (-wall_vec[1], wall_vec[0])  # Perpendicular to wall
    
    # Normalize the wall normal
    length = math.sqrt(wall_norm[0]**2 + wall_norm[1]**2)
    if length > 0:
        wall_norm = (wall_norm[0] / length, wall_norm[1] / length)
    
    # Make sure normal points toward ball
    ball_to_wall = (ball.x - wall_p1[0], ball.y - wall_p1[1])
    dot_product = ball_to_wall[0] * wall_norm[0] + ball_to_wall[1] * wall_norm[1]
    if dot_product < 0:
        wall_norm = (-wall_norm[0], -wall_norm[1])
    
    # Calculate the reflection
    v = (ball.vel_x, ball.vel_y)
    dot = v[0] * wall_norm[0] + v[1] * wall_norm[1]
    reflection = (
        v[0] - 2 * dot * wall_norm[0],
        v[1] - 2 * dot * wall_norm[1]
    )
    
    # Apply elasticity
    ball.vel_x = reflection[0] * ELASTICITY
    ball.vel_y = reflection[1] * ELASTICITY

def check_collision(ball, hexagon):
    # Check each edge of the hexagon
    for i in range(6):
        p1 = hexagon.vertices[i]
        p2 = hexagon.vertices[(i + 1) % 6]
        
        # Line from current position to next position
        next_x = ball.x + ball.vel_x
        next_y = ball.y + ball.vel_y
        
        # Check for collision with the line segment
        collision = line_intersection(
            ((ball.x, ball.y), (next_x, next_y)),
            (p1, p2)
        )
        
        if collision:
            # Move ball to collision point
            ball.x, ball.y = collision
            
            # Reflect velocity
            reflect_velocity(ball, p1, p2)
            return True
    
    # Check if ball is outside the hexagon
    inside = point_in_polygon(ball.x, ball.y, hexagon.vertices)
    if not inside:
        # Find closest edge and bounce off it
        min_dist = float('inf')
        closest_edge = None
        
        for i in range(6):
            p1 = hexagon.vertices[i]
            p2 = hexagon.vertices[(i + 1) % 6]
            
            # Calculate distance to edge
            dist = point_to_line_distance(ball.x, ball.y, p1, p2)
            if dist < min_dist:
                min_dist = dist
                closest_edge = (p1, p2)
        
        if closest_edge:
            # Reflect velocity off closest edge
            reflect_velocity(ball, closest_edge[0], closest_edge[1])
            
            # Move ball inside hexagon
            normal = get_normal(closest_edge[0], closest_edge[1])
            ball.x += normal[0] * (ball.radius - min_dist + 1)
            ball.y += normal[1] * (ball.radius - min_dist + 1)
            
            return True
    
    return False

def point_in_polygon(x, y, vertices):
    n = len(vertices)
    inside = False
    
    p1x, p1y = vertices[0]
    for i in range(n + 1):
        p2x, p2y = vertices[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def point_to_line_distance(x, y, line_p1, line_p2):
    # Distance from point to line segment
    x1, y1 = line_p1
    x2, y2 = line_p2
    
    A = x - x1
    B = y - y1
    C = x2 - x1
    D = y2 - y1
    
    dot = A * C + B * D
    len_sq = C * C + D * D
    
    if len_sq == 0:
        return math.sqrt(A * A + B * B)
    
    param = dot / len_sq
    
    if param < 0:
        xx = x1
        yy = y1
    elif param > 1:
        xx = x2
        yy = y2
    else:
        xx = x1 + param * C
        yy = y1 + param * D
    
    dx = x - xx
    dy = y - yy
    
    return math.sqrt(dx * dx + dy * dy)

def get_normal(p1, p2):
    # Get normal vector to line segment
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx*dx + dy*dy)
    
    if length > 0:
        nx = -dy / length
        ny = dx / length
        return (nx, ny)
    return (0, 0)

def main():
    # Set up the display
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ball Bouncing in Spinning Hexagon")
    clock = pygame.time.Clock()
    
    # Create objects
    ball = Ball(WIDTH // 2, HEIGHT // 2 - 100)
    hexagon = Hexagon(WIDTH // 2, HEIGHT // 2)
    
    # Initial velocity
    ball.vel_x = 2
    ball.vel_y = 0
    
    # Main game loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Reset ball position on space bar
                if event.key == pygame.K_SPACE:
                    ball.x = WIDTH // 2
                    ball.y = HEIGHT // 2 - 100
                    ball.vel_x = 2
                    ball.vel_y = 0
        
        # Rotate the hexagon
        hexagon.rotate()
        
        # Check for collision
        check_collision(ball, hexagon)
        
        # Update ball
        ball.update()
        
        # Draw everything
        screen.fill(BLACK)
        hexagon.draw(screen)
        ball.draw(screen)
        
        # Update the display
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()