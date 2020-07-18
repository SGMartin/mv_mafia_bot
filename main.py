import os.path
import pandas as pd

import mafia_bot
import user

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
    
    bot = mafia_bot.MafiaBot(bot_config['game_thread'], bot_config['gm'],
                             bot_config['mv_id'], bot_config['mv_password'],  60)

 
if __name__ == "__main__":
	main()