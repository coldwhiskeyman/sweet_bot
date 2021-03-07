import json
import logging
from io import BytesIO
from random import randint

import requests
from pony.orm import db_session
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

import handlers
import settings
from models import UserState

log = logging.getLogger('bot')


def configure_logging():
    """Настройка логгирования"""
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M'))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class Bot:
    """
    Бот vk.com для просмотра ассортимента кондитерской лавки.
    """
    def __init__(self, group_id: int, token: str):
        """
        :param group_id: group id из группы VK
        :param token: секретный токен
        """
        self.group_id = group_id
        self.token = token
        self.vk = VkApi(token=token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()
        self.user_states = {}

    def run(self):
        """Запуск бота"""
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('Ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        Обрабатывает введенные данные
        :param event: VkBotMessageEvent object
        """
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.object.message['peer_id']
            current_section = UserState.get_current_section(user_id)
            text = event.object.message['text']
            self.check_choice(user_id, current_section, text)
        else:
            log.debug(event.type)
            return

    def check_choice(self, user_id: int, current_section: str, text: str):
        """
        Проверка выбора из вариантов кнопок клавиатуры
        :param user_id: id пользователя
        :param current_section: название текущего раздела
        :param text: текст сообщения
        """
        if current_section == 'root':
            msg_data = handlers.root_choice_handler(text, user_id)
            if msg_data:
                text_to_send = msg_data[0]
                keyboard = msg_data[1]
                self.send_text(text_to_send, user_id, keyboard)
                return
        else:
            msg_data = handlers.section_choice_handler(text, current_section)
            if msg_data:
                text_to_send = msg_data[0]
                image = msg_data[1]
                self.send_image(image, user_id)
                self.send_text(text_to_send, user_id)
                return
        self.check_intents(user_id, text)

    def check_intents(self, user_id: int, text: str):
        """
        Проверка возможных запросов
        :param user_id: id пользователя
        :param text: текст сообщения
        """
        msg_data = handlers.intents_handler(text, user_id)
        if msg_data:
            text_to_send = msg_data[0]
            keyboard = msg_data[1]
            self.send_text(text_to_send, user_id, keyboard)
        else:
            keyboard = json.dumps(self.get_keyboard('root'))
            UserState.set_current_section(user_id, 'root')
            self.send_text(settings.DEFAULT_ANSWER, user_id, keyboard)

    def send_text(self, text_to_send: str, user_id: int, keyboard: str = None):
        """
        Отправка сообщения в VK
        :param text_to_send: текст отправляемого сообщения
        :param user_id: id пользователя
        :param keyboard: JSON-строка, представляющая клавиатуру
        """
        self.api.messages.send(
            keyboard=keyboard,
            message=text_to_send,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id
        )

    def send_image(self, image: BytesIO, user_id: int):
        """
        Отправка изображения в VK
        :param image: файловый объект картинки
        :param user_id: id пользователя
        """
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'

        self.api.messages.send(
            attachment=attachment,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id
        )


if __name__ == "__main__":
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()
