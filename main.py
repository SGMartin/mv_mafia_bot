import os.path
import requests

from bs4 import BeautifulSoup
import pandas as pd

import mafia_bot

def main():

    # Initialize global var.
    page_count = 1
    last_page_parsed = 1

    bot_config = {'game_thread': '',
                  'gm': '',
                  'mv_id': '',
                  'mv_password': ''}

    ## Attempt to load config file ##
    try:
        config = pd.read_csv('config.csv', sep=',', index_col=0)
        bot_config['game_thread'] = config.loc['game_thread', 'value']
        bot_config['gm']          = config.loc['GM', 'value']
        bot_config['mv_id']       = config.loc['mediavida_user', 'value']
        bot_config['mv_password'] = config.loc['mediavida_password', 'value']
        print('Configuration... LOADED')
    
    except:
        print('Failed to load config.csv')
        raise
    
    
    ## Get thread id ##
    name_and_thread_id = bot_config['game_thread'].split('/')[5]
    thread_id = int(name_and_thread_id.split('-')[-1]) #get last element


    ## Attempt to load previous run database ##
    database_path = 'mafia_' + str(thread_id) + '.csv'

    if os.path.exists(database_path):
        previous_run = pd.read_csv(filepath_or_buffer=database_path,
                                   sep=',',
                                   index_col=0)
        
        last_page_parsed = previous_run.loc['last_page', 'value']
    else:
        print('No data found for this game... starting from scratch')
        previous_run  = pd.DataFrame({'record': ['last_page'], 'value':[1]})
        previous_run.set_index('record', inplace=True)

    if last_page_parsed == 1:
        # Fresh run, initialize game
       Mafiabot = mafia_bot.MafiaBot(bot_config['game_thread'])

    else:  ## Recap. counting votes
        print('Testing vote count')
        Mafiabot = mafia_bot.MafiaBot(bot_config['game_thread'])
        Mafiabot.count_votes_from_page(93)



 
if __name__ == "__main__":
	main()