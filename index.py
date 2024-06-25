import betbot

BLUE = '\033[34m'
RESET = '\033[0m'
app = betbot.BetBot()

if __name__ == "__main__":
    print(BLUE + "BetBot by itisFarzin" + RESET)
    app.run()
