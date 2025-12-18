from collections import Counter
import time
import random

class BaseLevel:
    """Základní blok pro všechny herní úrovně."""
    def __init__(self, config, players_count):
        self.id = config["id"]
        self.type = config["type"]
        self.title = config["title"]
        self.description = config["description"]
        self.time_limit = config.get("time_limit", 60)
        self.start_time = time.time()
        self.finished = False

    def get_time_left(self):
        """Vrací zbývající čas do konce úrovně v sekundách."""
        return max(0, int(self.time_limit - (time.time() - self.start_time)))

    def check_victory(self, players):
        """Metoda pro kontrolu vítězství, kterou musí implementovat konkrétní úrovně."""
        return False

class FormationLevel(BaseLevel):
    """Level, kde studenti doplňují chybějící body v komplexním vánočním obrazu."""
    def __init__(self, config, players_count, shapes_config):
        super().__init__(config, players_count)
        # Získáme všechny body definovaného tvaru z konfigurace
        shape_points = shapes_config.get(config["shape_key"], [])
        
        # Náhodně vybereme body, které musí obsadit studenti (podle aktuálního počtu hráčů).
        # Tyto body jsou pro studenty neviditelné (musí je odhadnout).
        if len(shape_points) >= players_count:
            self.target_points = random.sample(shape_points, players_count)
        else:
            # Pokud je hráčů více než bodů v definici, použijeme všechny body
            self.target_points = list(shape_points)
            
        # Ostatní body obrazu, které tam zůstanou jako statická nápověda (šablona)
        self.static_points = [p for p in shape_points if p not in self.target_points]

    def check_victory(self, players):
        """Kontroluje, zda jsou všechny chybějící body (target_points) obsazeny hráči."""
        if not players or not self.target_points: 
            return False
            
        occupied_count = 0
        # Převedeme aktuální pozice hráčů na seznam n-tic pro snadné porovnání
        p_positions = [(p['x'], p['y']) for p in players.values()]
        
        # Zkontrolujeme každý cílový bod
        for target in self.target_points:
            # Bod musí být obsazen alespoň jedním hráčem
            if tuple(target) in p_positions:
                occupied_count += 1
        
        # Vítězství: Počet obsazených unikátních cílových bodů odpovídá celkovému počtu cílů
        return occupied_count >= len(self.target_points)
    
class QuizLevel(BaseLevel):
    """Týmový kvíz s demokratickým hlasováním."""
    def __init__(self, config, players_count):
        super().__init__(config, players_count)
        self.pool = config["pool"]
        self.target_score = config.get("target_score", 10)
        self.score = 0
        self.current_q = random.choice(self.pool)
        self.votes = {} # player_id -> choice_index

    def process_vote(self, player_id, choice_idx):
        """Uloží hlas konkrétního hráče."""
        self.votes[player_id] = choice_idx

    def evaluate_votes(self, total_players):
        """Vyhodnotí hlasování, pokud všichni odhlasovali."""
        if len(self.votes) < total_players or total_players == 0:
            return False # Ještě neodhlasovali všichni
        
        # Zjisti nejčastější hlas (většina)
        counts = Counter(self.votes.values())
        majority_choice = counts.most_common(1)[0][0]
        
        # Kontrola správnosti
        correct_idx = int(self.current_q["a"])
        if majority_choice == correct_idx:
            self.score += 1
        
        # Vyčisti hlasy a vyber novou otázku
        self.votes = {}
        if self.score >= self.target_score:
            return True # Level dokončen
        else:
            self.current_q = random.choice(self.pool)
            return False # Pokračujeme s další otázkou

    def check_victory(self, players):
        # Vítězství je řízeno přes evaluate_votes, ne přes pozice
        return self.score >= self.target_score