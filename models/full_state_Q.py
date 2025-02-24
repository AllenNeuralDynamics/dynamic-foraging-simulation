# -*- coding: utf-8 -*-
"""
Created on Fri May  8 22:29:03 2020

@author: Han
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter

from utils.helper_func import choose_ps, softmax

class FullStateQ():

    def __init__(self, K_arm = 2, first_choice = None,
                 max_run_length = 10, 
                 discount_rate = 0.99,
                 
                 learn_rate = 0.1,
                 softmax_temperature = None, 
                 epsilon = None,
                 if_record_Q = '',
                 ):
        
        self.if_record_Q = if_record_Q
        self.learn_rate = learn_rate
        self.softmax_temperature = softmax_temperature
        self.discount_rate = discount_rate
        self.epsilon = epsilon
        
        self._init_states(max_run_length, K_arm)
        self.ax = []
        
        if first_choice is None: 
            first_choice = np.random.choice(K_arm)
        self.current_state = self.states[first_choice, 0]  # Randomly initialize the first choice
        self.backup_SA = [self.current_state, -1]  # First trial is a STAY at first_choice
        
        if self.softmax_temperature is not None:
            self.if_softmax = True
        elif self.epsilon is not None:
            self.if_softmax = False
        else:
            raise ValueError('Both softmax_temp and epsilon are missing!')

    def _init_states(self, max_run_length, K_arm):
        # Generate a K_arm * max_run_length numpy array of states
        max_run_length = int(np.ceil(max_run_length))
        
        self.states = np.zeros([K_arm, max_run_length], dtype=object)
        for k in range(K_arm):
            for r in range(max_run_length):
                self.states[k,r] = State(k, r)
                
        # Define possible transitions
        for k in range(K_arm):
            for r in range(max_run_length):
                for kk in range(K_arm):
                    # Leave: to any other arms
                    if k != kk: self.states[k, r].add_next_states([self.states[kk, 0]])
                
                if r < max_run_length-1: self.states[k, r].add_next_states([self.states[k, r+1]])  # Stay is always the last index
                
    def act(self):   # State transition
        if self.if_softmax:
            next_state_idx = self.current_state.act_softmax(self.softmax_temperature)  # Next state index!!
        else:  # Epsilon-greedy
            next_state_idx = self.current_state.act_epsilon(self.epsilon)  # Next state index!!
        
        self.backup_SA = [self.current_state, next_state_idx]     # For one-step backup in Q-learning
        self.current_state = self.current_state.next_states[next_state_idx]
        choice = self.current_state.which[0]  # Return absolute choice! (LEFT/RIGHT)
        return choice  
        
    def update_Q(self, reward):    # Q-learning (off-policy TD-0 bootstrap)
        max_next_SAvalue_for_backup_state = np.max(self.current_state.Q)  # This makes it off-policy
        last_state, last_choice = self.backup_SA
        last_state.Q[last_choice] += self.learn_rate * (reward + self.discount_rate * max_next_SAvalue_for_backup_state 
                                                        - last_state.Q[last_choice])  # Q-learning

        # print('Last: ', last_state.which, '(updated); This: ', self.current_state.which)
        # print('----------------------------------')
        # print('Left, leave: ', [s.Q[0] for s in self.states[0,:]])
        # print('Right,leave: ', [s.Q[0] for s in self.states[1,:]])
        # print('Left, stay : ', [s.Q[1] for s in self.states[0,:]])
        # print('Right,stay : ', [s.Q[1] for s in self.states[1,:]])
        
    def plot_Q(self, time = np.nan, reward = np.nan, p_reward = np.nan, description = ''):  # Visualize value functions (Q(s,a))
        # Initialization
        if self.ax == []:   
            # Prepare axes
            self.fig, self.ax = plt.subplots(2,2, sharey=True, figsize=[12,8])
            plt.subplots_adjust(hspace=0.5, top=0.85)
            self.ax2 = self.ax.copy()
            self.annotate = plt.gcf().text(0.05, 0.9, '', fontsize = 13)
            for c in [0,1]:
                for d in [0,1]:
                    self.ax2[c, d] = self.ax[c,d].twinx()
                    
            # Prepare animation
            if self.if_record_Q:
                metadata = dict(title='FullStateQ', artist='Matplotlib')
                self.writer = FFMpegWriter(fps=25, metadata=metadata)
                self.writer.setup(self.fig, "..\\results\\%s.mp4"%description, 150)
            
        direction = ['LEFT', 'RIGHT']    
        decision = ['Leave', 'Stay']
        X = np.r_[1:np.shape(self.states)[1]-0.1]  # Ignore the last run_length (Must leave)
        
        # -- Q values and policy --
        for d in [0,1]:
            # Compute policy p(a|s)
            if self.if_softmax:
                Qs = np.array([s.Q for s in self.states[d,:-1]])
                ps = []
                for qq in Qs:
                    ps.append(softmax(qq, self.softmax_temperature))    
                ps = np.array(ps)
                
            for c in [0,1]:
                self.ax[c, d].cla()
                self.ax2[c, d].cla()
                
                self.ax[c, d].set_xlim([0, max(X)+1])
                self.ax[c, d].set_ylim([-0.05,max(plt.ylim())])

                bar_color = 'r' if c == 0 else 'g'

                self.ax[c, d].bar(X, Qs[:,c], color=bar_color, alpha = 0.5)
                self.ax[c, d].set_title(direction[d] + ', ' + decision[c])
                self.ax[c, d].axhline(0, color='k', ls='--')
                if d == 0: self.ax[c, d].set_ylabel('Q(s,a)', color='k')                
                # self.ax[c, d].set_xticks(np.round(self.ax[c, d].get_xticks()))
                self.ax[c, d].set_xticks(X)
                
                self.ax2[c, d].plot(X, ps[:,c], bar_color+'-o')
                if d == 1: self.ax2[c, d].set_ylabel('P(a|s)', color=bar_color)
                self.ax2[c, d].axhline(0, color=bar_color, ls='--')
                self.ax2[c, d].axhline(1, color=bar_color, ls='--')
                self.ax2[c, d].set_ylim([-0.05,1.05])
                
        # -- This state --
        last_state = self.backup_SA[0].which
        current_state = self.current_state.which
        if time > 1: self.ax2[0, last_state[0]].plot(last_state[1]+1, self.last_reward, 'go', markersize=10, alpha = 0.5)
        self.ax2[0, current_state[0]].plot(current_state[1]+1, reward, 'go', markersize=15)
        self.last_reward = reward
            
        # plt.ylim([-1,1])
        self.annotate.set_text('%s\nt = %g, p_reward = %s\n%s --> %s, reward = %g\n' % (description, time, p_reward, last_state, current_state, reward))
        if self.if_record_Q:
            print(time)
            self.writer.grab_frame()
            return True
        else:
            plt.gcf().canvas.draw()
            return plt.waitforbuttonpress()
        
class State():   
    
    '''
    Define states. 
    Technically, they're "agent states" in the agent's mind, 
    but in the baiting problem, they're actually also the CORRECT state representation of the environment
    '''    
    def __init__(self, _k, _run_length):
        # Which state is this?
        self.which = [_k, _run_length] # To be pricise: run_length - 1
        
        self.Q = np.array([.0, .0])   # Action values for [Leave, Stay] of this state. Initialization value could be considered as priors?
        self.next_states = []  # All possible next states (other instances of class State)
    
    def add_next_states(self, next_states):
        self.next_states.extend(next_states)
        
    def act_softmax(self, softmax_temp):  # Generate the next action using softmax(Q) policy
        next_state_idx = choose_ps(softmax(self.Q[:len(self.next_states)], softmax_temp))
        return next_state_idx  # Return the index of the next state

    def act_epsilon(self, epsilon):  # Generate the next action using epsilon-greedy (More exploratory)
        if np.random.rand() < epsilon:
            next_state_idx = np.random.choice(len(self.next_states))
        else:   # Greedy
            Q_available = self.Q[:len(self.next_states)]
            next_state_idx = np.random.choice(np.where(Q_available == Q_available.max())[0])
        return next_state_idx  # Return the index of the next state
