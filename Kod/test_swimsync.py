import os
import pytest
from datetime import datetime, timedelta


from entities import ProfilUzytkownika, TorBasenowy, GrupaPlywacka, Rezerwacja, Obecnosc, Harmonogram, Raport
from database import BazaDanych
from controllers import (
    PowiadomieniaController, ZarzadzanieController, 
    HarmonogramController, RezerwacjeController, 
    ObecnoscController, RaportController
)
from boundaries import InterfejsWebowy, PortalZapisow, SystemAplikacja, SystemCron


# Przygotowanie środowiska testowego

@pytest.fixture
def temp_db(tmp_path):
    """Tworzy instancję bazy danych w tymczasowym folderze, odizolowaną od prawdziwych danych."""
    storage_dir = tmp_path / "test_data"
    return BazaDanych(storage_dir=str(storage_dir))

@pytest.fixture
def controllers(temp_db):
    """Zwraca słownik ze wszystkimi zainicjalizowanymi kontrolerami wstrzykniętymi z temp_db."""
    pow_ctrl = PowiadomieniaController(temp_db)
    return {
        'db': temp_db,
        'powiadomienia': pow_ctrl,
        'zarzadzanie': ZarzadzanieController(temp_db, pow_ctrl),
        'harmonogram': HarmonogramController(temp_db, pow_ctrl),
        'rezerwacje': RezerwacjeController(temp_db),
        'obecnosc': ObecnoscController(temp_db),
        'raport': RaportController(temp_db)
    }


# 1. TESTY Entities

class TestEntities:
    def test_profil_uzytkownika_tworzenie_i_haslo(self):
        profil = ProfilUzytkownika(user_id=10)
        profil.set_attributes(wiek=25, poziom="zaawansowany")
        
        assert profil.wiek == 25
        assert profil.poziom_zaawansowania == "zaawansowany"
        
        haslo = profil.generate_temp_password()
        assert len(haslo) == 10
        assert type(haslo) is str

    def test_grupa_plywacka_wolne_miejsca(self):
        dane_grupy = {'grupa_id': 1, 'max_wielkosc': 10}
        grupa = GrupaPlywacka(dane_grupy)
        
        # Limit toru to 6, limit grupy to 10. Bezpieczny limit = 6
        wolne = grupa.sprawdzWolneMiejsca(limit_toru=6, zapisani_kursanci=4)
        assert wolne == 2 # 6 - 4 = 2
        
        # Limit toru to 12, limit grupy to 10. Bezpieczny limit = 10
        wolne = grupa.sprawdzWolneMiejsca(limit_toru=12, zapisani_kursanci=4)
        assert wolne == 6 # 10 - 4 = 6

    def test_rezerwacja_status_zmiana(self):
        rez = Rezerwacja(kursant_id=1, zajecia_id=10)
        assert rez.status == "aktywna"
        
        rez.zmienStatus("anulowana")
        assert rez.status == "anulowana"

    def test_raport_agregacja(self):
        raport = Raport()
        dane_frekwencji = [
            {'zajecia_id': 1, 'status': 'obecny'},
            {'zajecia_id': 1, 'status': 'obecny'},
            {'zajecia_id': 2, 'status': 'obecny'}
        ]
        wynik = raport.agregujPopularnosc(dane_frekwencji)
        assert wynik[1] == 2
        assert wynik[2] == 1


# 2. TESTY Database

class TestDatabase:
    def test_inicjalizacja_plikow(self, temp_db):
        """Sprawdza, czy BazaDanych tworzy wymagane pliki JSON."""
        pliki = os.listdir(temp_db.storage_dir)
        assert 'uzytkownicy.json' in pliki
        assert 'rezerwacje.json' in pliki
        assert 'tory.json' in pliki

    def test_insert_i_pobierz_tor(self, temp_db):
        tor = TorBasenowy(tor_id=1, max_pojemnosc=8)
        temp_db.save(tor)
        
        pobrany_tor = temp_db.pobierzTor(1)
        assert pobrany_tor.tor_id == 1
        assert pobrany_tor.max_pojemnosc == 8

    def test_bulk_insert_obecnosci(self, temp_db):
        obecnosci = [
            Obecnosc(uzytkownik_id=1, zajecia_id=10, status="obecny"),
            Obecnosc(uzytkownik_id=2, zajecia_id=10, status="nieobecny")
        ]
        temp_db.bulk_insert(obecnosci)
        
        zapisane = temp_db.pobierzZarejestrowaneObecnosci({})
        assert len(zapisane) == 2
        assert zapisane[0]['uzytkownik_id'] == 1


# 3. TESTY Controllers

class TestZarzadzanieController:
    def test_aktualizuj_profil(self, controllers):
        ctrl = controllers['zarzadzanie']
        db = controllers['db']
        
        ctrl.aktualizujProfil(user_id=5, wiek=30, poziom="Początkujący")
        profil_z_bazy = db.query(email=None) # Mock query method w prawdziwym życiu odpytałby po user_id
        
        # Sprawdzenie czy plik się zaktualizował
        users = db._read_file('uzytkownicy.json')
        assert len(users) == 1
        assert users[0]['wiek'] == 30
        assert users[0]['poziom_zaawansowania'] == "Początkujący"

    def test_zaktualizuj_pojemnosc_sukces(self, controllers):
        ctrl = controllers['zarzadzanie']
        db = controllers['db']
        
        tor = TorBasenowy(tor_id=1, max_pojemnosc=6)
        db.save(tor)
        
        # Test udanego zmniejszenia pojemności
        ctrl.zaktualizujPojemnosc(tor_id=1, nowa_pojemnosc=5)
        assert db.pobierzTor(1).max_pojemnosc == 5

    def test_zaktualizuj_pojemnosc_konflikt(self, controllers):
        ctrl = controllers['zarzadzanie']
        db = controllers['db']
        
        # Symulacja dużej grupy na torze
        grupa = GrupaPlywacka({'tor_id': 1, 'max_wielkosc': 10})
        
        prawdziwe_grupa_id = db.insert(grupa) 
        
        # Dodajemy 4 kursantów do wygenerowanego ID
        for i in range(4):
            db.insert(Rezerwacja(kursant_id=i, zajecia_id=prawdziwe_grupa_id))
            
        # Zmniejszamy pojemność do 3 (błąd, bo zapisanych jest 4)
        with pytest.raises(ValueError, match="przekracza nową pojemność toru"):
            ctrl.zaktualizujPojemnosc(tor_id=1, nowa_pojemnosc=3)

    def test_zablokuj_termin_bez_konfliktu(self, controllers):
        ctrl = controllers['zarzadzanie']
        start = datetime(2025, 1, 1, 10, 0)
        end = datetime(2025, 1, 1, 12, 0)
        
        # Zablokowanie terminu powinno przejść cicho
        ctrl.zablokujTermin(instruktor_id=1, start_date=start, end_date=end)
        blokady = controllers['db']._read_file('blokady.json')
        assert len(blokady) == 1
        assert blokady[0]['konflikt'] is False

    def test_zablokuj_termin_z_konfliktem(self, controllers):
        ctrl = controllers['zarzadzanie']
        db = controllers['db']
        
        start = datetime(2025, 1, 1, 10, 0)
        db.zapiszZajeciaWPlanu({'zajecia_id': 1, 'instruktor_id': 1, 'czas': start.isoformat()})
        
        # Próba blokady pokrywającej się z zajęciami
        with pytest.raises(UserWarning, match="Zgłoszono konieczność zastępstwa"):
            ctrl.zablokujTermin(instruktor_id=1, start_date=datetime(2025, 1, 1, 9, 0), end_date=datetime(2025, 1, 1, 11, 0))


class TestRezerwacjeController:
    def test_procesuj_zapis_sukces(self, controllers):
        ctrl = controllers['rezerwacje']
        db = controllers['db']
        
        grupa_id = db.insert(GrupaPlywacka({'tor_id': 1, 'max_wielkosc': 5}))
        db.save(TorBasenowy(tor_id=1, max_pojemnosc=10))
        
        ctrl.procesujZapis(kursant_id=1, zajecia_id=10, grupa_id=grupa_id)
        
        rez = db._read_file('rezerwacje.json')
        assert len(rez) == 1
        assert rez[0]['kursant_id'] == 1

    def test_procesuj_zapis_brak_miejsc(self, controllers):
        ctrl = controllers['rezerwacje']
        db = controllers['db']
        
        grupa_id = db.insert(GrupaPlywacka({'tor_id': 1, 'max_wielkosc': 1}))
        db.save(TorBasenowy(tor_id=1, max_pojemnosc=10))
        
        # Zapis pierwszej osoby
        ctrl.procesujZapis(kursant_id=1, zajecia_id=10, grupa_id=grupa_id)
        
        # Zapis drugiej osoby (błąd - max 1 miejsce)
        with pytest.raises(ValueError, match="Brak wolnych miejsc"):
            ctrl.procesujZapis(kursant_id=2, zajecia_id=10, grupa_id=grupa_id)

    def test_anulowanie_sukces_soft_delete(self, controllers):
        ctrl = controllers['rezerwacje']
        db = controllers['db']
        
        # Tworzenie zajęć w dalekiej przyszłości
        zajecia_czas = datetime.now() + timedelta(days=5)
        db.zapiszZajeciaWPlanu({'zajecia_id': 10, 'czas': zajecia_czas.isoformat()})
        rez_id = db.insert(Rezerwacja(kursant_id=1, zajecia_id=10))
        
        ctrl.procesujAnulowanie(rez_id)
        
        rez_db = db._read_file('rezerwacje.json')[0]
        assert rez_db['status'] == "anulowana"

    def test_anulowanie_zbyt_pozno(self, controllers):
        ctrl = controllers['rezerwacje']
        db = controllers['db']
        
        # Tworzenie zajęć za 2 godziny
        zajecia_czas = datetime.now() + timedelta(hours=2)
        db.zapiszZajeciaWPlanu({'zajecia_id': 10, 'czas': zajecia_czas.isoformat()})
        rez_id = db.insert(Rezerwacja(kursant_id=1, zajecia_id=10))
        
        with pytest.raises(ValueError, match="Zbyt mało czasu"):
            ctrl.procesujAnulowanie(rez_id)


class TestHarmonogramController:
    def test_zapisz_bez_konfliktu(self, controllers):
        ctrl = controllers['harmonogram']
        db = controllers['db']
        
        czas = datetime(2025, 5, 5, 12, 0)
        ctrl.sprawdzIZapiszHarmonogram({'tor_id': 1, 'instruktor_id': 2, 'czas': czas})
        
        zajecia = db._read_file('zajecia.json')
        assert len(zajecia) == 1

    def test_zapisz_z_konfliktem(self, controllers):
        ctrl = controllers['harmonogram']
        db = controllers['db']
        
        czas = datetime(2025, 5, 5, 12, 0)
        db.zapiszZajeciaWPlanu({'tor_id': 1, 'instruktor_id': 2, 'czas': czas.isoformat()})
        
        # Próba zapisu innych zajęć na tym samym torze w tym samym czasie
        with pytest.raises(ValueError, match="System technicznie uniemożliwia utworzenie konfliktu"):
            ctrl.sprawdzIZapiszHarmonogram({'tor_id': 1, 'instruktor_id': 99, 'czas': czas})


class TestObecnoscController:
    def test_zapisz_frekwencje(self, controllers):
        ctrl = controllers['obecnosc']
        db = controllers['db']
        
        # Rezerwujemy zajęcia dla 3 kursantów
        db.insert(Rezerwacja(kursant_id=101, zajecia_id=5))
        db.insert(Rezerwacja(kursant_id=102, zajecia_id=5))
        db.insert(Rezerwacja(kursant_id=103, zajecia_id=5))
        
        # Obecni tylko 101 i 103
        ctrl.zapiszFrekwencje(zajecia_id=5, lista_obecnych_ids=[101, 103])
        
        obecnosci = db._read_file('obecnosci.json')
        assert len(obecnosci) == 3
        status_102 = next(o['status'] for o in obecnosci if o['uzytkownik_id'] == 102)
        assert status_102 == "nieobecny"


# 4. TESTY Boundaries / UI Output

class TestBoundaries:
    def test_ui_zresetuj_haslo_print(self, controllers, capsys):
        ui = InterfejsWebowy(controllers['zarzadzanie'])
        ui.zresetujHaslo(user_id=1)
        
        # capsys przechwytuje printy w teście
        captured = capsys.readouterr()
        assert "Hasło zresetowane pomyślnie" in captured.out
        assert "Nowe hasło" in captured.out

    def test_portal_zapisow_blad_konfliktu_print(self, controllers, capsys):
        portal = PortalZapisow(controllers['rezerwacje'], controllers['harmonogram'])
        czas = datetime(2025, 5, 5, 12, 0)
        
        # Tworzenie konfliktu
        controllers['db'].zapiszZajeciaWPlanu({'tor_id': 1, 'instruktor_id': 2, 'czas': czas.isoformat()})
        
        # UI powinno wyłapać exception i wypisać print z błędem
        portal.przypiszZajecia(grupa_id=1, tor_id=1, instruktor_id=99, czas=czas)
        
        captured = capsys.readouterr()
        assert "UI KONFLIKT HARMONOGRAMU" in captured.out
        assert "System technicznie uniemożliwia utworzenie konfliktu" in captured.out

    def test_system_cron_uruchomienie(self, controllers, capsys):
        cron = SystemCron(controllers['powiadomienia'])
        
        # Zapisanie zajęć na jutro, by powiadomienie zadziałało
        jutro = datetime.now() + timedelta(days=1, hours=1)
        controllers['db'].zapiszZajeciaWPlanu({'zajecia_id': 1, 'czas': jutro.isoformat()})
        controllers['db'].insert(Rezerwacja(kursant_id=1, zajecia_id=1))
        
        cron.cronJob_sprawdzHarmonogram()
        
        captured = capsys.readouterr()
        assert "Inicjalizacja procesu" in captured.out
        assert "Powiadomienie PUSH do Usera 1" in captured.out