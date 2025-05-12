import pygame
import random
import time
import math

pygame.init()
pygame.mixer.init()

# Load sounds
eat_sound = pygame.mixer.Sound("eat.mp3")
bomb_sound = pygame.mixer.Sound("bomb.mp3")
# victory_sound will be loaded on demand
# warning_sound = pygame.mixer.Sound("warning.mp3")
# rage_sound = pygame.mixer.Sound("rage_activate.mp3") # Optional sound for rage mode
pygame.mixer.music.load("bgm.mp3") # Load default BGM

# Screen setup
WIDTH, HEIGHT = 800, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hungry Snake - Boss RAGE!")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128) # Default Boss Color
DARK_RED = (139, 0, 0) # Boss Rage Color
ORANGE = (255, 165, 0)

# Clock and font
clock = pygame.time.Clock()
font_small = pygame.font.SysFont(None, 35)
font_medium = pygame.font.SysFont(None, 50)
font_large = pygame.font.SysFont(None, 75)
font_xlarge = pygame.font.SysFont(None, 100)

snake_block = 20
game_speed = 60
enemy_base_speed = 1.1 # Adjusted for balance
dart_speed_value = 15
game_border_thickness = 20

BOSS_TRIGGER_SCORE = 10 # Adjusted for easier testing, revert to 200 for release
DART_COOLDOWN_TIME = 1.0
BOSS_BASE_SPEED_NORMAL = enemy_base_speed * 1.05 # Normal boss speed
BOSS_MAX_HEALTH_HITS = 15
SNAKE_MOVE_INTERVAL = 0.08
BOSS_WARNING_DURATION = 3

def get_random_pos_unoccupied(item_size, occupied_rects, border=game_border_thickness):
    max_attempts = 100
    for _ in range(max_attempts):
        x = random.randrange(border, WIDTH - border - item_size, snake_block)
        y = random.randrange(border, HEIGHT - border - item_size, snake_block)
        potential_rect = pygame.Rect(x, y, item_size, item_size)
        is_occupied = False
        if occupied_rects:
            for occupied_rect in occupied_rects:
                if occupied_rect and potential_rect.colliderect(occupied_rect):
                    is_occupied = True; break
        if not is_occupied: return [x, y]
    return [random.randrange(border, WIDTH - border - item_size, snake_block),
            random.randrange(border, HEIGHT - border - item_size, snake_block)]

def message(msg, color, x, y, font_to_use=font_small, center_x=False, center_y=False):
    mesg = font_to_use.render(msg, True, color)
    text_rect = mesg.get_rect()
    if center_x: text_rect.centerx = x
    else: text_rect.x = x
    if center_y: text_rect.centery = y
    else: text_rect.y = y
    screen.blit(mesg, text_rect)

def draw_triangle_dart(surface, color, dart_rect, direction):
    points = []
    cx, cy = dart_rect.centerx, dart_rect.centery
    size = dart_rect.width 
    half_size = size // 2
    if direction == 'UP': points = [(cx, cy - half_size), (cx - half_size, cy + half_size), (cx + half_size, cy + half_size)]
    elif direction == 'DOWN': points = [(cx, cy + half_size), (cx - half_size, cy - half_size), (cx + half_size, cy - half_size)]
    elif direction == 'LEFT': points = [(cx - half_size, cy), (cx + half_size, cy - half_size), (cx + half_size, cy + half_size)]
    elif direction == 'RIGHT': points = [(cx + half_size, cy), (cx - half_size, cy - half_size), (cx - half_size, cy + half_size)]
    elif isinstance(direction, tuple): pygame.draw.circle(surface, color, (cx,cy), half_size); return
    if points: pygame.draw.polygon(surface, color, points)
    else: pygame.draw.rect(surface, color, dart_rect)

def get_dart_vectors(base_direction_str, num_darts, spread_angle_deg=15):
    vectors = []
    base_angle_rad = 0
    if base_direction_str == 'UP': base_angle_rad = math.radians(-90)
    elif base_direction_str == 'DOWN': base_angle_rad = math.radians(90)
    elif base_direction_str == 'LEFT': base_angle_rad = math.radians(180)
    elif base_direction_str == 'RIGHT': base_angle_rad = math.radians(0)
    if num_darts == 1:
        vectors.append((math.cos(base_angle_rad) * dart_speed_value, math.sin(base_angle_rad) * dart_speed_value))
    else:
        angle_offsets_rad = []
        if num_darts == 2:
            half_spread = math.radians(spread_angle_deg / 2)
            angle_offsets_rad = [-half_spread, half_spread]
        elif num_darts >= 3:
            spread_rad = math.radians(spread_angle_deg)
            angle_offsets_rad = [-spread_rad, 0, spread_rad]
        for offset in angle_offsets_rad:
            current_angle_rad = base_angle_rad + offset
            dx = math.cos(current_angle_rad) * dart_speed_value
            dy = math.sin(current_angle_rad) * dart_speed_value
            vectors.append((dx, dy))
    return vectors

def game_loop():
    game_state = "PLAYING"
    x, y = WIDTH // 2, HEIGHT // 2
    snake_visual_size = snake_block
    score = 0

    snake_vx, snake_vy = 0, 0
    last_committed_vx, last_committed_vy = 0, 0 # Initialize to 0,0
    last_snake_move_time = 0
    snake_move_interval = SNAKE_MOVE_INTERVAL

    apple_pos, apple_rect = None, None
    blue_item_pos, blue_item_rect = None, None
    blue_item_active_timer, apples_eaten_for_blue_item, blue_items_eaten_this_game = 0, 0, 0
    blue_item_spawn_delay = 7

    darts, dart_ready, last_dart_time = [], True, 0
    dart_cooldown = DART_COOLDOWN_TIME
    snake_facing_direction_str = 'UP'
    num_darts_per_shot = 1

    enemies, num_enemies_to_spawn_next, last_enemy_cleared_time = [], 1, 0
    enemy_respawn_delay = 5

    bombs, last_bomb_spawn_time = [], time.time()
    bomb_spawn_interval, max_bombs_on_screen = 10, 15

    shockwave_active, shockwave_radius, shockwave_charges, max_shockwave_charges = False, 0, 1, 5
    max_shockwave_radius = 250

    boss_rect, boss_health = None, 0
    boss_max_health = BOSS_MAX_HEALTH_HITS
    current_boss_speed = BOSS_BASE_SPEED_NORMAL
    boss_rage_mode_active = False
    boss_size = snake_block * 3

    warning_start_time = 0

    snake_rect = pygame.Rect(x, y, snake_visual_size, snake_visual_size)

    def get_current_occupied_rects():
        occupied = [snake_rect, apple_rect, blue_item_rect]
        occupied.extend(bombs); occupied.extend([e['rect'] for e in enemies])
        if boss_rect: occupied.append(boss_rect)
        return [r for r in occupied if r is not None]

    def spawn_apple():
        nonlocal apple_pos, apple_rect
        apple_pos = tuple(get_random_pos_unoccupied(snake_block, get_current_occupied_rects()))
        apple_rect = pygame.Rect(apple_pos[0], apple_pos[1], snake_block, snake_block)

    def spawn_blue_item():
        nonlocal blue_item_pos, blue_item_rect, blue_item_active_timer
        blue_item_pos = tuple(get_random_pos_unoccupied(snake_block, get_current_occupied_rects()))
        blue_item_rect = pygame.Rect(blue_item_pos[0], blue_item_pos[1], snake_block, snake_block)
        blue_item_active_timer = time.time()

    def spawn_enemies_wave(count):
        nonlocal enemies
        current_occupied = get_current_occupied_rects()
        for _ in range(count):
            ex, ey = get_random_pos_unoccupied(snake_block, current_occupied)
            new_enemy_rect = pygame.Rect(ex, ey, snake_block, snake_block)
            enemies.append({'rect': new_enemy_rect, 'speed': enemy_base_speed + random.uniform(-0.2, 0.2)}) # Slightly vary speed
            current_occupied.append(new_enemy_rect)

    def add_new_bomb_item():
        nonlocal bombs
        if len(bombs) >= max_bombs_on_screen: return
        bx, by = get_random_pos_unoccupied(snake_block, get_current_occupied_rects())
        bombs.append(pygame.Rect(bx, by, snake_block, snake_block))

    def initialize_boss_fight():
        nonlocal game_state, enemies, bombs, apple_pos, apple_rect, blue_item_pos, blue_item_rect
        nonlocal boss_rect, boss_health, current_boss_speed, boss_rage_mode_active
        game_state = "BOSS_FIGHT"
        enemies.clear(); bombs.clear(); apple_pos, apple_rect, blue_item_pos, blue_item_rect = None, None, None, None
        darts.clear()
        boss_x, boss_y = WIDTH // 2 - boss_size // 2, game_border_thickness + 20
        boss_rect, boss_health = pygame.Rect(boss_x, boss_y, boss_size, boss_size), boss_max_health
        current_boss_speed = BOSS_BASE_SPEED_NORMAL
        boss_rage_mode_active = False
        
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.load("boss.mp3") 
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print(f"Could not load or play boss.mp3: {e}. Playing default BGM.")
            pygame.mixer.music.load("bgm.mp3")
            pygame.mixer.music.play(-1)


    spawn_apple()
    if not enemies: spawn_enemies_wave(num_enemies_to_spawn_next); last_enemy_cleared_time = time.time()

    running_game_logic = True
    while running_game_logic:
        current_time = time.time()
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running_game_logic = False; return "QUIT"
            if game_state in ["PLAYING", "BOSS_FIGHT", "BOSS_WARNING"]:
                if event.type == pygame.KEYDOWN:
                    # Store potential new direction
                    potential_new_vx, potential_new_vy = snake_vx, snake_vy
                    potential_new_facing_str = snake_facing_direction_str

                    if (event.key == pygame.K_w or event.key == pygame.K_UP):
                        potential_new_vx, potential_new_vy, potential_new_facing_str = 0, -1, 'UP'
                    elif (event.key == pygame.K_s or event.key == pygame.K_DOWN):
                        potential_new_vx, potential_new_vy, potential_new_facing_str = 0, 1, 'DOWN'
                    elif (event.key == pygame.K_a or event.key == pygame.K_LEFT):
                        potential_new_vx, potential_new_vy, potential_new_facing_str = -1, 0, 'LEFT'
                    elif (event.key == pygame.K_d or event.key == pygame.K_RIGHT):
                        potential_new_vx, potential_new_vy, potential_new_facing_str = 1, 0, 'RIGHT'
                    
                    # Check for 180-degree turn against the *last committed* direction
                    # Allow change if snake is stationary (last_committed_vx/vy are 0)
                    can_change_direction = True
                    if (last_committed_vx != 0 or last_committed_vy != 0): # If snake was moving
                        if potential_new_vx == -last_committed_vx and potential_new_vy == -last_committed_vy:
                            can_change_direction = False
                    
                    if can_change_direction:
                        snake_vx, snake_vy = potential_new_vx, potential_new_vy
                        snake_facing_direction_str = potential_new_facing_str
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and dart_ready:
                        dart_ready, last_dart_time = False, current_time
                        dart_vectors = get_dart_vectors(snake_facing_direction_str, num_darts_per_shot)
                        for dv_x, dv_y in dart_vectors:
                            dsx, dsy = snake_rect.centerx, snake_rect.centery
                            ndr = pygame.Rect(dsx - snake_block // 2, dsy - snake_block // 2, snake_block, snake_block)
                            darts.append({'rect': ndr, 'exact_x': float(ndr.x), 'exact_y': float(ndr.y), 
                                          'dx': dv_x, 'dy': dv_y, 'visual_direction_str': snake_facing_direction_str})
                    if event.button == 3 and shockwave_charges > 0 and not shockwave_active:
                        shockwave_active, shockwave_radius, shockwave_charges = True, 1, shockwave_charges - 1

        if game_state in ["PLAYING", "BOSS_FIGHT", "BOSS_WARNING"]:
            if current_time - last_snake_move_time > snake_move_interval:
                if snake_vx != 0 or snake_vy != 0: 
                    # Before moving, check if the intended move (snake_vx, snake_vy)
                    # is a 180 of the last_committed_vx, last_committed_vy
                    # This is mostly a safeguard; the KEYDOWN logic should handle it.
                    # However, it's good for situations where snake_vx/vy might be set programmatically.
                    
                    # If the snake is trying to move into the block it just came from,
                    # and it's not stationary, ignore the input for this tick by not moving.
                    # This effectively makes it "bump" its head and wait for a new valid direction.
                    
                    # Simplified: The input logic now more robustly sets snake_vx/vy.
                    # So, we just commit the move if snake_vx/vy is set.
                    x += snake_vx * snake_block
                    y += snake_vy * snake_block
                    last_committed_vx, last_committed_vy = snake_vx, snake_vy
                else: # If snake_vx and snake_vy are 0 (player released keys or initial state)
                      # ensure last_committed direction isn't immediately reversed on next key press
                      # This case happens if player stops, then presses reverse.
                      # last_committed_vx/vy are already set from the last actual move.
                      pass

                last_snake_move_time = current_time
            
            snake_rect.topleft = (x, y); snake_rect.size = (snake_visual_size, snake_visual_size)
            if not (game_border_thickness <= snake_rect.left and snake_rect.right <= WIDTH - game_border_thickness and \
                    game_border_thickness <= snake_rect.top and snake_rect.bottom <= HEIGHT - game_border_thickness):
                bomb_sound.play(); game_state = "GAME_OVER"
            if not dart_ready and current_time - last_dart_time > dart_cooldown: dart_ready = True
        
        if game_state == "PLAYING":
            if score >= BOSS_TRIGGER_SCORE: game_state = "BOSS_WARNING"; warning_start_time = current_time
            if not blue_item_pos and apples_eaten_for_blue_item >= 3: spawn_blue_item(); apples_eaten_for_blue_item = 0
            if blue_item_rect and current_time - blue_item_active_timer > blue_item_spawn_delay: blue_item_pos, blue_item_rect = None, None
            if not enemies and current_time - last_enemy_cleared_time > enemy_respawn_delay:
                num_enemies_to_spawn_next = min(num_enemies_to_spawn_next * 2, 10)
                spawn_enemies_wave(num_enemies_to_spawn_next); last_enemy_cleared_time = current_time
            if current_time - last_bomb_spawn_time > bomb_spawn_interval: add_new_bomb_item(); last_bomb_spawn_time = current_time
            for enemy in enemies:
                if snake_rect.centerx > enemy['rect'].centerx: enemy['rect'].x += enemy['speed']
                elif snake_rect.centerx < enemy['rect'].centerx: enemy['rect'].x -= enemy['speed']
                if snake_rect.centery > enemy['rect'].centery: enemy['rect'].y += enemy['speed']
                elif snake_rect.centery < enemy['rect'].centery: enemy['rect'].y -= enemy['speed']
            if apple_rect and snake_rect.colliderect(apple_rect):
                eat_sound.play(); score += 5; snake_visual_size = min(snake_visual_size + 2, snake_block * 2.5)
                apples_eaten_for_blue_item += 1; spawn_apple()
            if blue_item_rect and snake_rect.colliderect(blue_item_rect):
                eat_sound.play(); blue_items_eaten_this_game += 1
                if blue_items_eaten_this_game == 1: num_darts_per_shot = 2
                elif blue_items_eaten_this_game >= 2: num_darts_per_shot = 3
                if blue_items_eaten_this_game % 3 == 0: shockwave_charges = min(shockwave_charges + 1, max_shockwave_charges)
                blue_item_pos, blue_item_rect = None, None
            for bomb_r in bombs:
                if snake_rect.colliderect(bomb_r): bomb_sound.play(); game_state = "GAME_OVER"; break
            if game_state == "GAME_OVER": continue
            for enemy in enemies:
                if snake_rect.colliderect(enemy['rect']): bomb_sound.play(); game_state = "GAME_OVER"; break
            if game_state == "GAME_OVER": continue

        elif game_state == "BOSS_WARNING":
            if current_time - warning_start_time > BOSS_WARNING_DURATION: initialize_boss_fight()
            for bomb_r in bombs: 
                if snake_rect.colliderect(bomb_r): bomb_sound.play(); game_state = "GAME_OVER"; break
            if game_state == "GAME_OVER": continue
            for enemy in enemies:
                if snake_rect.colliderect(enemy['rect']): bomb_sound.play(); game_state = "GAME_OVER"; break
            if game_state == "GAME_OVER": continue
        
        elif game_state == "BOSS_FIGHT":
            if boss_rect:
                if snake_rect.centerx > boss_rect.centerx: boss_rect.x += current_boss_speed
                elif snake_rect.centerx < boss_rect.centerx: boss_rect.x -= current_boss_speed
                if snake_rect.centery > boss_rect.centery: boss_rect.y += current_boss_speed
                elif snake_rect.centery < boss_rect.centery: boss_rect.y -= current_boss_speed
                boss_rect.clamp_ip(screen.get_rect())
                if snake_rect.colliderect(boss_rect): bomb_sound.play(); game_state = "GAME_OVER"

        if game_state in ["PLAYING", "BOSS_FIGHT", "BOSS_WARNING"]:
            for dart in list(darts):
                dart['exact_x'] += dart['dx']; dart['exact_y'] += dart['dy']
                dart['rect'].topleft = (int(dart['exact_x']), int(dart['exact_y']))
                if not screen.get_rect().colliderect(dart['rect']): darts.remove(dart); continue
                dart_consumed = False
                if game_state in ["PLAYING", "BOSS_WARNING"]: 
                    for enemy in list(enemies):
                        if dart['rect'].colliderect(enemy['rect']):
                            enemies.remove(enemy); score += 10
                            if dart in darts: darts.remove(dart)
                            if not enemies and game_state == "PLAYING": last_enemy_cleared_time = current_time
                            dart_consumed = True; break 
                if dart_consumed: continue 
                if game_state == "BOSS_FIGHT" and boss_rect and dart['rect'].colliderect(boss_rect):
                    boss_health -= 1
                    if dart in darts: darts.remove(dart)
                    if not boss_rage_mode_active and boss_health <= boss_max_health / 2:
                        boss_rage_mode_active = True
                        current_boss_speed = BOSS_BASE_SPEED_NORMAL * 2
                    if boss_health <= 0: game_state = "VICTORY"
            
            if shockwave_active:
                shockwave_radius += 10; shockwave_center = snake_rect.center
                if game_state in ["PLAYING", "BOSS_WARNING"]:
                    for enemy in list(enemies):
                        if math.hypot(enemy['rect'].centerx - shockwave_center[0], enemy['rect'].centery - shockwave_center[1]) < shockwave_radius + (enemy['rect'].width // 2):
                            enemies.remove(enemy); score += 10
                    if not enemies and game_state == "PLAYING": last_enemy_cleared_time = current_time
                    for bomb_r in list(bombs):
                        if math.hypot(bomb_r.centerx - shockwave_center[0], bomb_r.centery - shockwave_center[1]) < shockwave_radius + (bomb_r.width // 2):
                            bombs.remove(bomb_r); score += 2
                if game_state == "BOSS_FIGHT" and boss_rect:
                    if math.hypot(boss_rect.centerx - shockwave_center[0], boss_rect.centery - shockwave_center[1]) < shockwave_radius + (boss_rect.width // 2):
                        boss_health -= 2; shockwave_active = False
                        if not boss_rage_mode_active and boss_health <= boss_max_health / 2:
                            boss_rage_mode_active = True
                            current_boss_speed = BOSS_BASE_SPEED_NORMAL * 2
                        if boss_health <= 0: game_state = "VICTORY"
                if shockwave_radius > max_shockwave_radius and shockwave_active: shockwave_active = False

        # --- Drawing ---
        if game_state in ["PLAYING", "BOSS_FIGHT", "BOSS_WARNING"]:
            pygame.draw.rect(screen, WHITE, snake_rect)
            if game_state in ["PLAYING", "BOSS_WARNING"]:
                if apple_rect: pygame.draw.circle(screen, GREEN, apple_rect.center, snake_block // 2)
                if blue_item_rect: pygame.draw.circle(screen, BLUE, blue_item_rect.center, snake_block // 2)
                for bomb_r in bombs: pygame.draw.rect(screen, RED, bomb_r)
                for enemy in enemies: pygame.draw.rect(screen, YELLOW, enemy['rect'])
            if game_state == "BOSS_WARNING":
                if int(current_time * 2) % 2 == 0: 
                    message("WARNING!", RED, WIDTH // 2, HEIGHT // 2 - 50, font_xlarge, center_x=True, center_y=True)
                    message("BOSS INCOMING!", RED, WIDTH // 2, HEIGHT // 2 + 50, font_large, center_x=True, center_y=True)
            if game_state == "BOSS_FIGHT" and boss_rect:
                boss_color = DARK_RED if boss_rage_mode_active else PURPLE
                pygame.draw.rect(screen, boss_color, boss_rect)
                hbw, hbh = 200, 20; chw = max(0, (boss_health / boss_max_health) * hbw)
                pygame.draw.rect(screen, RED, [WIDTH // 2 - hbw // 2, 30, hbw, hbh])
                pygame.draw.rect(screen, ORANGE, [WIDTH // 2 - hbw // 2, 30, chw, hbh])
                message("BOSS", WHITE, WIDTH//2, 10, font_small, center_x=True)
            for d_info in darts: draw_triangle_dart(screen, GRAY, d_info['rect'], d_info['visual_direction_str'])
            if shockwave_active: pygame.draw.circle(screen, BLUE, snake_rect.center, int(shockwave_radius), 3)
            message(f"Score: {score}", WHITE, 10, 10); message(f"Shockwave: {shockwave_charges}", WHITE, 10, 40); message(f"Darts: {num_darts_per_shot}", WHITE, 10, 70)
            ccp = (current_time - last_dart_time) / dart_cooldown; dbw = 100 * min(1, ccp if not dart_ready else 1)
            bar_col = GREEN if dart_ready else RED
            pygame.draw.rect(screen, bar_col, [10, HEIGHT - 30, dbw, 10]); pygame.draw.rect(screen, WHITE, [10, HEIGHT - 30, 100, 10], 2)
            message("Dart CD", WHITE, 120, HEIGHT - 35)
        
        elif game_state == "GAME_OVER" or game_state == "VICTORY":
            # Stop any game/boss music first
            pygame.mixer.music.stop() 

            msg_txt = "Game Over!" if game_state == "GAME_OVER" else "VICTORY!"
            msg_col = RED if game_state == "GAME_OVER" else GREEN
            
            if game_state == "VICTORY":
                try:
                    # Using a Sound object for victory sfx as music channel is tricky here
                    victory_sfx = pygame.mixer.Sound("victory.mp3")
                    victory_sfx.play() 
                except pygame.error as e:
                    print(f"Could not load or play victory.mp3 as SFX: {e}")

            message(msg_txt, msg_col, WIDTH // 2, HEIGHT // 2 - 80, font_large, center_x=True, center_y=True)
            message(f"Final Score: {score}", WHITE, WIDTH // 2, HEIGHT // 2, font_medium, center_x=True, center_y=True)
            message("Play Again? (Y/N)", YELLOW, WIDTH // 2, HEIGHT // 2 + 80, font_medium, center_x=True, center_y=True)
            running_game_logic = False

        pygame.display.update()
        clock.tick(game_speed)

    # This stop is mainly for if the game loop exits unexpectedly (e.g. direct quit during gameplay)
    # For GAME_OVER/VICTORY, music is handled above or in the input loop.
    if game_state not in ["GAME_OVER", "VICTORY"]: # Only stop if not already handled by end screens
         pygame.mixer.music.stop()


    if game_state == "GAME_OVER" or game_state == "VICTORY":
        waiting_for_input = True
        while waiting_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # If victory_sfx was playing, it will just finish or be cut by quit
                    return "QUIT"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        # If victory_sfx was playing, it will just finish or be cut
                        return "PLAY_AGAIN"
                    if event.key == pygame.K_n:
                        # If victory_sfx was playing, it will just finish or be cut
                        return "QUIT"
            clock.tick(15)
            
    return "QUIT" 

if __name__ == '__main__':
    current_music_file = "bgm.mp3"
    while True:
        try:
            pygame.mixer.music.load(current_music_file)
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print(f"Error loading/playing music {current_music_file}: {e}")
            # Optionally, try to load a fallback or proceed without music
            if current_music_file != "bgm.mp3": # If boss music failed, try default
                try:
                    current_music_file = "bgm.mp3"
                    pygame.mixer.music.load(current_music_file)
                    pygame.mixer.music.play(-1)
                except pygame.error:
                    print("Could not load default BGM either.")


        action = game_loop() 
        
        # Music is stopped inside game_loop before it returns for GAME_OVER/VICTORY,
        # or at the very end of game_loop if it's a direct quit.

        if action == "QUIT":
            break
        elif action == "PLAY_AGAIN":
            current_music_file = "bgm.mp3" 
            # The loop will reload and play bgm.mp3 at the start of the next iteration
            continue 
    pygame.quit()