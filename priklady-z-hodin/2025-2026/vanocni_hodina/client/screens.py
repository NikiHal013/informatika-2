import pygame
import sys

# UI Konstanty
WIDTH, HEIGHT = 800, 750
GRID_SIZE, CELL_SIZE = 20, 30
OFFSET_X, OFFSET_Y = 100, 100

class BaseScreen:
    """Základní třída pro všechny obrazovky v aplikaci."""
    def __init__(self, app):
        self.app = app
        self.font_m = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_s = pygame.font.SysFont("Arial", 18)

    def handle_event(self, event): pass
    def update(self): pass
    def draw(self, screen): pass

    def draw_center_text(self, screen, text, y, font, color=(255, 255, 255)):
        surf = font.render(text, True, color)
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))

class InputScreen(BaseScreen):
    """Obrazovka pro zadávání IP adresy nebo Jména studenta."""
    def __init__(self, app, prompt, next_state):
        super().__init__(app)
        self.prompt = prompt
        self.next_state = next_state

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.app.state == "INPUT_IP":
                    self.app.network.host = self.app.input_text or "127.0.0.1"
                    if self.app.network.connect():
                        self.app.state = "INPUT_NAME"
                        self.app.input_text = ""
                else:
                    self.app.player_name = self.app.input_text or "Student"
                    self.app.network.send({"type": "join", "name": self.app.player_name})
                    self.app.state = "LOBBY"
                    self.app.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.app.input_text = self.app.input_text[:-1]
            else:
                if event.unicode.isprintable():
                    self.app.input_text += event.unicode

    def draw(self, screen):
        self.draw_center_text(screen, self.prompt, 200, self.font_m)
        pygame.draw.rect(screen, (255, 255, 255), (WIDTH // 2 - 100, 300, 200, 40), 2)
        input_val = getattr(self.app, 'input_text', "")
        self.draw_center_text(screen, input_val + "|", 310, self.font_m)

class LobbyScreen(BaseScreen):
    """Obrazovka čekárny před zahájením hry učitelem."""
    def draw(self, screen):
        player_count = getattr(self.app, 'player_count', 0)
        self.draw_center_text(screen, "VÁNOČNÍ LOBBY", 100, self.font_m, (255, 215, 0))
        self.draw_center_text(screen, f"Připojených studentů: {player_count}", 250, self.font_m)
        self.draw_center_text(screen, "Čekejte na pokyn učitele...", 450, self.font_s, (150, 150, 150))

class FormationScreen(BaseScreen):
    """Obrazovka pro doplňování obrazců (grid, pohyb, statické body)."""
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            players = getattr(self.app, 'players', {})
            player_name = getattr(self.app, 'player_name', "")
            me = next((p for p in players.values() if p["name"] == player_name), None)
            
            if me:
                nx, ny = me["x"], me["y"]
                if event.key == pygame.K_UP: ny -= 1
                elif event.key == pygame.K_DOWN: ny += 1
                elif event.key == pygame.K_LEFT: nx -= 1
                elif event.key == pygame.K_RIGHT: nx += 1
                
                if nx != me["x"] or ny != me["y"]:
                    self.app.network.send({"type": "move", "x": nx, "y": ny})

    def draw(self, screen):
        time_left = getattr(self.app, 'time_left', 0)
        self.draw_center_text(screen, f"ČAS: {time_left}s", 30, self.font_m)
        
        players = getattr(self.app, 'players', {})
        player_name = getattr(self.app, 'player_name', "")
        me = next((p for p in players.values() if p["name"] == player_name), None)
        
        static_set = {tuple(s) for s in getattr(self.app, 'static_points', [])}
        walls_set = {tuple(w) for w in getattr(self.app, 'walls', [])}
        use_fog = getattr(self.app, 'use_fog', False)
        target_pos = getattr(self.app, 'target_pos', None)
        
        # Vykreslení hrací plochy (mřížka)
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                visible = True
                if use_fog and me:
                    dist = max(abs(x - me["x"]), abs(y - me["y"]))
                    if dist > 2: visible = False
                
                rect = (OFFSET_X + x * CELL_SIZE, OFFSET_Y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                
                if visible:
                    pygame.draw.rect(screen, (40, 50, 60), rect, 1)
                    
                    # Statické části obrazce (zelené)
                    if (x, y) in static_set:
                        pygame.draw.rect(screen, (30, 80, 30), (rect[0]+2, rect[1]+2, CELL_SIZE-4, CELL_SIZE-4))
                        pygame.draw.rect(screen, (50, 120, 50), (rect[0]+2, rect[1]+2, CELL_SIZE-4, CELL_SIZE-4), 1)
                    
                    # Zdi pro bludiště
                    if (x, y) in walls_set:
                        pygame.draw.rect(screen, (100, 100, 100), rect)
                    
                    # Cílová pozice bludiště
                    if target_pos and target_pos == [x, y]:
                        pygame.draw.rect(screen, (0, 150, 255), rect, 3)
                else:
                    pygame.draw.rect(screen, (0, 0, 0), rect)

        # Vykreslení hráčů
        for p in players.values():
            if use_fog and me:
                if max(abs(p["x"] - me["x"]), abs(p["y"] - me["y"])) > 2:
                    continue
            
            px, py = OFFSET_X + p["x"] * CELL_SIZE, OFFSET_Y + p["y"] * CELL_SIZE
            pygame.draw.rect(screen, p["color"], (px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4), border_radius=4)
            
            if p["name"] == player_name:
                name_surf = self.font_s.render("TY", True, (255, 255, 255))
                screen.blit(name_surf, (px + (CELL_SIZE // 2 - name_surf.get_width() // 2), py - 20))

class QuizScreen(BaseScreen):
    """Speciální obrazovka pro kvízové otázky."""
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
            if event.key in keys:
                choice = keys[event.key]
                self.app.my_vote = choice # Uložíme si lokálně naši volbu
                self.app.network.send({"type": "vote", "choice": choice})

    def draw(self, screen):
        self.draw_center_text(screen, f"ZBÝVAJÍCÍ ČAS: {self.app.time_left}s", 50, self.font_m, (255, 200, 0))
        
        # Horní panel informací
        self.draw_center_text(screen, f"Úspěšné odpovědi: {self.app.score}", 110, self.font_m, (100, 255, 100))
        
        # Průběh hlasování
        votes = self.app.votes
        total = self.app.player_count
        progress_color = (0, 200, 255) if votes < total else (0, 255, 100)
        self.draw_center_text(screen, f"Odhlasovalo: {votes} z {total} studentů", 150, self.font_s, progress_color)

        if self.app.question:
            # Box s otázkou
            q_rect = pygame.Rect(80, 200, WIDTH - 160, 420)
            pygame.draw.rect(screen, (30, 45, 65), q_rect, border_radius=15)
            pygame.draw.rect(screen, (60, 80, 110), q_rect, 2, border_radius=15)
            
            # Otázka
            self.draw_center_text(screen, self.app.question["q"], 240, self.font_m)
            
            # Možnosti
            for i, option in enumerate(self.app.question["o"]):
                y_pos = 330 + i * 60
                is_selected = (self.app.my_vote == i)
                
                # Pozadí pro vybranou možnost
                opt_rect = pygame.Rect(120, y_pos - 10, WIDTH - 240, 45)
                if is_selected:
                    pygame.draw.rect(screen, (40, 100, 80), opt_rect, border_radius=8)
                    pygame.draw.rect(screen, (0, 255, 150), opt_rect, 2, border_radius=8)
                else:
                    pygame.draw.rect(screen, (45, 60, 85), opt_rect, border_radius=8)

                text = f"{i+1}) {option}"
                color = (255, 255, 255) if not is_selected else (255, 215, 0)
                screen.blit(self.font_s.render(text, True, color), (140, y_pos))

            if self.app.my_vote is not None:
                self.draw_center_text(screen, "Váš hlas byl zaznamenán. Čekejte na ostatní...", 640, self.font_s, (0, 200, 150))
            else:
                self.draw_center_text(screen, "Hlasujte stisknutím klávesy 1 - 4", 640, self.font_s, (180, 180, 180))

class EndScreen(BaseScreen):
    """Obrazovka po skončení hry (vítězství nebo vypršení času)."""
    def draw(self, screen):
        end_msg = getattr(self.app, 'end_msg', "Konec hry")
        color = (0, 255, 100) if any(word in end_msg for word in ["Veselé", "Vítězství", "Merry"]) else (255, 100, 100)
        self.draw_center_text(screen, end_msg, HEIGHT // 2 - 50, self.font_m, color)
        self.draw_center_text(screen, "Čekejte na další pokyn učitele...", HEIGHT // 2 + 20, self.font_s, (150, 150, 150))

class GameScreen(BaseScreen):
    """
    Kontejnerová obrazovka, která automaticky přepíná mezi FORMATION a QUIZ
    podle toho, jaká data posílá server.
    """
    def __init__(self, app):
        super().__init__(app)
        self.formation_sub = FormationScreen(app)
        self.quiz_sub = QuizScreen(app)

    def handle_event(self, event):
        lvl_type = getattr(self.app, 'lvl_type', "")
        if lvl_type == "QUIZ":
            self.quiz_sub.handle_event(event)
        else:
            self.formation_sub.handle_event(event)

    def draw(self, screen):
        lvl_type = getattr(self.app, 'lvl_type', "")
        if lvl_type == "QUIZ":
            self.quiz_sub.draw(screen)
        else:
            self.formation_sub.draw(screen)