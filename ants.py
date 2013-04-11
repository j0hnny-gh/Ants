#!/usr/bin/env python
import sys
import traceback
import random
import time
from collections import defaultdict
from math import sqrt

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHI'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT

AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
RIGHT = {'n': 'e',
         'e': 's',
         's': 'w',
         'w': 'n'}
LEFT = {'n': 'w',
        'e': 'n',
        's': 'e',
        'w': 's'}
BEHIND = {'n': 's',
          's': 'n',
          'e': 'w',
          'w': 'e'}

class Ants():
    def __init__(self):
        self.cols = None
        self.rows = None
        self.map = None
        self.hill_list = {}
        self.ant_list = {}
        self.dead_list = defaultdict(list)
        self.food_list = []
        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.vision = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0
        self.turn = 0
        self.log_vision = open('vision.log', 'w')
        self.wave = None
        self.global_vision = None
        self.damage_map = None
        self.take_food = {}
        self.explore_map = {}
        self.links = {}
        self.hidden = []
        
    def __del__(self):
      self.log_vision.close()

    def setup(self, data):
        'parse initial input and setup starting game state'
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        self.map = [[LAND for col in range(self.cols)] for row in range(self.rows)]  
        self.wave = [[-1 for col in range(self.cols)] for row in range(self.rows)]
        self.global_vision = [[0 for col in range(self.cols)] for row in range(self.rows)]
        self.damage_map = [[0 for col in range(self.cols)] for row in range(self.rows)]
        
    def render_text_map(self):
        tmp = ''
        for row in self.map:
            tmp += '# %s\n' % ''.join([MAP_RENDER[col] for col in row])
        return tmp
        
    def render_text_wave(self):
        tmp = '    '
        for col in range(self.cols):
          tmp += repr(col).rjust(4)
        tmp += '\n'
        r = 0
        for row in self.wave:
            tmp += repr(r).rjust(4) + '%s\n' % ''.join([repr(col).rjust(4) for col in row])
            r += 1
        return tmp
    
    def render_text_damage(self):
        tmp = '    '
        for col in range(self.cols):
          tmp += repr(col).rjust(4)
        tmp += '\n'
        r = 0
        for row in self.damage_map:
            tmp += repr(r).rjust(4) + '%s\n' % ''.join([repr(col).rjust(4) for col in row])
            r += 1
        return tmp
    
    def create_vision(self):
        self.vision_offsets_2 = []
        mx = int(sqrt(self.viewradius2))
        for d_row in range(-mx,mx+1):
            for d_col in range(-mx,mx+1):
                d = d_row**2 + d_col**2
                if d <= self.viewradius2:
                    self.vision_offsets_2.append((
                        d_row%self.rows-self.rows,
                        d_col%self.cols-self.cols
                    ))
                    
    def create_move(self):
        self.move_offsets_2 = []
        mx = int(sqrt(self.viewradius2))
        for d_row in range(-mx,mx+1):
            for d_col in range(-mx,mx+1):
                d = d_row**2 + d_col**2
                if d <= self.viewradius2:
                    self.move_offsets_2.append((
                        d_row%self.rows-self.rows,
                        d_col%self.cols-self.cols
                    ))
    
    def visible(self, loc):
        ' determine which squares are visible to the given player '

        if self.vision == None:
            if not hasattr(self, 'vision_offsets_2'):
                # precalculate squares around an ant to set as visible
                self.create_vision()
            # set all spaces as not visible
            # loop through ants and set all squares around ant as visible
            self.vision = [[False]*self.cols for row in range(self.rows)]
            for ant in self.my_ants():
                a_row, a_col = ant
                for v_row, v_col in self.vision_offsets_2:
                    self.vision[a_row+v_row][a_col+v_col] = True
                    self.global_vision[a_row+v_row][a_col+v_col] = 1
        row, col = loc
        return self.vision[row][col]
        
    def destination(self, loc, direction):
        'calculate a new location given the direction and wrap correctly'
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.rows, (col + d_col) % self.cols)
        
    def place_marker(self, loc, size):
        row, col = loc
        for r in range(-size+1, size):
            for c in range(-size+1, size):
                x, y = ((row + r) % self.rows, (col + c) % self.cols)
                if self.wave[x][y] != 999:
                    self.wave[x][y] += max(0, size - abs(r) - abs(c))
                    
    def place_marker_sqr(self, loc, size):
        row, col = loc
        for r in range(-size+1, size):
            for c in range(-size+1, size):
                x, y = ((row + r) % self.rows, (col + c) % self.cols)
                if self.wave[x][y] != 999:
                    self.wave[x][y] += max(0, size - int(sqrt(r*r + c*c)))
                    
    def place_damage_marker(self, loc, size, value):
        row, col = loc
        for r in range(-size+1, size):
            for c in range(-size+1, size):
                x, y = ((row + r) % self.rows, (col + c) % self.cols)
                if size - abs(r) - abs(c) > 0:
                    if self.damage_map[x][y] != -999:
                        self.damage_map[x][y] += value
                    
    def place_damage_marker_sqr(self, loc, size, value):
        row, col = loc
        for r in range(-size+1, size):
            for c in range(-size+1, size):
                x, y = ((row + r) % self.rows, (col + c) % self.cols)
                if (size - int(sqrt(r*r + c*c))) > 0:
                  if value > 0:
                    if self.damage_map[x][y] != -999:
                      self.damage_map[x][y] += value
                  else:
                    if self.damage_map[x][y] == -999:
                        self.damage_map[x][y] = value
                    else:
                        self.damage_map[x][y] += value
    
    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.clock()
        
        # reset vision
        self.vision = None
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
                            
        self.check_food()
        
        if len(self.explore_map) == 0:
          for row, col in self.hill_list:
            if self.hill_list[(row, col)] == MY_ANT:
              self.hidden.append((row, col, 0, 0))
              
        self.check_expore()
        
        self.build_damage_map()
        
        self.calc_combat()
        
        self.log_vision.write(self.render_text_map() + '\n')
        self.log_vision.write('turn ' + repr(self.turn) + ' %s\n\n' % self.time_remaining())
        self.turn += 1
    
    # -------------------- FOOD --------------------------
    
    def check_food(self):
      # check ants to gather food
      self.take_food = {}
      map_tmp = [[self.map[row][col] for col in range(self.cols)] for row in range(self.rows)]
      
      for row, col in self.hill_list:
        if self.hill_list[(row, col)] != MY_ANT:
          self.food_list.append((row, col))
      
      for row, col in self.food_list:
        res, r, c, l, dir = self.search_ant(map_tmp, (row, col))
        
        if not hasattr(self, 'move_offsets_2'):
          self.create_move()
          
        #self.log_vision.write(self.render_food_map(map_tmp) + '\n')
          
        for v_row, v_col in self.move_offsets_2:
          map_tmp[row+v_row][col+v_col] = self.map[row+v_row][col+v_col]
          
        #self.log_vision.write(self.render_food_map(map_tmp) + '\n')
        
        if res:
          if (r, c) not in self.take_food:
            self.take_food[(r, c)] = (l, dir)
            self.log_vision.write("Gatherer found at {0}, {1} for {2}, {3} length {4} dir {5}\n".format(r, c, row, col, l, dir))
          else:
            l_old, dir_old = self.take_food[(r, c)]
            if (l_old > l):
              self.take_food[(r, c)] = (l, dir)
              self.log_vision.write("Gatherer found at {0}, {1} for {2}, {3} length {4} (replaced {5}) dir {6}\n".format(r, c, row, col, l, l_old, dir))
            else:
              self.log_vision.write("Gatherer not found for {0}, {1}\n".format(row, col))
              
      self.log_vision.write('Gathered, %s left.\n\n' % self.time_remaining())
      
    def search_ant(self, map_tmp, (row, col)):
      front = [(row, col, row, col)]
      new_front = []
      for w in range(int(sqrt(2*self.viewradius2))):
        for (r, c, arow, acol) in front:
          for dir in AIM:
            dx, dy = AIM[dir]
            dr = arow + dx
            dc = acol + dy
            if ((dr-row)**2 + (dc-col)**2) < self.viewradius2 :
              x, y = self.destination((r, c), dir)
              if self.map[x][y] == MY_ANT:
                return (True, x, y, w, BEHIND[dir])
              if map_tmp[x][y] == LAND:
                map_tmp[x][y] = w+1
                new_front.append((x, y, dr, dc))
        front = new_front
        new_front = []
        
      return (False, 0, 0, 0, 0)
      
    def need_take_food(self, loc):
      if loc in self.take_food:
        l, dir = self.take_food[loc]
        return True, dir
      return False, 0
      
    def render_food_map(self, map):
      tmp = '   '
      for col in range(self.cols):
        tmp += repr(col).rjust(2)
      tmp += '\n'
      r = 0
      for row in map:
        tmp += repr(r).rjust(3) + '%s\n' % ''.join([repr(col).rjust(2) for col in row])
        r += 1
      return tmp
      
    # -------------------- FOOD --------------------------
    
    # -------------------- EXPRORE --------------------------
    
    def check_expore(self):
      check_nodes = self.hidden[:]
      self.hidden = []
      leafs = []
      
      self.visible((0, 0))
      
      while len(check_nodes) != 0:
        new_check_nodes = []
        for node in check_nodes:
          row, col, depth, pdir = node
          
          if self.global_vision[row][col] == 1:
            
            if (row, col) not in self.explore_map and self.map[row][col]!=WATER:
              # node explored
              if pdir != 0:
                self.explore_map[(row, col)] = (pdir, depth, 0, 0)
                pr, pc = self.destination((row, col), pdir)
                if (pr, pc) not in self.links:
                  self.links[(pr, pc)] = []
                self.links[(pr, pc)].append((row, col))
              else:
                self.explore_map[(row, col)] = (pdir, depth, 0, 0)

              for dir in AIM:
                r, c = self.destination((row, col), dir)
                if (r, c) not in self.explore_map:
                  new_check_nodes.append((r, c, depth+1, BEHIND[dir]))
              
          else:
            
            if (row, col, depth, pdir) not in self.hidden:
              self.hidden.append((row, col, depth, pdir))
            
        check_nodes = new_check_nodes[:]
        
        #for row, col, depth, pdir in self.hidden:      
        #  self.log_vision.write("Hidden at {0}, {1} depth {2} parent {3}\n".format(row, col, depth, pdir))
          
        #for row, col, depth, pdir in check_nodes:      
        #  self.log_vision.write("check_nodes at {0}, {1} depth {2} parent {3}\n".format(row, col, depth, pdir))
          
        #for r, c in self.explore_map.keys():
        #  dir, depth, ants, hidden = self.explore_map[(r, c)]
        #  self.log_vision.write("Explore graph {0}, {1} depth {2} parent {3} ants {4} hidden {5}\n".format(r, c, depth, dir, ants, hidden))
          
        #for row, col in self.links.keys():
        #  self.log_vision.write("Links from {0} {1} to".format(row, col) + '%s\n' % ''.join([' ('+repr(r)+', '+repr(c)+')' for r, c in self.links[row, col]]))
      
      # reset explore map
      for r, c in self.explore_map.keys():
        dir, depth, ants, hidden = self.explore_map[(r, c)]
        if self.map[r][c]==MY_ANT:
          ants = 1
        else:
          ants = 0
        self.explore_map[(r, c)] = (dir, depth, ants, 0)
      
      # count hidden in nearest nodes
      for row, col, depth, pdir in self.hidden:
        pr, pc = self.destination((row, col), pdir)
        dir, depth, ants, hidden = self.explore_map[(pr, pc)]
        hidden = hidden + 1
        self.explore_map[(pr, pc)] = (dir, depth, ants, hidden)
      
      self.log_vision.write('Explored, %s left.\n\n' % self.time_remaining())
      
      # count ants and hidden for whole graph
      visited = []
      def add_to_parent(row, col, child_ants, child_hidden):
        dir, depth, ants, hidden = self.explore_map[(row, col)]
        ants = ants + child_ants
        hidden = hidden + child_hidden
        self.explore_map[(row, col)] = (dir, depth, ants, hidden)
        #self.log_vision.write("Node {0} {1} ants {2} hidden {3} depth {4}\n".format(row, col, ants, hidden, depth))
        if depth > 0:
          r, c = self.destination((row, col), dir)
          if ((r, c) in visited):
            add_to_parent(r, c, child_ants, child_hidden)
          else:
            visited.append((r, c))
            add_to_parent(r, c, ants, hidden)
      
      for row, col in self.explore_map:
        if (row, col) not in self.links:
          leafs.append((row, col))
      
      def get_root(row, col):
        dir, depth, ants, hidden = self.explore_map[(row, col)]
        if depth > 0:
          r, c = self.destination((row, col), dir)
          return get_root(r, c)
        else:
          return (row, col)
          
      def calc_stats(row, col):
        dir, depth, ants, hidden = self.explore_map[(row, col)]
        
        if (row, col) in leafs:
          leafs.remove((row, col))
        else:
          for r, c in self.links[(row, col)]:
            a, h = calc_stats(r, c)
            ants = ants + a
            hidden = hidden + h
        
        self.explore_map[(row, col)] = dir, depth, ants, hidden
        
        return (ants, hidden)
      
      #for row, col in leafs:
      #    self.log_vision.write("Leaf at {0} {1}\n".format(row, col))
      
      
      while len(leafs) != 0:
        row, col = leafs[0]
        root_r, root_c = get_root(row, col)
        calc_stats(root_r, root_c)
         
      
      #for row, col in leafs:
      #  add_to_parent(row, col, 0, 0)
      
      #for row, col, depth, pdir in self.hidden:      
      #  self.log_vision.write("Hidden at {0}, {1} depth {2} parent {3}\n".format(row, col, depth, pdir))
        
      #for r, c in self.explore_map.keys():
      #  dir, depth, ants, hidden = self.explore_map[(r, c)]
      #  self.log_vision.write("Explore graph {0}, {1} depth {2} parent {3} ants {4} hidden {5}\n".format(r, c, depth, dir, ants, hidden))
        
      #for r, c, in leafs:
      #  self.log_vision.write("Leaf at {0} {1}\n".format(r, c))
      
      #for row, col in self.links.keys():
      #  self.log_vision.write("Links from {0} {1} to".format(row, col) + '%s\n' % ''.join([' ('+repr(r)+', '+repr(c)+')' for r, c in self.links[row, col]]))
      
      self.log_vision.write('Exploration done, %s left.\n\n' % self.time_remaining())
    
    def get_explore(self, loc):
      if loc in self.explore_map:
        return self.explore_map[loc]
      return False
      
    def get_links(self, loc):
      if loc in self.links:
        return self.links[loc]
      return False
    
    # -------------------- EXPRORE --------------------------
    
    # -------------------- DAMAGE MAP --------------------------
    
    def build_damage_map(self):
      self.damage_map = [[-999 for col in range(self.cols)] for row in range(self.rows)]
      for row, col in self.ant_list:
        if self.ant_list[(row, col)] != MY_ANT:
          self.place_damage_marker_sqr((row, col), int(sqrt(self.attackradius2))+2, -1)
            
      for row, col in self.ant_list:
        if self.ant_list[(row, col)] == MY_ANT:
          self.place_damage_marker_sqr((row, col), int(sqrt(self.attackradius2))-1, 1)
            
      for row, col in self.hill_list:
        if self.hill_list[(row, col)] == MY_ANT:
          self.place_damage_marker_sqr((row, col), int(sqrt(self.viewradius2))+2, 4)
        
      #self.log_vision.write(self.render_text_damage() + '\n')
      self.log_vision.write('Damage map build, %s left.\n\n' % self.time_remaining())
      
    def get_damage(self, loc):
      row, col = loc
      return self.damage_map[row][col]
        
    # -------------------- DAMAGE MAP --------------------------
    
    # -------------------- SMALL COMBAT --------------------------
    
    def get_distance(self, p1, p2):
      row1, col1 = p1
      row2, col2 = p2
      d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
      d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
      return (d_col)**2 + (d_row)**2
      
    def evalute(self, my, enemy):
      enemy_dmg_total = {}
      for _enemy in enemy:
        enemy_ant, de = _enemy
        enemy_dmg_total[enemy_ant] = 0.0
      
      for _my in my:
        my_ant, dm = _my
        num = 0
        enemy_dmg = []
        for _enemy in enemy:
          enemy_ant, de = _enemy
          if self.get_distance(my_ant, enemy_ant) <= self.attackradius2:
          #  x1, y1 = my_ant
          #  x2, y2 = enemy_ant
          #  self.log_vision.write('DETECTED {0}, {1} and {2}, {3}\n'.format(x1, y1, x2, y2))
            enemy_dmg.append(enemy_ant)
            num = num + 1
        
        for enemy_ant in enemy_dmg:
          enemy_dmg_total[enemy_ant] = enemy_dmg_total[enemy_ant] + 1.0/num
      
      res = 0
      for enemy_ant in enemy_dmg_total:
        if enemy_dmg_total[enemy_ant] >= 0.999:
          res = res + 1
      #self.log_vision.write('RESULT {0}\n'.format(res))
      return res
      
    def get_moves(self, ants):
      if len(ants) == 0:
        return []
      
      OFFSETS = {
       'p': (0, 0),
       'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
      
      #self.log_vision.write("get_moves ants" + str(ants) + "\n")
      
      row, col = ants[0]
      res = []
      rec_res = self.get_moves(ants[1:])
      for dir in OFFSETS:
        drow, dcol = OFFSETS[dir]
        if len(rec_res) > 0:
          for sequence in rec_res:
            loc = ((row + drow) % self.rows, (col + dcol) % self.cols)
            if self.passable(loc) and (loc not in sequence):
              seq_ext = [(loc, dir)]
              seq_ext.extend(sequence)
              res.append(seq_ext)
        else:
          loc = ((row + drow) % self.rows, (col + dcol) % self.cols)
          if self.passable(loc):
            res.append([(loc, dir)])
        
      #self.log_vision.write("get_moves res" + str(res) + "\n")
      return res
    
    def minmax(self, my, enemy):
      #self.log_vision.write("minmax my ants:" + str(my) + "\n")
      #self.log_vision.write("minmax enemy ants:" + str(enemy) + "\n")
      optimal = []
      optimal_val = -10000
      for my_move in self.get_moves(my):
        candidate = 10000
        for enemy_move in self.get_moves(enemy):
          balance = (1.0 + self.evalute(my_move, enemy_move)) /(1.0 + 2.0*self.evalute(enemy_move, my_move))
          #self.log_vision.write("Balance " + str(balance) + "\n")
          if optimal_val > balance:
            candidate = -10000
            break
          if candidate > balance:
            candidate = balance
        if candidate > optimal_val and candidate != 10000:
          optimal = my_move
          optimal_val = candidate
      
      res = {}
      #self.log_vision.write(str(my)+"\n")
      #self.log_vision.write(str(optimal_val)+str(optimal)+"\n")
      for index, loc in enumerate(my):
        res[loc] = optimal[index]
      return res
      
    def calc_combat(self):
      self.combat_moves = {}

      if not hasattr(self, 'attack_offsets_2'):
        self.attack_offsets_2 = []
        mx = 2+int(sqrt(self.attackradius2))
        for d_row in range(-mx,mx+1):
          for d_col in range(-mx,mx+1):
            d = d_row**2 + d_col**2
            if d <= mx**2 and d != 0:
              self.attack_offsets_2.append((d_row%self.rows-self.rows, d_col%self.cols-self.cols))
        #self.log_vision.write("attack_offsets_2 res" + str(self.attack_offsets_2) + "\n")
      
      for row, col in self.ant_list:
        if self.ant_list[(row, col)] == MY_ANT and self.get_combat_move((row, col)) == False:
          my_ants = [(row, col)]
          enemy_ants = []
          if self.damage_map[row][col] != -999:
            for v_row, v_col in self.attack_offsets_2:
              loc = ((row+v_row)%self.rows, (col+v_col)%self.cols)
              if loc in self.ant_list:
                if (self.ant_list[loc] == MY_ANT) and (self.get_combat_move(loc) == False):
                  my_ants.append(loc)
                if self.ant_list[loc] != MY_ANT:
                  enemy_ants.append(loc)
            if len(my_ants)<4 and len(enemy_ants)<4:
              self.combat_moves.update(self.minmax(my_ants, enemy_ants))
          #else:
          #  self.log_vision.write('damage_map[{0}][{1}] = {2}\n'.format(row, col, self.damage_map[row][col]))
            
      self.log_vision.write('MinMax combat done, %s left.\n\n' % self.time_remaining())
      
    def get_combat_move(self, loc):
      if loc in self.combat_moves:
        return self.combat_moves[loc]
      return False
      
    # -------------------- SMALL COMBAT --------------------------
    
    def update_dep(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.clock()
        
        # reset vision
        self.vision = None
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        last_food = self.food_list
        self.food_list = []
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
        # DAMAGE MAP
        self.damage_map = [[-999 for col in range(self.cols)] for row in range(self.rows)]
        for row, col in self.ant_list:
            if self.ant_list[(row, col)] != MY_ANT:
              self.place_damage_marker_sqr((row, col), int(sqrt(self.attackradius2))+1, -1)
              
        for row, col in self.ant_list:
            if self.ant_list[(row, col)] == MY_ANT:
              self.place_damage_marker_sqr((row, col), int(sqrt(self.attackradius2))-1, 1)
              
        for row, col in self.hill_list:
            if self.hill_list[(row, col)] == MY_ANT:
              self.place_damage_marker_sqr((row, col), int(sqrt(self.viewradius2))+2, 4)
        
        # MY ANTS COUNT
        my_ants = 1
        for row, col in self.ant_list:
            if self.ant_list[(row, col)] == MY_ANT:
              my_ants += 1
        
        # VISIBILITY AND OCCLUDERS
        self.wave = [[-1 for col in range(self.cols)] for row in range(self.rows)]
        for row in range(self.rows):
            for col in range(self.cols):
                #  WATER
                if self.map[row][col] == WATER:
                  self.wave[row][col] = 999
                #  VISION
                elif self.global_vision[row][col] == 0:
                  if not self.visible((row, col)):
                    self.wave[row][col] = 0
                  else:
                    self.global_vision[row][col] = 1
                elif not self.visible((row, col)):
                  self.wave[row][col] = 2*int(sqrt(self.viewradius2))#min(998, int((self.rows * self.cols)/my_ants))
        
        # FOOD MARKS
        for row, col in self.food_list:
            self.wave[row][col] = 0
            
        for row, col in last_food:
            if not self.visible((row, col)):
                self.wave[row][col] = 0
        
        # ENEMY HILL
        for row, col in self.hill_list:
            if self.hill_list[(row, col)] != MY_ANT:
                self.wave[row][col] = 0
            else:
                self.wave[row][col] = 999
        
        # ATTACK ENEMY ANTS
        for row in range(self.rows):
            for col in range(self.cols):
                if self.damage_map[row][col] > 0 and self.wave[row][col] != 999:
                  if self.wave[row][col] >= self.damage_map[row][col]:
                    self.wave[row][col] -= self.damage_map[row][col]
                  else:
                    self.wave[row][col] = 0
                    
        #self.log_vision.write(self.render_text_wave() + '\n')
        
        # WAVE GENERATION
        front = []
        for row in range(self.rows):
            for col in range(self.cols):
                if front.count((row, col))==0:
                    w = 1 + self.wave[row][col]
                    if w!=0 and w!=1000 and w!=999:
                        for dir in AIM:
                            x, y = self.destination((row, col), dir)
                            if self.wave[x][y]==-1 or (w < self.wave[x][y] and self.wave[x][y]!=999):
                                self.wave[x][y] = w
                                front.append((x, y))
        
        new_front = []
        while len(front)!=0:
            for row, col in front:
                w = 1 + self.wave[row][col]
                for dir in AIM:
                    x, y = self.destination((row, col), dir)
                    if self.wave[x][y]==-1 or (w < self.wave[x][y] and self.wave[x][y]!=999):
                        self.wave[x][y] = w
                        new_front.append((x, y))
            front = new_front
            new_front = []
            
        # AVOID ENEMY ANTS
        for row in range(self.rows):
            for col in range(self.cols):
                if self.damage_map[row][col] <= 0 and self.damage_map[row][col] != -999:
                  if self.wave[row][col] != 999:
                    self.wave[row][col] += 2-self.damage_map[row][col]
        
        # MY HILL
        #for row, col in self.hill_list:
            #if self.hill_list[(row, col)] == MY_ANT:
                #self.place_marker((row, col), int(sqrt(self.attackradius2)))
        
        # ANT MARKERS
        #for row, col in self.ant_list:
        #    if self.ant_list[(row, col)] == MY_ANT:
        #        self.place_marker_sqr((row, col), 1+int(sqrt(self.attackradius2)))
        
        # WALLS PUSH
        #for row in range(self.rows):
        #  for col in range(self.cols):
        #    if self.wave[row][col] == 999:
        #      self.place_marker((row, col), 2)
        
        # LOG
        self.log_vision.write(self.render_text_map() + '\n')
        self.log_vision.write(self.render_text_wave() + '\n')
        self.log_vision.write(self.render_text_damage() + '\n')
        self.log_vision.write('turn ' + repr(self.turn) + ' %s\n\n' % self.time_remaining())
        
        self.turn += 1
        
    def log(self, str):
        self.log_vision.write(str + '\n')
        
    def time_remaining(self):
        return self.turntime - int(1000 * (time.clock() - self.turn_start_time))
    
    def issue_order(self, order):
        'issue an order by writing the proper ant location and direction'
        (row, col), direction = order
        sys.stdout.write('o %s %s %s\n' % (row, col, direction))
        sys.stdout.flush()
        
    def finish_turn(self):
        'finish the turn by writing the go line'
        sys.stdout.write('go\n')
        sys.stdout.flush()
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        'return a list of all food locations'
        return self.food_list[:]

    def passable(self, loc):
        'true if not water'
        row, col = loc
        return self.map[row][col] != WATER
    
    def unoccupied(self, loc):
        'true if no ants are at the location'
        row, col = loc
        return self.map[row][col] in (LAND, DEAD)
        
    def get_wave(self, loc):
        row, col = loc
        return self.wave[row][col]

    def distance(self, loc1, loc2):
        'calculate the closest distance between to locations'
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def direction(self, loc1, loc2):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = loc1
        row2, col2 = loc2
        height2 = self.rows//2
        width2 = self.cols//2
        d = []
        if row1 < row2:
            if row2 - row1 >= height2:
                d.append('n')
            if row2 - row1 <= height2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= height2:
                d.append('s')
            if row1 - row2 <= height2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= width2:
                d.append('w')
            if col2 - col1 <= width2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= width2:
                d.append('e')
            if col1 - col2 <= width2:
                d.append('w')
        return d

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        'parse input, update game state and call the bot classes do_turn method'
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()