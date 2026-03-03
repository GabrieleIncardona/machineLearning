import pygame
import math
import random
import constant as c
import bullet as b

class Bot:
    def __init__(self, x, y, color, genome):
        self.start_x = x                                # posizione iniziale x
        self.start_y = y                                # posizione iniziale y
        self.x = x                                      # posizione corrente x  
        self.y = y                                      # posizione corrente y
        self.color = color                              # colore del bot
        self.genome = genome                            # genoma (lista di parametri)
        self.health = c.MAX_HEALTH                      # salute iniziale
        self.angle = 0                                  # angolo di mira
        self.vx = 0                                     # velocità orizzontale
        self.vy = 0                                     # velocità verticale
        self.bullets = []                               # lista di proiettili
        self.cooldown = 0                               # cooldown di sparo
        
        # Statistiche per fitness
        self.damage_dealt = 0                           # danno totale inflitto
        self.hits = 0                                   # numero di colpi andati a segno
        self.shots_fired = 0                            # numero di colpi sparati
        self.time_alive = 0                             # tempo di sopravvivenza in frame
        
    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.health = c.MAX_HEALTH
        self.angle = 0
        self.vx = 0
        self.vy = 0
        self.bullets = []
        self.cooldown = 0
        self.damage_dealt = 0
        self.hits = 0
        self.shots_fired = 0
        self.time_alive = 0
    
    def update(self, enemy):
        if self.health <= 0:
            return
        
        self.time_alive += 1
        
        # Decodifica genoma
        speed = self.genome[0] * 5 + 1  # 1-6
        aggression = self.genome[1]  # 0-1              # livello di aggressività (0 = difensivo, 1 = aggressivo)
        shoot_freq = self.genome[2] * 0.1  # 0-0.1      # frequenza di tiro (0 = non spara, 0.1 = spara spesso)
        aim_skill = self.genome[3]  # 0-1               # abilità di mira (0 = scarsa, 1 = perfetta)
        dodge_skill = self.genome[4]  # 0-1             # abilità di schivata (0 = nessuna, 1 = perfetta)
        circle_tendency = self.genome[5] * 2 - 1  # -1 a 1      # tendenza a muoversi in cerchio ( -1 = orario, 1 = antiorario)
        keep_distance = self.genome[6] * 300 + 100  # 100-400   # distanza da mantenere dal nemico
        strafe_weight = self.genome[7]  # 0-1           # peso del movimento laterale (0 = solo avanti e indietro, 1 = molto laterale)
        retreat_health = self.genome[8] * 50 + 20  # 20-70      # salute sotto la quale ritirarsi
        predictive_aim = self.genome[9]  # 0-1          # abilità di mira predittiva (0 = nessuna, 1 = perfetta)
        burst_fire = self.genome[10]  # 0-1             # modalità di fuoco a raffica (0 = no, 1 = sì)
        corner_avoid = self.genome[11]  # 0-1           # abilità di evitare gli angoli (0 = nessuna, 1 = perfetta)
        
        # Calcola vettore verso nemico
        dx = enemy.x - self.x
        dy = enemy.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)     # distanza dal nemico
        angle_to_enemy = math.atan2(dy, dx)     # angolo verso il nemico

        # Strategia di movimento
        desired_angle = angle_to_enemy
        
        # Mantieni distanza
        if dist < keep_distance:
            desired_angle += math.pi  # vado indietro
        
        # Movimento circolare
        desired_angle += circle_tendency * math.pi / 4      # aggiungo un angolo per il movimento circolare(fa fatica a colpire)

        # Movimento laterale
        dir_x = math.cos(desired_angle)
        dir_y = math.sin(desired_angle)

        strafe_angle = desired_angle + math.pi / 2

        strafe_x = math.cos(strafe_angle)
        strafe_y = math.sin(strafe_angle)

        move_x = dir_x * (1 - strafe_weight) + strafe_x * strafe_weight     # interpolazione tra movimento avanti/indietro e laterale
        move_y = dir_y * (1 - strafe_weight) + strafe_y * strafe_weight     # interpolazione tra movimento avanti/indietro e laterale

        desired_angle = math.atan2(move_y, move_x)

        
        # Evasione proiettili
        for bullet in enemy.bullets:
            if not bullet.active:
                continue
            bdx = bullet.x - self.x
            bdy = bullet.y - self.y
            bdist = math.sqrt(bdx * bdx + bdy * bdy)
            if bdist < 80:
                dodge_angle = math.atan2(bdy, bdx) + math.pi / 2
                desired_angle += dodge_angle * dodge_skill * 0.5        # sposta il bot lontano dalla traiettoria del proiettile
        
        # Evita angoli
        margin = 80

        wall_force_x = 0.0
        wall_force_y = 0.0

        # Spinta orizzontale
        if self.x < margin:                                                     # vicino al bordo sinistro
            wall_force_x += (margin - self.x) / margin                          # spinta verso destra
        elif self.x > c.ARENA_WIDTH - margin:                                   # vicino al bordo destro
            wall_force_x -= (self.x - (c.ARENA_WIDTH - margin)) / margin        # spinta verso sinistra

        # Spinta verticale
        if self.y < margin:                                                     # vicino al bordo superiore
            wall_force_y += (margin - self.y) / margin                          # spinta verso il basso
        elif self.y > c.ARENA_HEIGHT - margin:                                  # vicino al bordo inferiore
            wall_force_y -= (self.y - (c.ARENA_HEIGHT - margin)) / margin       # spinta verso l'alto

        # Somma vettoriale con la direzione desiderata
        move_x = math.cos(desired_angle)
        move_y = math.sin(desired_angle)

        move_x += wall_force_x * corner_avoid
        move_y += wall_force_y * corner_avoid

        desired_angle = math.atan2(move_y, move_x)

        
        # Comportamento in base alla salute
        if self.health < retreat_health:
            # Ritirata tattica
            desired_angle = angle_to_enemy + math.pi
            speed *= 1.3
        
        # Applica movimento
        self.vx = math.cos(desired_angle) * speed
        self.vy = math.sin(desired_angle) * speed
        self.x += self.vx
        self.y += self.vy
        
        # Limiti arena
        self.x = max(c.BOT_SIZE, min(c.ARENA_WIDTH - c.BOT_SIZE, self.x))       # limite orizzontale (non esco dall'arena)
        self.y = max(c.BOT_SIZE, min(c.ARENA_HEIGHT - c.BOT_SIZE, self.y))      # limite verticale (non esco dall'arena)

        # Mira con predizione
        if predictive_aim > 0.5 and dist > 0:
            # Predici posizione futura del nemico
            time_to_hit = dist / c.BULLET_SPEED
            pred_x = enemy.x + enemy.vx * time_to_hit
            pred_y = enemy.y + enemy.vy * time_to_hit
            pred_dx = pred_x - self.x
            pred_dy = pred_y - self.y
            self.angle = math.atan2(pred_dy, pred_dx)
        else:
            self.angle = angle_to_enemy
        
        # Aggiungi errore di mira
        aim_error = (1 - aim_skill) * 0.4                           # massimo errore (più il bot è scarso a mirare, più l'errore è grande)
        self.angle += (random.random() - 0.5) * aim_error           # errore casuale nell'angolo di mira
        
        # Sistema di sparo
        self.cooldown -= 1                             # riduci cooldown (pronto a sparare?)
        should_shoot = False
        
        if burst_fire > 0.5:                          # spara in modalità raffica
            # Modalità burst (3 colpi rapidi)
            if self.cooldown <= 0 and random.random() < shoot_freq * aggression:        
                should_shoot = True
                self.cooldown = 5  # Cooldown ridotto per burst
        else:
            # Modalità normale
            if self.cooldown <= 0 and random.random() < shoot_freq * aggression * 2:        #il *2 serve per aumentare la probabilità di sparo e dare equilibrio tra modalità burst e normale
                should_shoot = True
                self.cooldown = 20
        
        if should_shoot:
            self.shoot()
        
        # Aggiorna proiettili
        for bullet in self.bullets:
            bullet.update()
        self.bullets = [b for b in self.bullets if b.active]           # rimuovi proiettili inattivi
    
    def shoot(self):
        offset = c.BOT_SIZE
        bullet_x = self.x + math.cos(self.angle) * offset
        bullet_y = self.y + math.sin(self.angle) * offset
        self.bullets.append(b.Bullet(bullet_x, bullet_y, self.angle, self.color))
        self.shots_fired += 1               # incrementa il contatore dei colpi sparati (per la fitness)
    
    def check_hits(self, enemy):
        for bullet in self.bullets:
            if not bullet.active:
                continue
            dx = bullet.x - enemy.x
            dy = bullet.y - enemy.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < c.BOT_SIZE:
                damage = 10
                enemy.health -= damage
                self.damage_dealt += damage             # aggiorna il danno totale inflitto (per la fitness)
                self.hits += 1                          # incrementa il contatore dei colpi andati a segno (per la fitness)
                bullet.active = False
    
    def get_fitness(self):
        fitness = 0
        # Sopravvivenza
        fitness += self.health * 5
        fitness += self.time_alive * 2

        # Danno inflitto
        fitness += self.damage_dealt * 30
        fitness += self.hits * 70

        # Precisione
        if self.shots_fired > 0:
            accuracy = self.hits / self.shots_fired
            fitness += accuracy * 300

        # Bonus sopravvivenza
        if self.health > 0:
            fitness += 500

        # Penalità per non aver sparato
        if self.shots_fired == 0:
            fitness -= 200
        return fitness,

    def draw(self, screen):
        if self.health <= 0:
            return
        
        # Corpo
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), c.BOT_SIZE)
        
        # Cannone
        end_x = self.x + math.cos(self.angle) * c.BOT_SIZE
        end_y = self.y + math.sin(self.angle) * c.BOT_SIZE
        pygame.draw.line(screen, c.BLACK, (self.x, self.y), (end_x, end_y), 4)
        
        # Barra vita
        bar_width = c.BOT_SIZE * 2
        bar_height = 4
        bar_x = self.x - bar_width / 2
        bar_y = self.y - c.BOT_SIZE - 10
        pygame.draw.rect(screen, c.BLACK, (bar_x, bar_y, bar_width, bar_height))
        health_width = bar_width * (self.health / c.MAX_HEALTH)
        health_color = c.GREEN if self.health > 50 else c.RED
        pygame.draw.rect(screen, health_color, (bar_x, bar_y, health_width, bar_height))
        
        # Proiettili
        for bullet in self.bullets:
            bullet.draw(screen)