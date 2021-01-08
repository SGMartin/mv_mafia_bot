import enum

class Action(enum.Enum):
    get_voters     = 'votantes'
    modkill        = 'modkill'
    replace        = 'reemplazo'
    request_count  = 'recuento'
    replace_player = 'reemplazo'
    unknown        = 'unknown'
    unvote         = 'desvoto'
    vote           = 'voto'
    vote_history   = 'historial'


    