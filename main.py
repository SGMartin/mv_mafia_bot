from datetime import date
import logging
import math
import os.path
import time
import sys

import pandas as pd

import config
import user
import vote_count
import modules.thread_reader as tr
import states.stage as stages
import states.action as actions

def main():

    ## SETUP GLOBAL VARIABLES ##
    global majority_reached
    global player_list
    global settings
    global staff

    ### SETUP UP PROGRAM LEVEL LOGGER ###
    logger = logging.getLogger("mafia_bot")
    logger.setLevel(logging.DEBUG)

    #TODO: make this configurable
    logging.basicConfig(filename='mafia.log',
                        level=logging.DEBUG,
                        format='%(asctime)s %(message)s')

    # Silence requests logger #
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    settings           = config.Config(file_to_load='config.csv')
    majority_reached   =  False
    
    ## DEFINE STAFF MEMBERS ##
    staff = list(map(str.lower, settings.moderators))
    staff.append(settings.game_master.lower())

    run(settings.update_time)


def run(update_tick: int):
    '''
    Main bot loop. It iterates each N seconds, as defined by the config file. 
    For each iteration, it parses the game thread if we are on day phase, 
    then collects and resolves all the game actions and decide 
    if a new vote count should be pushed.

    Parameters: 
    update_tick (int): Seconds to pass between bot iterations.

    Returns: None
    '''
    bot_cyles = 0
    while(True):

        global player_list

        update_tick     = settings.update_time

        game_status     = tr.get_game_phase(game_thread=settings.game_thread,
                                            game_master=settings.game_master)
       
        if game_status[0] == stages.Stage.Day:

            current_day_start_post = game_status[1]
            VoteCount              = vote_count.VoteCount(staff=staff,
                                                          day_start_post=current_day_start_post,
                                                          bot_cyle=bot_cyles)

            print('We are on day time!')

            player_list    = tr.get_player_list(game_thread=settings.game_thread,
                                                start_day_post_id=current_day_start_post)

            last_votecount = tr.get_last_votecount(game_thread=settings.game_thread,
                                                   bot_id=settings.mediavida_user)

            last_votecount_id = last_votecount[0]
            majority_reached  = last_votecount[1]
            
            if not majority_reached:

                last_thread_post  = tr.get_last_post(game_thread=settings.game_thread)

                logging.info(f'Starting vote count. Last vote count: {last_votecount_id}. Last reply: {last_thread_post}')

                start_page = tr.get_page_number_from_post(current_day_start_post)
                page_count = tr.request_page_count(game_thread=settings.game_thread)

                logging.info(f'Detected day start at page: {start_page}')
                logging.info(f'Detected {page_count} pages')

                for cur_page in range(start_page, (page_count + 1)):

                    logging.info(f'Checking page: {cur_page}')

                    action_queue = tr.get_actions_from_page(game_thread = settings.game_thread,
                                                            page_to_scan = cur_page,
                                                            start_from_post = current_day_start_post)

                    logging.info(f'Retrieved {len(action_queue)} actions for page {cur_page}')

                    resolve_action_queue(queue=action_queue, vcount=VoteCount, last_count=last_votecount_id)

                ## get votes casted since last update
                votes_since_update = len(VoteCount._vote_table[VoteCount._vote_table['post_id'] > last_votecount_id].index)

                should_update =  update_thread_vote_count(last_count=last_votecount_id,
                                                          last_post=last_thread_post,
                                                          votes_since_update=votes_since_update)     
                
                if should_update:
                    logging.info('Pushing a new votecount')
                    push_vote_count(vote_table=VoteCount._vote_table,
                                    last_parsed_post=last_thread_post)
                else:
                    logging.info('Recent votecount detected. ')
                
            else:
                logging.info('Majority already reached. Skipping...')   

            # Save the vote history for the next iteration
            VoteCount.save_vote_history()

        elif game_status[0]  == stages.Stage.Night:

            logging.info('Night phase detected. Skipping...')
            print('We are on night phase!')

        #TODO: Exit routine here
        elif game_status[0] == stages.Stage.End:
            
            print('Game ended!')
            logging.info(f'Game ended. Exiting now')
            time.sleep(5)
            sys.exit()

        logging.info(f'Sleeping for {update_tick} seconds.')  

        print(f'Sleeping for {update_tick} seconds.')

        bot_cyles += 1
        time.sleep(update_tick)


#TODO: Handle actual permissions without a giant if/else
#TODO: This func. is prime candidate for refactoring
def resolve_action_queue(queue: list, vcount: vote_count.VoteCount, last_count:int):
    '''
    Parameters:  \n
    queue: A list of game actions.\n
    vcount: The current Vote Count.\n
    '''
    User = user.User(config=settings)

    allowed_actors      = player_list + staff

    for game_action in queue:

        if game_action.author in allowed_actors:

            if game_action.type == actions.Action.vote:

                vcount.vote_player(action=game_action)

                if is_lynched(victim=game_action.victim, vcount=vcount):

                    global majority_reached
                    majority_reached = True

                    User.push_lynch(last_votecount=vcount._vote_table,
                                    victim=game_action.victim,
                                    post_id=game_action.id)

            elif game_action.type == actions.Action.unvote:
                vcount.unvote_player(action=game_action)
            
            elif game_action.type == actions.Action.replace_player and game_action.author in staff:

                if game_action.actor in player_list:

                    vcount.replace_player(replaced=game_action.actor, replaced_by=game_action.victim)
                    allowed_actors.remove(game_action.actor)

                    if game_action.victim not in player_list:
                        allowed_actors.append(game_action.victim)
                        player_list.append(game_action.victim)
 
                    logging.info(f'{game_action.actor} replaced by {game_action.victim} at {game_action.id}.')
                else:
                    logging.info(f'Skipping replacement for player {game_action.actor} by {game_action.victim} at {game_action.id}')


            elif game_action.type == actions.Action.modkill:
                if game_action.author in staff:
                    if game_action.victim in player_list:
                        player_list.remove(game_action.victim)
                        vcount.remove_player(game_action.victim)


            #TODO: refactor candidate
            elif game_action.type == actions.Action.vote_history:

                ## Get the proper name from the lowercased name.
                ## If it does not exist, it may be an alias like cuervo, so pass
                ## it anyway
                real_names      = vcount.get_real_names()

                #key,default
                game_action.victim = real_names.get(game_action.victim, game_action.victim)

                ## get the last time we pushed the vhistory for this player
                last_vhistory_for_victim = tr.get_last_vhistory_from(game_thread=settings.game_thread,
                                                                     bot_id=settings.mediavida_user,
                                                                     player=game_action.victim)
                if game_action.id > last_vhistory_for_victim:
                    User.add_vhistory_to_queue(action=game_action,
                                               vhistory=vcount._vote_history)
            
            #TODO: refactor candidate
            elif game_action.type == actions.Action.get_voters:

                real_names = vcount.get_real_names()

                #key,default
                game_action.victim = real_names.get(game_action.victim, game_action.victim)

                last_voters_history = tr.get_last_voters_from(game_thread=settings.game_thread,
                                                              bot_id=settings.mediavida_user,
                                                              player=game_action.victim)

                if game_action.id > last_voters_history:
                    User.add_voters_history_to_queue(action=game_action,
                                                     vhistory=vcount._vote_history)
            
            
            elif game_action.type == actions.Action.request_count: 

                if game_action.author in staff:

                    if game_action.id > last_count:
                        if game_action.target_post != 0:
                            table_to_push = vcount._vote_table[vcount._vote_table['post_id'] <= game_action.target_post]
                            parsed_post   = game_action.target_post

                        else:
                            table_to_push = vcount._vote_table
                            parsed_post   = game_action.id

                        push_vote_count(vote_table=table_to_push,
                                        last_parsed_post=parsed_post)
          
    ## Finally, push the queue If needed
    User.push_queue()
                
def update_thread_vote_count(last_count:int, last_post:int, votes_since_update:int) -> bool:
    '''
    Decides if a new vote count should be posted based on:
        
    a) Pending GM requests.\n
    b) How many messages were posted since the last vote count. This is used-defined.

    Parameters: None

    Returns:
    True/False (bool): Whether to push a new vote count.
    '''

    post_update = False
    vote_update = False

    if last_post - last_count >= settings.posts_until_update:
        post_update = True
    elif votes_since_update >= settings.votes_until_update:
        vote_update = True

    return (vote_update | post_update)


def get_vote_majority() -> int:
    '''
    Calculates the amount of votes necessary to reach an absolute majority
    and lynch a player based on the amount of alive players. 

    Parameters:  \n
    Returns: \n
    majority (int): The absolute majority of votes required  to lynch a player.
    '''

    if (len(player_list) % 2) == 0:
        majority = math.ceil(len(player_list) / 2) + 1
    else:
        majority = math.ceil(len(player_list) / 2)
                
    return majority


def is_lynched(victim:str, vcount: vote_count.VoteCount) -> bool:
    '''
    Checks if a given player has received enough votes to be lynched. This
    function evaluates if a given player accumulates enough votes by calculating
    the current absolute majority required and adding to it a player specific
    lynch modifier as defined in the vote rights table.

    Parameters:\n 
    victim (str): The player who receives the vote.\n
    Returns:\n 
    True if the player should be lynched.  False otherwise.
    '''
    lynched = False

    # Count this player votes
    lynch_votes     = vcount.get_victim_current_votes(victim)
    player_majority = get_vote_majority() + vcount.get_player_mod_to_lynch(victim)
        
    if lynch_votes >= player_majority:
        lynched = True
        
    return lynched

    
def push_vote_count(vote_table: pd.DataFrame, last_parsed_post: int):
    '''
    When this function is called, a new User object is built to push a vote
    count using the current vote table. The object is deleted when the function
    ends.

    Parameters: \n
    vote_table: A dataframe with the vote table to parse for the post.\n
    last_parsed_post: Last post parsed by the bot.\n
    Returns: None
    '''

    User = user.User(config=settings)
                    
    User.push_votecount(vote_count=vote_table,
                        alive_players=len(player_list),
                        vote_majority=get_vote_majority(),
                        post_id=last_parsed_post)

    del User



if __name__ == "__main__":
	main()