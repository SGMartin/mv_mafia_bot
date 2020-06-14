import os.path
import requests

from bs4 import BeautifulSoup
import pandas as pd

import mafia_bot
import game_day

def main():


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
    
    
   # bot = mafia_bot.MafiaBot(bot_config['game_thread'], bot_config['gm'])
   # bot.count_votes_from_page(93)

    ## test
    response = requests.get('https://www.mediavida.com/foro/juegos-mesa-rol/mafia-mv-fortaleza-frontera-654693?u=DarkRaptor&pagina=9')
    test_day = game_day.GameDay(4338, response)
if __name__ == "__main__":
	main()