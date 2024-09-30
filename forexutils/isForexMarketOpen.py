import datetime

def isForexMarketOpen():
    # 5 is isoweekday Friday
    # 6 is isoweekday Saturday
    # 7 is isoweekday Sunday
    d = datetime.now()
    # check not Saturday -
    if d.isoweekday() != 6: 
        
        # Friday split at 13 - 1:00 PM local time
        if d.isoweekday()==5 and d.hour<13:
            return True
        elif d.isoweekday()==5 and d.hour>=13:
            return False
        
        # Sunday split at 14 - 2:00 PM local time
        elif d.isoweekday()==7 and d.hour>=14:
            return True
        elif d.isoweekday()==7 and d.hour<14:
            return False
        
        # catch all other days of the week
        else:
            return True
    else:
        return False