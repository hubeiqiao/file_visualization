import pygame
import math

# Constants
WIDTH, HEIGHT = 600, 600
GRAVITY = 0.5
FRICTION = 0.99
HEXAGON_RADIUS = 200
BALL_RADIUS = 10
ROTATION_SPEED = 1  # Degrees per frame

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 2
        self.vy = 0
    
    def update(self):
        self.vy += GRAVITY  # Apply gravity
        self.vx *= FRICTION  # Apply friction
        self.vy *= FRICTION
        
        self.x += self.vx
        self.y += self.vy

    def check_collision(self, hexagon_vertices):
        """Check collision with the hexagon and update velocity accordingly"""
        for i in range(len(hexagon_vertices)):
            p1 = hexagon_vertices[i]
            p2 = hexagon_vertices[(i + 1) % len(hexagon_vertices)]
            
            # Vector from p1 to p2
            edge_vector = (p2[0] - p1[0], p2[1] - p1[1])
            edge_length = math.sqrt(edge_vector[0] ** 2 + edge_vector[1] ** 2)
            edge_unit = (edge_vector[0] / edge_length, edge_vector[1] / edge_length)

            # Ball to edge vector
            ball_vector = (self.x - p1[0], self.y - p1[1])
            projection = ball_vector[0] * edge_unit[0] + ball_vector[1] * edge_unit[1]

            # Closest point on edge
            if projection < 0:
                closest_point = p1
            elif projection > edge_length:
                closest_point = p2
            else:
                closest_point = (p1[0] + projection * edge_unit[0], p1[1] + projection * edge_unit[1])

            # Distance from ball to closest point
            dist_x = self.x - closest_point[0]
            dist_y = self.y - closest_point[1]
            distance = math.sqrt(dist_x ** 2 + dist_y ** 2)

            # If collision occurs
            if distance < BALL_RADIUS:
                normal = (dist_x / distance, dist_y / distance)
                dot_product = self.vx * normal[0] + self.vy * normal[1]
                self.vx -= 2 * dot_product * normal[0]
                self.vy -= 2 * dot_product * normal[1]

                # Move the ball outside the hexagon
                self.x = closest_point[0] + normal[0] * BALL_RADIUS
                self.y = closest_point[1] + normal[1] * BALL_RADIUS

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 0, 0), (int(self.x), int(self.y)), BALL_RADIUS)

def get_hexagon_vertices(center_x, center_y, radius, angle):
    """Return the vertices of a rotated hexagon"""
    vertices = []
    for i in range(6):
        theta = math.radians(angle + i * 60)
        x = center_x + radius * math.cos(theta)
        y = center_y + radius * math.sin(theta)
        vertices.append((x, y))
    return vertices

def main():
    running = True
    ball = Ball(WIDTH // 2, HEIGHT // 2 - 100)
    angle = 0

    while running:
        screen.fill((30, 30, 30))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Rotate hexagon
        angle += ROTATION_SPEED
        hexagon_vertices = get_hexagon_vertices(WIDTH // 2, HEIGHT // 2, HEXAGON_RADIUS, angle)

        # Update ball physics
        ball.update()
        ball.check_collision(hexagon_vertices)

        # Draw hexagon
        pygame.draw.polygon(screen, (0, 255, 255), hexagon_vertices, 2)

        # Draw ball
        ball.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()