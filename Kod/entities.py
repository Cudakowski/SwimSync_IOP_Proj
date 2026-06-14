import random
import string
from typing import Any, Dict
from datetime import datetime

class ProfilUzytkownika:
    def __init__(self, user_id: int = 0):
        self.user_id: int = user_id
        self.instruktor_id: int = 0
        self.wiek: int = 0
        self.poziom_zaawansowania: str = ""
        self.kwalifikacje: str = ""
        self.email: str = ""
        self.haslo_hash: str = ""

    def znajdzLubUtworz(self, user_id: int) -> 'ProfilUzytkownika':
        self.user_id = user_id
        return self

    def znajdz(self, instruktor_id: int) -> 'ProfilUzytkownika':
        self.instruktor_id = instruktor_id
        return self

    def set_attributes(self, wiek: int, poziom: str) -> bool:
        self.wiek = wiek
        self.poziom_zaawansowania = poziom
        return True

    def set_description(self, kwalifikacje_text: str) -> bool:
        self.kwalifikacje = kwalifikacje_text
        return True

    def generate_temp_password(self) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProfilUzytkownika':
        obj = cls()
        obj.__dict__.update(data)
        return obj


class TorBasenowy:
    def __init__(self, tor_id: int = 0, max_pojemnosc: int = 6):
        self.tor_id: int = tor_id
        self.max_pojemnosc: int = max_pojemnosc

    def find(self, tor_id: int) -> 'TorBasenowy':
        self.tor_id = tor_id
        return self

    def set_max_capacity(self, nowa_pojemnosc: int) -> bool:
        self.max_pojemnosc = nowa_pojemnosc
        return True

    def pobierzLimit(self) -> int:
        return self.max_pojemnosc

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict) -> 'TorBasenowy':
        return cls(data.get('tor_id', 0), data.get('max_pojemnosc', 6))


class GrupaPlywacka:
    def __init__(self, dane_grupy_dict: dict):
        self.grupa_id: int = dane_grupy_dict.get('grupa_id', 0)
        self.tor_id: int = dane_grupy_dict.get('tor_id', 0)
        self.max_wielkosc: int = dane_grupy_dict.get('max_wielkosc', 10)
        self.wiek: int = dane_grupy_dict.get('wiek', 0)
        self.poziom: str = dane_grupy_dict.get('poziom', "")

    def sprawdzWolneMiejsca(self, limit_toru: int, zapisani_kursanci: int) -> int:
        bezpieczny_limit = min(self.max_wielkosc, limit_toru)
        return bezpieczny_limit - zapisani_kursanci

    def sprawdzMiejsca(self, zapisani_kursanci: int) -> bool:
        return zapisani_kursanci < self.max_wielkosc

    def zwolnijMiejsce(self) -> bool:
        return True

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict) -> 'GrupaPlywacka':
        return cls(data)


class Harmonogram:
    def dodajBlokadeInstruktora(self, instruktor_id: int, start_date: datetime, end_date: datetime, konflikt: bool) -> dict:
        return {
            "instruktor_id": instruktor_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "konflikt": konflikt
        }


class Rezerwacja:
    def __init__(self, kursant_id: int, zajecia_id: int, rezerwacja_id: int = 0, status: str = "aktywna"):
        self.rezerwacja_id: int = rezerwacja_id
        self.kursant_id: int = kursant_id
        self.zajecia_id: int = zajecia_id
        self.status: str = status

    def zmienStatus(self, nowy_status: str) -> bool:
        self.status = nowy_status
        return True

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict) -> 'Rezerwacja':
        return cls(data['kursant_id'], data['zajecia_id'], data.get('rezerwacja_id', 0), data.get('status', 'aktywna'))


class Obecnosc:
    def __init__(self, uzytkownik_id: int, zajecia_id: int, status: str):
        self.uzytkownik_id: int = uzytkownik_id
        self.zajecia_id: int = zajecia_id
        self.status: str = status

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict) -> 'Obecnosc':
        return cls(data['uzytkownik_id'], data['zajecia_id'], data['status'])


class Raport:
    def __init__(self):
        self.dane = {}

    def agregujPopularnosc(self, dane_frekwencji: list) -> dict:
        for obecnosc in dane_frekwencji:
            self.dane[obecnosc['zajecia_id']] = self.dane.get(obecnosc['zajecia_id'], 0) + 1
        return self.dane

    def obliczPrzepracowaneGodziny(self, dane_zajec: list) -> dict:
        for zajecia in dane_zajec:
            inst_id = zajecia.get('instruktor_id')
            self.dane[inst_id] = self.dane.get(inst_id, 0) + 1
        return self.dane

    def generujPlik(self) -> str:
        return f"Raport_wygenerowany_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"