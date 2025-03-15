import pygame
import math
import random

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bouncing Ball in Rotating Hexagon")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

# Ball properties
ball_radius = 10
ball_pos = [WIDTH // 2, HEIGHT // 2]
ball_vel = [random.uniform(-3, 3), random.uniform(-3, 3)]

# Physics constants
GRAVITY = 0.2
FRICTION = 0.99
BOUNCE = 0.8  # Energy loss on bounce (0 to 1)

# Hexagon properties
hex_radius = 200
hex_center = [WIDTH // 2, HEIGHT // 2]
hex_angle = 0
hex_rot_speed = 0.02  # Radians per frame

# Calculate hexagon vertices
def get_hex_vertices(center, radius, angle):
    vertices = []
    for i in range(6):
        vertex_angle = angle + i * math.pi / 3
        x = center[0] + radius * math.cos(vertex_angle)
        y = center[1] + radius * math.sin(vertex_angle)
        vertices.append((x, y))
    return vertices

# Line intersection test
def line_intersection(p1, p2, p3, p4):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4) and 
            ccw(p1, p2, p3) != ccw(p1, p2, p4))

# Reflect velocity across a normal vector
def reflect(velocity, normal):
    dot = velocity[0] * normal[0] + velocity[1] * normal[1]
    return [
        velocity[0] - 2 * dot * normal[0],
        velocity[1] - 2 * dot * normal[1]
    ]

# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear screen
    screen.fill(BLACK)

    # Update ball physics
    ball_vel[1] += GRAVITY  # Apply gravity
    ball_vel[0] *= FRICTION  # Apply friction
    ball_vel[1] *= FRICTION
    
    # Store previous position for collision detection
    prev_pos = ball_pos.copy()
    ball_pos[0] += ball_vel[0]
    ball_pos[1] += ball_vel[1]

    # Update hexagon rotation
    hex_angle += hex_rot_speed
    vertices = get_hex_vertices(hex_center, hex_radius, hex_angle)

    # Check collision with hexagon walls
    for i in range(6):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % 6]
        
        # Check if ball crossed the wall
        if line_intersection(
            (prev_pos[0], prev_pos[1]),
            (ball_pos[0], ball_pos[1]),
            v1, v2
        ):
            # Calculate wall normal
            wall_vec = [v2[0] - v1[0], v2[1] - v1[1]]
            normal = [-wall_vec[1], wall_vec[0]]
            normal_len = math.sqrt(normal[0]**2 + normal[1]**2)
            normal = [normal[0]/normal_len, normal[1]/normal_len]
            
            # Reflect velocity and apply bounce coefficient
            ball_vel = reflect(ball_vel, normal)
            ball_vel[0] *= BOUNCE
            ball_vel[1] *= BOUNCE
            
            # Move ball back to previous position to prevent sticking
            ball_pos = prev_pos.copy()
            break

    # Keep ball within screen bounds (optional)
    if ball_pos[0] < ball_radius:
        ball_pos[0] = ball_radius
        ball_vel[0] = -ball_vel[0] * BOUNCE
    if ball_pos[0] > WIDTH - ball_radius:
        ball_pos[0] = WIDTH - ball_radius
        ball_vel[0] = -ball_vel[0] * BOUNCE
    if ball_pos[1] < ball_radius:
        ball_pos[1] = ball_radius
        ball_vel[1] = -ball_vel[1] * BOUNCE
    if ball_pos[1] > HEIGHT - ball_radius:
        ball_pos[1] = HEIGHT - ball_radius
        ball_vel[1] = -ball_vel[1] * BOUNCE

    # Draw hexagon
    pygame.draw.polygon(screen, WHITE, vertices, 2)
    
    # Draw ball
    pygame.draw.circle(screen, RED, (int(ball_pos[0]), int(ball_pos[1])), ball_radius)

    # Update display
    pygame.display.flip()
    clock.tick(60)  # 60 FPS

pygame.quit()