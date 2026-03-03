import pygame
import numpy as np
import random
import math
from deap import base, creator, tools, algorithms
from collections import deque
import constant as c
import bullet as b
import bot as bot_module




class BattleArena:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((c.ARENA_WIDTH, c.ARENA_HEIGHT + 150))    # finestra di gioco
        pygame.display.set_caption("Battle Bots Arena - DEAP Evolution")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Setup DEAP
        self.setup_deap()
        
        # Popolazioni
        self.red_population = self.toolbox.population(n=c.POPULATION_SIZE)  # popolazione rossa
        self.blue_population = self.toolbox.population(n=c.POPULATION_SIZE) # popolazione blu
        
        self.generation = 1     # Generazione corrente
        self.red_wins = 0
        self.blue_wins = 0
        self.current_battle = 0     # Contatore battaglie nella generazione
        self.battle_time = 0        # Tempo trascorso nella battaglia corrente
        
        self.best_red_genome = None
        self.best_blue_genome = None
        
        # Storia fitness
        self.red_fitness_history = deque(maxlen=50)     # per medie mobili
        self.blue_fitness_history = deque(maxlen=50)    # per medie mobili
    
    def setup_deap(self):
        # Crea tipi DEAP
        """
        Potremmo avere bisogno di resettare i tipi se eseguiamo più volte lo script per questo ho bisogno di questo controllo
        (evita errori "A class with name 'FitnessMax/Individual' already exists in the creator module")

        """
        if hasattr(creator, "FitnessMax"):
            del creator.FitnessMax
        if hasattr(creator, "Individual"):
            del creator.Individual
            
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        self.toolbox = base.Toolbox()
        
        # Ogni gene è un float tra 0 e 1
        # 12 geni: speed, aggression, shoot_freq, aim_skill, dodge_skill, 
        #          circle_tendency, keep_distance, strafe_weight, retreat_health,
        #          predictive_aim, burst_fire, corner_avoid
        self.toolbox.register("attr_float", random.random)
        self.toolbox.register("individual", tools.initRepeat, creator.Individual,
                             self.toolbox.attr_float, n=12)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Operatori genetici
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
        self.toolbox.register("evaluate", self.evaluate_individual)
    
    def evaluate_individual(self, individual):
        # Questa funzione viene chiamata esternamente dopo le battaglie
        return individual.fitness.values if individual.fitness.valid else (0,)  # se la fitness è stata calcolata allora restituiscila altrimenti 0
    
    def run_battle(self, red_genome, blue_genome):
        red_bot = bot_module.Bot(100, c.ARENA_HEIGHT // 2, c.RED, red_genome)   # Bot(x_iniziale, y_iniziale, gruppo di appartenenza, gene)
        blue_bot = bot_module.Bot(c.ARENA_WIDTH - 100, c.ARENA_HEIGHT // 2, c.BLUE, blue_genome)
        
        # per ogni frame aggiorno i valori dei Bot 
        for frame in range(c.BATTLE_DURATION):
            red_bot.update(blue_bot)
            blue_bot.update(red_bot)
            # controllo se ho colpito
            red_bot.check_hits(blue_bot)
            blue_bot.check_hits(red_bot)

            # se qualcuno "muore" interrompi
            if red_bot.health <= 0 or blue_bot.health <= 0:
                break
        
        red_fitness = red_bot.get_fitness()[0]
        blue_fitness = blue_bot.get_fitness()[0]
        
        return red_fitness, blue_fitness, red_bot.health > blue_bot.health
    
    def evolve_generation(self):
        # Valuta tutti gli individui tramite battaglie round-robin
        print(f"\n--- Generazione {self.generation} ---")
        
        # Reset fitness
        for ind in self.red_population:
            ind.fitness.values = (0,)
        for ind in self.blue_population:
            ind.fitness.values = (0,)
        
        # Battaglie BILANCIATE: ogni rosso vs ogni blu combatte 2 volte (invertendo posizioni)
        battle_count = 0
        total_battles = c.POPULATION_SIZE * 10  # 5 avversari x 2 posizioni
        
        for i, red_ind in enumerate(self.red_population):
            # Ogni rosso combatte contro 5 blu casuali
            opponents = random.sample(self.blue_population, 5)
            for blue_ind in opponents:
                # Battaglia 1: Red a sinistra, Blue a destra
                red_fit1, blue_fit1, red_won1 = self.run_battle(red_ind, blue_ind)
                
                # Battaglia 2: INVERTI POSIZIONI - Blue a sinistra, Red a destra
                blue_fit2, red_fit2, blue_won2 = self.run_battle(blue_ind, red_ind)
                
                # Accumula fitness (media delle 2 battaglie)
                red_ind.fitness.values = (red_ind.fitness.values[0] + (red_fit1 + red_fit2) / 2,)
                blue_ind.fitness.values = (blue_ind.fitness.values[0] + (blue_fit1 + blue_fit2) / 2,)
                
                # Conta vittorie
                if red_won1:
                    self.red_wins += 1
                else:
                    self.blue_wins += 1
                    
                if blue_won2:
                    self.blue_wins += 1
                else:
                    self.red_wins += 1
                
                battle_count += 2
                if battle_count % 20 == 0:
                    print(f"Battaglie completate: {battle_count}/{total_battles}")
        
        # Media fitness (ora su 10 battaglie invece di 5)
        for ind in self.red_population:
            ind.fitness.values = (ind.fitness.values[0] / 5,)  # Diviso 5 perché ogni battaglia conta doppio
        for ind in self.blue_population:
            ind.fitness.values = (ind.fitness.values[0] / 5,)
        
        # Statistiche
        red_fits = [ind.fitness.values[0] for ind in self.red_population]
        blue_fits = [ind.fitness.values[0] for ind in self.blue_population]
        
        self.red_fitness_history.append(max(red_fits))
        self.blue_fitness_history.append(max(blue_fits))
        
        print(f"Red - Max: {max(red_fits):.0f}, Avg: {sum(red_fits)/len(red_fits):.0f}")
        print(f"Blue - Max: {max(blue_fits):.0f}, Avg: {sum(blue_fits)/len(blue_fits):.0f}")
        print(f"Vittorie - Red: {self.red_wins}, Blue: {self.blue_wins}")
        
        # Salva migliori
        self.best_red_genome = tools.selBest(self.red_population, 1)[0]
        self.best_blue_genome = tools.selBest(self.blue_population, 1)[0]
        
        # Evoluzione con DEAP
        self.red_population = self.toolbox.select(self.red_population, len(self.red_population))    # seleziona i migliori
        self.blue_population = self.toolbox.select(self.blue_population, len(self.blue_population))
        
        # Clona per evitare riferimenti
        self.red_population = list(map(self.toolbox.clone, self.red_population))
        self.blue_population = list(map(self.toolbox.clone, self.blue_population))
        
        # Crossover
        for child1, child2 in zip(self.red_population[::2], self.red_population[1::2]): # accoppia a due a due
            if random.random() < c.CXPB:
                self.toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        
        for child1, child2 in zip(self.blue_population[::2], self.blue_population[1::2]):
            if random.random() < c.CXPB:        # crossover con probabilità CXPB 
                self.toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        
        # Mutazione
        for mutant in self.red_population:
            if random.random() < c.MUTPB:
                self.toolbox.mutate(mutant)
                # Clamp valori tra 0 e 1
                for i in range(len(mutant)):
                    mutant[i] = max(0, min(1, mutant[i]))
                del mutant.fitness.values
        
        for mutant in self.blue_population:
            if random.random() < c.MUTPB:
                self.toolbox.mutate(mutant)
                for i in range(len(mutant)):
                    mutant[i] = max(0, min(1, mutant[i]))
                del mutant.fitness.values
        
        self.generation += 1
    
    def draw_ui(self):
        # Pannello info
        pygame.draw.rect(self.screen, c.DARK_GRAY, (0, c.ARENA_HEIGHT, c.ARENA_WIDTH, 150))
        
        # Generazione
        gen_text = self.font.render(f"Gen: {self.generation}", True, c.WHITE)
        self.screen.blit(gen_text, (20, c.ARENA_HEIGHT + 20))
        
        # Punteggi
        red_text = self.font.render(f"Red: {self.red_wins}", True, c.RED)
        blue_text = self.font.render(f"Blue: {self.blue_wins}", True, c.BLUE)
        self.screen.blit(red_text, (200, c.ARENA_HEIGHT + 20))
        self.screen.blit(blue_text, (400, c.ARENA_HEIGHT + 20))
        
        # Istruzioni
        inst1 = self.small_font.render("SPAZIO: Prossima Gen | ESC: Esci", True, c.WHITE)
        self.screen.blit(inst1, (20, c.ARENA_HEIGHT + 70))
        
        # Mostra migliori genomi
        if self.best_red_genome and self.best_blue_genome:
            best_text = self.small_font.render("Migliori Bot:", True, c.WHITE)
            self.screen.blit(best_text, (20, c.ARENA_HEIGHT + 100))
            
            red_stats = f"R: Spd={self.best_red_genome[0]:.1f} Agg={self.best_red_genome[1]:.1f} Aim={self.best_red_genome[3]:.1f}"
            blue_stats = f"B: Spd={self.best_blue_genome[0]:.1f} Agg={self.best_blue_genome[1]:.1f} Aim={self.best_blue_genome[3]:.1f}"
            
            red_stats_text = self.small_font.render(red_stats, True, c.RED)
            blue_stats_text = self.small_font.render(blue_stats, True, c.BLUE)
            
            self.screen.blit(red_stats_text, (150, c.ARENA_HEIGHT + 100))
            self.screen.blit(blue_stats_text, (150, c.ARENA_HEIGHT + 120))
    
    def visualize_battle(self, red_genome, blue_genome):
        red_bot = bot_module.Bot(100, c.ARENA_HEIGHT // 2, c.RED, red_genome)
        blue_bot = bot_module.Bot(c.ARENA_WIDTH - 100, c.ARENA_HEIGHT // 2, c.BLUE, blue_genome)
        
        for frame in range(c.BATTLE_DURATION):
            # controllo di uscita
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
            
            red_bot.update(blue_bot)
            blue_bot.update(red_bot)
            red_bot.check_hits(blue_bot)
            blue_bot.check_hits(red_bot)
            
            # Disegna
            self.screen.fill(c.GRAY)
            
            # Griglia
            for i in range(0, c.ARENA_WIDTH, 50):
                pygame.draw.line(self.screen, c.DARK_GRAY, (i, 0), (i, c.ARENA_HEIGHT), 1)
            for i in range(0, c.ARENA_HEIGHT, 50):
                pygame.draw.line(self.screen, c.DARK_GRAY, (0, i), (c.ARENA_WIDTH, i), 1)
            
            red_bot.draw(self.screen)
            blue_bot.draw(self.screen)
            
            self.draw_ui()
            
            pygame.display.flip()
            self.clock.tick(60)
            
            if red_bot.health <= 0 or blue_bot.health <= 0:
                pygame.time.wait(1000)
                break
        
        return True
    
    def run(self):
        running = True
        auto_evolve = False
        
        while running and self.generation <= c.GENERATIONS:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        auto_evolve = not auto_evolve
            
            # Evolvi generazione
            self.evolve_generation()
            
            # Visualizza battaglia tra i migliori
            if self.best_red_genome and self.best_blue_genome:
                if not self.visualize_battle(self.best_red_genome, self.best_blue_genome):
                    running = False
            
            if not auto_evolve:
                # Aspetta input utente
                waiting = True
                while waiting and running:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            waiting = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_SPACE:
                                waiting = False
                            elif event.key == pygame.K_ESCAPE:
                                running = False
                                waiting = False

                    self.screen.fill(c.DARK_GRAY)
                    wait_text = self.font.render("Premi SPAZIO per continuare", True, c.WHITE)
                    self.screen.blit(wait_text, (c.ARENA_WIDTH//2 - 200, c.ARENA_HEIGHT//2))
                    pygame.display.flip()
                    self.clock.tick(30)
        
        pygame.quit()

if __name__ == "__main__":
    arena = BattleArena()
    arena.run()