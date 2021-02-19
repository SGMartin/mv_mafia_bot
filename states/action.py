import enum

class Action(enum.Enum):
    freeze_vote    = 'congelar'
    get_voters     = 'votantes'
    lylo           = 'lylo'
    modkill        = 'modkill'
    request_count  = 'recuento'
    replace_player = 'reemplazo'
    unknown        = 'unknown'
    unvote         = 'desvoto'
    vote           = 'voto'
    vote_history   = 'historial'


    