import pytest
import pytest_timeout
import requests
import time
import zipfile
import yaml
import shogi
import engine_ctrl
import threading
import shogi.KIF as kif
import shutil
import importlib
import random
from shutil import copyfile
import importlib
copyfile('./test/lishogi.py', 'lishogi.py')
lishogi_bot = importlib.import_module("lishogi-bot")


def test_nothing():
    assert True


def download_yo():
    response = requests.get("https://github.com/mizar/YaneuraOu/releases/download/v7.0.0/Suisho5-YaneuraOu-v7.0.0-windows.zip", allow_redirects=True)
    with open("yo.zip", "wb") as file:
        file.write(response.content)
    with zipfile.ZipFile("yo.zip", "r") as zip_ref:
        zip_ref.extractall(".")
    shutil.copyfile(f"YaneuraOu_NNUE-tournament-clang++-sse42.exe", f"yo.exe")


class RandomEngine:
    def play(self, board, *args):
        return random.choice(board.legal_moves)


def run_bot(CONFIG, logging_level):
    lishogi_bot.logger.info(lishogi_bot.intro())
    li = lishogi_bot.lishogi.Lishogi(CONFIG["token"], CONFIG["url"], lishogi_bot.__version__)

    user_profile = li.get_profile()
    username = user_profile["username"]
    is_bot = user_profile.get("title") == "BOT"
    lishogi_bot.logger.info("Welcome {}!".format(username))

    if not is_bot:
        is_bot = lishogi_bot.upgrade_account(li)

    if is_bot:
        engine_factory = lishogi_bot.partial(lishogi_bot.engine_wrapper.create_engine, CONFIG)

        @pytest.mark.timeout(300)
        def run_test():

            def test_thr():
                open('events.txt', 'w').close()

                board = shogi.Board()
                btime = 60
                wtime = 60

                with open('states.txt', 'w') as file:
                    file.write('\n60,60')

                engine = engine_ctrl.Engine('yo.exe')
                engine.usi()
                engine.isready()
                engine.setoption('Skill Level', 0)
                engine.setoption('Move Overhead', 1000)

                while True:
                    if board.is_game_over():
                        with open('events.txt', 'w') as file:
                            file.write('end')
                        break

                    if len(board.move_stack) % 2 == 0:
                        with open('states.txt') as states:
                            state = states.read().split('\n')
                        moves = state[0]
                        if not board.move_stack:
                            move, _ = engine.go('startpos', '', movetime=1000)
                        else:
                            start_time = time.perf_counter_ns()
                            move, _ = engine.go('startpos', moves.split(), btime=int((btime - 2) * 1000), binc=2000)
                            end_time = time.perf_counter_ns()
                            btime -= (end_time - start_time) / 1e9
                            btime += 2
                        board.push_usi(move)

                        with open('states.txt') as states:
                            state = states.read().split('\n')
                        state[0] += ' ' + move
                        state = '\n'.join(state)
                        with open('states.txt', 'w') as file:
                            file.write(state)

                    else:  # lishogi-bot move
                        start_time = time.perf_counter_ns()
                        while True:
                            with open('states.txt') as states:
                                state2 = states.read()
                            time.sleep(0.001)
                            if state != state2:
                                break
                        with open('states.txt') as states:
                            state2 = states.read()
                        end_time = time.perf_counter_ns()
                        if len(board.move_stack) > 1:
                            wtime -= (end_time - start_time) / 1e9
                            wtime += 2
                        move = state2.split('\n')[0].split(' ')[-1]
                        board.push_usi(move)

                    time.sleep(0.001)
                    with open('states.txt') as states:
                        state = states.read().split('\n')
                    state[1] = f'{wtime},{btime}'
                    state = '\n'.join(state)
                    with open('states.txt', 'w') as file:
                        file.write(state)

                engine.quit()
                win = board.is_checkmate() and board.turn == shogi.BLACK
                assert win

            thr = threading.Thread(target=test_thr)
            thr.start()
            lishogi_bot.start(li, user_profile, engine_factory, CONFIG, logging_level, None, one_game=True)
            thr.join()

        run_test()
    else:
        lishogi_bot.logger.error("{} is not a bot account. Please upgrade it to a bot account!".format(user_profile["username"]))

def test_bot():
    logging_level = lishogi_bot.logging.INFO  # lishogi_bot.logging_level.DEBUG
    lishogi_bot.logging.basicConfig(level=logging_level, filename=None, format="%(asctime)-15s: %(message)s")
    lishogi_bot.enable_color_logging(debug_lvl=logging_level)
    download_yo()
    lishogi_bot.logger.info("Downloaded YaneuraOu for NNUE")
    with open("./config.yml.default") as file:
        CONFIG = yaml.safe_load(file)
    CONFIG["token"] = ''
    CONFIG["engine"]["dir"] = "./"
    CONFIG["engine"]["name"] = "yo.exe"
    CONFIG["engine"]["usi_options"]["BookFile"] = "no_book"
    CONFIG["engine"]["usi_options"]["NetworkDelay"] = 500
    run_bot(CONFIG, logging_level)


if __name__ == "__main__":
    test_bot()