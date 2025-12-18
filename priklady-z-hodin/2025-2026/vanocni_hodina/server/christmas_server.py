import socket
import threading
import json
import time
import os
import sys
from levels_logic import FormationLevel, QuizLevel

class ChristmasServer:
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 5555
        self.clients = {} # socket: addr
        self.player_data = {} # socket: dict
        self.game_started = False
        self.current_level = None
        self.level_idx = 0
        
        with open('levels.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(20)

    def log(self, msg):
        print(f"[*] {msg}")
        sys.stdout.flush()

    def broadcast(self, data):
        msg = (json.dumps(data) + "\n").encode('utf-8')
        for client in list(self.clients.keys()):
            try:
                client.sendall(msg)
            except:
                self.remove_client(client)

    def remove_client(self, conn):
        if conn in self.clients: del self.clients[conn]
        if conn in self.player_data: del self.player_data[conn]
        conn.close()
        self.broadcast({"type": "lobby_sync", "count": len(self.clients)})

    def start_level(self):
        if self.level_idx >= len(self.config["level_sequence"]):
            self.broadcast({"type": "victory", "msg": "Merry Christmas! All levels cleared!"})
            self.game_started = False
            return

        conf = self.config["level_sequence"][self.level_idx]
        p_count = len(self.player_data)

        if conf["type"] == "FORMATION":
            self.current_level = FormationLevel(conf, p_count, self.config["shapes"])
        elif conf["type"] == "MAZE":
            self.current_level = MazeLevel(conf, p_count)
        elif conf["type"] == "QUIZ":
            self.current_level = QuizLevel(conf, p_count)

        self.broadcast({
            "type": "start_level",
            "title": self.current_level.title,
            "desc": self.current_level.description
        })

    def game_loop(self):
        while True:
            if self.game_started and self.current_level:
                # Check Victory
                if self.current_level.check_victory(self.player_data):
                    self.level_idx += 1
                    self.start_level()
                
                # Check Timeout
                if self.current_level.get_time_left() <= 0:
                    self.broadcast({"type": "game_over", "msg": "Time is up! Back to lobby."})
                    self.game_started = False
                    self.current_level = None
                
                # Sync
                self.sync_players()
            time.sleep(0.1)

    def sync_players(self):
        if not self.current_level: return
        data = {
            "type": "sync",
            "lvl_type": self.current_level.type,
            "time_left": self.current_level.get_time_left(),
            "players": {id(s): d for s, d in self.player_data.items()}
        }
        if self.current_level.type == "FORMATION":
            data["targets"] = self.current_level.target_points
            data["static_points"] = self.current_level.static_points
        elif self.current_level.type == "MAZE":
            data["walls"] = self.current_level.walls
            data["target"] = self.current_level.target
            data["use_fog"] = self.current_level.use_fog
        elif self.current_level.type == "QUIZ":
            data["question"] = self.current_level.current_q
            data["score"] = self.current_level.score
            data["votes"] = len(self.current_level.votes) 

        self.broadcast(data)

    def handle_client(self, conn, addr):
        self.clients[conn] = addr
        self.broadcast({"type": "lobby_sync", "count": len(self.clients)})
        
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    msg = json.loads(line)
                    
                    if msg["type"] == "join":
                        import random
                        self.player_data[conn] = {
                            "name": msg["name"], "x": 10, "y": 10,
                            "color": (random.randint(50,255), random.randint(50,255), random.randint(50,255))
                        }
                        self.log(f"Student {msg['name']} joined.")
                        self.broadcast({"type": "lobby_sync", "count": len(self.clients)})
                    
                    elif msg["type"] == "move":
                        if conn in self.player_data:
                            self.player_data[conn]["x"] = max(0, min(19, msg["x"]))
                            self.player_data[conn]["y"] = max(0, min(19, msg["y"]))
                    
                    elif msg["type"] == "vote":
                        if self.current_level and self.current_level.type == "QUIZ":
                            self.current_level.process_vote(id(conn), msg["choice"])
                            if self.current_level.evaluate_votes(len(self.player_data)):
                                self.level_idx += 1
                                self.start_level()
        except: pass
        finally: self.remove_client(conn)

    def admin_console(self):
        """Command line interface for the teacher."""
        while True:
            cmd = input("ADMIN > ").strip().lower()
            if cmd == "start":
                if not self.player_data:
                    print("[!] Nelze spustit hru bez studentů.")
                else:
                    self.level_idx = 0
                    self.game_started = True
                    self.start_level()
                    print("[OK] Hra spuštěna.")
            elif cmd == "status":
                print(f"--- STAV ---")
                print(f"Studentů: {len(self.player_data)}")
                print(f"Hra běží: {self.game_started}")
                if self.current_level:
                    print(f"Level: {self.current_level.title} ({self.current_level.type})")
            elif cmd == "list":
                print("--- SEZNAM STUDENTŮ ---")
                for data in self.player_data.values():
                    print(f"- {data['name']} (pozice: [{data['x']}, {data['y']}])")
            elif cmd == "exit":
                print("[*] Vypínám server...")
                os._exit(0)
            elif cmd == "help":
                print("Příkazy: start, status, list, exit")

    def run(self):
        threading.Thread(target=self.admin_console, daemon=True).start()
        threading.Thread(target=self.game_loop, daemon=True).start()
        self.log(f"Server listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()