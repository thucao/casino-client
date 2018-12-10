"""
    Author: all_in

    client side functions to connect to the casino/server and interact
    with it to play games
"""

import socket
import select
import sys
import json

SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def main(args):
    if len(args) != 3:
        sys.exit("Usage: script, IP address, port number")
    ip_addr = str(args[1])
    port    = int(args[2])

    SERVER.connect((ip_addr, port))

    """ 
        server sends messages with action verbs to dictate what needs to be 
        executed
    """
    actions = {
        'name'        : insert_preference,
        'game'        : insert_preference,
        'bet'         : handle_bet,
        'print'       : print_a_message,
        'result'      : handle_result,
        'bjack-cards' : handle_bjack,
        'bjack-hit'   : handle_hit,
    }

    print("Entered casino")

    """ loop to listen to messages from the server """
    loop = True
    while loop:
        """ get sockets that are ready to be read from """
        read_sockets, _, _ = select.select([SERVER], [], [], 0.01)

        """ loop through sockets, and if it's the server, receive messages """
        for socks in read_sockets:
            if socks == SERVER:
                """ messages are seperated by the null char delimiter """
                messages = socks.recv(4096).split("\0")
                try:
                    for m in messages:
                        if m == "":
                            continue
                        message = json.loads(m)

                        """ action verb from server """
                        action = message[0]
                        
                        """ arguments for function to be executed """
                        details = message[1:]

                        """ execute function corresponding to action verb """
                        loop = actions[action](details, SERVER)
                except Exception, e:
                    message = messages
                    # print "exception in client listen"
                    # print str(e)
                    # print("message from server loop exception " \
                    #           + ": " + str(messages)) # debug print
    SERVER.close()

def try_to_get_input(message):
    """ 
        tries to get input from the user, if none is given, keeps trying.
        if given the message 'blackjack', doesn't try to get input
    """
    if message == 'blackjack\n':
        return "blackjack"
    user_input = ''
    while user_input == '':
        try:
            user_input = raw_input(message)
        except:
            user_input = ''
            pass

    return user_input.lower()

def insert_preference(details, server):
    """ asks the user what their name is or what game they want to play """
    print(details[0])
    reply = sys.stdin.readline()
    server.send(reply)
    sys.stdout.flush()
    return True

def handle_bjack(details, server):
    """ 
        handles messages being sent by blackjack.
        details = [cards, username]
        sends the user what their initial hand is and asks them whether they
        want to hit or stand.
        Sends the result back to the server to be sent to the game manager
    """
    cards = details[0]
    msg = "Here are your cards: " + cards[0][0] + " of " + cards[0][1] \
        + " and " + cards[1][0] + " of " + cards[1][1] + "\n" \
        + "Hit or Stand?\n"
    
    while True:
        move = try_to_get_input(msg)
        if move != 'hit' and move != 'stand':
            print "Please type either hit or stand"
        else:
            break

    if move == 'stand':
        print "Waiting for other users to finish betting"
    
    server.send(json.dumps(['bjack-move', details[1], move, 'blackjack']))
    return True

def handle_hit(details, server):
    """
        handles message being sent by blackjack when the user chooses to hit.
        details = [card, username]
        Asks the user if they want to continue or stand.
        Sends the result back to the server to be sent to the game manager
    """
    card = details[0]
    msg = "Here's your next card: " + card[0] + " of " + card[1] + "\n" \
        + "Hit or Stand?\n"
    
    while True:
        move = try_to_get_input(msg)
        if move != 'hit' and move != 'stand':
            print "Please type either hit or stand"
        else:
            break

    if move == 'stand':
        print "Waiting for other users to finish betting"
    server.send(json.dumps(['bjack-move', details[1], move, 'blackjack']))
    return True

def handle_bet(details, server):
    """
        asks the user how much money they want to bet and what they want to
        bet on.
        details = [username, user_money, bet_msg, possible_bets, game_name]
        Sends the result back to the server to be sent to the game manager
    """
    betsize = try_to_get_input("How much do you want to bet? Note: " \
                            + "your total money is " + str(details[1]) + '\n')

    """ check whether input is a proper number """
    while True:
        try:
            betsize = int(betsize)
        except:
            betsize = try_to_get_input("Not a number. Please insert a number.\
                \n")
            continue

        if int(betsize) > int(details[1]) or int(betsize) <= 0:
            betsize = try_to_get_input("Your bet exceeds your total money " \
                        + "or is 0 or less. Please insert a positive bet " \
                        + "less than your total.\n")
        else:
            break

    beton = try_to_get_input(details[2] + '\n')

    """ check whether input matches anything in the set of proper bets """
    while str(beton) not in set(details[3]):
        beton = try_to_get_input("Not a valid side to bet on\n" \
                            + "Options are: " + json.dumps(details[3]) + '\n')

    message = ['bet', details[0], details[1], betsize, beton, details[-1]]
    server.send(json.dumps(message))
    return True

def print_a_message(details, server):
    """ prints a message """
    print(details[1])
    return True

def handle_result(details, server):
    """ 
        handles the result of the game.
        details = [username, msg, user_money, game_name]
        If the user has no more money left, quits the game.
        Otherwise, asks the user if they want to continue playing the game,
        switch to another game or quit. 
        Sends the result back to the server and executes the appropriate 
        command (quit, continue or switch)
    """
    
    """ prints result message """
    print(details[1])
    
    """ user has no more money left """
    if details[2] <= 0:
        print("You have no money left. Better luck next time!\n" \
            + "Quitting game.")
        message = ['quit', details[0], details[1], details[-1]]
        server.send(json.dumps(message))
        return False

    ans = try_to_get_input("Continue game? Please type yes or no\n")
    while str(ans).lower() not in set(['yes', 'no']):
        ans = try_to_get_input("Please enter 'yes' or 'no'.\n")

    """ 
        assigns correct command for associated input, i.e. continue, quit
        or switch games
    """
    if str(ans) == 'yes':
        command = 'continue'
        ans = details[-1]
        print "Waiting for more users to join the room"
    elif str(ans) == 'no':
        set_of_ans = set(['blackjack', 'roulette', 'baccarat'])
        set_of_ans.remove(details[-1])
        
        ans = try_to_get_input("Which game do you want to play now? Please" \
                + " enter " + json.dumps(list(set_of_ans))[1:-1] \
                + ". If you want to quit, please enter 'quit'.\n")
        set_of_ans.add('quit')

        while str(ans).lower() not in set_of_ans:
            ans = try_to_get_input("Invalid input. Please enter one of the" \
                + " following:\n" + json.dumps(list(set_of_ans))[1:-1] + "\n") 
  
        if ans == 'quit':
            command = ans
            ans = details[-1]
        else:
            command = 'switch'

    message = [command, details[0], details[2], ans]
    server.send(json.dumps(message) + "\0")
    if command == 'quit':
        server.close()
        return False
    return True


if __name__ == '__main__':
    main(sys.argv)
