# -*- coding: utf-8 -*-

from typing import Any, List, Optional
from dataclasses import dataclass

import vlc
import requests
from bs4 import BeautifulSoup


URL = 'https://radiopotok.ru/rock'
'https://rock.amgradio.ru/RusRock/'


@dataclass
class Station:
	id: int
	title: str
	stream_url: str

	def __str__(self):
		return self.title


class _StationParser:
	def get_station_list(self) -> List[Station]:
		''' Получить список станций '''

		response = requests.get(URL)
		if response.status_code != 200:
			raise ValueError('Invalid connection!')

		soup = BeautifulSoup(response.text, 'html.parser')

		output: List[Station] = []
		html_buttons = soup.find_all('button', attrs={'class': 'radio-card'})

		for btn in html_buttons:
			radio_id = int(btn['data-id'])
			radio_title = btn['aria-label'].split(maxsplit=1)[1]
			file_url = btn.find('script').text.strip().split('file')[1].split('"')[2].replace('\\', '')
			output.append(Station(id=radio_id,
			                      title=radio_title,
			                      stream_url=file_url))

		return output


class Radio:
	def __init__(self):
		self._now_station: Station = None

	@property
	def now_station(self) -> Optional[Station]:
		return self._now_station

	@now_station.setter
	def now_station(self, station: Station) -> None:
		if not isinstance(station, Station):
			raise AttributeError(f'{station} is not Station type')

		self._now_station = station

	def select_station(self, station: Station) -> None:
		''' Выбрать станцию '''

		self.now_station = station

	def play(self) -> None:
		''' Начать проигрывание '''

		self.stop()
		instance = vlc.Instance('--input-repeat=-1', '--fullscreen')
		self.player = instance.media_player_new()
		media = instance.media_new(self.now_station.stream_url)
		self.player.set_media(media)
		self.player.play()
		print(f'Сейчас играет "{self.now_station.title}"')

	def stop(self) -> None:
		if hasattr(self, 'player'):
			self.player.stop()

	def volume(self, value: int) -> None:
		if not hasattr(self, 'player'):
			return

		self.player.audio_set_volume(value)


class UI:
	def __init__(self):
		self._parser = _StationParser()
		self.stations = self._parser.get_station_list()

	def show_station_list(self) -> None:
		''' Отобразить список станций '''

		print('Select station:')
		i = 0
		while i <= len(self.stations):
			num_1 = f'{i+1}.'.ljust(4)
			station_1 = f'{num_1} {self.stations[i]}'.ljust(40)
			try:
				num_2 = f'{i+2}.'.ljust(4)
				station_2 = f'{num_2} {self.stations[i+1]}'
			except IndexError:
				station_2 = ''

			print(station_1 + station_2)
			i += 2

	def ask_station(self) -> int:
		''' Запросить номер станции у пользователя '''

		self.show_station_list()
		station_number = int(input('Введи номер станции: '))-1

		return self.stations[station_number]


class PathManager:
	def __init__(self, page_manager):
		self.memory: List[str] = ['menu',]
		self.page_manager = page_manager

	def forward(self, name: str) -> None:
		self.memory.append(name)
		finded_page = filter(lambda p: p.name==name, self.page_manager.pages)
		self.page_manager.current_page = next(finded_page)

	def back(self) -> None:
		if len(self.memory) > 1:
			self.memory = self.memory[:-1]

		last_page = self.memory[-1]
		self.memory = self.memory[:-1]
		self.forward(last_page)


@dataclass
class AskPage:
	name: str

	def show_text(self) -> None:
		pass

	def get_input(self) -> None:
		pass


class AskStation(AskPage):
	''' Страница выбора станции '''

	name = 'station'

	def __init__(self, path_manager: PathManager):
		super().__init__(self.name)
		self.path_manager = path_manager

		self.radio = Radio()
		self._parser = _StationParser()
		self.stations = self._parser.get_station_list()

	def show_text(self) -> None:
		''' Отобразить список станций '''

		print('Select station:')
		i = 0
		while i <= len(self.stations):
			num_1 = f'{i+1}.'.ljust(4)
			station_1 = f'{num_1} {self.stations[i]}'.ljust(40)
			try:
				num_2 = f'{i+2}.'.ljust(4)
				station_2 = f'{num_2} {self.stations[i+1]}'
			except IndexError:
				station_2 = ''

			print(station_1 + station_2)
			i += 2
		print()

	def get_input(self) -> int:
		''' Запросить номер станции у пользователя '''

		self.show_text()
		station_number = int(input('Введи номер станции: '))-1

		return self.stations[station_number]

	def run_callback(self, station: Station) -> None:
		''' Запустить радиостанцию '''

		self.radio.stop()
		self.radio.select_station(station)
		self.radio.play()
		self.path_manager.back()


class AskMenu(AskPage):
	''' Главная страница '''

	name = 'menu'

	def __init__(self, path_manager: PathManager):
		super().__init__(self.name)

		self.path_manager = path_manager
		self.callbacks = [
			lambda: exit(),
			lambda: self.path_manager.forward('station'),
			lambda: self.path_manager.forward('volume_settings')]

	def show_text(self) -> None:
		print('1. Выбрать станцию\n2. Настройка громкости\n0. Выход', end='\n'*2)

	def get_input(self) -> int:
		self.show_text()
		selected_element = int(input('Введи номер строки: '))

		return selected_element

	def run_callback(self, index: int) -> None:
		''' Запустить выбранный callback '''

		self.callbacks[index]()


class AskManager:
	def __init__(self):
		self.__asks: AskPage = []
		self.path_manager = PathManager(self)

		self.add_ask(AskMenu(path_manager=self.path_manager))
		self.add_ask(AskStation(path_manager=self.path_manager))

		self.__current_page = self.__asks[0]

	@property
	def current_page(self) -> AskPage:
		return self.__current_page

	@current_page.setter
	def current_page(self, page: AskPage) -> None:
		if not isinstance(page, AskPage):
			raise AttributeError(f'{page} is not AskPage type')

		self.__current_page = page

	@property
	def pages(self) -> List[AskPage]:
		return self.__asks

	def add_ask(self, new_ask: AskPage) -> None:
		self.__asks.append(new_ask)

	def get_input(self) -> Any:
		return self.current_page.get_input()


class Controller:
	def __init__(self):
		self.view = AskManager()

	def mainloop(self) -> None:
		while True:
			inp = self.view.get_input()
			self.view.current_page.run_callback(inp)


if __name__ == '__main__':
	controller = Controller()
	controller.mainloop()
