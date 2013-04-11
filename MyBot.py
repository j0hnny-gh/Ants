#!/usr/bin/env python
from ants import *

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us
class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        self.orders = {}
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    # the ants class is created and setup by the Ants.run method
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        pass
    
    # do turn is run once per turn
    # the ants class has the game state and is updated by the Ants.run method
    # it also has several helper methods to use
    def do_turn(self, ants):
    
      last_orders = {}
      for loc in self.orders:
          last_orders[loc] = self.orders[loc]
      self.orders = {}
      moves = {}
      occupied_orders = {}
      
      AIM = {(-1, 0): 'n',
       (0, 1): 'e',
       (1, 0): 's',
       (0, -1): 'w'}
        
      def do_move_direction(new_loc):
        if (new_loc not in self.orders and new_loc not in occupied_orders): 
            return True
        else:
            return False
            
      def move_to(ant_loc, direction):
        new_loc = ants.destination(ant_loc, direction)
        if do_move_direction(new_loc):
          if ants.unoccupied(new_loc):
            self.orders[new_loc] = direction
            moves[ant_loc] = direction
            x, y  = ant_loc
            #ants.log('Move for {0} {1}\n'.format(x, y))
          else:
            occupied_orders[new_loc] = (ant_loc, direction)
          return True
        return False
      
      for ant_loc in ants.my_ants():
        new = ants.get_combat_move(ant_loc)
        if new != False:
          new_loc, dir = new
          r, c = ant_loc
          #ants.log('Combat move to {0}, {1} form {2}, {3}\n'.format(nr, nc, r, c))
          if dir != 'p':
            move_to(ant_loc, dir)
            #  ants.log('Combat move dir {0} {1}\n'.format(dir, moves[ant_loc]))
            #else:
            #  ants.log('Rejected move dir {0}\n'.format(dir))
      
      for ant_loc in ants.my_ants():
        # combat
        if ants.get_combat_move(ant_loc) != False:
          #x, y  = ant_loc
          #ants.log('Skiping move for {0} {1}\n'.format(x, y))
          continue
          
        dmg = ants.get_damage(ant_loc)
        w_dir = 0
        if dmg != -999:
          p_dir = ants.get_explore(ant_loc)[0]
          if p_dir == 0: # should prevent blocking hill
            dmg = -1000
          for dir in ['n','e','s','w']:
            loc = ants.destination(ant_loc, dir)
            if ants.passable(loc) and do_move_direction(loc):
              dir_dmg =  ants.get_damage(loc)
              if (dir_dmg>dmg and (dir_dmg>0 or dmg!=-999)) or (dir_dmg==-999 and dmg<=0):
                w_dir = dir
                dmg = dir_dmg
          if w_dir!=0:
            move_to(ant_loc, w_dir)
        else:
          # food
          res, dir = ants.need_take_food(ant_loc)
          if res:
            move_to(ant_loc, dir)
          else:
            # exploration
            w, w_loc = 0, (-1, -1)
            explore = []
            if ants.get_links(ant_loc) != False:
              explore = [(loc, ants.get_explore(loc)) for loc in ants.get_links(ant_loc)]
            #ants.log(str(explore))
            p_dir = ants.get_explore(ant_loc)[0]
            p_loc = (-1, -1)
            if p_dir != 0:
              p_loc = ants.destination(ant_loc, p_dir)
            for data in explore:
              loc, res = data
              if res != False:
                depth, ants_num, hidden = res[1:]
                if (w < hidden/(1.0+ants_num)) and do_move_direction(loc) and loc!=p_loc:
                  w = hidden/(1.0+ants_num)
                  w_loc = loc
            if w_loc != (-1, -1):
              w_dir = BEHIND[ants.get_explore(w_loc)[0]]
              if ants.unoccupied(w_loc):
                self.orders[w_loc] = w_dir
                moves[ant_loc] = w_dir
              else:
                occupied_orders[w_loc] = (ant_loc, w_dir)
            else:
              if p_dir==0 or not move_to(ant_loc, p_dir):
                # patrol
                directions = ['n','e','s','w']
                random.shuffle(directions)
                for dir in directions:
                  if move_to(ant_loc, dir):
                    break
        
        if ants.time_remaining() < 100:
          break
          
      l = len(occupied_orders)
      new_l = 0
        
      while l > new_l:
        l = len(occupied_orders)
        #ants.log('occupied_orders len = {0} {1}\n'.format(l, ants.time_remaining()))
        if ants.time_remaining() < 40:
          break
        occupied_orders_copy = occupied_orders.copy()
        for new_loc in occupied_orders_copy:
          #ants.log('occupied_orders loc = {0} {1}\n'.format(new_loc, ants.time_remaining()))
          if (new_loc in moves and new_loc not in self.orders):
            loc, dir = occupied_orders[new_loc]
            moves[loc] = dir
            self.orders[new_loc] = dir
            del occupied_orders[new_loc]
            #ants.log('occupied_orders--\n')
        new_l = len(occupied_orders)
        
      for ant_loc in ants.my_ants():
        if ant_loc in moves:
          dir = moves[ant_loc]
          #ants.log('orders loc = {0} {1}'.format(ant_loc, dir))
          ants.issue_order((ant_loc, dir))
     
    def do_turn_depr(self, ants):
        last_orders = {}
        for loc in self.orders:
            last_orders[loc] = self.orders[loc]
        self.orders = {}
        moves = {}
        occupied_orders = {}
        
        def do_move_direction(new_loc):
            if (new_loc not in self.orders and new_loc not in occupied_orders): 
                return True
            else:
                return False
        
        for ant_loc in ants.my_ants():
            directions = ['n','e','s','w']
            random.shuffle(directions)
            w_min = 999
            w_dir = {}
            
            if ant_loc in last_orders:
                w_dir = last_orders[ant_loc]
                new_loc = ants.destination(ant_loc, w_dir)
                if do_move_direction(new_loc):
                    w_min = ants.get_wave(new_loc)
            
            for direction in directions:
                new_loc = ants.destination(ant_loc, direction)
                w = ants.get_wave(new_loc)
                if w < w_min and do_move_direction(new_loc):
                    w_min = w
                    w_dir = direction
                    
            w = ants.get_wave(ant_loc)
            if w < w_min:
                w_min = 999
            
            if w_min!=999:
                new_loc = ants.destination(ant_loc, w_dir)
                if ants.unoccupied(new_loc):
                  self.orders[new_loc] = w_dir
                  moves[ant_loc] = w_dir
                else:
                  occupied_orders[new_loc] = (ant_loc, w_dir)
            
            if ants.time_remaining() < 100:
                break
        
        l = len(occupied_orders)
        new_l = 0
        while l > new_l:
          l = len(occupied_orders)
          #ants.log('occupied_orders len = {0} {1}\n'.format(l, ants.time_remaining()))
          if ants.time_remaining() < 10:
            break
          occupied_orders_copy = occupied_orders.copy()
          for new_loc in occupied_orders_copy:
            #ants.log('occupied_orders loc = {0} {1}\n'.format(new_loc, ants.time_remaining()))
            if (new_loc in moves and new_loc not in self.orders):
              loc, dir = occupied_orders[new_loc]
              moves[loc] = dir
              self.orders[new_loc] = dir
              del occupied_orders[new_loc]
              #ants.log('occupied_orders--\n')
          new_l = len(occupied_orders)
        
        for new_loc in occupied_orders:
          ant_loc, dir = occupied_orders[new_loc]
          directions = ['n','e','s','w']
          random.shuffle(directions)
          w_min = 999
          w_dir = {}
          for direction in directions:
            if direction!=dir:
              rnd_loc = ants.destination(ant_loc, direction)
              if do_move_direction(rnd_loc) and ants.unoccupied(rnd_loc):
                w = ants.get_wave(new_loc)
                if w < w_min:
                  w_min = w
                  w_dir = direction
          
          if w_min != 999:
            dst = ants.destination(ant_loc, w_dir)
            self.orders[dst] = w_dir
            moves[ant_loc] = w_dir
            
        for ant_loc in ants.my_ants():
          if ant_loc in moves:
            dir = moves[ant_loc]
            #ants.log('orders loc = {0} {1}'.format(ant_loc, dir))
            ants.issue_order((ant_loc, dir))
            
if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
