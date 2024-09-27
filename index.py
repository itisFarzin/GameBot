import gamebot

BLUE = '\033[34m'
RESET = '\033[0m'
app = gamebot.GameBot()

if __name__ == "__main__":
    print(BLUE + "GameBot by itisFarzin" + RESET)
    try:
        app.run()
    except KeyboardInterrupt:
        print("Cya!")
