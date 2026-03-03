import pygame
import math
import constant as c

class Bullet:
    def __init__(self, x, y, angle, color):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * c.BULLET_SPEED      # velocità orizzontale
        self.vy = math.sin(angle) * c.BULLET_SPEED      # velocità verticale
        self.color = color
        self.active = True
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > c.ARENA_WIDTH or self.y < 0 or self.y > c.ARENA_HEIGHT:
            self.active = False
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), c.BULLET_SIZE)