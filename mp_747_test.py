from drivers import mp_747
from utilities import log

if __name__ == "__main__":
    comport = input('Port:')
    log.register()
    
    # s = Initialize_Serial(comport)
    # Initialize_747(s)

    mp747 = mp_747.MP_747(comport)