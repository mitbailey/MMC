from midw_netcomms import MidwNetComm
import time
import signal

# Handles when the user presses ^C.
def sighandler(signal, x):
    print("KeyboardInterrupt\n^C")

    # This will signal the main thread to move from busy-waiting to waiting on join().
    global done 
    done = True

#%%
if __name__ == '__main__':
    net = MidwNetComm()
    global done
    done = False

    # Register our ^C callback.
    signal.signal(signal.SIGINT, sighandler)

    while net._done == False:
        # print("Loop.")
        time.sleep(1)
        if done:
            net._done = True