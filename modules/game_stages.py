import datetime
import pytz

import ntplib

from states.stage import Stage

class GameStage():
    def __init__(self, post_id:int, game_stage:Stage, stage_start_time:int):

        self.game_stage = game_stage
        self.stage_start_time = stage_start_time
        self.stage_start_post = post_id

        self._stage_duration = 48
    
    
    def set_stage_duration(self, stage_hours:int):
        """Change the duration of the stage in hours. Defaults to 48.

        Args:
            stage_hours (int): How many hours the stage should take
        """

        if stage_hours > 0:
            self._stage_duration = stage_hours
        else:
            raise ValueError(f"Invalid stage duration. Negative numbers are not allowed")

    def get_start_time(self, time_format:str="utc"):
        """Get when this stage started in different time formats

        Args:
            time_format (str, optional): The start time of the stage can be reported in UTC or mediavida (Madrid) timezone
            . Defaults to "utc".

        Raises:
            ValueError: Only UTC/mediavida are currently supported.
        Returns:
            _type_: Datetime object
        """
        self._valid_formats = ["utc", "mediavida"]

        if time_format not in self._valid_formats:
            raise ValueError(f"Invalid time format. Expected one of {self._valid_formats}, got {time_format}")
        
        self._utc_zone = pytz.timezone("UTC")
        self._madrid_zone = pytz.timezone("Europe/Madrid")

        self._utc_time = datetime.datetime.utcfromtimestamp(self.stage_start_time)
        self._utc_time = self._utc_zone.localize(self._utc_time)
            
        if time_format == "utc":
            return self._utc_time
        else:
            return self._utc_time.astimezone(self._madrid_zone)
    

    def get_end_of_stage(self) -> int:
        """Returns the end of this GameStage object based on configuration

        Returns:
            int: Unix epoch time
        """
        self._start_time = self.get_start_time(time_format="mediavida")        
        self._end_time = self._start_time + datetime.timedelta(hours=self._stage_duration)
        self._end_time = self._end_time.replace(hour=21, minute=10, second=0, microsecond=0).timestamp()
        return self._end_time
    

    def is_end_of_stage(self, current_time:int) -> int:
        self._this_stage_end = self.get_end_of_stage()

        if current_time > self._this_stage_end:
            return True
        else:
            return False