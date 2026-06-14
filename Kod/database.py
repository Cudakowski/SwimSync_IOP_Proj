import os
import json
import random
from typing import Tuple, List, Optional
from datetime import datetime, timedelta
from entities import Rezerwacja, GrupaPlywacka, TorBasenowy, ProfilUzytkownika, Obecnosc

class BazaDanych:
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = storage_dir
        self._ensure_storage()

    def _ensure_storage(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        files = ['uzytkownicy.json', 'tory.json', 'grupy.json', 'zajecia.json', 'rezerwacje.json', 'obecnosci.json', 'blokady.json']
        for f in files:
            path = os.path.join(self.storage_dir, f)
            if not os.path.exists(path):
                self._write_file(f, [])

    def _read_file(self, filename: str) -> list:
        with open(os.path.join(self.storage_dir, filename), 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_file(self, filename: str, data: list) -> None:
        with open(os.path.join(self.storage_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def save(self, obiekt: object) -> bool:
        if isinstance(obiekt, ProfilUzytkownika):
            data = self._read_file('uzytkownicy.json')
            data = [u for u in data if u.get('user_id') != obiekt.user_id]
            data.append(obiekt.to_dict())
            self._write_file('uzytkownicy.json', data)
        elif isinstance(obiekt, TorBasenowy):
            data = self._read_file('tory.json')
            data = [t for t in data if t.get('tor_id') != obiekt.tor_id]
            data.append(obiekt.to_dict())
            self._write_file('tory.json', data)
        elif isinstance(obiekt, Rezerwacja):
            data = self._read_file('rezerwacje.json')
            data = [r for r in data if r.get('rezerwacja_id') != obiekt.rezerwacja_id]
            data.append(obiekt.to_dict())
            self._write_file('rezerwacje.json', data)
        return True

    def query(self, email: str) -> dict:
        users = self._read_file('uzytkownicy.json')
        for u in users:
            if u.get('email') == email:
                return u
        return {}

    def save_password_hash(self, user_id: int, hash_hasla: str) -> bool:
        users = self._read_file('uzytkownicy.json')
        for u in users:
            if u.get('user_id') == user_id:
                u['haslo_hash'] = hash_hasla
                break
        self._write_file('uzytkownicy.json', users)
        return True

    def pobierzAktywneGrupyDlaToru(self, tor_id: int) -> list:
        grupy_data = self._read_file('grupy.json')
        return [GrupaPlywacka.from_dict(g) for g in grupy_data if g.get('tor_id') == tor_id]

    def insert(self, obiekt: object) -> int:
        new_id = random.randint(1000, 9999)
        if isinstance(obiekt, GrupaPlywacka):
            obiekt.grupa_id = new_id
            data = self._read_file('grupy.json')
            data.append(obiekt.to_dict())
            self._write_file('grupy.json', data)
        elif isinstance(obiekt, Rezerwacja):
            obiekt.rezerwacja_id = new_id
            data = self._read_file('rezerwacje.json')
            data.append(obiekt.to_dict())
            self._write_file('rezerwacje.json', data)
        return new_id

    def pobierzZaplanowaneZajecia(self, instruktor_id: int, start_date: datetime, end_date: datetime) -> list:
        zajecia = self._read_file('zajecia.json')
        wynik = []
        for z in zajecia:
            czas_zajec = datetime.fromisoformat(z['czas'])
            if z.get('instruktor_id') == instruktor_id and start_date <= czas_zajec <= end_date:
                wynik.append(z)
        return wynik

    def pobierzWszystkieZajeciaDlaCyklu(self, cykl_id: int) -> list:
        zajecia = self._read_file('zajecia.json')
        return [z for z in zajecia if z.get('cykl_id') == cykl_id]

    def pobierzRezerwacjeIZajecia(self, rezerwacja_id: int) -> Tuple[Optional[Rezerwacja], Optional[datetime]]:
        rezerwacje = self._read_file('rezerwacje.json')
        rez_data = next((r for r in rezerwacje if r.get('rezerwacja_id') == rezerwacja_id), None)
        if not rez_data:
            return None, None
        
        rez = Rezerwacja.from_dict(rez_data)
        zajecia = self._read_file('zajecia.json')
        zaj_data = next((z for z in zajecia if z.get('zajecia_id') == rez.zajecia_id), None)
        
        if zaj_data:
            return rez, datetime.fromisoformat(zaj_data['czas'])
        return rez, None

    def pobierzNakladajaceSieZajecia(self, tor_id: int, instruktor_id: int, czas: datetime) -> list:
        zajecia = self._read_file('zajecia.json')
        konflikty = []
        for z in zajecia:
            czas_zajec = datetime.fromisoformat(z['czas'])
            if czas_zajec == czas and (z.get('tor_id') == tor_id or z.get('instruktor_id') == instruktor_id):
                konflikty.append(z)
        return konflikty

    def zapiszZajeciaWPlanu(self, dane: dict) -> bool:
        if isinstance(dane.get('czas'), datetime):
            dane['czas'] = dane['czas'].isoformat()
        if 'zajecia_id' not in dane:
            dane['zajecia_id'] = random.randint(1000, 9999)
            
        zajecia = self._read_file('zajecia.json')
        zajecia.append(dane)
        self._write_file('zajecia.json', zajecia)
        return True

    def pobierzZapisanychUczestnikow(self, zajecia_id: int) -> list:
        rezerwacje = self._read_file('rezerwacje.json')
        return [r['kursant_id'] for r in rezerwacje if r.get('zajecia_id') == zajecia_id and r.get('status') == 'aktywna']

    def bulk_insert(self, kolekcja_obiektow: list) -> bool:
        obecnosci = self._read_file('obecnosci.json')
        for ob in kolekcja_obiektow:
            obecnosci.append(ob.to_dict())
        self._write_file('obecnosci.json', obecnosci)
        return True

    def pobierzZarejestrowaneObecnosci(self, parametry_dict: dict) -> list:
        # Można tu dodać filtrowanie po parametrach
        return self._read_file('obecnosci.json')

    def pobierzOdbyteZajecia(self, miesiac: int) -> list:
        zajecia = self._read_file('zajecia.json')
        wynik = []
        for z in zajecia:
            czas_zajec = datetime.fromisoformat(z['czas'])
            if czas_zajec.month == miesiac and czas_zajec < datetime.now():
                wynik.append(z)
        return wynik

    def pobierzAdresyEmail(self, grupa_docelowa: str) -> list:
        # Uproszczenie: zwracamy maile wszystkich kursantów
        users = self._read_file('uzytkownicy.json')
        return [u['email'] for u in users if u.get('email')]

    def pobierzZajeciaJutro(self) -> list:
        zajecia = self._read_file('zajecia.json')
        jutro_start = datetime.now() + timedelta(days=1)
        jutro_start = jutro_start.replace(hour=0, minute=0, second=0, microsecond=0)
        jutro_end = jutro_start + timedelta(days=1)
        
        wynik = []
        for z in zajecia:
            czas_zajec = datetime.fromisoformat(z['czas'])
            if jutro_start <= czas_zajec < jutro_end:
                wynik.append(z)
        return wynik

    def pobierzUczestnikow(self, zajecia_id: int) -> list:
        return self.pobierzZapisanychUczestnikow(zajecia_id)

    def pobierzZainteresowanych(self, zajecia_id: int) -> Tuple[dict, list]:
        zajecia = self._read_file('zajecia.json')
        zaj = next((z for z in zajecia if z.get('zajecia_id') == zajecia_id), None)
        
        instruktor = {}
        if zaj:
            users = self._read_file('uzytkownicy.json')
            instruktor = next((u for u in users if u.get('instruktor_id') == zaj.get('instruktor_id')), {})
            
        uczestnicy = self.pobierzZapisanychUczestnikow(zajecia_id)
        return instruktor, uczestnicy
        
    def zapiszBlokade(self, blokada_dict: dict) -> bool:
        blokady = self._read_file('blokady.json')
        blokady.append(blokada_dict)
        self._write_file('blokady.json', blokady)
        return True
    
    def pobierzTor(self, tor_id: int) -> TorBasenowy:
        tory = self._read_file('tory.json')
        tor_data = next((t for t in tory if t.get('tor_id') == tor_id), None)
        if tor_data:
            return TorBasenowy.from_dict(tor_data)
        # Fallback
        t = TorBasenowy(tor_id, 6)
        self.save(t)
        return t
        
    def pobierzGrupe(self, grupa_id: int) -> GrupaPlywacka:
        grupy = self._read_file('grupy.json')
        g_data = next((g for g in grupy if g.get('grupa_id') == grupa_id), None)
        if g_data:
            return GrupaPlywacka.from_dict(g_data)
        raise ValueError("Grupa nie istnieje.")