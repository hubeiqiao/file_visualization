import pygame
import sys
import math
import numpy as np

# Initialize pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
SCREEN_CENTER = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Ball Bouncing in a Spinning Hexagon")

clock = pygame.time.Clock()

# Physics parameters
GRAVITY = pygame.Vector2(0, 0.5)
FRICTION = 0.99
BOUNCE_DAMPING = 0.8

# Ball parameters
ball_pos = pygame.Vector2(SCREEN_CENTER.x, SCREEN_CENTER.y - 100)
ball_vel = pygame.Vector2(3, -5)
ball_radius = 15

# Hexagon parameters
HEXAGON_RADIUS = 250
HEXAGON_SIDES = 6
angle = 0
angular_speed = 0.01  # radians per frame

def get_hexagon_points(center, radius, angle):
    points = []
    for i in range(HEXAGON_SIDES):
        theta = angle + (math.pi * 2 / HEXAGON_SIDES) * i
        x = center.x + radius * math.cos(theta)
        y = center.y + radius * math.sin(theta)
        points.append((x, y))
    return points

def collide_ball_line(p, v, r, a, b):
    ap = p - a
    ab = b - a
    ab_length_squared = ab.dot(ab)
    t = max(0, min(1, ap.dot(ab) / ab_length_squared))
    closest = a + ab * t
    normal = p - closest
    distance = normal.length()
    if distance < r and distance != 0:
        penetration = r - distance
        normal = normal.normalize()
        v_reflect = v.reflect(normal) * BOUNCE_DAMPING
        p += normal * penetration
        return True, p, v_reflect
    return False, p, v

# Main simulation loop
running = True
while running:
    clock.tick(60)
  
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
  
    # Update hexagon rotation angle
    angle += angular_speed
  
    # Physics update for ball
    ball_vel += GRAVITY
    ball_pos += ball_vel
    ball_vel *= FRICTION
    
    hexagon_points = get_hexagon_points(SCREEN_CENTER, HEXAGON_RADIUS, angle)

    # Collision detection with hexagon walls
    for i in range(HEXAGON_SIDES):
        a = pygame.Vector2(hexagon_points[i])
        b = pygame.Vector2(hexagon_points[(i + 1) % HEXAGON_SIDES])
        collided, ball_pos, ball_vel = collide_ball_line(ball_pos, ball_vel, ball_radius, a, b)
        if collided:
            break  # Only handle one collision per frame
  
    # Rendering
    screen.fill((30, 30, 30))
  
    # Draw hexagon
    pygame.draw.polygon(screen, (250, 250, 250), hexagon_points, width=3)
  
    # Draw ball
    pygame.draw.circle(screen, (255, 100, 100), (int(ball_pos.x), int(ball_pos.y)), ball_radius)
  
    pygame.display.flip()

pygame.quit()
sys.exit()