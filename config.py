import logging
import os.path
import sys

import pandas as pd


class Config:

    def __init__(self, file_to_load):
        '''
        This module loads and parses the general config file. Parsing errors
        are logged and config parameters exposed through public vars.
        '''
        self.game_thread        = ''
        self.game_master        = ''
        self.moderators         = []
        self.mediavida_user     = ''
        self.mediavida_pwd      = ''
        self.update_time        = 60
        self.posts_until_update = 30
        self.votes_until_update = 10

        self._config_file = file_to_load
        self._raw_config  = self._load_file(self._config_file)

        self._parse_config(self._raw_config)

        print('Configuration loaded')
        logging.info('Configuration loaded')


    def reload_config(self):
        '''
        Reload the config.
        '''
        self._new_raw_config = self._load_file(self._config_file)
        self._parse_config(self._new_raw_config)


    def _load_file(self, file_to_load:str) -> pd.DataFrame:
        '''
        Loads a config file.
        '''
        if os.path.isfile(file_to_load):
            try:
                self._config = pd.read_csv(file_to_load, sep=',', index_col=0)
                return self._config
            except:
                logging.critical('Could not load config file. Check the format.')
                sys.exit('Could not load config file.')
        else:
            logging.critical('Cannot find config file.')
            sys.exit('Could not find config file.')

    
    def _parse_config(self, raw_config: pd.DataFrame) -> dict:
        '''
        Parses the loaded config. If any field is missing or wrong type values
        are present, it will exit the bot, logging an exception.
        '''
        try:
            self.game_thread    = raw_config.loc['game_thread', 'value'] 
            self.game_master    = raw_config.loc['game_master', 'value']
        
            self.mediavida_user = raw_config.loc['mediavida_user', 'value']
            self.mediavida_pwd  = raw_config.loc['mediavida_password', 'value']

            self.update_time    = raw_config.loc['update_time_seconds', 'value']
            self.posts_until_update = raw_config.loc['push_vote_count_interval', 'value']
            self.votes_until_update = raw.config.loc['votes_until_update', 'value']

            if self.update_time < 10:
                self.update_time == 10
            
            if self.posts_until_update <= 0:
                self.posts_until_update = -1

            
            ## Attempt to populate moderator lists
            if pd.notna(raw_config.loc['Moderators', 'value']):

                self.moderators = raw_config.loc['Moderators', 'value']
                self.moderators = self.moderators.split(',')

                ## clean up of trailing and ending whitespaces
                self.moderators = [mod.split(' ') for mod in self.moderators]

                ## just for testing:
                print('Remove me: There are', len(self.moderators), 'coGM')
    
        except Exception:
                logging.exception('Cannot parse config file!')
                sys.exit('Config could not be parsed')



