import math
import js
import random
import json

# Stage Configuration
STAGES = [
    {"name": "清水町", "sub": "Shimizu-cho", "color": "#000033", "dist": 5000}, 
    {"name": "中町",   "sub": "Naka-machi",  "color": "#777777", "dist": 6000}, 
    {"name": "北町",   "sub": "Kita-machi",  "color": "#222222", "dist": 7000}, 
    {"name": "中町西", "sub": "Nakamachi-Nishi", "color": "#8b0000", "dist": 7500}, 
    {"name": "沢町",   "sub": "Sawamachi",   "color": "#006400", "dist": 8000}, 
    {"name": "畑山町", "sub": "Hatayama-cho","color": "#8b4500", "dist": 8500}, 
    {"name": "東町",   "sub": "Higashi-machi","color": "#00008b", "dist": 9000}, 
    {"name": "水池町", "sub": "Mizuike-cho", "color": "#4b0082", "dist": 9500}, 
    {"name": "八田北", "sub": "Hatta-kita",  "color": "#d4af37", "dist": 10000} 
]

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.state = "TITLE" # TITLE is now Stage Select
        self.stage_index = 0
        self.total_score = 0
        
        self.select_cursor = 0 # 0-8 for Stage Selection
        
        self.current_stage_data = STAGES[self.stage_index]
        self.player = Player(100, 500, self.current_stage_data["color"]) 
        self.camera = Camera(width, height)
        self.raining = False
        self.score_bonus = 0
        self.level_time = 0.0
        
        self.platforms = []
        self.enemies = []
        self.items = []
        self.water_stations = []
        self.lightnings = []
        self.goal_x = 0
        self.attack_timer = 0
        
        # Load Rankings
        self.rankings = {}
        try:
            stored = js.localStorage.getItem("danjiri_records")
            if stored:
                data = json.loads(stored)
                # Migration: Convert old single-float records to lists
                cleaned = {}
                for k, v in data.items():
                    if isinstance(v, (float, int)): cleaned[k] = [float(v)]
                    elif isinstance(v, list): cleaned[k] = v
                    else: cleaned[k] = []
                self.rankings = cleaned
        except:
            pass

        # Audio System
        try:
            self.bgm = js.Audio.new("bgm.mp3")
            self.bgm.loop = True
            self.bgm.volume = 0.5
        except:
            pass 

    def save_ranking(self):
        try:
            idx_str = str(self.stage_index)
            records = self.rankings.get(idx_str, [])
            records.append(self.level_time)
            records.sort() # low time is best
            records = records[:3] # Keep top 3
            
            self.rankings[idx_str] = records
            js.localStorage.setItem("danjiri_records", json.dumps(self.rankings))
            
            # Return true if this was a new #1 record
            if records[0] == self.level_time: return True
        except:
            pass
        return False

    def init_level(self):
        self.current_stage_data = STAGES[self.stage_index]
        distance = self.current_stage_data["dist"]
        
        self.raining = random.random() < 0.3 
        
        self.platforms = [({"x": 0, "y": 600, "w": 1000, "h": 120})]
        self.enemies = []
        self.items = []
        self.water_stations = []
        self.lightnings = []
        
        current_x = 1000
        goal_x = distance
        gap_min = 100 + (self.stage_index * 10)
        gap_max = 300 + (self.stage_index * 20)
        
        while current_x < goal_x:
            w = random.randint(200, 800)
            gap = random.randint(gap_min, gap_max)
            y = random.choice([600, 500, 450])
            
            if random.random() < 0.3: 
                self.platforms.append({"x": current_x + gap, "y": y - 150, "w": w, "h": 20})
            else: 
                self.platforms.append({"x": current_x, "y": 600, "w": w + gap, "h": 120})
                if random.random() < 0.15: 
                    self.water_stations.append({"x": current_x + 50, "y": 600 - 60, "w": 80, "h": 60, "active": True})
            
            current_x += w + gap
            center_x = current_x - (w/2)
            
            if random.random() < 0.6: 
                etype = random.choice(["police", "prius", "crow", "police"])
                if etype == "crow": self.enemies.append(Enemy(center_x, random.randint(300, 450), "crow", patrol_dist=500))
                elif etype == "police": self.enemies.append(Enemy(center_x, 600 - 50, "police", patrol_dist=50))
                else: self.enemies.append(Enemy(center_x, 600 - 50, "prius", patrol_dist=300))

            if random.random() < 0.7: 
                rand_val = random.random()
                itype = "towel"
                iy = -100
                if rand_val < 0.15: itype = "uchiwa"; iy = 400
                elif rand_val < 0.45: itype = "sake"; iy = 600 - 40 
                elif rand_val < 0.75: itype = "money"; iy = -100 
                else: itype = "towel"; iy = -100
                self.items.append(Item(center_x + random.randint(-50, 50), iy, itype))

        self.platforms.append({"x": goal_x, "y": 600, "w": 1000, "h": 120})
        self.goal_x = goal_x + 500
        
        self.player.happi_color = self.current_stage_data["color"]
        self.player.reset_pos(100, 500)
        self.camera.x = 0
        self.attack_timer = 0 
        self.level_time = 0.0

    def next_level(self):
        self.save_ranking()
        self.total_score += int(self.player.x / 10) + self.score_bonus
        # Return to Title for Stage Selection
        self.state = "TITLE" 

    def update(self, dt, input_state):
        keys_pressed = input_state.keys_pressed.to_py()
        keys_down = input_state.keys_down.to_py()
        mouse = input_state.mouse
        
        if self.state == "TITLE":
            # Stage Selection Logic
            if "ArrowRight" in keys_pressed: self.select_cursor = (self.select_cursor + 1) % 9
            if "ArrowLeft" in keys_pressed: self.select_cursor = (self.select_cursor - 1) % 9
            if "ArrowDown" in keys_pressed: self.select_cursor = (self.select_cursor + 3) % 9
            if "ArrowUp" in keys_pressed: self.select_cursor = (self.select_cursor - 3) % 9
            
            # Click detection (Simplified grid mapping)
            if mouse.clicked:
                # Map mouse to grid? Too complex for quick implementation without known coords
                # Just use keyboard or Space to confirm for now, or implement mouse hit test later
                pass
                
            if "Space" in keys_pressed or "Enter" in keys_pressed or mouse.clicked:
                self.stage_index = self.select_cursor
                self.state = "PLAY"
                self.init_level()
                try: self.bgm.play()
                except: pass
        
        elif self.state == "GAMEOVER":
             if "Space" in keys_pressed or mouse.clicked:
                 self.state = "TITLE"

        elif self.state == "RESULT":
            if "Space" in keys_pressed or mouse.clicked:
                self.next_level()

        elif self.state == "PLAY":
            try:
                if "Escape" in keys_pressed:
                    self.state = "TITLE"
                    return

                if math.isnan(dt) or dt < 0: dt = 0.016
                
                # Game Over Check
                if self.player.hp <= 0:
                    self.state = "GAMEOVER"
                    self.player.hp = 0
                    return

                self.player.update(dt, keys_down, keys_pressed, self.platforms, self.enemies)
                self.camera.update(self.player)
                self.level_time += dt
                
                # Cleanup
                self.enemies = [e for e in self.enemies if e.alive]
                self.items = [i for i in self.items if i.active]
                self.lightnings = [l for l in self.lightnings if l.active]
                
                # Attack Timer
                self.attack_timer += dt
                if self.attack_timer > 4.0: 
                    if random.random() < 0.6: 
                        self.spawn_aggressive_car()
                    self.attack_timer = 0
                
                # Lightning
                if random.random() < 0.005:
                    mid = self.camera.x + self.width / 2
                    lx = mid + random.randint(-self.width/2, self.width/2)
                    self.lightnings.append(Lightning(lx))
                
                # Updates
                for e in self.enemies: e.update(dt)
                for l in self.lightnings: 
                    l.update(dt)
                    if l.is_striking and not l.has_hit:
                        if abs(self.player.x + self.player.w/2 - l.x) < 50:
                            self.player.hp -= 2; self.player.burnt_timer = 3.0; l.has_hit = True
                            
                for i in self.items:
                    i.update(dt, self.player)
                    if i.active and self.check_collision(self.player, i):
                        i.active = False
                        if i.type == "uchiwa": self.player.roof_guy_scale += 0.5 
                        elif i.type == "towel": self.score_bonus += 500
                        elif i.type == "money":
                            # MONEY Effect: Visual Upgrade
                            self.player.money_count += 1
                            self.score_bonus += 1000
                        elif i.type == "sake":
                            self.player.drunk_timer = 5.0 
                            # self.player.hp -= 3 # Disabled HP penalty
                
                for ws in self.water_stations:
                    if ws["active"]:
                        if (self.player.x < ws["x"] + ws["w"] and self.player.x + self.player.w > ws["x"] and self.player.y < ws["y"] + ws["h"] and self.player.y + self.player.h > ws["y"]):
                            self.player.hp += 0.1; 
                            if self.player.hp > 20: self.player.hp = 20
                            
                if self.player.x > self.goal_x:
                    self.save_ranking() # Save on clear
                    self.state = "RESULT"
                
                if self.player.y > self.height + 100:
                    self.player.hp = 0; self.state = "GAMEOVER"
                    
            except Exception as e:
                js.console.error(f"Error in Update: {e}"); import traceback; traceback.print_exc()

    def spawn_aggressive_car(self):
        spawn_front = random.random() < 0.5
        if spawn_front: sx = self.camera.x + self.width + 100; vx = -500 
        else: sx = self.camera.x - 100; vx = 600 
        car = Enemy(sx, 600 - 30, "patrol_car", patrol_dist=99999); car.vx = vx; car.aggressive = True
        self.enemies.append(car)

    def check_collision(self, player, item):
        return (player.x < item.x + item.w and player.x + player.w > item.x and player.y < item.y + item.h and player.y + player.h > item.y)

    def draw(self, ctx):
        try:
            ctx.setTransform(1, 0, 0, 1, 0, 0)
            ctx.clearRect(0, 0, self.width, self.height)
            
            if self.raining: ctx.fillStyle = "#050510" 
            elif self.state == "GAMEOVER": ctx.fillStyle = "#220000" 
            elif self.state == "TITLE": ctx.fillStyle = "#110a22" # Dark Title BG
            else: ctx.fillStyle = "#1a0b2e"
            ctx.fillRect(0, 0, self.width, self.height)
            
            if self.state == "TITLE": self.draw_title(ctx)
            else:
                self.draw_background(ctx)
                if self.state == "PLAY": self.draw_play(ctx)
                elif self.state == "RESULT": self.draw_result(ctx)
                elif self.state == "GAMEOVER": self.draw_gameover(ctx)
                if self.raining and self.state == "PLAY": self.draw_rain(ctx)
                
        except Exception as e:
            js.console.error(f"Draw Error: {e}")

    def draw_rain(self, ctx):
        ctx.save(); ctx.strokeStyle = "rgba(150, 150, 255, 0.5)"; ctx.lineWidth = 1; ctx.beginPath(); t = int(self.player.timer * 1000)
        for i in range(100):
            rx = (i * 137 + t * 2) % self.width; ry = (i * 43 + t * 3) % self.height
            ctx.moveTo(rx, ry); ctx.lineTo(rx - 5, ry + 20)
        ctx.stroke(); ctx.restore()

    def draw_background(self, ctx):
        ctx.save()
        for i in range(25):
            x = (i * 120 - self.camera.x * 0.5) % self.width; h = 40 + (i * 997) % 80
            ctx.fillStyle = "rgba(255, 200, 100, 0.3)" if not self.raining else "rgba(100, 100, 150, 0.3)"
            ctx.fillRect(x, self.height - 100 - h, 60, h)
        if not self.raining: 
            lantern_spacing = 150; offset_x = -(self.camera.x * 0.8) % lantern_spacing
            ctx.beginPath(); ctx.moveTo(0, 50); ctx.lineTo(self.width, 50); ctx.strokeStyle = "#8b4513"; ctx.lineWidth = 3; ctx.stroke()
            for i in range(int(self.width / lantern_spacing) + 2):
                x = offset_x + i * lantern_spacing; y = 50
                ctx.fillStyle = "#ffdddd" if i % 2 == 0 else "#ff5555"; ctx.shadowBlur = 15; ctx.shadowColor = ctx.fillStyle
                ctx.beginPath(); ctx.ellipse(x, y + 30, 20, 30, 0, 0, math.pi * 2); ctx.fill()
                ctx.fillStyle = "black"; ctx.shadowBlur = 0; ctx.font = "16px serif"; ctx.textAlign = "center"
                t_name = self.current_stage_data["name"]
                ctx.fillText(t_name[0:1], x, y + 26); 
                if len(t_name) > 1: ctx.fillText(t_name[1:2], x, y + 46) 
                ctx.fillStyle = "#333"; ctx.fillRect(x - 12, y + 2, 24, 5); ctx.fillRect(x - 12, y + 55, 24, 5)
        ctx.fillStyle = "#4a3c31"; ctx.fillRect(0, self.height - 100, self.width, 100); ctx.restore()

    def draw_title(self, ctx):
        ctx.save()
        ctx.textAlign = "center"; ctx.shadowBlur = 0; ctx.fillStyle = "white"; ctx.font = "bold 40px 'Shippori Mincho', serif"
        ctx.fillText("深井だんじり祭り - ステージ選択", self.width / 2, 60)
        
        # Guide
        ctx.font = "20px serif"; ctx.fillStyle = "#ccc"
        ctx.fillText("Stage Select Mode", self.width / 2, 90)

        # Draw 3x3 Grid
        start_x = self.width / 2 - 250; start_y = 120; cell_w = 160; cell_h = 140; gap = 20
        
        for i in range(9):
            row = i // 3; col = i % 3
            x = start_x + col * (cell_w + gap)
            y = start_y + row * (cell_h + gap)
            
            # Cursor Highlight
            is_selected = (self.select_cursor == i)
            if is_selected:
                ctx.fillStyle = "gold"; ctx.fillRect(x - 5, y - 5, cell_w + 10, cell_h + 10)
            
            stg = STAGES[i]
            ctx.fillStyle = stg["color"]; ctx.fillRect(x, y, cell_w, cell_h)
            ctx.fillStyle = "white"; ctx.font = "bold 24px serif"; ctx.fillText(stg["name"], x + cell_w/2, y + 40)
            ctx.font = "14px serif"; ctx.fillText(stg["sub"], x + cell_w/2, y + 60)
            
            # Record
            records = self.rankings.get(str(i), [])
            # Fill up to 3 with placeholders
            while len(records) < 3: records.append(None)
            
            ctx.fillStyle = "#aaa"; ctx.font = "14px monospace"; ctx.textAlign = "left"
            base_tx = x + 30
            
            # Rank 1
            ctx.fillStyle = "gold" if records[0] else "#555"
            t1 = f"1st: {records[0]:.2f}s" if records[0] else "1st: --.--"
            ctx.fillText(t1, base_tx, y + 90)
            
            # Rank 2
            ctx.fillStyle = "silver" if records[1] else "#555"
            t2 = f"2nd: {records[1]:.2f}s" if records[1] else "2nd: --.--"
            ctx.fillText(t2, base_tx, y + 105)
            
            # Rank 3
            ctx.fillStyle = "#cd7f32" if records[2] else "#555" # Bronze
            t3 = f"3rd: {records[2]:.2f}s" if records[2] else "3rd: --.--"
            ctx.fillText(t3, base_tx, y + 120)
            
        ctx.textAlign = "center"
        ctx.fillStyle = "white"; ctx.font = "24px serif"
        ctx.fillText("矢印キーで選択 / スペースキーで決定", self.width / 2, self.height - 50)
        ctx.restore()

    def draw_result(self, ctx):
        ctx.save(); ctx.textAlign = "center"; ctx.fillStyle = "rgba(0, 0, 0, 0.8)"; ctx.fillRect(0, 0, self.width, self.height)
        ctx.shadowBlur = 20; ctx.fillStyle = "gold"; ctx.font = "bold 60px serif"; ctx.fillText("宮入完了！", self.width / 2, self.height / 2 - 50)
        stg_score = int(self.player.x / 10) + self.score_bonus; ctx.fillStyle = "white"; ctx.shadowBlur = 0; ctx.font = "40px serif"
        ctx.fillText(f"タイム: {self.level_time:.2f}秒", self.width / 2, self.height / 2 + 50)
        ctx.font = "24px serif"; ctx.fillText("スペースキー で 選択画面へ", self.width / 2, self.height / 2 + 120); ctx.restore()

    def draw_gameover(self, ctx):
        ctx.save(); ctx.textAlign = "center"; ctx.fillStyle = "rgba(50, 0, 0, 0.8)"; ctx.fillRect(0, 0, self.width, self.height)
        ctx.shadowBlur = 20; ctx.shadowColor = "red"; ctx.fillStyle = "red"; ctx.font = "bold 80px serif"; ctx.fillText("曳行不能...", self.width / 2, self.height / 2 - 40)
        ctx.fillStyle = "white"; ctx.shadowBlur = 0; ctx.font = "30px serif"; ctx.fillText("曳き手がいなくなりました", self.width / 2, self.height / 2 + 40)
        ctx.font = "20px serif"; ctx.fillText("スペースキー で 選択画面へ", self.width / 2, self.height / 2 + 100); ctx.restore()

    def draw_play(self, ctx):
        ctx.save(); ctx.translate(-self.camera.x, 0)
        for ws in self.water_stations:
            if ws["active"]:
                ctx.fillStyle = "rgba(100, 200, 255, 0.5)"; ctx.fillRect(ws["x"], ws["y"], ws["w"], ws["h"])
                ctx.fillStyle = "white"; ctx.beginPath(); ctx.moveTo(ws["x"], ws["y"]); ctx.lineTo(ws["x"] + ws["w"]/2, ws["y"]-30); ctx.lineTo(ws["x"]+ws["w"], ws["y"]); ctx.fill()
                ctx.fillStyle = "blue"; ctx.font = "12px serif"; ctx.textAlign = "center"; ctx.fillText("給水所", ws["x"] + ws["w"]/2, ws["y"] - 5)
        ctx.fillStyle = "#555"; ctx.strokeStyle = "#777"; ctx.lineWidth = 2
        for p in self.platforms:
            ctx.fillRect(p["x"], p["y"], p["w"], p["h"]); ctx.strokeRect(p["x"], p["y"], p["w"], p["h"])
            if p["w"] > 200 and p["y"] >= 600: 
                ctx.fillStyle = "white"; 
                for i in range(0, int(p["w"]), 100): ctx.fillRect(p["x"] + i, p["y"] + 10, 50, 5)
        self.draw_torii(ctx, self.goal_x, 600)
        self.player.draw(ctx)
        for e in self.enemies: e.draw(ctx)
        for i in self.items: i.draw(ctx)
        for l in self.lightnings: l.draw(ctx)
        ctx.restore()
        
        # UI
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0) 
        ctx.fillStyle = "white"; ctx.shadowColor = "black"; ctx.shadowBlur = 4; ctx.font = "bold 24px serif"; ctx.textAlign = "left"
        town_name = self.current_stage_data["name"]
        if self.player.hp < 3: ctx.fillStyle = "red"
        elif self.player.hp < 6: ctx.fillStyle = "yellow"
        else: ctx.fillStyle = "white"
        hp_display = int(max(0, self.player.hp)) 
        ctx.fillText(f"【{town_name}】 曳き手: {hp_display}人", 20, 40)
        
        ctx.fillStyle = "white"; ctx.textAlign = "center"; ctx.font = "bold 30px monospace"
        time_str = f"{self.level_time:.2f}"; ctx.fillText(f"TIME: {time_str}", self.width / 2, 40)
        
        ctx.fillStyle = "white"; dist = int(self.player.x / 100); ctx.textAlign = "right"; ctx.font = "bold 24px serif"
        ctx.fillText(f"奉納点: {dist * 10 + self.score_bonus}", self.width - 20, 40)
        ctx.font = "16px serif"; ctx.fillText(f"残り: {(self.goal_x - self.player.x) / 100:.0f}m", self.width - 20, 65)
        ctx.restore()

    def draw_torii(self, ctx, x, ground_y):
        ctx.save(); ctx.fillStyle = "#888888"; h = 300; w = 250; ctx.fillRect(x, ground_y - h, 30, h); ctx.fillRect(x + w, ground_y - h, 30, h)
        ctx.fillStyle = "#999999"; ctx.fillRect(x - 20, ground_y - h + 20, w + 70, 30); ctx.fillRect(x, ground_y - h + 70, w + 30, 20) 
        ctx.fillStyle = "#333"; ctx.fillRect(x + w/2 - 15, ground_y - h + 30, 30, 40); ctx.restore()

class Lightning:
    def __init__(self, x):
        self.x = x; self.y = 0; self.active = True; self.timer = 0; self.warning_duration = 0.8; self.strike_duration = 0.2; self.is_striking = False; self.has_hit = False
    def update(self, dt):
        self.timer += dt
        if self.timer > self.warning_duration: self.is_striking = True
        if self.timer > self.warning_duration + self.strike_duration: self.active = False
    def draw(self, ctx):
        if not self.active: return
        ctx.save()
        if not self.is_striking:
            ctx.strokeStyle = "rgba(255, 255, 0, 0.5)"; ctx.lineWidth = 2; ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.moveTo(self.x, 0); ctx.lineTo(self.x, 600); ctx.stroke(); ctx.fillStyle = "rgba(255, 0, 0, 0.5)"; ctx.beginPath(); ctx.ellipse(self.x, 600, 30, 10, 0, 0, math.pi*2); ctx.fill()
        else:
            ctx.fillStyle = "rgba(255, 255, 255, 0.3)"; ctx.fillRect(0, 0, 99999, 99999) 
            ctx.strokeStyle = "white"; ctx.lineWidth = 5; ctx.shadowColor = "blue"; ctx.shadowBlur = 20; ctx.beginPath(); ctx.moveTo(self.x, 0)
            curr_y = 0; 
            while curr_y < 600: next_y = curr_y + random.randint(20, 50); next_x = self.x + random.randint(-20, 20); ctx.lineTo(next_x, next_y); curr_y = next_y
            ctx.stroke()
        ctx.restore()

class Enemy:
    def __init__(self, x, y, type="police", patrol_dist=100):
        self.type = type; self.x = x; self.y = y; self.start_x = x; self.patrol_dist = patrol_dist
        self.vx = 80; self.alive = True; self.timer = 0; self.aggressive = False; self.w = 40; self.h = 40
        if type == "police": self.w = 30; self.h = 40
        elif type in ["patrol_car", "ambulance", "prius"]: self.w = 100; self.h = 40; self.y = y + 10 
        elif type == "crow": self.w = 30; self.h = 20; self.vx = -150

    def update(self, dt):
        if not self.alive: return
        self.timer += dt
        if self.aggressive:
            self.x += self.vx * dt
            if abs(self.x - self.start_x) > 5000: self.alive = False
            return
        if self.type == "crow": self.x += self.vx * dt; self.y += math.sin(self.timer * 10) * 2
        else:
            self.x += self.vx * dt
            if self.x > self.start_x + self.patrol_dist: self.vx = -abs(self.vx)
            elif self.x < self.start_x: self.vx = abs(self.vx)
            
    def draw(self, ctx):
        if not self.alive: return
        ctx.save(); facing_right = self.vx > 0
        if self.type == "crow":
            ctx.fillStyle = "black"; ctx.translate(self.x, self.y)
            if not facing_right: ctx.scale(-1, 1) 
            ctx.beginPath(); ctx.ellipse(15, 10, 15, 8, 0, 0, math.pi * 2); ctx.fill()
            ctx.beginPath(); ctx.arc(25, 5, 6, 0, math.pi * 2); ctx.fill(); ctx.fillStyle = "yellow"; ctx.beginPath(); ctx.moveTo(28, 5); ctx.lineTo(35, 8); ctx.lineTo(28, 11); ctx.fill() 
            mid_wing_y = -10 if int(self.timer * 10) % 2 == 0 else 0
            ctx.fillStyle = "#222"; ctx.beginPath(); ctx.moveTo(10, 10); ctx.lineTo(20, mid_wing_y); ctx.lineTo(30, 10); ctx.fill()
        elif self.type == "police":
            ctx.fillStyle = "#1e3f5a"; ctx.fillRect(self.x, self.y, self.w, self.h); ctx.fillStyle = "white"; ctx.fillRect(self.x, self.y - 5, self.w, 5)
            if (int(self.timer * 5) % 2) == 0: ctx.fillStyle = "#ff0000"; ctx.fillRect(self.x + (25 if facing_right else -5), self.y + 10, 5, 20)
        elif self.type == "patrol_car":
            ctx.fillStyle = "black"; ctx.fillRect(self.x, self.y + 10, self.w, 30); ctx.fillStyle = "white"; ctx.fillRect(self.x, self.y + 10, self.w, 15)
            if (int(self.timer * 10) % 2) == 0: ctx.fillStyle = "red"; ctx.shadowBlur = 20; ctx.shadowColor = "red"; ctx.fillRect(self.x + 40, self.y, 20, 10)
        elif self.type == "ambulance":
            ctx.fillStyle = "white"; ctx.fillRect(self.x, self.y, self.w, 40); ctx.fillStyle = "red"; ctx.fillRect(self.x, self.y + 15, self.w, 5)
            ctx.fillRect(self.x + 40, self.y + 10, 5, 20); ctx.fillRect(self.x + 32, self.y + 18, 20, 5)
            if (int(self.timer * 10) % 2) == 0: ctx.fillStyle = "red"; ctx.shadowBlur = 20; ctx.shadowColor = "red"; ctx.fillRect(self.x + 10, self.y - 5, 10, 5); ctx.fillRect(self.x + 80, self.y - 5, 10, 5)
        elif self.type == "prius":
            ctx.fillStyle = "#c0c0c0"; ctx.fillRect(self.x + 10, self.y + 10, self.w - 20, 30); ctx.fillStyle = "#a8e4ff"; ctx.beginPath(); ctx.moveTo(self.x + 10, self.y + 10); ctx.lineTo(self.x + 30, self.y); ctx.lineTo(self.x + 70, self.y); ctx.lineTo(self.x + 90, self.y + 10); ctx.fill()
        if self.type in ["patrol_car", "ambulance", "prius"]:
            ctx.fillStyle = "#333"; ctx.shadowBlur = 0; wheel_y = self.y + 35; ctx.beginPath(); ctx.arc(self.x + 20, wheel_y, 8, 0, math.pi * 2); ctx.arc(self.x + self.w - 20, wheel_y, 8, 0, math.pi * 2); ctx.fill()
        ctx.restore()

class Item:
    def __init__(self, x, y, type):
        self.x = x; self.y = y; self.w = 30; self.h = 30; self.type = type; self.active = True; self.timer = 0
        self.vy = 50 if type in ["towel", "money"] else 0
        if type == "sake": self.vy = 0
    def update(self, dt, player):
        if not self.active: return
        self.timer += dt
        if self.type in ["towel", "money"]:
            self.y += self.vy * dt
            if self.y > 600 - 30: self.y = 600 - 30; self.vy = 0
        if self.type == "uchiwa": self.y += math.sin(self.timer * 5) * 0.5
    def draw(self, ctx):
        if not self.active: return
        ctx.save()
        if self.type == "uchiwa":
            ctx.translate(self.x + 15, self.y + 15); ctx.rotate(math.sin(self.timer * 3) * 0.2)
            ctx.fillStyle = "white"; ctx.beginPath(); ctx.arc(0, -5, 15, 0, math.pi * 2); ctx.fill(); ctx.fillStyle = "red"; ctx.font = "10px serif"; ctx.textAlign = "center"; ctx.fillText("祭", 0, 0); ctx.strokeStyle = "#8b4513"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 5); ctx.lineTo(0, 20); ctx.stroke()
        elif self.type == "towel":
            ctx.fillStyle = "white"; ctx.fillRect(self.x, self.y, 20, 30); ctx.fillStyle = "blue"; ctx.fillRect(self.x + 5, self.y, 2, 30); ctx.fillRect(self.x + 13, self.y, 2, 30)
        elif self.type == "sake":
            ctx.translate(self.x + 15, self.y + 30); ctx.fillStyle = "#4b2d0b"; ctx.fillRect(-10, -30, 20, 30); ctx.fillRect(-5, -40, 10, 10); ctx.fillStyle = "#f5f5dc"; ctx.fillRect(-8, -25, 16, 15); ctx.fillStyle = "black"; ctx.font = "8px serif"; ctx.textAlign = "center"; ctx.fillText("酒", 0, -15)
        elif self.type == "money":
            ctx.save(); ctx.translate(self.x, self.y); ctx.rotate(math.sin(self.timer * 5) * 0.3); ctx.fillStyle = "#e0d6bd"; ctx.fillRect(0, 0, 40, 20); ctx.fillStyle = "#333"; ctx.font = "10px serif"; ctx.fillText("壱万", 5, 14); ctx.beginPath(); ctx.arc(30, 10, 5, 0, math.pi * 2); ctx.fillStyle = "#ccc"; ctx.fill(); ctx.restore()
        ctx.restore()

class Player:
    def __init__(self, x, y, happi_color="#000033"):
        self.reset_pos(x, y); self.happi_color = happi_color; self.roof_guy_scale = 1.0; self.shout_text = ""; self.shout_timer = 0; self.drunk_timer = 0; self.burnt_timer = 0 
        self.money_count = 0
        
    def reset_pos(self, x, y):
        self.x = x; self.y = y; self.w = 80; self.h = 90; self.vx = 0; self.vy = 0; self.jump_force = -650; self.gravity = 1000; self.grounded = False
        self.hp = 10; self.timer = 0; self.invincible = 0; self.shout_text = ""; self.shout_timer = 0; self.drunk_timer = 0; self.burnt_timer = 0
        self.money_count = 0 
        
    def update(self, dt, keys_down, keys_pressed, platforms, enemies):
        self.timer += dt
        if self.invincible > 0: self.invincible -= dt
        if self.shout_timer > 0: self.shout_timer -= dt
        if self.drunk_timer > 0: self.drunk_timer -= dt
        if self.burnt_timer > 0: self.burnt_timer -= dt
        
        if self.hp > 0: self.hp -= dt * 0.1 
        puller_factor = max(1, self.hp); base_speed = 100 + (puller_factor * 20) 
        if base_speed > 350: base_speed = 350
        if self.drunk_timer > 0: base_speed *= 0.5
            
        direction = 0
        if "ArrowLeft" in keys_down or "KeyA" in keys_down: direction -= 1
        if "ArrowRight" in keys_down or "KeyD" in keys_down: direction += 1
        self.vx = direction * base_speed
        
        if math.isnan(self.x) or math.isnan(self.y): js.console.error(f"NaN DETECTED! x={self.x}, y={self.y}, vx={self.vx}, vy={self.vy}, dt={dt}"); self.reset_pos(100, 500)
        self.x += self.vx * dt; self.vy += self.gravity * dt; self.y += self.vy * dt
        
        if ("Space" in keys_pressed or "KeyW" in keys_pressed) and self.grounded:
            force = self.jump_force
            if "ArrowUp" in keys_down: force *= 1.4; self.shout_text = "ソーリャ！"; self.shout_timer = 1.0
            else: self.shout_text = "ホイサ" if random.random() < 0.5 else "エンヤ"; self.shout_timer = 0.5
            self.vy = force; self.grounded = False
        self.grounded = False
        for p in platforms:
            if (self.x < p["x"] + p["w"] and self.x + self.w > p["x"] and self.y < p["y"] + p["h"] and self.y + self.h > p["y"]):
                overlap_x = min(self.x + self.w - p["x"], p["x"] + p["w"] - self.x)
                overlap_y = min(self.y + self.h - p["y"], p["y"] + p["h"] - self.y)
                if overlap_x > overlap_y:
                    if self.y + self.h / 2 < p["y"] + p["h"] / 2:
                        if self.vy >= 0: self.y = p["y"] - self.h; self.vy = 0; self.grounded = True
                    else:
                        if self.vy < 0: self.y = p["y"] + p["h"]; self.vy = 0
                else:
                    if self.vx > 0: self.x = p["x"] - self.w
                    elif self.vx < 0: self.x = p["x"] + p["w"]
        for e in enemies:
            if not e.alive: continue
        for e in enemies:
            if not e.alive: continue
            
            # Calculate Player Full Hitbox including Pullers
            # Pullers extend horizontally.
            puller_len = int(max(0, self.hp)) * 30
            if self.vx >= 0: # Facing Right
                p_x1 = self.x
                p_x2 = self.x + self.w + puller_len
            else: # Facing Left
                p_x1 = self.x - puller_len
                p_x2 = self.x + self.w
            
            p_y1 = self.y
            p_y2 = self.y + self.h

            # Check Intersection
            if (p_x1 < e.x + e.w and p_x2 > e.x and p_y1 < e.y + e.h and p_y2 > e.y):
                if self.vy > 0 and self.y + self.h < e.y + e.h / 2 + 10:
                    e.alive = False; self.vy = -300; self.hp += 3; self.shout_text = "引手+3！"; self.shout_timer = 1.0
                elif self.invincible <= 0: 
                    self.hp -= 2; self.invincible = 1.0; self.vy = -200; self.vx = -self.vx 
                    if e.type == "crow": self.shout_text = "イテッ！" 
                    
    def _draw_wheel_at(self, ctx, wx, wy, rotation):
        ctx.save(); ctx.translate(wx, wy); ctx.rotate(rotation); ctx.fillStyle = "#5c4033"; ctx.beginPath(); ctx.arc(0, 0, 16, 0, math.pi * 2); ctx.fill()
        ctx.fillStyle = "#8b5a2b"; ctx.fillRect(-14, -2, 28, 4); ctx.fillRect(-2, -14, 4, 28); ctx.fillStyle = "gold"; ctx.beginPath(); ctx.arc(0, 0, 5, 0, math.pi * 2); ctx.fill(); ctx.restore()

    def draw(self, ctx):
        if self.invincible > 0 and (int(self.timer * 10) % 2) == 0: return 
        ctx.save()
        bob_y = math.sin(self.timer * 20) * 2 if abs(self.vx) > 10 else 0
        wheel_rot = (self.x / 20) % (math.pi * 2)
        danjiri_x = self.x; danjiri_y = self.y + bob_y
        
        # --- CUSTOMIZATION LEVELS ---
        # 0: Normal
        # 1+ Money: Gold Railings
        # 3+ Money: Lanterns
        # 5+ Money: Golden Roof Phoenix / Ornaments
        # 10+ Money: Sparkle Aura
        has_gold_rails = self.money_count >= 1
        has_lanterns = self.money_count >= 3
        has_phoenix = self.money_count >= 5
        has_aura = self.money_count >= 10
        
        if has_aura:
           ctx.shadowColor = "gold"; ctx.shadowBlur = 20
        
        ctx.fillStyle = "#5c4033"
        self._draw_wheel_at(ctx, danjiri_x + 15, danjiri_y + self.h, wheel_rot); self._draw_wheel_at(ctx, danjiri_x + self.w - 15, danjiri_y + self.h, wheel_rot)
        ctx.shadowBlur = 0 
        
        ctx.fillStyle = "#8b5a2b"; ctx.fillRect(danjiri_x + 5, danjiri_y + self.h - 15, self.w - 10, 15) 
        ctx.fillStyle = "#a0522d"; ctx.fillRect(danjiri_x + 10, danjiri_y + 20, self.w - 20, self.h - 35)
        
        # Railings
        rail_color = "gold" if has_gold_rails else "#2f2f2f"
        ctx.fillStyle = "#2f2f2f"; ctx.beginPath(); ctx.moveTo(danjiri_x - 5, danjiri_y + 20); ctx.lineTo(danjiri_x + self.w / 2, danjiri_y - 10); ctx.lineTo(danjiri_x + self.w + 5, danjiri_y + 20); ctx.fill()
        ctx.strokeStyle = rail_color; ctx.lineWidth = 2; ctx.stroke()
        
        if has_lanterns:
            for i in range(3):
                lx = danjiri_x + 10 + i * 25
                ly = danjiri_y + 20
                ctx.fillStyle = "white" if i%2==0 else "red"
                ctx.beginPath(); ctx.arc(lx, ly, 5, 0, math.pi*2); ctx.fill()
        

        if has_phoenix:
             ctx.fillStyle = "gold"; ctx.beginPath(); ctx.moveTo(danjiri_x + self.w/2, danjiri_y - 15); ctx.lineTo(danjiri_x + self.w/2 - 10, danjiri_y - 25); ctx.lineTo(danjiri_x + self.w/2 + 10, danjiri_y - 25); ctx.fill()

        # Flags (Nobori) - New Feature
        num_flags = min(4, self.money_count // 2)
        if num_flags > 0:
            flag_colors = ["#ff0000", "#ffffff", "#0000ff", "#ffff00"]
            for i in range(num_flags):
                fx = danjiri_x + 10 + (i * 15)
                fy = danjiri_y - 40 # Above roof
                ctx.fillStyle = "#8b4513"; ctx.fillRect(fx, fy, 2, 40) # Pole
                
                # Waving Flag
                ctx.fillStyle = flag_colors[i % 4]
                ctx.beginPath()
                ctx.moveTo(fx + 2, fy)
                for f_seg in range(20):
                     wave = math.sin(self.timer * 10 + f_seg * 0.5 + i) * 3
                     ctx.lineTo(fx + 2 + f_seg + max(0, abs(self.vx)/20), fy + 5 + wave)
                ctx.lineTo(fx + 2 + 20 + max(0, abs(self.vx)/20), fy + 20)
                ctx.lineTo(fx + 2, fy + 25)
                ctx.fill()
                
                # Text on Flag
                ctx.fillStyle = "black" if i % 2 == 1 else "white"; ctx.font = "10px serif"; ctx.textAlign = "center"
                ctx.fillText("祭", fx + 10, fy + 15)

        puller_count = int(max(0, self.hp))
        puller_spacing = 30; facing_right = self.vx >= 0
        start_x = self.x + self.w + 20 if facing_right else self.x - 20; dir_mult = 1 if facing_right else -1
        rope_end_x = start_x + (puller_count * puller_spacing * dir_mult)
        if puller_count > 0:
            ctx.strokeStyle = "#eee8aa"; ctx.lineWidth = 4; ctx.beginPath(); anchor_x = self.x + self.w if facing_right else self.x
            ctx.moveTo(anchor_x, danjiri_y + self.h - 20); mid_x = (anchor_x + rope_end_x) / 2; mid_y = danjiri_y + self.h - 10 + bob_y 
            ctx.quadraticCurveTo(mid_x, mid_y, rope_end_x, danjiri_y + self.h - 30); ctx.stroke()
        for i in range(puller_count):
            px = start_x + (i * puller_spacing * dir_mult); py = self.y + self.h - 40 
            leg_offset = math.sin(self.timer * 20 + i) * 5 if abs(self.vx) > 10 else 0
            ctx.fillStyle = self.happi_color; ctx.fillRect(px - 10, py + leg_offset, 20, 35) 
            ctx.fillStyle = "white"; ctx.fillRect(px - 2, py + leg_offset, 4, 35)
            ctx.fillStyle = "#ffe0bd"; ctx.beginPath(); ctx.arc(px, py - 10 + leg_offset, 8, 0, math.pi * 2); ctx.fill()
            ctx.fillStyle = "white"; ctx.fillRect(px - 9, py - 14 + leg_offset, 18, 4)
            ctx.fillStyle = "#ffe0bd"; rope_y_at_x = danjiri_y + self.h - 30 + (bob_y * 0.5)
            ctx.beginPath(); ctx.arc(px + (5 * dir_mult), rope_y_at_x, 4, 0, math.pi * 2); ctx.fill()
        roof_guy_x = danjiri_x + self.w / 2
        guy_jump = 0; guy_arm_angle = 0; dance_timer = self.timer * 8; is_jumping = False
        if int(dance_timer) % 2 == 0: guy_jump = -5; guy_arm_angle = -math.pi / 4; is_jumping = True
        else: guy_jump = 0; guy_arm_angle = math.pi / 4 
        roof_guy_y_feet = danjiri_y + guy_jump 
        ctx.save(); ctx.translate(roof_guy_x, roof_guy_y_feet); ctx.scale(self.roof_guy_scale, self.roof_guy_scale) 
        
        body_color = self.happi_color; face_color = "#ffe0bd"
        if self.burnt_timer > 0: body_color = "#333"; face_color = "#555"
            
        ctx.fillStyle = body_color; ctx.fillRect(-10, -25, 20, 25)
        ctx.fillStyle = face_color; ctx.beginPath(); ctx.arc(0, -30, 8, 0, math.pi * 2); ctx.fill()
        
        ctx.fillStyle = "white"; ctx.beginPath(); fan_x = 15 * dir_mult; fan_y = -30
        ctx.translate(fan_x, fan_y); ctx.rotate(guy_arm_angle * dir_mult); ctx.arc(0, 0, 10, 0, math.pi * 2); ctx.fill()
        ctx.strokeStyle = "brown"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 10); ctx.lineTo(0, 20); ctx.stroke()
        if is_jumping: ctx.fillStyle = "white"; ctx.shadowColor = "black"; ctx.shadowBlur = 3; ctx.font = "bold 14px serif"; ctx.textAlign = "center"; ctx.fillText("ちょい", 0, -45)
        if self.shout_timer > 0:
            ctx.fillStyle = "gold" if "ソーリャ" in self.shout_text else "white"; ctx.shadowColor = "black"; ctx.shadowBlur = 3; ctx.font = "bold 20px serif"; ctx.textAlign = "center"
            text_y = -60 - (1.0 - self.shout_timer) * 20; ctx.fillText(self.shout_text, 0, text_y)
        if self.drunk_timer > 0: ctx.fillStyle = "pink"; ctx.font = "bold 16px serif"; ctx.fillText("酔", 0, -80)
        ctx.restore(); ctx.restore()

class Camera:
    def __init__(self, screen_w, screen_h):
        self.x = 0; self.screen_w = screen_w
    def update(self, player):
        target_x = player.x - self.screen_w / 3; 
        if target_x < 0: target_x = 0; 
        self.x += (target_x - self.x) * 0.1
