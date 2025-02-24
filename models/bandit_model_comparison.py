# -*- coding: utf-8 -*-
"""
Created on Sat Apr 11 15:15:49 2020

@author: Han
"""
import numpy as np
import pandas as pd
import time

from models.fitting_functions import fit_bandit, cross_validate_bandit
from utils.plot_fitting import plot_model_comparison_predictive_choice_prob, plot_model_comparison_result
from IPython.display import display

# Default models (reordered with hindsight results). Use the format: [forager, [para_names], [lower bounds], [higher bounds]]
MODELS = [
            # No bias (1-8)
            ['LossCounting', ['loss_count_threshold_mean', 'loss_count_threshold_std'], [0,0], [40,10]],                   
            ['RW1972_epsi', ['learn_rate', 'epsilon'],[0, 0],[1, 1]],
            ['LNP_softmax',  ['tau1', 'softmax_temperature'], [1e-3, 1e-2], [100, 15]],                 
            ['LNP_softmax', ['tau1', 'tau2', 'w_tau1', 'softmax_temperature'],[1e-3, 1e-1, 0, 1e-2],[15, 40, 1, 15]],                 
            ['RW1972_softmax', ['learn_rate', 'softmax_temperature'],[0, 1e-2],[1, 15]],
            ['Hattori2019', ['learn_rate_rew', 'learn_rate_unrew', 'softmax_temperature'],[0, 0, 1e-2],[1, 1, 15]],
            ['Bari2019', ['learn_rate', 'forget_rate', 'softmax_temperature'],[0, 0, 1e-2],[1, 1, 15]],
            ['Hattori2019', ['learn_rate_rew', 'learn_rate_unrew', 'forget_rate', 'softmax_temperature'],[0, 0, 0, 1e-2],[1, 1, 1, 15]],
            
            # With bias (9-15)
            ['RW1972_epsi', ['learn_rate', 'epsilon', 'biasL'],[0, 0, -0.5],[1, 1, 0.5]],
            ['LNP_softmax',  ['tau1', 'softmax_temperature', 'biasL'], [1e-3, 1e-2, -5], [100, 15, 5]],                 
            ['LNP_softmax', ['tau1', 'tau2', 'w_tau1', 'softmax_temperature', 'biasL'],[1e-3, 1e-1, 0, 1e-2, -5],[15, 40, 1, 15, 5]],                 
            ['RW1972_softmax', ['learn_rate', 'softmax_temperature', 'biasL'],[0, 1e-2, -5],[1, 15, 5]],
            ['Hattori2019', ['learn_rate_rew', 'learn_rate_unrew', 'softmax_temperature', 'biasL'],[0, 0, 1e-2, -5],[1, 1, 15, 5]],
            ['Bari2019', ['learn_rate', 'forget_rate', 'softmax_temperature', 'biasL'],[0, 0, 1e-2, -5],[1, 1, 15, 5]],
            ['Hattori2019', ['learn_rate_rew', 'learn_rate_unrew', 'forget_rate', 'softmax_temperature', 'biasL'],[0, 0, 0, 1e-2, -5],[1, 1, 1, 15, 5]],
            
            # With bias and choice kernel (16-21)
            ['LNP_softmax_CK',  ['tau1', 'softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'], 
                             [1e-3, 1e-2, -5, 0, 1e-2], [100, 15, 5, 1, 20]],                 
            ['LNP_softmax_CK', ['tau1', 'tau2', 'w_tau1', 'softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
                             [1e-3, 1e-1, 0, 1e-2, -5, 0, 1e-2],[15, 40, 1, 15, 5, 1, 20]],                 
            ['RW1972_softmax_CK', ['learn_rate', 'softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
                             [0, 1e-2, -5, 0, 1e-2],[1, 15, 5, 1, 20]],
            ['Hattori2019_CK', ['learn_rate_rew', 'learn_rate_unrew', 'softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
                             [0, 0, 1e-2, -5, 0, 1e-2],[1, 1, 15, 5, 1, 20]],
            ['Bari2019_CK', ['learn_rate', 'forget_rate', 'softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
                             [0, 0, 1e-2, -5, 0, 1e-2],[1, 1, 15, 5, 1, 20]],
            ['Hattori2019_CK', ['learn_rate_rew','learn_rate_unrew', 'forget_rate','softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
                               [0, 0, 0, 1e-2, -5, 0, 1e-2],[1, 1, 1, 15, 5, 1, 20]],
            # ['Hattori2019_CK', ['learn_rate_rew','learn_rate_unrew', 'forget_rate','softmax_temperature', 'biasL', 'choice_step_size','choice_softmax_temperature'],
            #                    [0, 0, 0, 1e-2, -5, 1, 1e-2],[1, 1, 1, 15, 5, 1, 20]],  # choice_step_size fixed at 1 --> Bari 2019: only the last choice matters
            
         ]

# Define notations
PARA_NOTATIONS = {'loss_count_threshold_mean': '$\\mu_{LC}$',
            'loss_count_threshold_std': '$\\sigma_{LC}$',
            'tau1': '$\\tau_1$',
            'tau2': '$\\tau_2$',
            'w_tau1': '$w_{\\tau_1}$',
            'learn_rate': '$\\alpha$',   
            'learn_rate_rew': '$\\alpha_{rew}$',   
            'learn_rate_unrew': '$\\alpha_{unr}$',   
            'forget_rate': '$\\delta$',
            'softmax_temperature': '$\\sigma$',
            'epsilon': '$\\epsilon$',
            'biasL': '$b_L$',
            'biasR': '$b_R$',
            'choice_step_size': '$\\alpha_c$',
            'choice_softmax_temperature': '$\\sigma_c$',
            }


class BanditModelComparison:
    
    '''
    A new class that can define models, receive data, do fitting, and generate plots.
    This is the minimized module that can be plugged into Datajoint for real data.
    
    '''
    
    def __init__(self, choice_history, reward_history, p_reward = None, session_num = None, models = None):
        """

        Parameters
        ----------
        choice_history, reward_history, (p_reward), (session_num)
            DESCRIPTION. p_reward is only for plotting or generative validation; session_num is for pooling across sessions
        models : list of integers or models, optional
            DESCRIPTION. If it's a list of integers, the models will be selected from the pre-defined models.
            If it's a list of models, then it will be used directly. Use the format: [forager, [para_names], [lower bounds], [higher bounds]]
            The default is None (using all pre-defined models).
        Returns
        -------
        None.

        """
        
        if models is None:  
            self.models = MODELS
        elif type(models[0]) is int:
            self.models = [MODELS[i-1] for i in models]
        else:
            self.models = models
            
        self.fit_choice_history, self.fit_reward_history, self.p_reward, self.session_num = choice_history, reward_history, p_reward, session_num
        self.K, self.n_trials = np.shape(self.fit_reward_history)
        assert np.shape(self.fit_choice_history)[1] == self.n_trials, 'Choice length should be equal to reward length!'
        
        return
        
    def fit(self, fit_method = 'DE', fit_settings = {'DE_pop_size': 16}, pool = '',
                  if_verbose = True, 
                  plot_predictive = None,  # E.g.: 0,1,2,-1: The best, 2nd, 3rd and the worst model
                  plot_generative = None):
        
        self.results_raw = []
        self.results = pd.DataFrame()
        
        if if_verbose: print('=== Model Comparison ===\nMethods = %s, %s, pool = %s' % (fit_method, fit_settings, pool!=''))
        for mm, model in enumerate(self.models):
            # == Get settings for this model ==
            forager, fit_names, fit_lb, fit_ub = model
            fit_bounds = [fit_lb, fit_ub]
            
            para_notation = ''
            Km = 0
            
            for name, lb, ub in zip(fit_names, fit_lb, fit_ub):
                # == Generate notation ==
                if lb < ub:
                    para_notation += PARA_NOTATIONS[name] + ', '
                    Km += 1
            
            para_notation = para_notation[:-2]
            
            # == Do fitting here ==
            #  Km = np.sum(np.diff(np.array(fit_bounds),axis=0)>0)
            
            if if_verbose: print('Model %g/%g: %15s, Km = %g ...'%(mm+1, len(self.models), forager, Km), end='')
            start = time.time()
                
            result_this = fit_bandit(forager, fit_names, fit_bounds, self.fit_choice_history, self.fit_reward_history, self.session_num,
                                     fit_method = fit_method, **fit_settings, 
                                     pool = pool, if_predictive = True) #plot_predictive is not None)
            
            if if_verbose: print(' AIC = %g, BIC = %g (done in %.3g secs)' % (result_this.AIC, result_this.BIC, time.time()-start) )
            self.results_raw.append(result_this)
            self.results = self.results.append(pd.DataFrame({'model': [forager], 'Km': Km, 'AIC': result_this.AIC, 'BIC': result_this.BIC, 
                                    'LPT_AIC': result_this.LPT_AIC, 'LPT_BIC': result_this.LPT_BIC, 'LPT': result_this.LPT,
                                    'para_names': [fit_names], 'para_bounds': [fit_bounds], 
                                    'para_notation': [para_notation], 'para_fitted': [np.round(result_this.x,3)]}, index = [mm+1]))
        
        # == Reorganize data ==
        delta_AIC = self.results.AIC - np.min(self.results.AIC) 
        delta_BIC = self.results.BIC - np.min(self.results.BIC)

        # Relative likelihood = Bayes factor = p_model/p_best = exp( - delta_AIC / 2)
        self.results['relative_likelihood_AIC'] = np.exp( - delta_AIC / 2)
        self.results['relative_likelihood_BIC'] = np.exp( - delta_BIC / 2)

        # Model weight = Relative likelihood / sum(Relative likelihood)
        self.results['model_weight_AIC'] = self.results['relative_likelihood_AIC'] / np.sum(self.results['relative_likelihood_AIC'])
        self.results['model_weight_BIC'] = self.results['relative_likelihood_BIC'] / np.sum(self.results['relative_likelihood_BIC'])
        
        # log_10 (Bayes factor) = log_10 (exp( - delta_AIC / 2)) = (-delta_AIC / 2) / log(10)
        self.results['log10_BF_AIC'] = - delta_AIC/2 / np.log(10) # Calculate log10(Bayes factor) (relative likelihood)
        self.results['log10_BF_BIC'] = - delta_BIC/2 / np.log(10) # Calculate log10(Bayes factor) (relative likelihood)
        
        self.results['best_model_AIC'] = (self.results.AIC == np.min(self.results.AIC)).astype(int)
        self.results['best_model_BIC'] = (self.results.BIC == np.min(self.results.BIC)).astype(int)
        
        self.results_sort = self.results.sort_values(by='AIC')
        
        self.trial_numbers = result_this.trial_numbers 
        
        # == Plotting == 
        if plot_predictive is not None: # Plot the predictive choice trace of the best fitting of the best model (Using AIC)
            self.plot_predictive = plot_predictive
            self.plot_predictive_choice()
        return
    
    def cross_validate(self, k_fold = 2, fit_method = 'DE', fit_settings = {'DE_pop_size': 16}, pool = '', if_verbose = True):
        
        self.prediction_accuracy_CV = pd.DataFrame()
        
        if if_verbose: print('=== Cross validation ===\nMethods = %s, %s, pool = %s' % (fit_method, fit_settings, pool!=''))
        
        for mm, model in enumerate(self.models):
            # == Get settings for this model ==
            forager, fit_names, fit_lb, fit_ub = model
            fit_bounds = [fit_lb, fit_ub]
            
            para_notation = ''
            Km = 0
            
            for name, lb, ub in zip(fit_names, fit_lb, fit_ub):
                # == Generate notation ==
                if lb < ub:
                    para_notation += PARA_NOTATIONS[name] + ', '
                    Km += 1
            
            para_notation = para_notation[:-2]
            
            # == Do fitting here ==
            #  Km = np.sum(np.diff(np.array(fit_bounds),axis=0)>0)
            
            if if_verbose: print('Model %g/%g: %15s, Km = %g ...'%(mm+1, len(self.models), forager, Km), end = '')
            start = time.time()
                
            prediction_accuracy_test, prediction_accuracy_fit, prediction_accuracy_test_bias_only= cross_validate_bandit(forager, fit_names, fit_bounds, 
                                                                                      self.fit_choice_history, self.fit_reward_history, self.session_num, 
                                                                                      k_fold = k_fold, **fit_settings, pool = pool, if_verbose = if_verbose) #plot_predictive is not None)
            
            if if_verbose: print('  \n%g-fold CV: Test acc.= %s, Fit acc. = %s (done in %.3g secs)' % (k_fold, prediction_accuracy_test, prediction_accuracy_fit, time.time()-start) )
            
            self.prediction_accuracy_CV = pd.concat([self.prediction_accuracy_CV, 
                                                     pd.DataFrame({'model#': mm,
                                                                   'forager': forager,
                                                                   'Km': Km,
                                                                   'para_notation': para_notation,
                                                                   'prediction_accuracy_test': prediction_accuracy_test, 
                                                                   'prediction_accuracy_fit': prediction_accuracy_fit,
                                                                   'prediction_accuracy_test_bias_only': prediction_accuracy_test_bias_only})])
            
        return

    def plot_predictive_choice(self):
        plot_model_comparison_predictive_choice_prob(self)

    def show(self):
        pd.options.display.max_colwidth = 100
        display(self.results_sort[['model','Km', 'AIC','log10_BF_AIC', 'model_weight_AIC', 'BIC','log10_BF_BIC', 'model_weight_BIC', 'para_notation','para_fitted']].round(2))
        
    def plot(self):
        plot_model_comparison_result(self)

