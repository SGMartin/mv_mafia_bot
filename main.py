import logging

import os.path
import pandas as pd

import mafia_bot
import user

def main():

    ### SETUP UP PROGRAM LEVEL LOGGER ###

    # create logger
    logger = logging.getLogger("mafia_bot")
    logger.setLevel(logging.DEBUG)

    #TODO: make this configurable
    logging.basicConfig(filename='mafia.log',
                        level=logging.DEBUG,
                        format='%(asctime)s %(message)s')

    # Silence requests logger #
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Load confic  dict.
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
        bot_config['update_time_seconds'] = config.loc['update_time_seconds', 'value']
        bot_config['post_push_interval']  = config.loc['push_vote_count_interval', 'value']

        print('Configuration... LOADED')
        logging.info('Configuration loaded')
    
    except:
        logging.critical('Failed to load config.csv')
        raise
    


    MafiaBot = mafia_bot.MafiaBot(game_url=bot_config['game_thread'],
                                  game_master=bot_config['gm'],
                                  bot_userID=bot_config['mv_id'],
                                  bot_password=bot_config['mv_password'],
                                  loop_waittime_seconds=int(bot_config['update_time_seconds']),
                                  post_push_interval = int(bot_config['post_push_interval'])
                                 )
    


 
if __name__ == "__main__":
	main()