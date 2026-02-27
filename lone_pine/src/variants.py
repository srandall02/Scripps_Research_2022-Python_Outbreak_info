## variants.py holds all the required variants of interest and concern
## so that they can be easily accessed by other modules.

def _load_variant_list_from_file( loc ):
    with open( loc, "r" ) as i:
        return { k : v for k, v in map( lambda x: x.strip().split( ",", 1 ), i )}

VOC = _load_variant_list_from_file( "resources/voc.txt" )
VOI = _load_variant_list_from_file( "resources/voi.txt" )