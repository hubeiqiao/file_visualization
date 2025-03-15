from ursina import *

app = Ursina()

# --- Parameters ---
gravity = 9.8           # Gravity acceleration.
table_size = 10         # Size of the table (plane and wall boundaries).
ball_radius = 0.5       # Radius of the ball.
impulse_strength = 10   # Strength of the flipper impulse on the ball.

# --- Create the Pinball Table ---
# Floor (table)
floor = Entity(
    model='plane',
    scale=(table_size, table_size),
    texture='white_cube',
    texture_scale=(table_size, table_size),
    collider='box'
)

# Walls
wall_thickness = 0.5
left_wall = Entity(
    model='cube',
    scale=(wall_thickness, 2, table_size),
    position=(-table_size/2, 1, 0),
    color=color.gray,
    collider='box'
)
right_wall = Entity(
    model='cube',
    scale=(wall_thickness, 2, table_size),
    position=(table_size/2, 1, 0),
    color=color.gray,
    collider='box'
)
back_wall = Entity(
    model='cube',
    scale=(table_size, 2, wall_thickness),
    position=(0, 1, -table_size/2),
    color=color.gray,
    collider='box'
)
front_wall = Entity(
    model='cube',
    scale=(table_size, 2, wall_thickness),
    position=(0, 1, table_size/2),
    color=color.gray,
    collider='box'
)

# --- Create the Ball ---
ball = Entity(
    model='sphere',
    color=color.white,
    scale=ball_radius,
    position=(0, 2, 0)
)
ball.velocity = Vec3(0, 0, 0)  # Custom attribute for simple physics.

# --- Create the Flippers ---
left_flipper = Entity(
    model='cube',
    scale=(2, 0.2, 0.5),
    position=(-2, 0.5, 2),
    color=color.red
)
right_flipper = Entity(
    model='cube',
    scale=(2, 0.2, 0.5),
    position=(2, 0.5, 2),
    color=color.blue
)
# Set the origin (pivot point) for rotation.
left_flipper.origin = (-1, 0, 0)   # Pivot at the right end.
right_flipper.origin = (1, 0, 0)     # Pivot at the left end.

# --- Update Function for Game Physics ---
def update():
    # Apply gravity to the ball.
    ball.velocity.y -= gravity * time.dt
    ball.position += ball.velocity * time.dt

    # Bounce off the floor.
    if ball.y < ball_radius:
        ball.y = ball_radius
        ball.velocity.y *= -0.8

    # Bounce off the walls.
    if ball.x < -table_size/2 + ball_radius:
        ball.x = -table_size/2 + ball_radius
        ball.velocity.x *= -0.8
    if ball.x > table_size/2 - ball_radius:
        ball.x = table_size/2 - ball_radius
        ball.velocity.x *= -0.8
    if ball.z < -table_size/2 + ball_radius:
        ball.z = -table_size/2 + ball_radius
        ball.velocity.z *= -0.8
    if ball.z > table_size/2 - ball_radius:
        ball.z = table_size/2 - ball_radius
        ball.velocity.z *= -0.8

    # --- Simple Flipper-Ball Interaction ---
    # If a flipper is active (rotated) and the ball is nearby, add an impulse.
    left_dist = distance(ball.position, left_flipper.world_position)
    if left_flipper.rotation_z != 0 and left_dist < 2:
        direction = (ball.position - left_flipper.world_position).normalized()
        ball.velocity += direction * impulse_strength

    right_dist = distance(ball.position, right_flipper.world_position)
    if right_flipper.rotation_z != 0 and right_dist < 2:
        direction = (ball.position - right_flipper.world_position).normalized()
        ball.velocity += direction * impulse_strength

# --- Input Handling for Flippers ---
def input(key):
    if key == 'a':
        left_flipper.rotation_z = -45  # Raise left flipper.
    elif key == 'a up':
        left_flipper.rotation_z = 0    # Return left flipper.
    if key == 'l':
        right_flipper.rotation_z = 45  # Raise right flipper.
    elif key == 'l up':
        right_flipper.rotation_z = 0   # Return right flipper.

app.run()           