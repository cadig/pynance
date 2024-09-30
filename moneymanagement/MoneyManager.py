import math

class MoneyManager(object):
    """
    A class object that implements money management algorithms 
    based on initialization params
    """

    def __init__(self, cycle_target, base_risk_pct, pct_bump=.001, flat_lining=True, stay_at_max=True):
        self.cycle_target = cycle_target
        self.base_risk_pct = float( base_risk_pct )
        
        if pct_bump is not None:
            self.pct_bump = float( pct_bump )
        else:
            self.pct_bump = pct_bump
            
        self.flat_lining = flat_lining
        self.stay_at_max = stay_at_max
        
    def getMartingaleSizeTarget(self, loss_streak):
        """Doubles the bet size for every loss incurred in a consecutive streak, up to the max_loss_cycle number."""
        max_loss_cycle = self.cycle_target
        base_risk_pct = self.base_risk_pct  
    
        if loss_streak == 0:
            size_target = base_risk_pct
        elif loss_streak > max_loss_cycle:
            print('getCumulativeNegativeProgressionSizeTarget loss_streak is over max_loss_cycle! Using base_risk_pct...')
            size_target = base_risk_pct
        else:
            # for iter in range(0,loss_streak):
            size_target = (pow(2,loss_streak)*base_risk_pct) # + base_risk_pct
        return size_target
    
    def getReverseMartingaleSizeTarget(self, win_streak):
        """Doubles the bet size for every loss incurred in a consecutive streak, up to the max_loss_cycle number."""
        max_loss_cycle = self.cycle_target
        base_risk_pct = self.base_risk_pct  
    
        if win_streak == 0:
            size_target = base_risk_pct
        elif win_streak > max_loss_cycle:
            print('getReverseMartingaleSizeTarget win_streak is over max_win_cycle! Using base_risk_pct...')
            size_target = base_risk_pct
        else:
            size_target = (pow(2,win_streak)*base_risk_pct)
        return size_target

    def getConsecutiveWinsSizeTarget(self, win_streak):
        """Money management algorithm based on consecutive wins strategy. 
        Units are measured as percentage of account value.
        Note if flat_lining is false, then this function uses base_risk_pct 
        as the target variable during iterations."""
        cycle_target = self.cycle_target
        base_risk_pct = self.base_risk_pct
        pct_bump = self.pct_bump
        flat_lining = self.flat_lining
        stay_at_max = self.stay_at_max

        if win_streak == 0:
            size_target = base_risk_pct

        elif win_streak == cycle_target:
            if stay_at_max == False:
                #print('getConsecutiveWinsSizeTarget: cycle_target hit! Resetting size target...')
                size_target = base_risk_pct
            elif stay_at_max == True:
                #print('getConsecutiveWinsSizeTarget: cycle_target hit! Staying at max units...')
                size_target = base_risk_pct + (cycle_target * pct_bump)

        elif win_streak > cycle_target:
            if stay_at_max == False:
                cycle_resets = math.floor(win_streak / cycle_target)
                reset_win_streak = win_streak - (cycle_target * cycle_resets)
                if flat_lining:
                    size_target = base_risk_pct + (pct_bump*reset_win_streak)
                else:
                    size_target = base_risk_pct * (reset_win_streak+1)
                    print('getConsecutiveWinsSizeTarget: win_streak > cycle_target:',
                          '\n\twin_streak', win_streak,
                          '\n\tcycle_resets', cycle_resets,
                          '\n\treset_win_streak', reset_win_streak,
                          '\n\t### size_target', size_target, '###')
            elif stay_at_max == True:
                # print('getConsecutiveWinsSizeTarget: Passed cycle_target, staying at max units.')
                size_target = base_risk_pct + (cycle_target * pct_bump)

        elif win_streak >= 1:
            if flat_lining:
                size_target = base_risk_pct + (pct_bump*win_streak)
            else:
                size_target = base_risk_pct * (win_streak+1)

        return size_target
    
    # def getCumulativeWinsSizeTarget(self, results_column)
    
    def getKellySizeTarget(self, win_pct, win_size, loss_size, kelly_fraction):
        """
        win_pct: expected winning percentage of system
        win_size: average units of every win for the system
        loss_size: average units of every loss for the system
        kelly_fraction: fraction of real kelly size, if desired
        """
        kelly_size = win_pct - ( (1-win_pct) / (win_size/loss_size))
        size_target = round( kelly_size * kelly_fraction, 4)
        return size_target