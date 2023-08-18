import datetime
import logging
import os.path
import time
import sys

import pandas as pd
import ntplib

import config
import user
import vote_count
import player_list as pl
import modules.thread_reader as tr
import states.stage as stages
import states.action as actions

def main():

    ## SETUP GLOBAL VARIABLES ##
    global majority_reached
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
    """Main bot loop. It iterates each N seconds, as defined by the config file. 
    For each iteration, it parses the game thread if we are on day phase, 
    then collects and resolves all the game actions and decide 
    if a new vote count should be pushed.

    Args:
        update_tick (int): Seconds to pass between bot iterations.
    """

    ## Attempt to recover the last bot cycle just in case of an unexpected
    ## crash. Needed for the vhistory to work correctly.
    bot_cycles = get_last_bot_cycle()

    ## check if this is the first bot activation. Don't trust cycles
    if bot_cycles == 0:
        announce_bot_activation()

    while(True):


        update_tick     = settings.update_time

        game_status     = tr.get_game_phase(game_thread=settings.game_thread, game_master=settings.game_master)

        if game_status.game_stage == stages.Stage.Day:

            current_day_start_post = game_status.stage_start_post

            ## Set the duration of the day phase
            game_status.set_stage_duration(stage_hours = settings.day_duration)
            ## Set the stage start time
            game_status.set_stage_start_hour(stage_start=settings.stage_start_time)
            
            player_list    = tr.get_player_list(game_thread=settings.game_thread,
                                        start_day_post_id=current_day_start_post
                                        )

            Players = pl.Players(player_list, bot_cycles)

            VoteCount              = vote_count.VoteCount(staff=staff,
                                                          day_start_post=current_day_start_post,
                                                          bot_cycle=bot_cycles,
                                                          n_players=len(Players.players)
                                                          )

            print('We are on day time!')

            last_votecount = tr.get_last_votecount(game_thread=settings.game_thread,
                                                   bot_id=settings.mediavida_user)

            last_votecount_id = last_votecount[0]
            majority_reached  = last_votecount[1]

            if last_votecount_id < current_day_start_post and majority_reached:
                majority_reached = False            

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

                    resolve_action_queue(queue=action_queue,
                    vcount=VoteCount,
                    Players=Players,
                    last_count=last_votecount_id,
                    day_start = current_day_start_post,
                    eod_time=game_status.get_end_of_stage()
                    )

                ## Check If there is still time left to play. Otherwise, start the EoD
                if game_status.is_end_of_stage(current_time = get_current_ntp_time()) and not majority_reached:
                    
                    last_valid_action = [action for action in action_queue if action.post_time < game_status.get_end_of_stage()].pop()
                    majority_reached = True ## This will stop the bot in the next iteration
                    logging.info("EoD detected. Pushing last valid votecount and preparing flip routine")

                    end_of_day_victim = VoteCount.get_current_lynch_candidate()
                    lynch_is_revealed = settings.reveal_eod_lynch

                    if end_of_day_victim is None or end_of_day_victim == "no_lynch" or not lynch_is_revealed:
                        role_to_reveal = None
                    else:
                        role_to_reveal = f"{Players.get_player_role(end_of_day_victim)} - {Players.get_player_team(end_of_day_victim)}"

                    User = user.User(config=settings)
                    User.push_lynch(
                        last_votecount=VoteCount._vote_table,
                        victim=end_of_day_victim,
                        post_id=last_valid_action.id,
                        reveal=role_to_reveal,
                        is_eod=True
                        )

                    majority_reached = True

                ## get votes casted since last update
                votes_since_update = len(VoteCount._vote_table[VoteCount._vote_table['post_id'] > last_votecount_id].index)

                should_update =  update_thread_vote_count(last_count=last_votecount_id,
                                                          last_post=last_thread_post,
                                                          votes_since_update=votes_since_update
                                                          )     
                
                if should_update:
                    logging.info('Pushing a new votecount')
                    push_vote_count(vote_table=VoteCount._vote_table,
                                    alive_players=Players.players,
                                    last_parsed_post=last_thread_post,
                                    current_majority=VoteCount.current_majority
                                    )
                else:
                    logging.info('Recent votecount detected. ')
                
            else:
                logging.info('Majority already reached. Skipping...')   

            # Save the vote history for the next iteration
            VoteCount.save_vote_history()

        elif game_status.game_stage  == stages.Stage.Night:
            game_status.set_stage_duration(stage_hours = settings.night_duration)
            logging.info('Night phase detected. Skipping...')
            print('We are on night phase!')

        #TODO: Exit routine here
        elif game_status.game_stage == stages.Stage.End:
            
            print('Game ended!')
            logging.info(f'Game ended. Exiting now')
            time.sleep(5)
            sys.exit()

        logging.info(f'Sleeping for {update_tick} seconds.')  

        print(f'Sleeping for {update_tick} seconds.')

        bot_cycles += 1
        time.sleep(update_tick)


#TODO: Handle actual permissions without a giant if/else
#TODO: This func. is prime candidate for refactoring
def resolve_action_queue(queue: list, vcount: vote_count.VoteCount, Players: pl.Players, last_count:int, day_start:int, eod_time:int):
    '''
    Parameters:  \n
    queue: A list of game actions.\n
    vcount: The current Vote Count.\n
    '''

    User    = user.User(config=settings)
    allowed_actors = Players.players + staff

    for game_action in queue:

        ## Ignore actions out of EoD except those coming from the staff
        if game_action.post_time >= eod_time and game_action.author not in staff:
            continue

        if game_action.author in allowed_actors:

            if game_action.type == actions.Action.vote and (Players.player_exists(game_action.victim) or game_action.victim == "no_lynch"):

                vcount.vote_player(action=game_action)

                if vcount.is_lynched(victim=game_action.victim):

                    global majority_reached
                    majority_reached = True

                    User.push_lynch(last_votecount=vcount._vote_table,
                                    victim=game_action.victim,
                                    post_id=game_action.id,
                                    reveal=f"{Players.get_player_role(game_action.victim)} - {Players.get_player_team(game_action.victim)}"
                    )
                    break

            elif game_action.type == actions.Action.unvote:
                vcount.unvote_player(action=game_action)
            
            elif game_action.type == actions.Action.lylo:

                logging.info(f'{game_action.author} requested an vcount lock at  {game_action.id}')

                if game_action.author in staff:
                    vcount.lock_unvotes()

            elif game_action.type == actions.Action.replace_player and game_action.author in staff:

                Players.replace_player(player_out = game_action.actor,player_in = game_action.victim)
                vcount.replace_player(replaced=game_action.actor, replaced_by=game_action.victim)
                allowed_actors.remove(game_action.actor)

                if game_action.victim not in allowed_actors:
                    allowed_actors.append(game_action.victim)
 
            elif game_action.type == actions.Action.modkill or game_action.type == actions.Action.kill or game_action.type == actions.Action.winner:
                if game_action.author in staff:
                    Players.remove_player(game_action.victim)
                    vcount.remove_player(game_action.victim)
                   
            elif game_action.type == actions.Action.vote_history or game_action.type == actions.Action.get_voters:

                real_names = vcount.get_real_names()

                # get key, default
                game_action.victim = real_names.get(game_action.victim, game_action.victim)

                if game_action.type == actions.Action.vote_history:

                    victim_is_voter = True
                    last_request    = tr.get_last_vhistory_from(game_thread=settings.game_thread,
                                                                bot_id=settings.mediavida_user,
                                                                player=game_action.victim)
                else:
                    victim_is_voter = False
                    last_request    = tr.get_last_voters_from(game_thread=settings.game_thread,
                                                              bot_id=settings.mediavida_user,
                                                              player=game_action.victim)
                
                if game_action.id > last_request:
                    User.add_vhistory_to_queue(action=game_action,
                                               vhistory=vcount._vote_history,
                                               victim_is_voter=victim_is_voter)
            
            elif game_action.type == actions.Action.request_count: 

                if game_action.author in staff:

                    if game_action.id > last_count:
                        if game_action.target_post != 0:
                            parsed_post   = game_action.target_post
                            table_to_push = vcount._vote_history.loc[vcount._vote_history["post_id"] >= day_start]
                            table_to_push = table_to_push.loc[(table_to_push["post_id"] <= parsed_post) & ((table_to_push["unvoted_at"] == 0) | (table_to_push["unvoted_at"] > parsed_post))]
                        else:
                            table_to_push = vcount._vote_table
                            parsed_post   = game_action.id

                        push_vote_count(vote_table=table_to_push,
                                        alive_players=Players.players,
                                        last_parsed_post=parsed_post,
                                        current_majority=vcount.current_majority
                                        )


            elif game_action.type == actions.Action.freeze_vote:
                ## TODO: Move this logic to the vcount?
                if game_action.author in staff:
                    if game_action.victim == 'none': ## general freeze

                        for player in vcount._vote_table['voted_by'].unique():
                            vcount.freeze_player_votes(player)
                    else:
                        vcount.freeze_player_votes(game_action.victim)
            
            elif game_action.type == actions.Action.reveal:
                if game_action.author == vcount.mayor: ## mayor?
                    if vcount.vote_rights.loc[game_action.author, "allowed_votes"] < 3: ## nope, not revealed
                        vcount.update_vote_limits(player=game_action.author, new_limit=3)
                        announce_mayor(new_mayor=vcount.get_real_names()[game_action.author])


            elif game_action.type == actions.Action.revive and game_action.author in staff:
                if vcount.player_exists(game_action.victim.lower()): ## make sure this guy actually played and has rights
                    Players.revive_player(game_action.victim)
                else:
                    logging.warning(f"Attempting to revive invalid player {game_action.victim}")

            elif game_action.type == actions.Action.shoot:
                if Players.player_exists(game_action.victim) and game_action.victim not in staff:
                    was_valid_shot, is_dead_victim = Players.shoot_player(game_action)
                    if was_valid_shot:
                        if is_dead_victim:
                            vcount.remove_player(game_action.victim)
                        

                        attacker_real_name = vcount.get_real_names()[game_action.author]
                        victim_real_name = vcount.get_real_names()[game_action.victim]

                        ## check if the bot already announced this
                        last_shot_fired = tr.get_last_shot_by(
                            game_thread=settings.game_thread,
                            bot_id=settings.mediavida_user,
                            player=attacker_real_name
                            )

                        if game_action.id > last_shot_fired:
                            ## TODO: refactor when players are actual objects 
                            User.queue_shooting(
                                attacker=attacker_real_name,
                                victim=victim_real_name,
                                is_dead=is_dead_victim,
                                reveal=f"{Players.get_player_role(game_action.victim)} - {Players.get_player_team(game_action.victim)}"
                                )
                else:
                    logging.info(f"Invalid victim:{game_action.victim} at {game_action.id}")
            
     
    ## Finally, push the queue If needed
    User.push_queue()
                
def update_thread_vote_count(last_count:int, last_post:int, votes_since_update:int) -> bool:
    """Decide if a new vote count should be posted based on:
        
    a) Pending GM requests.\n
    b) How many messages were posted since the last vote count. This is used-defined.\n


    Args:
        last_count (int): The id of the last vote count pushed to the game thread.
        last_post (int): The id of the last post in the game thread.
        votes_since_update (int): The amount of casted votes since last_count.

    Returns:
        bool: Whether to push a new vote count.
    """
    post_update = False
    vote_update = False

    if last_post - last_count >= settings.posts_until_update:
        post_update = True
    elif votes_since_update >= settings.votes_until_update:
        vote_update = True

    return (vote_update | post_update)

  
def push_vote_count(vote_table: pd.DataFrame, alive_players: list, last_parsed_post: int, current_majority: int):
    """Instance a new User object to push a vote count using the current vote table. 
    The object is deleted afterwards.

    Args:
        vote_table (pd.DataFrame): A dataframe with the vote table to parse for the post.
        alive_players (list): The list of alive players.
        last_parsed_post (int):  Last post parsed by the bot.
        current_majority (int): The n. votes to reach majority.
    """
    User = user.User(config=settings)
                    
    User.push_votecount(vote_count=vote_table,
                        alive_players=alive_players,
                        vote_majority=current_majority,
                        post_id=last_parsed_post)

    del User

def announce_mayor(new_mayor: str):
    """Push a new mayor announcement to the bot as a priority message.

    Args:
        new_mayor (str): Mayor name
    """
    User = user.User(config=settings)
    User.push_new_mayor(new_mayor=new_mayor)
    del User


def announce_bot_activation():
    """ Announce bot activation to the thread
    """
    User = user.User(config=settings)
    User.push_welcome_message()
    del User

def get_last_bot_cycle() -> int:
    try:
        previous_vote_history = pd.read_csv('vote_history.csv', sep=',')
        last_cycle  = previous_vote_history['bot_cycle'].tail(1).values[0]
        cur_cycle   = last_cycle + 1
        return cur_cycle
    except:
        return 0

def get_current_ntp_time() -> int:
    try:
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request("pool.ntp.org")
        current_time = response.tx_time
    except:
        current_time = datetime.datetime.now().timestamp()
    
    return current_time

if __name__ == "__main__":
	main()
