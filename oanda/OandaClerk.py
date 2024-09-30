import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.transactions as trans
import pandas as pd
import numpy as np
import math
import time
import ast
from os import path
import json

# TODO: this needs some major refactoring. Need to extract & rewrite data management functions like capturing opened/closed trades and trade history
class OandaClerk(object):
    """A class object that interfaces with the Oanda V20 API for clerical activities"""

    def __init__(self, accountID, access_token, environment, acc_denom):
        self.accountID = accountID
        self.access_token = access_token
        self.environment = environment
        self.client = oandapyV20.API(access_token=self.access_token, environment=self.environment)
        self.acc_denom = acc_denom

    def getOandaData(self, bar_count, granularity, instrument):
        """Pulls specified data from Oanda api"""
        params = {
                  "count": bar_count,
                  "granularity": granularity
        }
        r = instruments.InstrumentsCandles(instrument=instrument,
                                          params=params)
        response = self.client.request(r)
        return response

    def getTransactionIDRange(self, to_id,from_id):
        '''Retrieve a list of oanda account transactions from_id, to_id range'''
        params = {
            "to":to_id,
            "from":from_id
        }
        r = trans.TransactionIDRange(self.accountID, params=params)
        res = self.client.request(r)
        return res

    def getClosedTrades(self, history_fpath):
        '''Retrieve the latest closed trades from oanda and add them to a dataframe
        of the given history_fpath csv file. Used to update visualizations every week.
        Only works up until the last even 100 trade IDs have passed.'''
        # print(time.ctime(), ' OandaClerk.getClosedTrades entry...')
        def getTransactionIDRange(to_id,from_id):
            '''Retrieve a list of oanda account transactions from_id, to_id range'''
            params = {
                "to":to_id,
                "from":from_id
            }
            r = trans.TransactionIDRange(self.accountID, params=params)
            res = self.client.request(r)
            return res

        def preprocessTransactionResponse(res):
            df = pd.json_normalize(res['transactions'])
            if 'tradesClosed' in df.columns:
                df = df.fillna(0)
                df = df[(df['tradesClosed']) != 0]
                df = df[['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradesClosed',
                        'units', 'batchID', 'type', 'reason']]
                df['time'] = pd.to_datetime(df['time'], utc=True)
                df['accountBalance'] = pd.to_numeric(df['accountBalance'])
                df['halfSpreadCost'] = pd.to_numeric(df['halfSpreadCost'])
                df['units'] = pd.to_numeric(df['units'])
                df['batchID'] = pd.to_numeric(df['batchID'])
                df['tradesClosed'] = df['tradesClosed'].astype(str)
                df['pl'] = pd.to_numeric(df['pl'])
                df.drop_duplicates(keep='first',inplace=True)
                #df.index = df['time']
                tradesClosed_exists = True
            else:
                tradesClosed_exists = False
                print('WARNING preprocessTransactionResponse does not have tradesClosed column.')
            return df, tradesClosed_exists

        def getTransactions():
            r = trans.TransactionList(self.accountID)
            res = self.client.request(r)
            return res

        def roundup(x):
            '''Round up to the nearest 100th value'''
            return int(math.ceil(x / 100.0)) * 100

        def preprocessClosedTradesLoop(df, closes_only=False):
            pd.options.mode.chained_assignment = None
            if closes_only == True:
                df = df[['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradesClosed',
                         'units', 'batchID', 'type', 'reason']]
            df['time'] = pd.to_datetime(df['time'], utc=True)
            df['accountBalance'] = pd.to_numeric(df['accountBalance'])
            df['halfSpreadCost'] = pd.to_numeric(df['halfSpreadCost'])
            df['units'] = pd.to_numeric(df['units'])
            df['batchID'] = pd.to_numeric(df['batchID'])
            df['tradesClosed'] = df['tradesClosed'].astype(str)
            df['pl'] = pd.to_numeric(df['pl'])
            if closes_only == True:
                df.drop_duplicates(keep='first',inplace=True)
                #df.index = df['time']
            return df

        # read last saved dataframe
        odf = pd.read_csv(history_fpath)
        odf = preprocessClosedTradesLoop(odf, closes_only=True)
        if len(odf) == 0:
            #print('WARNING oanda.getClosedTrades() no trades found - empty dataframe.')
            lastbatch = 1
            lastTransID = 100
            to_val = 1
        else:
            # get the highest value from the saved dataframe, and last transaction ID
            lastbatch = odf['batchID'].max()
            lastTransID = int(getTransactions()['lastTransactionID'])
            # begin loop through the difference of the last
            to_val = roundup(lastbatch)
        # print('\nTo val:', to_val,
         #       '\nlastTransactionID (account): ', lastTransID,
         #       '\nLast csv batchID:', lastbatch, '\n')
        if to_val < lastTransID:
            #print('Initialize: from lastbatch: ',lastbatch,'-  to_val: ',to_val)
            res = getTransactionIDRange(to_val, lastbatch)
            mdf, tradesClosed_exists = preprocessTransactionResponse(res)
            if tradesClosed_exists:
                odf = odf.append(mdf, ignore_index=True)
                odf.drop_duplicates(keep='first', inplace=True)
            #print('\nTo val:', to_val,
            #        '\nlastTransactionID (account): ', lastTransID,
            #        '\nLast csv batchID:', lastbatch, '\n')
            while to_val <= lastTransID:
                to_val = to_val + 100
                from_val = to_val - 99
                # if to_val > lastTransID:
                #    to_val = lastTransID
                #print('LOOP from_val: ', from_val, '-  to_val: ', to_val)
                # pull dynamic range based on latest trades
                res = getTransactionIDRange(to_val, from_val)
                mdf, tradesClosed_exists = preprocessTransactionResponse(res)
                if tradesClosed_exists:
                    odf = odf.append(mdf, ignore_index=True)
                    #odf.drop_duplicates(keep='first', inplace=True)
                    odf = preprocessClosedTradesLoop(odf)
            # odf = testDropDuplicates(odf)
            odf.to_csv(history_fpath, index=False)
        elif to_val > lastTransID:
            res = getTransactionIDRange(to_val, lastbatch)
            mdf, tradesClosed_exists = preprocessTransactionResponse(res)
            if tradesClosed_exists:
                #print('tradesClosed_exists between to_val, lastbatch: ',to_val,lastbatch)
                #print('odf: ',odf)
                #print('odf.iloc[-1]',odf.iloc[[-1]])
                odf = odf.append(mdf, ignore_index=True)
                # print('len(odf) before drop: ',len(odf))
                odf['time'] = pd.to_datetime(odf['time'], utc=True)
                odf['accountBalance']=pd.to_numeric(odf['accountBalance'])
                odf['halfSpreadCost']=pd.to_numeric(odf['halfSpreadCost'])
                odf['units'] = pd.to_numeric(odf['units'])
                odf['batchID'] = pd.to_numeric(odf['batchID'])
                odf['pl']=pd.to_numeric(odf['pl'])
                # print('odf before drop dupes', odf)
                odf.drop_duplicates(keep='first', inplace=True)
                # odf = testDropDuplicates(odf)
                # print('odf after drop dupes', odf)
                # print('len(odf) after drop: ',len(odf))
            odf.to_csv(history_fpath, index=False)
            
        #print('odf len before drop: ',len(odf))
        odf.drop_duplicates(keep='first', inplace=True)
        # odf = testDropDuplicates(odf)
        #print('odf len before drop: ',len(odf))
        # print(time.ctime(), ' OandaClerk.getClosedTrades exit.')
        return odf

    def updateOpenedClosedFiles(self):
        '''Retrieves opened and closed data from oanda and adds them to
        opened-history.csv and closed-history.csv files. Used for retrieving
        timeintrade metrics for visualizations.'''
        print(time.ctime(), ' OandaClerk.updateOpenedClosedFiles entry...')

        def preprocessTransactionsDataframe(df,trade_state):
            pd.options.mode.chained_assignment = None
            df = df.fillna(0)

            if trade_state == 'opened':
                if 'tradeOpened.tradeID' in df.columns:
                    df = df[(df['tradeOpened.tradeID']) != 0]
                    df['tradeOpened'] = df['tradeOpened.tradeID']
                    df = df[['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradeOpened',
                                 'units', 'batchID', 'type', 'reason']]
                elif 'tradeOpened' in df.columns:
                    df = df[(df['tradeOpened']) != 0]
                    df = df[['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradeOpened',
                                 'units', 'batchID', 'type', 'reason']]
                    df['tradeOpened'] = df['tradeOpened'].astype(str)
                else:
                    print('preprocessTransactionsDataframe: tradeOpened.tradeID and tradeOpened not in response columns.')
                    df = pd.DataFrame()
                    return df
            elif trade_state == 'closed':
                if 'tradesClosed' in df.columns:
                    df = df[(df['tradesClosed']) != 0]
                    df = df[['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradesClosed',
                             'units', 'batchID', 'type', 'reason']]
                    df['tradesClosed'] = df['tradesClosed'].astype(str)
                else:
                    print('preprocessTransactionsDataframe: tradesClosed not in response columns.')
                    df = pd.DataFrame()
                    return df
            else:
                print('ERROR preprocessTransactionsDataframe(): Not a valid trade state.')
                df = pd.DataFrame()
                return df

            df['time'] = pd.to_datetime(df['time'], utc=True)
            df['accountBalance'] = pd.to_numeric(df['accountBalance'])
            df['halfSpreadCost'] = pd.to_numeric(df['halfSpreadCost'])
            df['pl'] = pd.to_numeric(df['pl'])
            df.drop_duplicates(keep='first',inplace=True)
            #df.index = df['time']
            return df

        def transformColumnID(opendf, trade_state):
            """Transforms column ID (tradeOpened or tradesClosed) to have int values and removes the dicts."""

            if trade_state == 'opened':
                print('Transforming tradeOpened column.')
                for row in range(0,len(opendf)):
                    if type(opendf.loc[row,'tradeOpened']) == int:
                        continue
                    elif type(ast.literal_eval(opendf.loc[row,'tradeOpened'])) == dict:
                        opendf.loc[row,'tradeOpened'] = int(ast.literal_eval(opendf.loc[row,'tradeOpened'])['tradeID'])

            elif trade_state == 'closed':
                print('Transforming tradesClosed column.')
                for row in range(0,len(opendf)):
                    if type(opendf.loc[row,'tradesClosed']) == int:
                        continue
                    elif type(ast.literal_eval(opendf.loc[row,'tradesClosed'])) == list:
                        opendf.loc[row,'tradesClosed'] = int(ast.literal_eval(opendf.loc[row,'tradesClosed'])[0]['tradeID'])
                    elif type(ast.literal_eval(opendf.loc[row,'tradesClosed'])) == dict: # unsure if dict exists here
                        opendf.loc[row,'tradesClosed'] = int(ast.literal_eval(opendf.loc[row,'tradesClosed'])['tradeID'])

            return opendf

        def initializeHistoryCsv(begTradeID, endTradeID, trade_state):
            """Retrieve either openedTrade or closedTrades data through iteration from the Oanda API and save it to a csv."""
            print('initializeHistoryCsv: Initializing ', trade_state, ' history.csv...')
            odf = pd.DataFrame()
            from_val = begTradeID
            to_val = begTradeID + 100

            while to_val < endTradeID:
                print('\tfrom_val: ', from_val, '-  to_val: ', to_val)
                transResponse = self.getTransactionIDRange(to_val, from_val)
                # last_transaction_id = transResponse['lastTransactionID']
                tid_df = pd.json_normalize(transResponse['transactions'])
                df = preprocessTransactionsDataframe(tid_df, trade_state=trade_state)
                if len(df) != 0:
                    odf = odf.append(df, ignore_index=True)
                    odf.drop_duplicates(keep='first', inplace=True)
                to_val = to_val + 100
                from_val = to_val - 99
            odf = transformColumnID(odf, trade_state)
            csv_name = trade_state + '-history.csv'
            odf.to_csv(csv_name, index=False)
            print('Saved ', csv_name, ' with length: ', len(odf), '\n')
            return odf

        def updateHistoryCsv(trade_state):
            """Read in closed or opened history csv, retrieve new data from oanda to append, and save it."""
            csv_name = trade_state + '-history.csv'
            if path.exists(csv_name):
                print('updateHistoryCsv: Updating ', csv_name, '...')
                odf = pd.read_csv(csv_name)
                from_val = odf['batchID'][-1:]
                if len(from_val) == 0:
                    from_val = 1
                else:
                    from_val = from_val.values[0]
            else:
                print('updateHistoryCsv: Initializing new file ', csv_name)
                odf = pd.DataFrame(columns=['accountBalance', 'halfSpreadCost', 'instrument', 'pl', 'time', 'tradesClosed',
                            'units', 'batchID', 'type', 'reason'])
                odf.to_csv(csv_name, index=False) # write it out and read it back in to continue the update
                odf = pd.read_csv(csv_name)
                from_val = 1

            transResponse = self.getTransactionIDRange(50,20) # arbitrary id selection - only retrieving last ID
            last_transaction_id = transResponse['lastTransactionID']
            to_val = int(last_transaction_id)
            numEntries = to_val - from_val

            if numEntries > 100:
                print('More than 100 new data points...')
                print('\tfrom_val : ', from_val, '-  to_val : ', to_val)
                odf = initializeHistoryCsv(from_val, to_val, trade_state)
            else:
                print('\tfrom_val loop: ', from_val, '-  to_val loop: ', to_val)
                transResponse = self.getTransactionIDRange(to_val,from_val)
                # lastTransID = transResponse['lastTransactionID']
                tid_df = pd.json_normalize(transResponse['transactions'])
                df = preprocessTransactionsDataframe(tid_df,trade_state=trade_state)
                if len(df) != 0:
                    odf = odf.append(df, ignore_index=True)
                    odf = transformColumnID(odf,trade_state)
                    odf.drop_duplicates(keep='first',inplace=True)
                odf.to_csv(csv_name,index=False)
                print('Saved ', csv_name, ' with length: ', len(odf), '\n')
            return odf

        def prepTradesClosed(adf): # not currently used
            """Input raw dataframe collected from multiple oanda requests and return a dataframe with matching tradeClose columns."""
            for idx in adf.index:
                tradesClosedRow = adf['tradesClosed'][idx]
                d = tradesClosedRow.replace("'", '"') # json transform wants double quotes
                jd = json.loads(d) # creates a list

                if type(jd) == list:
                    adf.loc[idx,'tradeClose.tradeID'] = jd[0]['tradeID']
                    adf.loc[idx,'tradeClose.units'] = jd[0]['units']
            return adf

        def getTimeInTrade(closed, opened):
            """input dataframe of updated dataframes with closed trades and opened trades"""
            closed['time'] = pd.to_datetime(closed['time'], utc=True)
            opened['time'] = pd.to_datetime(opened['time'], utc=True)
            if 'timeintrade' not in closed.columns:
                print('getTimeInTrade: init timeintrade column.')
                closed['timeintrade'] = 0
            for row in closed[closed['tradesClosed'] != 0].index:
                tradeID = closed.loc[row,'tradesClosed']
                close_time = closed.loc[row,'time']
                open_data = opened[opened['tradeOpened'] == tradeID]
                if len(open_data) != 0:
                    open_time = open_data['time'].values[0]
                    timeintrade = close_time - open_time
                    closed.loc[row,'timeintrade'] = timeintrade
                else:
                    print('getTimeInTrade: no matching tradeID in opened data for tradeID', tradeID)
            return closed

        opened = updateHistoryCsv(trade_state='opened')
        closed = updateHistoryCsv(trade_state='closed')
        closed = getTimeInTrade(closed, opened)
        closed.to_csv('closed-history.csv', index=False)
        print(time.ctime(), ' OandaClerk.updateOpenedClosedFiles exit.')
        return closed

    def getOandaDataByDate(self, start_date, end_date, granularity, instrument):
        """pulls specified data from Oanda api using date parameters instead of bar_count"""
        params = {
                "granularity": granularity,
                "from": start_date,
                "to": end_date
        }
        r = instruments.InstrumentsCandles(instrument=instrument,
                                            params=params)
        response = self.client.request(r)
        return response

    def formatOandaData(self, res, format_type, complete):
        df = pd.json_normalize(res['candles'])
        if complete:
            df = df[df['complete'] == True]
        if format_type == 'BuildAlpha':
            todatetime = pd.to_datetime(df['time'], utc=True)
            df['Date'] = todatetime.map(lambda x: x.strftime('%m/%d/%Y'))
            df['Time'] = todatetime.map(lambda x: x.strftime('%H:%M:%S'))
            df['Open'] = df['mid.o'].astype(float)
            df['High'] = df['mid.h'].astype(float)
            df['Low'] = df['mid.l'].astype(float)
            df['Close'] = df['mid.c'].astype(float)
            df['Vol'] = df['volume'].astype(int)
            df['OI'] = np.nan
            df = df[['Date','Time','Open','High','Low','Close','Vol','OI']]
        else:
            df['Date'] = pd.to_datetime(df['time'],utc=True)
            df['Open'] = df['mid.o'].astype(float)
            df['High'] = df['mid.h'].astype(float)
            df['Low'] = df['mid.l'].astype(float)
            df['Close'] = df['mid.c'].astype(float)
            df['Vol'] = df['volume'].astype(int)
            df = df[['Date','Open','High','Low','Close','Vol']]
        return df