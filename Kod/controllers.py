from typing import List
from datetime import datetime, timedelta
from database import BazaDanych
from entities import GrupaPlywacka, Obecnosc, ProfilUzytkownika, TorBasenowy, Raport, Rezerwacja, Harmonogram

class PowiadomieniaController:
    def __init__(self, db: BazaDanych):
        self.db = db

    def zglosKoniecznoscZastepstwa(self, instruktor_id: int, lista_zajec: list) -> None:
        pass # Wysłanie logów do systemu

    def broadcastMessage(self, grupa_docelowa: str, tresc: str) -> None:
        lista_maili = self.db.pobierzAdresyEmail(grupa_docelowa)
        for email in lista_maili:
            self._send_email(email, tresc)

    def _send_email(self, email: str, tresc: str) -> bool:
        return True

    def cronJob_sprawdzHarmonogram(self) -> None:
        lista_zajec_jutro = self.db.pobierzZajeciaJutro()
        for zajecia in lista_zajec_jutro:
            uczestnicy = self.db.pobierzUczestnikow(zajecia['zajecia_id'])
            for u_id in uczestnicy:
                self._wyslijPowiadomienie(u_id, "Przypomnienie: Zajęcia jutro o " + zajecia['czas'])

    def _wyslijPowiadomienie(self, user_id: int, msg: str) -> None:
        print(f"Powiadomienie PUSH do Usera {user_id}: {msg}")

    def trigger_zmianaHarmonogramu(self, zajecia_id: int) -> None:
        instruktor, uczestnicy = self.db.pobierzZainteresowanych(zajecia_id)


class ZarzadzanieController:
    def __init__(self, db: BazaDanych, powiadomienia_ctrl: PowiadomieniaController):
        self.db = db
        self.powiadomienia_ctrl = powiadomienia_ctrl

    def aktualizujProfil(self, user_id: int, wiek: int, poziom: str) -> None:
        profil = ProfilUzytkownika(user_id)
        profil.set_attributes(wiek, poziom)
        self.db.save(profil)

    def aktualizujOpisInstruktora(self, instruktor_id: int, kwalifikacje_text: str) -> None:
        profil = ProfilUzytkownika()
        profil.znajdz(instruktor_id)
        profil.set_description(kwalifikacje_text)
        self.db.save(profil)

    def szukajKonta(self, email: str) -> dict:
        return self.db.query(email)

    def generujNoweHaslo(self, user_id: int) -> str:
        profil = ProfilUzytkownika(user_id)
        nowe_haslo = profil.generate_temp_password()
        self.db.save_password_hash(user_id, nowe_haslo)
        return nowe_haslo

    def zaktualizujPojemnosc(self, tor_id: int, nowa_pojemnosc: int) -> None:
        tor = self.db.pobierzTor(tor_id)
        lista_grup = self.db.pobierzAktywneGrupyDlaToru(tor_id)
        
        if not self._sprawdzWielkoscGrup(lista_grup, nowa_pojemnosc):
            raise ValueError("Istnieje grupa, której liczba kursantów przekracza nową pojemność toru.")
        
        tor.set_max_capacity(nowa_pojemnosc)
        self.db.save(tor)

    def _sprawdzWielkoscGrup(self, lista_grup: list, nowa_pojemnosc: int) -> bool:
        for grupa in lista_grup:
            zapisani = len(self.db.pobierzZapisanychUczestnikow(grupa.grupa_id)) # symulacja dla grupy
            if zapisani > nowa_pojemnosc:
                return False
        return True

    def stworzNowaGrupe(self, dane_grupy_dict: dict) -> int:
        grupa = GrupaPlywacka(dane_grupy_dict)
        return self.db.insert(grupa)

    def zablokujTermin(self, instruktor_id: int, start_date: datetime, end_date: datetime) -> None:
        lista_zajec = self.db.pobierzZaplanowaneZajecia(instruktor_id, start_date, end_date)
        harmonogram = Harmonogram()
        
        if len(lista_zajec) > 0:
            self.powiadomienia_ctrl.zglosKoniecznoscZastepstwa(instruktor_id, lista_zajec)
            blokada = harmonogram.dodajBlokadeInstruktora(instruktor_id, start_date, end_date, True)
            self.db.zapiszBlokade(blokada)
            raise UserWarning("Zgłoszono konieczność zastępstwa.")
        else:
            blokada = harmonogram.dodajBlokadeInstruktora(instruktor_id, start_date, end_date, False)
            self.db.zapiszBlokade(blokada)


class HarmonogramController:
    def __init__(self, db: BazaDanych, powiadomienia_ctrl: PowiadomieniaController):
        self.db = db
        self.powiadomienia_ctrl = powiadomienia_ctrl

    def sprawdzIZapiszHarmonogram(self, dane_zajec_dict: dict) -> None:
        konflikty = self.db.pobierzNakladajaceSieZajecia(
            dane_zajec_dict['tor_id'], 
            dane_zajec_dict['instruktor_id'], 
            dane_zajec_dict['czas']
        )
        if len(konflikty) > 0:
            self._wykrytoKonflikt()
        else:
            self.db.zapiszZajeciaWPlanu(dane_zajec_dict)

    def _wykrytoKonflikt(self) -> None:
        raise ValueError("System technicznie uniemożliwia utworzenie konfliktu!")

    def trigger_zmianaHarmonogramu(self, zajecia_id: int) -> None:
        self.powiadomienia_ctrl.trigger_zmianaHarmonogramu(zajecia_id)


class RezerwacjeController:
    def __init__(self, db: BazaDanych):
        self.db = db

    def procesujZapis(self, kursant_id: int, zajecia_id: int, grupa_id: int) -> None:
        grupa = self.db.pobierzGrupe(grupa_id)
        tor = self.db.pobierzTor(grupa.tor_id)
        zapisani = len(self.db.pobierzZapisanychUczestnikow(zajecia_id))
        
        dostepne_miejsca = grupa.sprawdzWolneMiejsca(tor.pobierzLimit(), zapisani)
        
        if dostepne_miejsca > 0:
            rezerwacja = Rezerwacja(kursant_id, zajecia_id)
            self.db.insert(rezerwacja)
        else:
            raise ValueError("Brak wolnych miejsc w grupie.")

    def zapiszNaWieleZajec(self, kursant_id: int, cykl_id: int, grupa_id: int) -> None:
        lista_zajec = self.db.pobierzWszystkieZajeciaDlaCyklu(cykl_id)
        grupa = self.db.pobierzGrupe(grupa_id)
        
        for zajecia in lista_zajec:
            zapisani = len(self.db.pobierzZapisanychUczestnikow(zajecia['zajecia_id']))
            if grupa.sprawdzMiejsca(zapisani):
                rezerwacja = Rezerwacja(kursant_id, zajecia['zajecia_id'])
                self.db.insert(rezerwacja)

    def procesujAnulowanie(self, rezerwacja_id: int) -> None:
        rezerwacja, data_zajec = self.db.pobierzRezerwacjeIZajecia(rezerwacja_id)
        if not rezerwacja or not data_zajec:
            raise ValueError("Nie znaleziono rezerwacji.")
            
        czas_do_zajec = data_zajec - datetime.now()
        
        if czas_do_zajec >= timedelta(hours=24):
            rezerwacja.zmienStatus("anulowana")
            self.db.save(rezerwacja)
        else:
            raise ValueError("Zbyt mało czasu do zajęć (mniej niż 24h).")


class ObecnoscController:
    def __init__(self, db: BazaDanych):
        self.db = db
        self._kolekcja: List[Obecnosc] = []

    def zapiszFrekwencje(self, zajecia_id: int, lista_obecnych_ids: list) -> None:
        lista_wszystkich = self.db.pobierzZapisanychUczestnikow(zajecia_id)
        
        obecni = set(lista_obecnych_ids)
        wszyscy = set(lista_wszystkich)
        nieobecni = wszyscy - obecni
        
        self._przygotujPustaKolekcje()
        
        for u_id in obecni:
            self._dodajDoKolekcji(Obecnosc(u_id, zajecia_id, 'obecny'))
            
        for u_id in nieobecni:
            self._dodajDoKolekcji(Obecnosc(u_id, zajecia_id, 'nieobecny'))
            
        self.db.bulk_insert(self._kolekcja)

    def _przygotujPustaKolekcje(self) -> None:
        self._kolekcja = []

    def _dodajDoKolekcji(self, obecnosc: Obecnosc) -> None:
        self._kolekcja.append(obecnosc)


class RaportController:
    def __init__(self, db: BazaDanych):
        self.db = db

    def utworzZestawienie(self, typ_raportu: str, parametry_dict: dict) -> str:
        raport = Raport()
        if typ_raportu == "Frekwencja Grup":
            dane_frekwencji = self.db.pobierzZarejestrowaneObecnosci(parametry_dict)
            raport.agregujPopularnosc(dane_frekwencji)
        elif typ_raportu == "Godziny Instruktorów":
            dane_zajec = self.db.pobierzOdbyteZajecia(parametry_dict.get('miesiac', 1))
            raport.obliczPrzepracowaneGodziny(dane_zajec)
            
        plik = raport.generujPlik()
        return plik