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
        self.thread_id          = 0
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
        """Reload the config by both reading and parsing the config file."""
        self._new_raw_config = self._load_file(self._config_file)
        self._parse_config(self._new_raw_config)


    def _load_file(self, file_to_load:str) -> pd.DataFrame:
        """Attempt to load a config from a comma separated file.

        Args:
            file_to_load (str): The file to load.

        Returns:
            pd.DataFrame: The resulting config as a dataframe.
        """
        if os.path.isfile(file_to_load):
            try:
                self._config = pd.read_csv(file_to_load, sep=',', index_col=0)
                return self._config
            except:
                logging.critical('Could not load config file. Check the format.')
                sys.exit('ERROR: Could not load config file.')
        else:
            logging.critical('Cannot find config file.')
            sys.exit('ERROR: Could not find config file.')

    
    def _parse_config(self, raw_config: pd.DataFrame):
        """Attempt to fill all the fields of the class with the values provided
        Args:
            raw_config (pd.DataFrame): A dataframe of key-value pairs containing
            which will be used to fill the fields.
        """
        try:
            self.game_thread    = raw_config.loc['game_thread', 'value']
            self.thread_id      = int(self.game_thread.split('-')[-1])

            self.game_master    = raw_config.loc['GM', 'value']
        
            self.mediavida_user = raw_config.loc['mediavida_user', 'value']
            self.mediavida_pwd  = raw_config.loc['mediavida_password', 'value']

            self.update_time    = int(raw_config.loc['update_time_seconds', 'value'])
            self.posts_until_update = int(raw_config.loc['push_vote_count_interval', 'value'])
            self.votes_until_update = int(raw_config.loc['votes_until_update', 'value'])

            if self.update_time < 10:
                self.update_time = 10
            
            if self.posts_until_update <= 0:
                self.posts_until_update = -1

            
            ## Attempt to populate moderator lists
            if pd.notna(raw_config.loc['Moderators', 'value']):

                self.moderators = raw_config.loc['Moderators', 'value']
                self.moderators = self.moderators.split(';')

                ## clean up of trailing and ending whitespaces
                self.moderators = [mod.strip(' ') for mod in self.moderators]
    
        except Exception:
                logging.exception('Cannot parse config file!')
                sys.exit('ERROR: Config could not be parsed')



