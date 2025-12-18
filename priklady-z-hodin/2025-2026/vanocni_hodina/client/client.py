import pygame
import sys
from network_manager import NetworkManager
from screens import InputScreen, LobbyScreen, GameScreen, EndScreen

pygame.init()
pygame.mixer.init()

# Inicializace okna
pygame.init()
WIDTH, HEIGHT = 800, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vánoční Programátorská Výzva")

class GameApp:
    def __init__(self):
        self.network = NetworkManager("127.0.0.1")
        self.network.on_message_callback = self.on_message
        
        self.state = "INPUT_IP" 
        self.player_name = ""
        self.input_text = ""
        
        # Synchronizovaná data
        self.player_count = 0
        self.players = {}
        self.targets = []
        self.static_points = []
        self.time_left = 0
        self.lvl_type = ""
        self.end_msg = ""
        
        # Kvízová data
        self.question = None
        self.score = 0
        self.votes = 0
        self.my_vote = None # Index naší vybrané odpovědi

        self.screens = {
            "INPUT_IP": InputScreen(self, "IP", "INPUT_NAME"),
            "INPUT_NAME": InputScreen(self, "Jméno", "LOBBY"),
            "LOBBY": LobbyScreen(self),
            "GAME": GameScreen(self),
            "END": EndScreen(self)
        }
        self.play_background_music()

    def play_background_music(self):
        """Načte a spustí vánoční skladbu v nekonečné smyčce."""
        try:
            # Předpokládáme, že soubor 'christmas.mp3' je v adresáři s klientem.
            # Pokud soubor chybí, odchytíme chybu, aby se aplikace spustila i bez zvuku.
            pygame.mixer.music.load("Jingle-Bells.mp3")
            pygame.mixer.music.set_volume(0.2) # Nastavení nižší hlasitosti (20%)
            pygame.mixer.music.play(-1) # Parametr -1 zajistí opakování po skončení
        except pygame.error:
            print("Upozornění: Soubor 'christmas.mp3' nebyl nalezen. Hra bude bez hudby.")


    def on_message(self, msg):
        m_type = msg.get("type")
        if m_type == "lobby_sync":
            self.player_count = msg["count"]
        elif m_type == "start_level":
            self.state = "GAME"
            self.end_msg = ""
            self.my_vote = None
        elif m_type == "sync":
            self.lvl_type = msg["lvl_type"]
            self.time_left = msg["time_left"]
            self.players = msg["players"]
            self.static_points = msg.get("static_points", [])
            new_q = msg.get("question")
            if self.question != new_q:
                self.my_vote = None
                self.question = new_q
            self.score = msg.get("score", 0)
            self.votes = msg.get("votes", 0)
        elif m_type in ["victory", "game_over"]:
            self.state = "END"
            self.end_msg = msg.get("msg", "Konec hry")

    def run(self):
        clock = pygame.time.Clock()
        while True:
            current_screen = self.screens.get(self.state)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if current_screen:
                    current_screen.handle_event(event)

            if current_screen:
                screen.fill((20, 30, 40))
                current_screen.draw(screen)
            
            pygame.display.flip()
            clock.tick(30)

if __name__ == "__main__":
    app = GameApp()
    app.run()