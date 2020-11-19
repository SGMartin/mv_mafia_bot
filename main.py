import logging

import os.path
import pandas as pd

import config
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

    Config = config.Config(file_to_load='config.csv')

    MafiaBot = mafia_bot.MafiaBot(game_url=Config.game_thread,
                                  game_master=Config.game_master,
                                  bot_userID=Config.mediavida_user,
                                  bot_password=Config.mediavida_pwd,
                                  loop_waittime_seconds=Config.update_time,
                                  post_push_interval = Config.posts_until_update,
                                  moderators = Config.moderators)
                                 )
    

if __name__ == "__main__":
	main()