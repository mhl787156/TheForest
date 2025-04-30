import argparse
import pygame
import serial
import time

# Initialize pygame
pygame.init()

# Define screen dimensions and colors
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 200
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BUTTON_COLOR = (100, 100, 255)
BUTTON_COLOR_ACTIVE = (255, 100, 100)

# Button dimensions and positions
BUTTON_WIDTH, BUTTON_HEIGHT = 80, 50
BUTTON_SPACING = 20
BUTTONS_Y = (SCREEN_HEIGHT - BUTTON_HEIGHT) // 2

# Parse arguments
parser = argparse.ArgumentParser(description="Simulated Arduino with Pygame GUI.")
parser.add_argument("--port", type=str, required=True, help="Serial port for the simulator (e.g., /dev/pts/4).")
args = parser.parse_args()

# Initialize serial connection
serial_port = args.port
baud_rate = 9600

try:
    arduino_sim = serial.Serial(serial_port, baud_rate, timeout=1)
    print(f"Arduino simulator connected to {serial_port}")
except Exception as e:
    print(f"Error connecting to serial port {serial_port}: {e}")
    exit(1)

# Create screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Simulated Arduino Buttons")

# Create button states (initially all false)
button_states = [False] * 6

# Create button rectangles
buttons = [
    pygame.Rect(
        BUTTON_SPACING + i * (BUTTON_WIDTH + BUTTON_SPACING), BUTTONS_Y, BUTTON_WIDTH, BUTTON_HEIGHT
    )
    for i in range(6)
]

# Send button states over serial
def send_button_states():
    state_strings = ["1" if state else "0" for state in button_states]
    message = f"CAP,{','.join(state_strings)}\n"
    arduino_sim.write(message.encode('utf-8'))
    print(f"Sent: {message.strip()}")

# Main loop
running = True
last_send_time = time.time()

while running:
    screen.fill(WHITE)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if a button was clicked
            for i, button in enumerate(buttons):
                if button.collidepoint(event.pos):
                    button_states[i] = not button_states[i]  # Toggle button state
                    send_button_states()  # Send updated states

    # Draw buttons
    for i, button in enumerate(buttons):
        color = BUTTON_COLOR_ACTIVE if button_states[i] else BUTTON_COLOR
        pygame.draw.rect(screen, color, button)
        # Draw button labels
        font = pygame.font.Font(None, 36)
        text = font.render(f"B{i+1}", True, WHITE)
        text_rect = text.get_rect(center=button.center)
        screen.blit(text, text_rect)

    # Update display
    pygame.display.flip()

    # Periodically send states to simulate Arduino loop behavior
    # if time.time() - last_send_time > 1:  # Send every second
    #     send_button_states()
    #     last_send_time = time.time()

# Clean up
arduino_sim.close()
pygame.quit()
print("Simulation ended.")
