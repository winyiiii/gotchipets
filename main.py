import json
import math
import os
import sys
import random
import string
from datetime import datetime
import asyncio
import pygame

# True when running in the browser (pygbag). The browser has no system fonts.
ON_WEB = sys.platform == "emscripten"

pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gotchi Pets")
try:
    pygame.key.start_text_input()   # lets the name box accept accents, Cyrillic, Hangul, etc.
except Exception:
    pass
clock = pygame.time.Clock()

# --- Easy things to tweak ------------------------------------------------
STARTING_LIVES = 3
MAX_LIVES = 5             # a correct answer earns a heart, up to this many
THUMB_HEIGHT = 180        # pet size on the selection / intro screens
MAX_NAME_LENGTH = 12
ASSETS = "Assests/"       # kept your folder spelling

# One play per student: the quiz counts as played the moment "Let's go!" is pressed.
# On the website this is remembered in the browser's localStorage (so it survives
# closing the tab or refreshing). On a computer it is remembered in played.json.
# To let someone play again: set ALLOW_TEACHER_RESET = True and press Ctrl+Shift+R
# on the menu, or clear the site's data in the browser.
ONE_PLAY_ONLY = False
ALLOW_TEACHER_RESET = False
PLAYED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "played.json")
PLAYED_KEY = "petquiz_played"


def _local_storage():
    """The browser's localStorage when running on the web, otherwise None."""
    if not ON_WEB:
        return None
    try:
        import platform
        return platform.window.localStorage
    except Exception:
        return None


def has_played_before():
    storage = _local_storage()
    if storage is not None:
        try:
            value = storage.getItem(PLAYED_KEY)
            return bool(value) and str(value) not in ("None", "null", "undefined")
        except Exception:
            return False
    return os.path.exists(PLAYED_FILE)


def write_play_record(record):
    storage = _local_storage()
    if storage is not None:
        try:
            storage.setItem(PLAYED_KEY, json.dumps(record, ensure_ascii=False))
        except Exception:
            print("Could not save to the browser's localStorage.")
        return
    try:
        with open(PLAYED_FILE, "w", encoding="utf-8") as record_file:
            json.dump(record, record_file, ensure_ascii=False, indent=2)
    except OSError:
        print("Could not write", PLAYED_FILE, "- the game is only locked until it is closed.")


def clear_play_record():
    storage = _local_storage()
    if storage is not None:
        try:
            storage.removeItem(PLAYED_KEY)
        except Exception:
            pass
        return
    try:
        os.remove(PLAYED_FILE)
    except OSError:
        pass

# Main menu look: "menu screen.jpg" is the background. The "Gotchi Pets" logo is
# drawn on top automatically. Turn these on if you want a cream panel behind the
# buttons or the old plain text title as well.
SHOW_MENU_PANEL = False
SHOW_MENU_TITLE = False

TEXT_COLOR = (30, 20, 45)          # near-black purple for strong contrast
PANEL_COLOR = (255, 250, 245)
ACCENT_PINK = (255, 105, 180)      # highlight color (hearts ring, selected pet, name box)

# Quiz layout: pet on the left, bubble + answers on the right
PET_CENTER = (260, 420)
PET_MAX_SIZE = (340, 360)
COL_LEFT, COL_WIDTH = 490, 740


# --- Asset lookup ---------------------------------------------------------
# GitHub Pages is case-sensitive and Windows is not. This finds a file even if
# the capitalization differs, or if spaces vs underscores differ
# ("menu screen.jpg" will match "menu_screen.jpg" and "Menu Screen.jpg").
def _norm(name):
    return name.lower().replace(" ", "_")


def find_asset(name):
    """Return the real path of an asset, or None if it can't be found."""
    path = ASSETS + name
    if os.path.exists(path):
        return path
    try:
        files = os.listdir(ASSETS)
    except OSError:
        return None
    target = _norm(name)
    for real_name in files:
        if _norm(real_name) == target:
            return ASSETS + real_name
    return None


# --- Languages and translations -------------------------------------------
# To add a language: add it to LANGUAGES, add a block to TEXT, and add a
# translation to every question/answer list in QUESTIONS below.
LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "ko": "한국어",
    "ru": "Русский",
    "vi": "Tiếng Việt",
}

TEXT = {
    "en": {
        "title": "Gotchi Pets",
        "play": "Play",
        "language": "Language",
        "quit": "Quit",
        "choose_language": "Choose Language",
        "back": "Back",
        "next": "Next!",
        "pick_pet": "Pick a pet first",
        "name_hint": "Name your pet...",
        "how_to_play": "How to Play",
        "lets_go": "Let's go!",
        "intro_1": "Take care of {name} for a whole week!",
        "intro_2": "Answer {count} questions about substance use to keep {name} alive. "
                   "If your pet is alive after completing the questions, you get a certificate.",
        "intro_3": "Show the certificate to someone in room 402 to claim a prize!",
        "wrong": "Oops! The right answer is in green. Click to continue",
        "win": "{name} is proud of you! Click to play again",
        "game_over": "{name} ran out of lives! Click to try again",
        "pet_bunny": "Bunny",
        "pet_hamster": "Hamster",
        "pet_cat": "Cat",
        "pet_dog": "Dog",
        "win_once": "{name} is proud of you! Thanks for playing!",
        "game_over_once": "{name} ran out of lives! Thanks for playing!",
        "already_played": "You've already played. Thanks for playing!",
        "cert_title": "Certificate of Care",
        "cert_awarded": "Proudly awarded to the loving parent of",
        "cert_body": "Thanks to you, your pet stayed happy and healthy!",
    },
    "fr": {
        "title": "Gotchi Pets",
        "play": "Jouer",
        "language": "Langue",
        "quit": "Quitter",
        "choose_language": "Choisir la langue",
        "back": "Retour",
        "next": "Suivant !",
        "pick_pet": "Choisis un animal",
        "name_hint": "Nomme ton animal",
        "how_to_play": "Comment jouer",
        "lets_go": "C'est parti !",
        "intro_1": "Prends soin de {name} pendant une semaine entière !",
        "intro_2": "Réponds à {count} questions sur la consommation de substances pour garder "
                   "{name} en vie. Si ton animal est toujours en vie à la fin des questions, "
                   "tu reçois un certificat.",
        "intro_3": "Montre le certificat à quelqu'un dans la salle 402 pour réclamer un prix !",
        "wrong": "Oups ! La bonne réponse est en vert. Clique pour continuer",
        "win": "{name} te dit bravo ! Clique pour rejouer",
        "game_over": "{name} n'a plus de vies ! Clique pour réessayer",
        "pet_bunny": "Lapin",
        "pet_hamster": "Hamster",
        "pet_cat": "Chat",
        "pet_dog": "Chien",
        "win_once": "{name} te dit bravo ! Merci d'avoir joué !",
        "game_over_once": "{name} n'a plus de vies ! Merci d'avoir joué !",
        "already_played": "Tu as déjà joué. Merci d'avoir participé !",
        "cert_title": "Certificat de soins",
        "cert_awarded": "Décerné avec fierté au parent attentionné de",
        "cert_body": "Grâce à toi, ton animal est resté heureux et en bonne santé !",
    },
    "es": {
        "title": "Gotchi Pets",
        "play": "Jugar",
        "language": "Idioma",
        "quit": "Salir",
        "choose_language": "Elegir idioma",
        "back": "Atrás",
        "next": "¡Siguiente!",
        "pick_pet": "Elige una mascota",
        "name_hint": "Nombre de tu mascota",
        "how_to_play": "Cómo jugar",
        "lets_go": "¡Vamos!",
        "intro_1": "¡Cuida a {name} durante una semana entera!",
        "intro_2": "Responde {count} preguntas sobre el consumo de sustancias para mantener con "
                   "vida a {name}. Si tu mascota sigue con vida al terminar las preguntas, "
                   "recibes un certificado.",
        "intro_3": "¡Muestra el certificado a alguien en el salón 402 para reclamar un premio!",
        "wrong": "¡Ups! La respuesta correcta está en verde. Haz clic para continuar",
        "win": "¡Bien hecho! {name} está muy feliz. Haz clic para jugar de nuevo",
        "game_over": "¡{name} se quedó sin vidas! Haz clic para intentarlo de nuevo",
        "pet_bunny": "Conejo",
        "pet_hamster": "Hámster",
        "pet_cat": "Gato",
        "pet_dog": "Perro",
        "win_once": "¡Bien hecho! {name} está muy feliz. ¡Gracias por jugar!",
        "game_over_once": "¡{name} se quedó sin vidas! ¡Gracias por jugar!",
        "already_played": "Ya jugaste. ¡Gracias por participar!",
        "cert_title": "Certificado de cuidado",
        "cert_awarded": "Otorgado con orgullo al dueño cariñoso de",
        "cert_body": "¡Gracias a ti, tu mascota estuvo feliz y sana !",
    },
    "ko": {
        "title": "Gotchi Pets",
        "play": "시작",
        "language": "언어",
        "quit": "종료",
        "choose_language": "언어 선택",
        "back": "뒤로",
        "next": "다음!",
        "pick_pet": "동물을 골라 주세요",
        "name_hint": "이름을 지어 주세요",
        "how_to_play": "게임 방법",
        "lets_go": "시작하자!",
        "intro_1": "{name}을(를) 일주일 동안 잘 돌봐 주세요!",
        "intro_2": "약물 사용에 관한 질문 {count}개에 답하여 {name}을(를) 살려 주세요. "
                   "질문을 모두 마친 후에도 반려동물이 살아 있으면 인증서를 받아요.",
        "intro_3": "402호에 있는 사람에게 인증서를 보여 주고 상품을 받아 가세요!",
        "wrong": "앗! 정답은 초록색이에요. 계속하려면 클릭하세요",
        "win": "{name}이(가) 정말 기뻐해요! 다시 하려면 클릭하세요",
        "game_over": "{name}의 하트가 모두 사라졌어요! 다시 도전하려면 클릭하세요",
        "pet_bunny": "토끼",
        "pet_hamster": "햄스터",
        "pet_cat": "고양이",
        "pet_dog": "강아지",
        "win_once": "{name}이(가) 정말 기뻐해요! 플레이해 주셔서 감사합니다!",
        "game_over_once": "{name}의 하트가 모두 사라졌어요! 플레이해 주셔서 감사합니다!",
        "already_played": "이미 플레이했어요. 참여해 주셔서 감사합니다!",
        "cert_title": "돌봄 인증서",
        "cert_awarded": "다음 반려동물의 훌륭한 보호자에게 드립니다",
        "cert_body": "여러분 덕분에 반려동물이 행복하고 건강하게 지내고 있습니다!",
    },
    "ru": {
        "title": "Gotchi Pets",
        "play": "Играть",
        "language": "Язык",
        "quit": "Выход",
        "choose_language": "Выбор языка",
        "back": "Назад",
        "next": "Далее!",
        "pick_pet": "Выбери питомца",
        "name_hint": "Имя питомца...",
        "how_to_play": "Как играть",
        "lets_go": "Поехали!",
        "intro_1": "Заботься о {name} целую неделю!",
        "intro_2": "Ответь на вопросы об употреблении психоактивных веществ (всего их {count}), "
                   "чтобы сохранить жизнь питомцу {name}. Если после всех вопросов твой питомец "
                   "жив, ты получишь сертификат.",
        "intro_3": "Покажи сертификат кому-нибудь в кабинете 402, чтобы получить приз!",
        "wrong": "Ой! Правильный ответ выделен зелёным. Нажми, чтобы продолжить",
        "win": "{name} гордится тобой! Нажми, чтобы сыграть ещё раз",
        "game_over": "У {name} не осталось сердечек! Нажми, чтобы попробовать снова",
        "pet_bunny": "Кролик",
        "pet_hamster": "Хомяк",
        "pet_cat": "Кот",
        "pet_dog": "Собака",
        "win_once": "{name} гордится тобой! Спасибо за игру!",
        "game_over_once": "У {name} не осталось сердечек! Спасибо за игру!",
        "already_played": "Игра уже пройдена. Спасибо за участие!",
        "cert_title": "Сертификат заботы",
        "cert_awarded": "С гордостью вручается заботливому хозяину питомца",
        "cert_body": "Благодаря вам ваш питомец был здоров и счастлив !",
    },
    "vi": {
        "title": "Gotchi Pets",
        "play": "Chơi",
        "language": "Ngôn ngữ",
        "quit": "Thoát",
        "choose_language": "Chọn ngôn ngữ",
        "back": "Quay lại",
        "next": "Tiếp theo!",
        "pick_pet": "Hãy chọn thú cưng",
        "name_hint": "Đặt tên cho thú cưng",
        "how_to_play": "Cách chơi",
        "lets_go": "Bắt đầu thôi!",
        "intro_1": "Hãy chăm sóc {name} trong cả một tuần nhé!",
        "intro_2": "Hãy trả lời {count} câu hỏi về việc sử dụng chất gây nghiện để giữ cho {name} "
                   "sống sót. Nếu thú cưng vẫn còn sống sau khi hoàn thành các câu hỏi, "
                   "bạn sẽ nhận được một giấy chứng nhận.",
        "intro_3": "Hãy đưa giấy chứng nhận cho một người ở phòng 402 để nhận phần thưởng!",
        "wrong": "Ôi! Đáp án đúng có màu xanh lá. Nhấp chuột để tiếp tục",
        "win": "{name} rất tự hào về bạn! Nhấp chuột để chơi lại",
        "game_over": "{name} đã hết mạng! Nhấp chuột để thử lại",
        "pet_bunny": "Thỏ",
        "pet_hamster": "Hamster",
        "pet_cat": "Mèo",
        "pet_dog": "Chó",
        "win_once": "{name} rất tự hào về bạn! Cảm ơn bạn đã chơi!",
        "game_over_once": "{name} đã hết mạng! Cảm ơn bạn đã chơi!",
        "already_played": "Bạn đã chơi rồi. Cảm ơn bạn đã tham gia!",
        "cert_title": "Giấy chứng nhận chăm sóc",
        "cert_awarded": "Trân trọng trao tặng chủ nhân tuyệt vời của",
        "cert_body": "Nhờ có bạn, thú cưng của bạn đã khỏe mạnh và hạnh phúc !",
    },
}

QUESTIONS = [
    # 1
    {
        "q": {
            "en": "Substance use involves which of the following:",
            "fr": "La consommation de substances comprend lesquels des éléments suivants :",
            "es": "El consumo de sustancias incluye cuál de lo siguiente:",
            "ko": "약물 사용에는 다음 중 무엇이 포함되나요?",
            "ru": "Что включает в себя употребление психоактивных веществ?",
            "vi": "Sử dụng chất gây nghiện bao gồm điều nào sau đây:",
        },
        "answers": {
            "en": [
                "Consumption, inhalation and injection of substances",
                "Just consumption of substances",
                "Just inhalation of substances",
                "None of the above",
            ],
            "fr": [
                "La consommation, l'inhalation et l'injection de substances",
                "Seulement la consommation de substances",
                "Seulement l'inhalation de substances",
                "Aucune de ces réponses",
            ],
            "es": [
                "Consumo, inhalación e inyección de sustancias",
                "Solo el consumo de sustancias",
                "Solo la inhalación de sustancias",
                "Ninguna de las anteriores",
            ],
            "ko": [
                "약물의 섭취, 흡입, 주사",
                "약물의 섭취만",
                "약물의 흡입만",
                "해당 없음",
            ],
            "ru": [
                "Приём, вдыхание и инъекции веществ",
                "Только приём веществ",
                "Только вдыхание веществ",
                "Ничего из перечисленного",
            ],
            "vi": [
                "Uống, hít và tiêm các chất",
                "Chỉ uống các chất",
                "Chỉ hít các chất",
                "Không có đáp án nào đúng",
            ],
        },
        "correct": 0,
    },
    # 2
    {
        "q": {
            "en": "What are some common examples of substance use?",
            "fr": "Quels sont des exemples courants de consommation de substances ?",
            "es": "¿Cuáles son algunos ejemplos comunes de consumo de sustancias?",
            "ko": "약물 사용의 흔한 예에는 무엇이 있나요?",
            "ru": "Какие есть распространённые примеры употребления психоактивных веществ?",
            "vi": "Một số ví dụ phổ biến về sử dụng chất gây nghiện là gì?",
        },
        "answers": {
            "en": ["Gambling", "Drinking alcohol", "Lack of sleep", "Phone addiction"],
            "fr": ["Les jeux de hasard", "Boire de l'alcool", "Le manque de sommeil",
                   "La dépendance au téléphone"],
            "es": ["Los juegos de azar", "Beber alcohol", "La falta de sueño",
                   "La adicción al teléfono"],
            "ko": ["도박", "술 마시기", "수면 부족", "휴대폰 중독"],
            "ru": ["Азартные игры", "Употребление алкоголя", "Недостаток сна",
                   "Зависимость от телефона"],
            "vi": ["Cờ bạc", "Uống rượu bia", "Thiếu ngủ", "Nghiện điện thoại"],
        },
        "correct": 1,
    },
    # 3
    {
        "q": {
            "en": "How does substance use mainly affect you?",
            "fr": "Comment la consommation de substances t'affecte-t-elle principalement ?",
            "es": "¿Cómo te afecta principalmente el consumo de sustancias?",
            "ko": "약물 사용은 주로 나에게 어떤 영향을 주나요?",
            "ru": "Как употребление психоактивных веществ влияет на тебя в первую очередь?",
            "vi": "Việc sử dụng chất gây nghiện ảnh hưởng chủ yếu đến bạn như thế nào?",
        },
        "answers": {
            "en": [
                "It affects my behaviour",
                "It affects how smooth my skin feels",
                "It affects how others perceive you",
                "It affects your brain function, mood and behaviour",
            ],
            "fr": [
                "Elle affecte mon comportement",
                "Elle affecte la douceur de ma peau",
                "Elle affecte la façon dont les autres te perçoivent",
                "Elle affecte le fonctionnement de ton cerveau, ton humeur et ton comportement",
            ],
            "es": [
                "Afecta mi comportamiento",
                "Afecta lo suave que se siente mi piel",
                "Afecta cómo te perciben los demás",
                "Afecta el funcionamiento de tu cerebro, tu estado de ánimo y tu comportamiento",
            ],
            "ko": [
                "내 행동에 영향을 준다",
                "피부의 부드러움에 영향을 준다",
                "다른 사람들이 나를 보는 시선에 영향을 준다",
                "뇌 기능, 기분, 행동에 영향을 준다",
            ],
            "ru": [
                "Влияет на моё поведение",
                "Влияет на мягкость моей кожи",
                "Влияет на то, как тебя воспринимают другие",
                "Влияет на работу мозга, настроение и поведение",
            ],
            "vi": [
                "Nó ảnh hưởng đến hành vi của tôi",
                "Nó ảnh hưởng đến độ mịn của da tôi",
                "Nó ảnh hưởng đến cách người khác nhìn nhận bạn",
                "Nó ảnh hưởng đến chức năng não, tâm trạng và hành vi của bạn",
            ],
        },
        "correct": 3,
    },
    # 4
    {
        "q": {
            "en": "True or false, drinking affects brain development",
            "fr": "Vrai ou faux : boire de l'alcool affecte le développement du cerveau",
            "es": "¿Verdadero o falso? Beber alcohol afecta el desarrollo del cerebro.",
            "ko": "참일까요, 거짓일까요? 술은 뇌 발달에 영향을 준다.",
            "ru": "Верно или неверно: алкоголь влияет на развитие мозга?",
            "vi": "Đúng hay sai: uống rượu bia ảnh hưởng đến sự phát triển của não?",
        },
        "answers": {
            "en": ["False", "True"],
            "fr": ["Faux", "Vrai"],
            "es": ["Falso", "Verdadero"],
            "ko": ["거짓", "참"],
            "ru": ["Неверно", "Верно"],
            "vi": ["Sai", "Đúng"],
        },
        "correct": 1,
    },
    # 5
    {
        "q": {
            "en": "How can smoking cannabis affect your brain?",
            "fr": "Comment fumer du cannabis peut-il affecter ton cerveau ?",
            "es": "¿Cómo puede afectar tu cerebro fumar cannabis?",
            "ko": "대마초 흡연은 뇌에 어떤 영향을 줄 수 있나요?",
            "ru": "Как курение каннабиса может повлиять на твой мозг?",
            "vi": "Hút cần sa có thể ảnh hưởng đến não của bạn như thế nào?",
        },
        "answers": {
            "en": [
                "It can cause decreased mood",
                "It can cause you to develop an addiction",
                "It can cause cognitive deficits",
                "It can cause decreased hair growth",
            ],
            "fr": [
                "Cela peut causer une baisse d'humeur",
                "Cela peut causer une dépendance",
                "Cela peut causer des déficits cognitifs",
                "Cela peut ralentir la pousse des cheveux",
            ],
            "es": [
                "Puede causar un estado de ánimo más bajo",
                "Puede causar que desarrolles una adicción",
                "Puede causar déficits cognitivos",
                "Puede disminuir el crecimiento del cabello",
            ],
            "ko": [
                "기분을 가라앉게 할 수 있다",
                "중독이 생길 수 있다",
                "인지 기능 저하를 일으킬 수 있다",
                "머리카락이 덜 자라게 할 수 있다",
            ],
            "ru": [
                "Может ухудшить настроение",
                "Может вызвать зависимость",
                "Может вызвать когнитивные нарушения",
                "Может замедлить рост волос",
            ],
            "vi": [
                "Có thể làm giảm tâm trạng",
                "Có thể khiến bạn bị nghiện",
                "Có thể gây suy giảm nhận thức",
                "Có thể làm tóc mọc chậm lại",
            ],
        },
        "correct": 2,
    },
    # 6
    {
        "q": {
            "en": "Which of the following cognitive abilities can be negatively affected by cannabis use?",
            "fr": "Laquelle de ces capacités cognitives peut être affectée négativement par la consommation de cannabis ?",
            "es": "¿Cuál de las siguientes capacidades cognitivas puede verse afectada negativamente por el consumo de cannabis?",
            "ko": "다음 중 대마초 사용으로 부정적인 영향을 받을 수 있는 인지 능력은 무엇인가요?",
            "ru": "Какая из следующих когнитивных способностей может ухудшиться из-за употребления каннабиса?",
            "vi": "Khả năng nhận thức nào sau đây có thể bị ảnh hưởng tiêu cực do sử dụng cần sa?",
        },
        "answers": {
            "en": ["Hearing", "Learning", "Speaking", "Digestion"],
            "fr": ["L'ouïe", "L'apprentissage", "La parole", "La digestion"],
            "es": ["La audición", "El aprendizaje", "El habla", "La digestión"],
            "ko": ["청력", "학습", "말하기", "소화"],
            "ru": ["Слух", "Обучение", "Речь", "Пищеварение"],
            "vi": ["Thính giác", "Học tập", "Nói", "Tiêu hóa"],
        },
        "correct": 1,
    },
    # 7
    {
        "q": {
            "en": "How can cannabis use affect the adolescent brain's structure?",
            "fr": "Comment la consommation de cannabis peut-elle affecter la structure du cerveau des adolescents ?",
            "es": "¿Cómo puede afectar el consumo de cannabis a la estructura del cerebro adolescente?",
            "ko": "대마초 사용은 청소년 뇌의 구조에 어떤 영향을 줄 수 있나요?",
            "ru": "Как употребление каннабиса может повлиять на строение мозга подростка?",
            "vi": "Việc sử dụng cần sa có thể ảnh hưởng đến cấu trúc não của thanh thiếu niên như thế nào?",
        },
        "answers": {
            "en": [
                "Increase the size of grey matter",
                "Decrease the size of grey matter",
                "Improve brain development",
                "Increase the size of the hippocampus",
            ],
            "fr": [
                "Augmenter le volume de la matière grise",
                "Diminuer le volume de la matière grise",
                "Améliorer le développement du cerveau",
                "Augmenter la taille de l'hippocampe",
            ],
            "es": [
                "Aumentar el tamaño de la materia gris",
                "Disminuir el tamaño de la materia gris",
                "Mejorar el desarrollo del cerebro",
                "Aumentar el tamaño del hipocampo",
            ],
            "ko": [
                "회백질의 크기를 늘린다",
                "회백질의 크기를 줄인다",
                "뇌 발달을 향상시킨다",
                "해마의 크기를 늘린다",
            ],
            "ru": [
                "Увеличить объём серого вещества",
                "Уменьшить объём серого вещества",
                "Улучшить развитие мозга",
                "Увеличить размер гиппокампа",
            ],
            "vi": [
                "Làm tăng kích thước chất xám",
                "Làm giảm kích thước chất xám",
                "Cải thiện sự phát triển của não",
                "Làm tăng kích thước hồi hải mã",
            ],
        },
        "correct": 1,
    },
    # 8
    {
        "q": {
            "en": "Which of the following organs is most directly affected by vaping?",
            "fr": "Lequel de ces organes est le plus directement touché par le vapotage ?",
            "es": "¿Cuál de los siguientes órganos se ve afectado más directamente por el vapeo?",
            "ko": "다음 중 전자담배 사용(베이핑)의 영향을 가장 직접적으로 받는 장기는 무엇인가요?",
            "ru": "Какой из следующих органов страдает от вейпинга сильнее всего?",
            "vi": "Cơ quan nào sau đây bị ảnh hưởng trực tiếp nhất bởi việc vape?",
        },
        "answers": {
            "en": ["Liver", "Lungs", "Kidneys", "Stomach"],
            "fr": ["Le foie", "Les poumons", "Les reins", "L'estomac"],
            "es": ["El hígado", "Los pulmones", "Los riñones", "El estómago"],
            "ko": ["간", "폐", "신장", "위"],
            "ru": ["Печень", "Лёгкие", "Почки", "Желудок"],
            "vi": ["Gan", "Phổi", "Thận", "Dạ dày"],
        },
        "correct": 1,
    },
    # 9
    {
        "q": {
            "en": "True or False: Cannabis use during adolescence can negatively affect learning and memory.",
            "fr": "Vrai ou faux : la consommation de cannabis à l'adolescence peut nuire à l'apprentissage et à la mémoire.",
            "es": "¿Verdadero o falso? El consumo de cannabis durante la adolescencia puede afectar negativamente el aprendizaje y la memoria.",
            "ko": "참일까요, 거짓일까요? 청소년기의 대마초 사용은 학습과 기억력에 부정적인 영향을 줄 수 있다.",
            "ru": "Верно или неверно: употребление каннабиса в подростковом возрасте может негативно влиять на обучение и память.",
            "vi": "Đúng hay sai: sử dụng cần sa ở tuổi vị thành niên có thể ảnh hưởng tiêu cực đến việc học và trí nhớ.",
        },
        "answers": {
            "en": ["True", "False"],
            "fr": ["Vrai", "Faux"],
            "es": ["Verdadero", "Falso"],
            "ko": ["참", "거짓"],
            "ru": ["Верно", "Неверно"],
            "vi": ["Đúng", "Sai"],
        },
        "correct": 0,
    },
    # 10
    {
        "q": {
            "en": "Smoking cannabis can cause changes in the prefrontal cortex. Which of the following brain functions can be affected?",
            "fr": "Fumer du cannabis peut modifier le cortex préfrontal. Laquelle de ces fonctions du cerveau peut être affectée ?",
            "es": "Fumar cannabis puede provocar cambios en la corteza prefrontal. ¿Cuál de las siguientes funciones cerebrales puede verse afectada?",
            "ko": "대마초 흡연은 전전두엽 피질에 변화를 일으킬 수 있어요. 다음 중 영향을 받을 수 있는 뇌 기능은 무엇인가요?",
            "ru": "Курение каннабиса может изменять префронтальную кору. Какая из следующих функций мозга может пострадать?",
            "vi": "Hút cần sa có thể gây thay đổi ở vỏ não trước trán. Chức năng não nào sau đây có thể bị ảnh hưởng?",
        },
        "answers": {
            "en": ["Improved memory", "Improved decision-making", "Emotional regulation",
                   "Decreased heart rate"],
            "fr": ["Une meilleure mémoire", "Une meilleure prise de décision",
                   "La régulation des émotions", "Une baisse du rythme cardiaque"],
            "es": ["Mejor memoria", "Mejor toma de decisiones", "La regulación emocional",
                   "Menor frecuencia cardíaca"],
            "ko": ["기억력 향상", "의사 결정 능력 향상", "감정 조절", "심박수 감소"],
            "ru": ["Улучшение памяти", "Улучшение принятия решений", "Регуляция эмоций",
                   "Снижение частоты сердечных сокращений"],
            "vi": ["Cải thiện trí nhớ", "Cải thiện khả năng ra quyết định", "Điều hòa cảm xúc",
                   "Giảm nhịp tim"],
        },
        "correct": 2,
    },
    # 11
    {
        "q": {
            "en": "Why is cannabis use during adolescence a concern?",
            "fr": "Pourquoi la consommation de cannabis à l'adolescence est-elle préoccupante ?",
            "es": "¿Por qué preocupa el consumo de cannabis durante la adolescencia?",
            "ko": "청소년기의 대마초 사용이 걱정되는 이유는 무엇인가요?",
            "ru": "Почему употребление каннабиса в подростковом возрасте вызывает беспокойство?",
            "vi": "Tại sao việc sử dụng cần sa ở tuổi vị thành niên đáng lo ngại?",
        },
        "answers": {
            "en": [
                "The brain has already completed all its development",
                "The brain is still developing, and cannabis may affect important brain functions",
                "Cannabis only affects physical growth",
                "Cannabis improves attention and memory",
            ],
            "fr": [
                "Le cerveau a déjà terminé tout son développement",
                "Le cerveau est encore en développement et le cannabis peut affecter des fonctions importantes",
                "Le cannabis n'affecte que la croissance physique",
                "Le cannabis améliore l'attention et la mémoire",
            ],
            "es": [
                "El cerebro ya completó todo su desarrollo",
                "El cerebro aún se está desarrollando y el cannabis puede afectar funciones importantes",
                "El cannabis solo afecta el crecimiento físico",
                "El cannabis mejora la atención y la memoria",
            ],
            "ko": [
                "뇌가 이미 모든 발달을 마쳤기 때문에",
                "뇌가 아직 발달 중이라 대마초가 중요한 뇌 기능에 영향을 줄 수 있기 때문에",
                "대마초는 신체 성장에만 영향을 주기 때문에",
                "대마초가 집중력과 기억력을 높여 주기 때문에",
            ],
            "ru": [
                "Мозг уже полностью завершил своё развитие",
                "Мозг ещё развивается, и каннабис может повлиять на важные функции мозга",
                "Каннабис влияет только на физический рост",
                "Каннабис улучшает внимание и память",
            ],
            "vi": [
                "Não đã hoàn thành toàn bộ quá trình phát triển",
                "Não vẫn đang phát triển và cần sa có thể ảnh hưởng đến các chức năng quan trọng",
                "Cần sa chỉ ảnh hưởng đến sự phát triển thể chất",
                "Cần sa cải thiện sự chú ý và trí nhớ",
            ],
        },
        "correct": 1,
    },
    # 12
    {
        "q": {
            "en": "True or False: Vaping can increase the risk of developing asthma.",
            "fr": "Vrai ou faux : le vapotage peut augmenter le risque de développer de l'asthme.",
            "es": "¿Verdadero o falso? El vapeo puede aumentar el riesgo de desarrollar asma.",
            "ko": "참일까요, 거짓일까요? 전자담배 사용(베이핑)은 천식에 걸릴 위험을 높일 수 있다.",
            "ru": "Верно или неверно: вейпинг может повысить риск развития астмы.",
            "vi": "Đúng hay sai: vape có thể làm tăng nguy cơ mắc bệnh hen suyễn.",
        },
        "answers": {
            "en": ["True", "False"],
            "fr": ["Vrai", "Faux"],
            "es": ["Verdadero", "Falso"],
            "ko": ["참", "거짓"],
            "ru": ["Верно", "Неверно"],
            "vi": ["Đúng", "Sai"],
        },
        "correct": 0,
    },
    # 13
    {
        "q": {
            "en": "Which of the following is NOT a side effect of vaping?",
            "fr": "Lequel de ces effets n'est PAS un effet secondaire du vapotage ?",
            "es": "¿Cuál de los siguientes NO es un efecto secundario del vapeo?",
            "ko": "다음 중 전자담배 사용(베이핑)의 부작용이 아닌 것은 무엇인가요?",
            "ru": "Что из перечисленного НЕ является побочным эффектом вейпинга?",
            "vi": "Điều nào sau đây KHÔNG phải là tác dụng phụ của việc vape?",
        },
        "answers": {
            "en": [
                "Clotting proteins building up in lungs",
                "Widespread injury to lung air sacs",
                "Severe inflammation",
                "Thinning of lung walls",
            ],
            "fr": [
                "Accumulation de protéines de coagulation dans les poumons",
                "Lésions étendues des alvéoles pulmonaires",
                "Inflammation sévère",
                "Amincissement des parois des poumons",
            ],
            "es": [
                "Acumulación de proteínas de coagulación en los pulmones",
                "Daño generalizado a los alvéolos pulmonares",
                "Inflamación grave",
                "Adelgazamiento de las paredes de los pulmones",
            ],
            "ko": [
                "폐에 혈액 응고 단백질이 쌓임",
                "폐 공기주머니의 광범위한 손상",
                "심한 염증",
                "폐 벽이 얇아짐",
            ],
            "ru": [
                "Накопление свёртывающих белков в лёгких",
                "Обширное повреждение альвеол лёгких",
                "Сильное воспаление",
                "Истончение стенок лёгких",
            ],
            "vi": [
                "Các protein đông máu tích tụ trong phổi",
                "Tổn thương lan rộng ở các túi khí của phổi",
                "Viêm nặng",
                "Thành phổi bị mỏng đi",
            ],
        },
        "correct": 3,
    },
    # 14
    {
        "q": {
            "en": "How does vaping affect the lung structure?",
            "fr": "Comment le vapotage affecte-t-il la structure des poumons ?",
            "es": "¿Cómo afecta el vapeo a la estructura de los pulmones?",
            "ko": "전자담배 사용(베이핑)은 폐의 구조에 어떤 영향을 주나요?",
            "ru": "Как вейпинг влияет на строение лёгких?",
            "vi": "Việc vape ảnh hưởng đến cấu trúc phổi như thế nào?",
        },
        "answers": {
            "en": [
                "Fluid buildup between lungs and chest wall",
                "Thinning of lung membranes",
                "Increased mucous membranes",
                "Decreased air circulation",
            ],
            "fr": [
                "Accumulation de liquide entre les poumons et la paroi thoracique",
                "Amincissement des membranes pulmonaires",
                "Augmentation des muqueuses",
                "Diminution de la circulation de l'air",
            ],
            "es": [
                "Acumulación de líquido entre los pulmones y la pared torácica",
                "Adelgazamiento de las membranas pulmonares",
                "Aumento de las membranas mucosas",
                "Disminución de la circulación del aire",
            ],
            "ko": [
                "폐와 흉벽 사이에 체액이 고임",
                "폐 막이 얇아짐",
                "점막이 늘어남",
                "공기 순환이 줄어듦",
            ],
            "ru": [
                "Скопление жидкости между лёгкими и грудной стенкой",
                "Истончение оболочек лёгких",
                "Увеличение слизистых оболочек",
                "Ухудшение циркуляции воздуха",
            ],
            "vi": [
                "Tích tụ dịch giữa phổi và thành ngực",
                "Màng phổi bị mỏng đi",
                "Tăng niêm mạc",
                "Giảm lưu thông không khí",
            ],
        },
        "correct": 0,
    },
    # 15
    {
        "q": {
            "en": "Which part of the brain is responsible for decision-making and is affected by alcohol use?",
            "fr": "Quelle partie du cerveau est responsable de la prise de décision et est affectée par la consommation d'alcool ?",
            "es": "¿Qué parte del cerebro es responsable de la toma de decisiones y se ve afectada por el consumo de alcohol?",
            "ko": "의사 결정을 담당하며 음주의 영향을 받는 뇌의 부위는 어디인가요?",
            "ru": "Какая часть мозга отвечает за принятие решений и страдает от употребления алкоголя?",
            "vi": "Bộ phận nào của não chịu trách nhiệm ra quyết định và bị ảnh hưởng bởi rượu bia?",
        },
        "answers": {
            "en": ["Parietal lobe", "Brain stem", "Occipital lobe", "Prefrontal Cortex"],
            "fr": ["Le lobe pariétal", "Le tronc cérébral", "Le lobe occipital",
                   "Le cortex préfrontal"],
            "es": ["Lóbulo parietal", "Tronco encefálico", "Lóbulo occipital",
                   "Corteza prefrontal"],
            "ko": ["두정엽", "뇌간", "후두엽", "전전두엽 피질"],
            "ru": ["Теменная доля", "Ствол мозга", "Затылочная доля", "Префронтальная кора"],
            "vi": ["Thùy đỉnh", "Thân não", "Thùy chẩm", "Vỏ não trước trán"],
        },
        "correct": 3,
    },
    # 16
    {
        "q": {
            "en": "Which of the following does alcohol NOT affect?",
            "fr": "Lequel de ces éléments l'alcool n'affecte-t-il PAS ?",
            "es": "¿Cuál de los siguientes NO es afectado por el alcohol?",
            "ko": "다음 중 술이 영향을 주지 않는 것은 무엇인가요?",
            "ru": "На что из перечисленного алкоголь НЕ влияет?",
            "vi": "Rượu bia KHÔNG ảnh hưởng đến điều nào sau đây?",
        },
        "answers": {
            "en": ["Decreased memory", "Decreased processing", "Decreased heart rate",
                   "Decreased attention span"],
            "fr": ["Diminution de la mémoire", "Diminution de la vitesse de traitement",
                   "Diminution du rythme cardiaque", "Diminution de la durée d'attention"],
            "es": ["Disminución de la memoria", "Disminución del procesamiento",
                   "Disminución de la frecuencia cardíaca",
                   "Disminución de la capacidad de atención"],
            "ko": ["기억력 저하", "처리 속도 저하", "심박수 감소", "집중 시간 감소"],
            "ru": ["Ухудшение памяти", "Замедление обработки информации",
                   "Снижение частоты сердечных сокращений", "Снижение концентрации внимания"],
            "vi": ["Giảm trí nhớ", "Giảm khả năng xử lý thông tin", "Giảm nhịp tim",
                   "Giảm khả năng tập trung"],
        },
        "correct": 2,
    },
    # 17
    {
        "q": {
            "en": "True or False: alcohol use during adolescence is a concern because it can interfere with healthy brain development.",
            "fr": "Vrai ou faux : la consommation d'alcool à l'adolescence est préoccupante parce qu'elle peut nuire au développement sain du cerveau.",
            "es": "¿Verdadero o falso? El consumo de alcohol durante la adolescencia preocupa porque puede afectar el desarrollo sano del cerebro.",
            "ko": "참일까요, 거짓일까요? 청소년기의 음주는 건강한 뇌 발달을 방해할 수 있어서 걱정스럽다.",
            "ru": "Верно или неверно: употребление алкоголя в подростковом возрасте вызывает беспокойство, потому что оно может нарушать здоровое развитие мозга.",
            "vi": "Đúng hay sai: uống rượu bia ở tuổi vị thành niên đáng lo ngại vì có thể cản trở sự phát triển khỏe mạnh của não.",
        },
        "answers": {
            "en": ["True", "False"],
            "fr": ["Vrai", "Faux"],
            "es": ["Verdadero", "Falso"],
            "ko": ["참", "거짓"],
            "ru": ["Верно", "Неверно"],
            "vi": ["Đúng", "Sai"],
        },
        "correct": 0,
    },
    # 18
    {
        "q": {
            "en": "Which of the following cardiovascular effects is NOT caused by vaping?",
            "fr": "Lequel de ces effets cardiovasculaires n'est PAS causé par le vapotage ?",
            "es": "¿Cuál de los siguientes efectos cardiovasculares NO es causado por el vapeo?",
            "ko": "다음 중 전자담배 사용(베이핑)으로 생기지 않는 심혈관 영향은 무엇인가요?",
            "ru": "Какой из сердечно-сосудистых эффектов НЕ вызывается вейпингом?",
            "vi": "Tác động tim mạch nào sau đây KHÔNG do vape gây ra?",
        },
        "answers": {
            "en": ["Increased heart rate", "Increased blood pressure",
                   "Increased risk of heart attacks", "Increased blood flow"],
            "fr": ["Augmentation du rythme cardiaque", "Augmentation de la tension artérielle",
                   "Augmentation du risque de crise cardiaque",
                   "Augmentation du débit sanguin"],
            "es": ["Aumento de la frecuencia cardíaca", "Aumento de la presión arterial",
                   "Mayor riesgo de infarto", "Aumento del flujo sanguíneo"],
            "ko": ["심박수 증가", "혈압 상승", "심장마비 위험 증가", "혈류량 증가"],
            "ru": ["Учащение сердцебиения", "Повышение артериального давления",
                   "Повышенный риск сердечного приступа", "Усиление кровотока"],
            "vi": ["Tăng nhịp tim", "Tăng huyết áp", "Tăng nguy cơ đau tim",
                   "Tăng lưu lượng máu"],
        },
        "correct": 3,
    },
    # 19
    {
        "q": {
            "en": "Why is avoiding smoking or vaping around others important?",
            "fr": "Pourquoi est-il important d'éviter de fumer ou de vapoter près des autres ?",
            "es": "¿Por qué es importante evitar fumar o vapear cerca de otras personas?",
            "ko": "다른 사람 주변에서 흡연이나 베이핑을 피하는 것이 중요한 이유는 무엇인가요?",
            "ru": "Почему важно не курить и не вейпить рядом с другими людьми?",
            "vi": "Tại sao việc tránh hút thuốc hoặc vape khi ở gần người khác lại quan trọng?",
        },
        "answers": {
            "en": [
                "It only affects the person smoking or vaping",
                "It can affect the air quality",
                "It improves the health of people nearby",
                "It has no effect on other people",
            ],
            "fr": [
                "Cela n'affecte que la personne qui fume ou vapote",
                "Cela peut affecter la qualité de l'air",
                "Cela améliore la santé des personnes à proximité",
                "Cela n'a aucun effet sur les autres",
            ],
            "es": [
                "Solo afecta a la persona que fuma o vapea",
                "Puede afectar la calidad del aire",
                "Mejora la salud de las personas cercanas",
                "No tiene ningún efecto en los demás",
            ],
            "ko": [
                "흡연하거나 베이핑하는 사람에게만 영향을 주기 때문에",
                "공기의 질에 영향을 줄 수 있기 때문에",
                "주변 사람들의 건강을 좋게 해 주기 때문에",
                "다른 사람에게는 아무 영향이 없기 때문에",
            ],
            "ru": [
                "Это влияет только на того, кто курит или вейпит",
                "Это может ухудшить качество воздуха",
                "Это улучшает здоровье людей рядом",
                "Это никак не влияет на других людей",
            ],
            "vi": [
                "Nó chỉ ảnh hưởng đến người hút hoặc vape",
                "Nó có thể ảnh hưởng đến chất lượng không khí",
                "Nó cải thiện sức khỏe của những người xung quanh",
                "Nó không ảnh hưởng gì đến người khác",
            ],
        },
        "correct": 1,
    },
    # 20
    {
        "q": {
            "en": "What is one possible effect of second-hand smoke on other people?",
            "fr": "Quel est un effet possible de la fumée secondaire sur les autres ?",
            "es": "¿Cuál es un posible efecto del humo de segunda mano en otras personas?",
            "ko": "간접흡연이 다른 사람에게 줄 수 있는 영향은 무엇인가요?",
            "ru": "Каков один из возможных эффектов пассивного курения для окружающих?",
            "vi": "Một tác động có thể có của khói thuốc thụ động đối với người khác là gì?",
        },
        "answers": {
            "en": ["Reduced lung inflammation", "Inflamed lungs", "Improved lung function",
                   "Increased lung capacity"],
            "fr": ["Une réduction de l'inflammation des poumons", "Des poumons enflammés",
                   "Une meilleure fonction pulmonaire", "Une capacité pulmonaire accrue"],
            "es": ["Menor inflamación pulmonar", "Pulmones inflamados",
                   "Mejor función pulmonar", "Mayor capacidad pulmonar"],
            "ko": ["폐 염증 감소", "폐에 염증이 생김", "폐 기능 향상", "폐활량 증가"],
            "ru": ["Уменьшение воспаления лёгких", "Воспаление лёгких",
                   "Улучшение функции лёгких", "Увеличение объёма лёгких"],
            "vi": ["Giảm viêm phổi", "Phổi bị viêm", "Cải thiện chức năng phổi",
                   "Tăng dung tích phổi"],
        },
        "correct": 1,
    },
]


# --- Fonts ---------------------------------------------------------------
# Drop .ttf files into the Assests folder (the first match that can show the
# current language is used):
#  - Headings and buttons: Press Start 2P
#  - Body text: Pixelify Sans (much easier to read)
#  - Korean (optional, pixel style): Galmuri11.ttf or DungGeunMo.ttf
# On your computer, if a language can't be shown by those files, the game looks
# for an installed system font. In the browser there are no system fonts, so
# every language needs a .ttf file in the Assests folder (Korean especially).
PRESS_START_FILES = ["PressStart2P-Regular.ttf", "PressStart2P.ttf"]
PIXELIFY_FILES = [
    "PixelifySans-SemiBold.ttf",
    "PixelifySans-Bold.ttf",
    "PixelifySans-Medium.ttf",
    "PixelifySans-Regular.ttf",
    "PixelifySans-VariableFont_wght.ttf",
]
LANGUAGE_FONT_FILES = {
    "ko": ["Galmuri11.ttf", "Galmuri11-Bold.ttf", "Galmuri9.ttf",
           "DungGeunMo.ttf", "NeoDunggeunmo.ttf"],
}
SYSTEM_FONT_NAMES = {
    "ko": ["malgungothic", "applesdgothicneo", "applegothic", "nanumgothic",
           "notosanscjkkr", "notosanskr", "notosanscjk"],
}
GENERIC_SYSTEM_FONTS = ["trebuchetms", "verdana", "arial", "segoeui", "helvetica",
                        "dejavusans", "notosans", "freesans", "arialunicodems", "unifont"]

# role: (size when using a .ttf file, size when using a system font)
FONT_SIZES = {"body": (32, 30), "question": (40, 36), "big": (40, 52), "button": (24, 28)}


class GameFont:
    """A pygame Font plus whether to anti-alias it (pixel fonts stay crisp)."""

    def __init__(self, font, smooth):
        self.font = font
        self.smooth = smooth

    def render(self, text, color):
        return self.font.render(text, self.smooth, color)

    def size(self, text):
        return self.font.size(text)

    def get_height(self):
        return self.font.get_height()


def supports(font, chars):
    """True if the font can draw every character (no empty 'missing glyph' boxes)."""
    white = (255, 255, 255)
    try:
        missing = font.render("\ue000", False, white)   # a character no text font has
        missing_look = (missing.get_size(), pygame.image.tostring(missing, "RGBA"))
        for char in chars:
            if char.isspace() or not char.isprintable():
                continue
            glyph = font.render(char, False, white)
            if (glyph.get_size(), pygame.image.tostring(glyph, "RGBA")) == missing_look:
                return False
    except Exception:
        return False
    return True


def chars_for(code):
    """Every character the given language needs (plus basic Latin for pet names)."""
    pieces = list(TEXT[code].values())
    for question in QUESTIONS:
        pieces.append(question["q"].get(code, ""))
        pieces.extend(question["answers"].get(code, []))
    return set("".join(pieces) + string.ascii_letters + string.digits)


def font_candidates(role, code):
    """Fonts to try, best first: ('file', path) or ('system', name)."""
    if role in ("body", "question"):
        pixel_files = PIXELIFY_FILES
    else:
        pixel_files = PRESS_START_FILES + PIXELIFY_FILES
    files = LANGUAGE_FONT_FILES.get(code, []) + pixel_files
    candidates = []
    for name in files:
        path = find_asset(name)
        if path:
            candidates.append(("file", path))
    if not ON_WEB:   # the browser has no system fonts
        candidates += [("system", name)
                       for name in SYSTEM_FONT_NAMES.get(code, []) + GENERIC_SYSTEM_FONTS]
    return candidates


def build_font(role, code, chars):
    file_size, system_size = FONT_SIZES[role]
    pixel_smooth = role in ("body", "question")
    for kind, value in font_candidates(role, code):
        try:
            if kind == "file":
                font, smooth = pygame.font.Font(value, file_size), pixel_smooth
            else:
                path = pygame.font.match_font(value, bold=True)
                if path is None:
                    continue
                font, smooth = pygame.font.Font(path, system_size), True
        except Exception:
            continue
        if supports(font, chars):
            return GameFont(font, smooth)
    print(f"No installed font can show every '{code}' character. "
          f"Add a font that supports it to {ASSETS} (see the notes at the top).")
    try:
        return GameFont(pygame.font.Font(None, system_size), True)
    except Exception:
        return GameFont(pygame.font.SysFont(None, system_size), True)


# One font per language name, so the language buttons always show their own script
language_fonts = {code: build_font("button", code, set(name)) for code, name in LANGUAGES.items()}

body_font = question_font = big_font = button_font = None   # set by apply_language()
language = "en"
_font_cache = {}


def apply_language(code):
    """Switch the game language and pick fonts that can display it."""
    global language, body_font, question_font, big_font, button_font
    if code not in _font_cache:
        chars = chars_for(code)
        _font_cache[code] = {role: build_font(role, code, chars) for role in FONT_SIZES}
    fonts = _font_cache[code]
    language = code
    body_font, question_font = fonts["body"], fonts["question"]
    big_font, button_font = fonts["big"], fonts["button"]


apply_language("en")


# --- Load everything ONCE ------------------------------------------------
def load(name, alpha=False):
    path = find_asset(name)
    if path is None:
        raise FileNotFoundError(f"Missing image: {ASSETS}{name}")
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


def fit(image, max_w, max_h):
    ratio = min(max_w / image.get_width(), max_h / image.get_height())
    new_size = (max(1, int(image.get_width() * ratio)), max(1, int(image.get_height() * ratio)))
    return pygame.transform.smoothscale(image, new_size)


def make_rect(width, height, center):
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    return rect


def load_pets():
    """Load the pet images and lay the selection thumbnails out evenly."""
    pet_files = [
        ("bunny", "bunny.png"),
        ("hamster", "hamster.png"),
        ("cat", "cat.png"),
        ("dog", "dog.png"),
    ]
    loaded = []
    for key, filename in pet_files:
        image = load(filename, alpha=True)
        loaded.append({
            "name": key,
            "thumb": fit(image, 9999, THUMB_HEIGHT),   # selection + intro screens
            "game": fit(image, *PET_MAX_SIZE),         # quiz screen
        })

    gap = 70
    center_y = 330
    total_width = sum(item["thumb"].get_width() for item in loaded) + gap * (len(loaded) - 1)
    left = (WIDTH - total_width) // 2
    for item in loaded:
        thumb_w, thumb_h = item["thumb"].get_size()
        item["pos"] = (left, center_y - thumb_h // 2)
        item["rect"] = pygame.Rect(left - 12, center_y - thumb_h // 2 - 12,
                                   thumb_w + 24, thumb_h + 24)
        left += thumb_w + gap
    return loaded


select_bg = pygame.transform.scale(load("select.png"), (WIDTH, HEIGHT))
house_bg = pygame.transform.scale(load("house.jpg"), (WIDTH, HEIGHT))
menu_bg = pygame.transform.scale(load("menu screen.jpg"), (WIDTH, HEIGHT))
heart_full = load("life.png", alpha=True)
heart_empty = load("no life.png", alpha=True)
pets = load_pets()

CENTER_X = WIDTH // 2

# Menu screen widgets
MENU_PANEL = make_rect(800, 520, (CENTER_X, HEIGHT // 2))
menu_buttons = {
    "play": make_rect(420, 70, (CENTER_X, 300)),
    "language": make_rect(420, 70, (CENTER_X, 400)),
    "quit": make_rect(420, 70, (CENTER_X, 500)),
}

# Language screen widgets: two columns of buttons
language_buttons = {}
for index, code in enumerate(LANGUAGES):
    column, row = index % 2, index // 2
    language_buttons[code] = make_rect(360, 66, (CENTER_X - 200 + column * 400, 270 + row * 85))
language_back_button = make_rect(260, 64, (CENTER_X, MENU_PANEL.bottom - 55))

# Pet selection screen widgets
select_back_button = make_rect(240, 60, (150, 50))
input_box = make_rect(460, 60, (CENTER_X, 520))
start_button = make_rect(440, 64, (CENTER_X, 610))
try:
    pygame.key.set_text_input_rect(input_box)
except Exception:
    pass

# Intro ("How to Play") screen widgets
INTRO_PANEL = make_rect(1200, 640, (CENTER_X, HEIGHT // 2))
intro_go_button = make_rect(340, 64, (INTRO_PANEL.right - 40 - 170, INTRO_PANEL.bottom - 50))
intro_back_button = make_rect(240, 64, (INTRO_PANEL.x + 40 + 120, INTRO_PANEL.bottom - 50))

# --- Game state ----------------------------------------------------------
state = "menu"  # "menu" | "language" | "select" | "intro" | "quiz" | "feedback" | "win" | "game_over"
selected_pet = None
pet_name = ""
ime_text = ""         # text still being composed by the keyboard (e.g. Korean)
pet = None
display_name = ""
life = STARTING_LIVES
heart_flash_index = -1
heart_flash_until = 0
wrong_index = -1          # which answer the player clicked (for the feedback screen)
pending_result = None     # what happens after the feedback screen: None, "win" or "game_over"
already_played = ONE_PLAY_ONLY and has_played_before()
remaining = []
current = None
bubble_rect = None
question_lines = []   # (surface, rect)
answer_items = []     # ([(surface, rect), ...], box_rect)
intro_lines = []      # (surface, (x, y))


# --- Helpers -------------------------------------------------------------
def t(key, **values):
    """Look up a text in the current language (falls back to English)."""
    text = TEXT.get(language, TEXT["en"]).get(key, TEXT["en"][key])
    return text.format(**values) if values else text


def translated(options):
    """Pick the current language from a {"en": ..., "fr": ...} dict."""
    return options.get(language, options["en"])


def wrap_text(text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def scale_surface(surface, scale):
    if scale == 1:
        return surface
    return pygame.transform.smoothscale(
        surface, (max(1, int(surface.get_width() * scale)), max(1, int(surface.get_height() * scale)))
    )


def render_fit(font, text, color, max_width):
    """Render text, shrinking it if it would be wider than max_width."""
    surface = font.render(text, color)
    if surface.get_width() > max_width:
        surface = scale_surface(surface, max_width / surface.get_width())
    return surface


def draw_panel(panel):
    pygame.draw.rect(screen, PANEL_COLOR, panel, border_radius=18)
    pygame.draw.rect(screen, TEXT_COLOR, panel, 4, border_radius=18)


def draw_button(button, label, color, enabled=True, font=None):
    font = font or button_font
    if enabled and button.collidepoint(pygame.mouse.get_pos()):
        color = tuple(min(255, c + 25) for c in color)
    pygame.draw.rect(screen, color, button, border_radius=12)
    pygame.draw.rect(screen, TEXT_COLOR, button, 3, border_radius=12)
    max_width = button.width - 24
    shadow = render_fit(font, label, TEXT_COLOR, max_width)   # dark shadow behind white text
    screen.blit(shadow, shadow.get_rect(center=(button.centerx + 2, button.centery + 2)))
    text = render_fit(font, label, "white", max_width)
    screen.blit(text, text.get_rect(center=button.center))


def draw_message(message):
    """Big message on a panel near the top (win / game over)."""
    rendered = [render_fit(big_font, line, TEXT_COLOR, 1100)
                for line in wrap_text(message, big_font, 1000)]
    spacing = big_font.get_height() + 10
    panel = pygame.Rect(0, 0, max(r.get_width() for r in rendered) + 80,
                        spacing * len(rendered) + 40)
    panel.center = (WIDTH // 2, 190)
    draw_panel(panel)
    for index, line_surface in enumerate(rendered):
        screen.blit(line_surface,
                    line_surface.get_rect(midtop=(panel.centerx, panel.y + 25 + index * spacing)))


def layout_question(question, scale):
    """Build the bubble and answer boxes. Returns (bubble, lines, answers, bottom_y)."""
    rendered = [scale_surface(question_font.render(text_line, TEXT_COLOR), scale)
                for text_line in wrap_text(translated(question["q"]), question_font,
                                           (COL_WIDTH - 70) / scale)]
    spacing = (question_font.get_height() + 8) * scale
    bubble = pygame.Rect(COL_LEFT, 40, COL_WIDTH, int(spacing * len(rendered)) + 40)
    bubble_lines = [
        (surface, surface.get_rect(midtop=(bubble.centerx, bubble.y + 20 + int(index * spacing))))
        for index, surface in enumerate(rendered)
    ]

    answers = []
    answer_spacing = (body_font.get_height() + 8) * scale
    top = bubble.bottom + 30
    for answer in translated(question["answers"]):
        rendered = [scale_surface(body_font.render(text_line, TEXT_COLOR), scale)
                    for text_line in wrap_text(answer, body_font, (COL_WIDTH - 50) / scale)]
        box = pygame.Rect(COL_LEFT, top, COL_WIDTH, int(answer_spacing * len(rendered)) + 24)
        answer_lines = [
            (surface, surface.get_rect(midtop=(box.centerx, box.y + 12 + int(index * answer_spacing))))
            for index, surface in enumerate(rendered)
        ]
        answers.append((answer_lines, box))
        top += box.height + 14
    return bubble, bubble_lines, answers, top


def next_question():
    """Pop the next question; shrink the text a little if a language runs long."""
    global current, bubble_rect, question_lines, answer_items
    current = QUESTIONS[remaining.pop()]
    for scale in (1.0, 0.85, 0.72, 0.6):
        layout = layout_question(current, scale)
        if layout[3] <= HEIGHT - 20:
            break
    bubble_rect, question_lines, answer_items, _ = layout


def start_quiz():
    global life, remaining, heart_flash_until
    life = STARTING_LIVES
    heart_flash_until = 0
    remaining = list(range(len(QUESTIONS)))
    random.shuffle(remaining)
    next_question()


def layout_intro(paragraphs, scale):
    text_x = INTRO_PANEL.x + 340
    max_width = INTRO_PANEL.right - 40 - text_x
    spacing = (body_font.get_height() + 10) * scale
    top = INTRO_PANEL.y + 110
    items = []
    for paragraph in paragraphs:
        for text_line in wrap_text(paragraph, body_font, max_width / scale):
            surface = scale_surface(body_font.render(text_line, TEXT_COLOR), scale)
            items.append((surface, (text_x, int(top))))
            top += spacing
        top += 22 * scale
    return items, top


def build_intro():
    """Wrap the how-to-play text once, personalised with the pet's name."""
    global intro_lines
    paragraphs = [t("intro_1", name=display_name),
                  t("intro_2", name=display_name, count=len(QUESTIONS)),
                  t("intro_3")]
    for scale in (1.0, 0.85, 0.72, 0.6):
        intro_lines, bottom = layout_intro(paragraphs, scale)
        if bottom <= INTRO_PANEL.bottom - 95:
            break


def open_pet_select():
    global selected_pet, pet_name, ime_text, state
    if already_played:
        return
    selected_pet, pet_name, ime_text, state = None, "", "", "select"


def try_start():
    """Go to the intro screen once a pet is picked (blank name -> the pet's own name)."""
    global pet, display_name, state
    if selected_pet is None:
        return
    pet = selected_pet
    display_name = pet_name.strip() or t("pet_" + pet["name"])
    build_intro()
    state = "intro"


def save_play_record(result):
    """Remember that this person has played (and how it went) in played.json."""
    record = {
        "name": display_name,
        "pet": pet["name"],
        "hearts": life,
        "result": result,
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    write_play_record(record)


def reset_played():
    """Teacher reset: forget that the game was played."""
    global already_played
    already_played = False
    clear_play_record()


def begin_quiz():
    global state, already_played
    start_quiz()
    if ONE_PLAY_ONLY:
        already_played = True
        save_play_record("started")
    state = "quiz"


def finish_game(result):
    """End the quiz with result 'win' or 'game_over' and record how it went."""
    global state
    state = result
    if ONE_PLAY_ONLY:
        save_play_record(result)


# --- Gotchi Pets title + certificate -------------------------------------
TITLE_TEXT = "Gotchi Pets"
TITLE_COLORS = [(255, 105, 180), (255, 170, 60), (110, 200, 90), (90, 170, 240), (180, 120, 230)]
GOLD = (255, 200, 60)
small_heart = fit(heart_full, 44, 44)
small_heart_empty = fit(heart_empty, 44, 44)
_title_cache = {}


def build_title_glyphs():
    """One outlined, enlarged surface per letter (cached per font)."""
    edge = 3
    estimate = sum(big_font.size(c)[0] + edge * 2 for c in TITLE_TEXT) * 2
    pixel = 2 if estimate <= 1000 else 1
    glyphs = []
    for index, char in enumerate(TITLE_TEXT):
        if char == " ":
            width = (big_font.size("M")[0] // 2 + edge * 2) * pixel
            glyphs.append(pygame.Surface((width, (big_font.get_height() + edge * 2) * pixel),
                                         pygame.SRCALPHA))
            continue
        base = big_font.render(char, TITLE_COLORS[index % len(TITLE_COLORS)])
        dark = big_font.render(char, TEXT_COLOR)
        surface = pygame.Surface((base.get_width() + edge * 2, base.get_height() + edge * 2),
                                 pygame.SRCALPHA)
        for dx in (0, edge, edge * 2):          # dark outline
            for dy in (0, edge, edge * 2):
                surface.blit(dark, (dx, dy))
        surface.blit(base, (edge, edge))
        glyphs.append(pygame.transform.scale(
            surface, (surface.get_width() * pixel, surface.get_height() * pixel)))
    return glyphs


def draw_sparkle(center, size, color):
    x, y = center
    k = size * 0.28
    points = [(x, y - size), (x + k, y - k), (x + size, y), (x + k, y + k),
              (x, y + size), (x - k, y + k), (x - size, y), (x - k, y - k)]
    pygame.draw.polygon(screen, color, points)


def draw_game_title(center_y=130):
    """Bouncy rainbow 'Gotchi Pets' logo on a cream banner with hearts and sparkles."""
    if id(big_font) not in _title_cache:
        _title_cache[id(big_font)] = build_title_glyphs()
    glyphs = _title_cache[id(big_font)]
    now = pygame.time.get_ticks()
    steps = [int(g.get_width() * 0.93) for g in glyphs]
    total = sum(steps)

    banner = pygame.Rect(0, 0, total + 170, glyphs[0].get_height() + 70)
    banner.center = (CENTER_X, center_y)
    shade = pygame.Surface(banner.size, pygame.SRCALPHA)
    pygame.draw.rect(shade, (*PANEL_COLOR, 235), shade.get_rect(), border_radius=28)
    screen.blit(shade, banner)
    pygame.draw.rect(screen, ACCENT_PINK, banner, 6, border_radius=28)
    pygame.draw.rect(screen, GOLD, banner.inflate(16, 16), 3, border_radius=34)

    x = CENTER_X - total // 2
    for index, (glyph, step) in enumerate(zip(glyphs, steps)):
        bounce = int(math.sin(now / 300 + index * 0.6) * 8)
        screen.blit(glyph, (x, center_y - glyph.get_height() // 2 + bounce))
        x += step

    for side, phase in ((banner.left + 42, 0), (banner.right - 42, 1.5)):
        bob = int(math.sin(now / 350 + phase) * 6)
        screen.blit(small_heart, small_heart.get_rect(center=(side, center_y + bob)))
    for pos, phase in (((banner.left + 20, banner.top + 6), 0), ((banner.right - 20, banner.top + 6), 1),
                       ((banner.left + 70, banner.bottom - 4), 2), ((banner.right - 70, banner.bottom - 4), 3)):
        draw_sparkle(pos, 7 + 6 * abs(math.sin(now / 400 + phase)), GOLD)


def draw_rosette(center, radius):
    """A little prize ribbon."""
    cx, cy = center
    for sign in (-1, 1):
        tail = [(cx + sign * 8, cy + 20), (cx + sign * 36, cy + 28), (cx + sign * 30, cy + 95),
                (cx + sign * 20, cy + 80), (cx + sign * 4, cy + 95)]
        pygame.draw.polygon(screen, (230, 90, 150), tail)
        pygame.draw.polygon(screen, TEXT_COLOR, tail, 3)
    for step in range(14):
        angle = step * math.tau / 14
        pygame.draw.circle(screen, GOLD, (int(cx + math.cos(angle) * radius),
                                          int(cy + math.sin(angle) * radius)), 13)
    pygame.draw.circle(screen, GOLD, center, radius)
    pygame.draw.circle(screen, TEXT_COLOR, center, radius, 3)
    pygame.draw.circle(screen, ACCENT_PINK, center, radius - 12)
    screen.blit(small_heart, small_heart.get_rect(center=center))


def draw_certificate():
    """Shown when every question is answered and the pet is still alive."""
    now = pygame.time.get_ticks()
    screen.blit(house_bg, (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((40, 20, 60, 150))
    screen.blit(veil, (0, 0))

    cert = make_rect(1040, 620, (CENTER_X, 350))
    pygame.draw.rect(screen, PANEL_COLOR, cert, border_radius=30)
    pygame.draw.rect(screen, ACCENT_PINK, cert, 10, border_radius=30)
    pygame.draw.rect(screen, GOLD, cert.inflate(-36, -36), 4, border_radius=22)
    inner = cert.inflate(-60, -60)
    for dot_x in range(inner.left, inner.right + 1, 20):      # dotted line
        pygame.draw.circle(screen, ACCENT_PINK, (dot_x, inner.top), 3)
        pygame.draw.circle(screen, ACCENT_PINK, (dot_x, inner.bottom), 3)
    for dot_y in range(inner.top, inner.bottom + 1, 20):
        pygame.draw.circle(screen, ACCENT_PINK, (inner.left, dot_y), 3)
        pygame.draw.circle(screen, ACCENT_PINK, (inner.right, dot_y), 3)
    for corner in ((cert.left + 45, cert.top + 45), (cert.right - 45, cert.top + 45),
                   (cert.left + 45, cert.bottom - 45), (cert.right - 45, cert.bottom - 45)):
        pygame.draw.circle(screen, PANEL_COLOR, corner, 30)
        bob = int(math.sin(now / 300 + corner[0]) * 4)
        screen.blit(small_heart, small_heart.get_rect(center=(corner[0], corner[1] + bob)))

    # Title with a little shadow
    title = render_fit(big_font, t("cert_title"), ACCENT_PINK, 760)
    shadow = render_fit(big_font, t("cert_title"), TEXT_COLOR, 760)
    title_rect = title.get_rect(center=(CENTER_X, cert.y + 60))
    screen.blit(shadow, shadow.get_rect(center=(title_rect.centerx + 3, title_rect.centery + 3)))
    screen.blit(title, title_rect)
    for side in (title_rect.left - 40, title_rect.right + 40):
        draw_sparkle((side, title_rect.centery), 8 + 6 * abs(math.sin(now / 400 + side)), GOLD)

    # "Proudly awarded to the loving parent of"
    top = cert.y + 105
    for text_line in wrap_text(t("cert_awarded"), body_font, 800):
        surface = render_fit(body_font, text_line, TEXT_COLOR, 820)
        screen.blit(surface, surface.get_rect(midtop=(CENTER_X, top)))
        top += body_font.get_height() + 6

    # Pet (gently bobbing), prize ribbon and sparkles
    bob = int(math.sin(now / 250) * 6)
    pet_image = pet["thumb"]
    screen.blit(pet_image, pet_image.get_rect(center=(CENTER_X, cert.y + 285 + bob)))
    draw_rosette((cert.left + 190, cert.y + 270), 48)
    for pos, phase in (((cert.right - 220, cert.y + 230), 0), ((cert.right - 170, cert.y + 320), 1.7),
                       ((cert.right - 250, cert.y + 340), 3.1)):
        draw_sparkle(pos, 9 + 7 * abs(math.sin(now / 450 + phase)), GOLD)

    # Pet name
    name = render_fit(big_font, display_name, ACCENT_PINK, 700)
    name_shadow = render_fit(big_font, display_name, TEXT_COLOR, 700)
    name_rect = name.get_rect(center=(CENTER_X, cert.y + 405))
    screen.blit(name_shadow, name_shadow.get_rect(center=(name_rect.centerx + 3, name_rect.centery + 3)))
    screen.blit(name, name_rect)
    pygame.draw.line(screen, GOLD, (name_rect.left - 20, name_rect.bottom + 8),
                     (name_rect.right + 20, name_rect.bottom + 8), 4)

    # Body message
    top = cert.y + 462
    for text_line in wrap_text(t("cert_body"), body_font, 800):
        surface = render_fit(body_font, text_line, TEXT_COLOR, 820)
        screen.blit(surface, surface.get_rect(midtop=(CENTER_X, top)))
        top += body_font.get_height() + 6

    # Hearts left + date
    row_y = cert.bottom - 50
    start_x = CENTER_X - (MAX_LIVES * 52) // 2 + 26
    for index in range(MAX_LIVES):
        heart = small_heart if index < life else small_heart_empty
        screen.blit(heart, heart.get_rect(center=(start_x + index * 52, row_y)))
    date_text = render_fit(body_font, datetime.now().strftime("%Y-%m-%d"), TEXT_COLOR, 200)
    screen.blit(date_text, date_text.get_rect(midright=(cert.right - 95, row_y)))

    # Click prompt under the certificate
    message = t("win_once" if ONE_PLAY_ONLY else "win", name=display_name)
    foot_shadow = render_fit(body_font, message, TEXT_COLOR, 1100)
    foot = render_fit(body_font, message, "white", 1100)
    foot_rect = foot.get_rect(center=(CENTER_X, 694))
    screen.blit(foot_shadow, foot_shadow.get_rect(center=(foot_rect.centerx + 2, foot_rect.centery + 2)))
    screen.blit(foot, foot_rect)


def draw_menu():
    screen.blit(menu_bg, (0, 0))
    draw_game_title()
    if SHOW_MENU_PANEL:
        draw_panel(MENU_PANEL)
    if SHOW_MENU_TITLE:
        title = render_fit(big_font, t("title"), TEXT_COLOR, MENU_PANEL.width - 40)
        screen.blit(title, title.get_rect(center=(CENTER_X, MENU_PANEL.y + 80)))
    draw_button(menu_buttons["play"], t("play"),
                (120, 120, 130) if already_played else (40, 140, 70), enabled=not already_played)
    draw_button(menu_buttons["language"], t("language"), (200, 80, 140))
    draw_button(menu_buttons["quit"], t("quit"), (110, 110, 140))

    if already_played:
        rendered = [render_fit(body_font, text_line, TEXT_COLOR, 1000)
                    for text_line in wrap_text(t("already_played"), body_font, 1000)]
        spacing = body_font.get_height() + 6
        banner = pygame.Rect(0, 0, max(r.get_width() for r in rendered) + 60,
                             spacing * len(rendered) + 30)
        banner.center = (CENTER_X, 610)
        draw_panel(banner)
        for index, surface in enumerate(rendered):
            screen.blit(surface, surface.get_rect(midtop=(banner.centerx, banner.y + 15 + index * spacing)))


def draw_language_screen():
    screen.blit(menu_bg, (0, 0))
    draw_panel(MENU_PANEL)
    title = render_fit(big_font, t("choose_language"), TEXT_COLOR, MENU_PANEL.width - 40)
    screen.blit(title, title.get_rect(center=(CENTER_X, MENU_PANEL.y + 80)))
    for code, button in language_buttons.items():
        color = (40, 140, 70) if code == language else (110, 110, 140)
        draw_button(button, LANGUAGES[code], color, font=language_fonts[code])
    draw_button(language_back_button, t("back"), (200, 80, 140))


def draw_bubble():
    pygame.draw.rect(screen, PANEL_COLOR, bubble_rect, border_radius=22)
    pygame.draw.rect(screen, TEXT_COLOR, bubble_rect, 3, border_radius=22)
    # Tail on the left side, pointing toward the pet
    left_x, tail_y = bubble_rect.left, bubble_rect.bottom - 45
    tail = [(left_x + 3, tail_y - 16), (left_x + 3, tail_y + 16), (left_x - 32, tail_y + 22)]
    pygame.draw.polygon(screen, PANEL_COLOR, tail)
    pygame.draw.line(screen, TEXT_COLOR, tail[0], tail[2], 3)
    pygame.draw.line(screen, TEXT_COLOR, tail[1], tail[2], 3)
    for line_surface, line_rect in question_lines:
        screen.blit(line_surface, line_rect)


def draw_hearts():
    """Hearts in the top-left; a newly earned heart gets a ring for a moment."""
    now = pygame.time.get_ticks()
    for index in range(MAX_LIVES):
        heart = heart_full if index < life else heart_empty
        heart_rect = heart.get_rect(center=(60 + index * 60, 50))
        screen.blit(heart, heart_rect)
        if index == heart_flash_index and now < heart_flash_until:
            radius = max(heart_rect.width, heart_rect.height) // 2 + 8
            pygame.draw.circle(screen, ACCENT_PINK, heart_rect.center, radius, 4)


def draw_select():
    screen.blit(select_bg, (0, 0))
    mouse = pygame.mouse.get_pos()
    draw_button(select_back_button, t("back"), (110, 110, 140))

    for option in pets:
        screen.blit(option["thumb"], option["pos"])
        if option is selected_pet:
            pygame.draw.rect(screen, ACCENT_PINK, option["rect"], 5, border_radius=12)
        elif option["rect"].collidepoint(mouse):
            pygame.draw.rect(screen, "white", option["rect"], 3, border_radius=12)

    pygame.draw.rect(screen, PANEL_COLOR, input_box, border_radius=10)
    pygame.draw.rect(screen, ACCENT_PINK if selected_pet else TEXT_COLOR,
                     input_box, 3, border_radius=10)
    if pet_name or ime_text:
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        typed = render_fit(body_font, pet_name + ime_text + cursor, TEXT_COLOR, input_box.width - 30)
    else:
        typed = render_fit(body_font, t("name_hint"), (130, 120, 145), input_box.width - 30)
    screen.blit(typed, typed.get_rect(midleft=(input_box.x + 15, input_box.centery)))

    ready = selected_pet is not None
    draw_button(start_button, t("next") if ready else t("pick_pet"),
                (200, 80, 140) if ready else (120, 120, 130), enabled=ready)


def draw_intro():
    screen.blit(house_bg, (0, 0))
    draw_panel(INTRO_PANEL)

    title = render_fit(big_font, t("how_to_play"), TEXT_COLOR, INTRO_PANEL.width - 80)
    screen.blit(title, title.get_rect(center=(INTRO_PANEL.centerx, INTRO_PANEL.y + 50)))

    thumb = pet["thumb"]
    thumb_rect = thumb.get_rect(center=(INTRO_PANEL.x + 170, INTRO_PANEL.centery - 20))
    screen.blit(thumb, thumb_rect)
    name_tag = render_fit(body_font, display_name, TEXT_COLOR, 280)
    screen.blit(name_tag, name_tag.get_rect(center=(thumb_rect.centerx, thumb_rect.bottom + 30)))

    for line_surface, position in intro_lines:
        screen.blit(line_surface, position)

    draw_button(intro_back_button, t("back"), (110, 110, 140))
    draw_button(intro_go_button, t("lets_go"), (40, 140, 70))


def draw_quiz_scene():
    screen.blit(house_bg, (0, 0))

    # Pet on the left with a name tag
    pet_image = pet["game"]
    pet_rect = pet_image.get_rect(center=PET_CENTER)
    screen.blit(pet_image, pet_rect)
    name_tag = render_fit(body_font, display_name, TEXT_COLOR, 320)
    tag_rect = name_tag.get_rect(center=(PET_CENTER[0], min(pet_rect.bottom + 34, HEIGHT - 30)))
    draw_panel(tag_rect.inflate(30, 18))
    screen.blit(name_tag, tag_rect)

    draw_hearts()

    if state in ("quiz", "feedback"):
        draw_bubble()
        mouse = pygame.mouse.get_pos()
        for index, (answer_lines, box) in enumerate(answer_items):
            if state == "feedback":
                if index == current["correct"]:
                    fill = (190, 235, 190)      # right answer = green
                elif index == wrong_index:
                    fill = (255, 190, 190)      # the answer they picked = red
                else:
                    fill = PANEL_COLOR
            else:
                fill = (255, 232, 243) if box.collidepoint(mouse) else PANEL_COLOR
            pygame.draw.rect(screen, fill, box, border_radius=10)
            thick = 6 if state == "feedback" and index == current["correct"] else 3
            pygame.draw.rect(screen, TEXT_COLOR, box, thick, border_radius=10)
            for line_surface, line_rect in answer_lines:
                screen.blit(line_surface, line_rect)

        if state == "feedback":
            lines = [render_fit(body_font, text_line, TEXT_COLOR, 390)
                     for text_line in wrap_text(t("wrong"), body_font, 390)]
            spacing = body_font.get_height() + 6
            panel = pygame.Rect(20, 100, 420, spacing * len(lines) + 30)
            draw_panel(panel)
            for index, surface in enumerate(lines):
                screen.blit(surface, surface.get_rect(midtop=(panel.centerx, panel.y + 15 + index * spacing)))
    elif state == "game_over":
        draw_message(t("game_over_once" if ONE_PLAY_ONLY else "game_over", name=display_name))


# --- Main loop -----------------------------------------------------------
async def main():
    global state, selected_pet, pet_name, ime_text, life, heart_flash_index, heart_flash_until
    global wrong_index, pending_result
    running = True
    while running:
        # 1) Events first, then draw
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Esc goes back to the menu from anywhere
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # With one play only, Esc can't be used to walk out of a quiz in progress
                if state != "menu" and not (ONE_PLAY_ONLY and state in ("quiz", "feedback")):
                    state = "menu"

            elif event.type == pygame.KEYDOWN and state == "menu":
                mods = pygame.key.get_mods()
                if (ALLOW_TEACHER_RESET and event.key == pygame.K_r
                        and mods & pygame.KMOD_CTRL and mods & pygame.KMOD_SHIFT):
                    reset_played()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    open_pet_select()

            # Typing the pet's name: TEXTINPUT handles accents, Cyrillic, Hangul, ...
            elif event.type == pygame.TEXTINPUT and state == "select":
                ime_text = ""
                for char in event.text:
                    if (len(pet_name) < MAX_NAME_LENGTH and char.isprintable()
                            and supports(body_font.font, char)):
                        pet_name += char

            elif event.type == pygame.TEXTEDITING and state == "select":
                ime_text = event.text

            elif event.type == pygame.KEYDOWN and state == "select":
                if event.key == pygame.K_RETURN:
                    try_start()
                elif event.key == pygame.K_BACKSPACE and not ime_text:
                    pet_name = pet_name[:-1]

            elif event.type == pygame.KEYDOWN and state == "intro":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    begin_quiz()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if state == "menu":
                    if menu_buttons["play"].collidepoint(event.pos):
                        open_pet_select()
                    elif menu_buttons["language"].collidepoint(event.pos):
                        state = "language"
                    elif menu_buttons["quit"].collidepoint(event.pos):
                        running = False

                elif state == "language":
                    for code, button in language_buttons.items():
                        if button.collidepoint(event.pos):
                            apply_language(code)
                    if language_back_button.collidepoint(event.pos):
                        state = "menu"

                elif state == "select":
                    if select_back_button.collidepoint(event.pos):
                        state = "menu"
                    elif start_button.collidepoint(event.pos):
                        try_start()
                    else:
                        for option in pets:
                            if option["rect"].collidepoint(event.pos):
                                selected_pet = option
                                break

                elif state == "intro":
                    if intro_go_button.collidepoint(event.pos):
                        begin_quiz()
                    elif intro_back_button.collidepoint(event.pos):
                        state = "select"   # keeps the chosen pet and typed name

                elif state == "quiz":
                    for index, (_, box) in enumerate(answer_items):
                        if box.collidepoint(event.pos):
                            if index == current["correct"]:
                                if life < MAX_LIVES:          # right answer = earn a heart
                                    life += 1
                                    heart_flash_index = life - 1
                                    heart_flash_until = pygame.time.get_ticks() + 1000
                                if not remaining:
                                    finish_game("win")         # pet is alive -> certificate
                                else:
                                    next_question()
                            else:
                                life -= 1                      # wrong answer = lose a heart
                                wrong_index = index
                                if life <= 0:
                                    pending_result = "game_over"
                                elif not remaining:
                                    pending_result = "win"
                                else:
                                    pending_result = None
                                state = "feedback"             # show the right answer first
                            break

                elif state == "feedback":
                    if pending_result:
                        finish_game(pending_result)
                    else:
                        next_question()
                        state = "quiz"

                else:  # win / game_over
                    if ONE_PLAY_ONLY:
                        state = "menu"
                    else:
                        open_pet_select()

        # 2) Draw
        if state == "menu":
            draw_menu()
        elif state == "language":
            draw_language_screen()
        elif state == "select":
            draw_select()
        elif state == "intro":
            draw_intro()
        elif state == "win":
            draw_certificate()
        else:
            draw_quiz_scene()

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())