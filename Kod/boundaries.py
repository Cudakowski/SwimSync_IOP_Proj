from datetime import datetime
from controllers import (
    ZarzadzanieController,
    RezerwacjeController,
    HarmonogramController,
    ObecnoscController,
    RaportController,
    PowiadomieniaController
)

class InterfejsWebowy:
    def __init__(self, zarzadzanie_ctrl: ZarzadzanieController):
        self.zarzadzanie_ctrl = zarzadzanie_ctrl

    def wypelnijDaneProfilu(self, wiek: int, poziom_zaawansowania: str) -> None:
        # Symulacja zalogowanego użytkownika ID=1
        self.zarzadzanie_ctrl.aktualizujProfil(1, wiek, poziom_zaawansowania)
        self.dostosujWidoczneGrupy(wiek, poziom_zaawansowania)

    def dostosujWidoczneGrupy(self, wiek: int, poziom: str) -> None:
        print(f"[UI] Ekran zaktualizowany: Pokaż tylko grupy dla wieku {wiek} i poziomu '{poziom}'.")

    def dodajOpis(self, kwalifikacje_text: str) -> None:
        self.zarzadzanie_ctrl.aktualizujOpisInstruktora(1, kwalifikacje_text)
        print("[UI] Wyświetlono komunikat: 'Opis widoczny dla kursantów.'")

    def wyszukajUzytkownika(self, email: str) -> None:
        wyniki = self.zarzadzanie_ctrl.szukajKonta(email)
        print(f"[UI] Wyświetlanie wyników wyszukiwania w tabeli: {wyniki}")

    def zresetujHaslo(self, user_id: int) -> None:
        haslo = self.zarzadzanie_ctrl.generujNoweHaslo(user_id)
        print(f"[UI] Modal: Hasło zresetowane pomyślnie. Nowe hasło do skopiowania: {haslo}")

    def ustawPojemnoscToru(self, tor_id: int, nowa_pojemnosc: int) -> None:
        try:
            self.zarzadzanie_ctrl.zaktualizujPojemnosc(tor_id, nowa_pojemnosc)
            print("[UI] Komunikat: Pojemność toru zaktualizowana.")
        except ValueError as e:
            self.bladWalidacji(str(e))

    def bladWalidacji(self, msg: str) -> None:
        print(f"[UI BŁĄD WALIDACJI] Czerwony alert na ekranie: {msg}")

    def utworzGrupe(self, max_wielkosc: int, wiek: int, poziom: str) -> None:
        dane_grupy = {'max_wielkosc': max_wielkosc, 'wiek': wiek, 'poziom': poziom}
        self.zarzadzanie_ctrl.stworzNowaGrupe(dane_grupy)
        print("[UI] Pop-up: Grupa utworzona, gotowa do planowania.")

    def zglosNiedostepnosc(self, start_date: datetime, end_date: datetime) -> None:
        try:
            self.zarzadzanie_ctrl.zablokujTermin(1, start_date, end_date)
            print("[UI] Komunikat: Termin pomyślnie zablokowany bez konfliktów.")
        except UserWarning as e:
            print(f"[UI OSTRZEŻENIE] {str(e)}")


class PortalZapisow:
    def __init__(self, rezerwacje_ctrl: RezerwacjeController, harmonogram_ctrl: HarmonogramController):
        self.rezerwacje_ctrl = rezerwacje_ctrl
        self.harmonogram_ctrl = harmonogram_ctrl

    def zapiszNaZajecia(self, zajecia_id: int, grupa_id: int) -> None:
        try:
            # Symulacja kursanta ID=1
            self.rezerwacje_ctrl.procesujZapis(1, zajecia_id, grupa_id)
            print("[UI] Komunikat sukcesu: Miejsce zarezerwowane pomyślnie.")
        except ValueError as e:
            self.błąd(str(e))

    def błąd(self, wiadomosc: str) -> None:
        print(f"[UI BŁĄD REZERWACJI] Wyświetlono błąd: {wiadomosc}")

    def zapiszNaCykl(self, cykl_id: int, grupa_id: int) -> None:
        self.rezerwacje_ctrl.zapiszNaWieleZajec(1, cykl_id, grupa_id)
        print("[UI] Komunikat sukcesu: Gwarancja miejsca na cały semestr.")

    def anulujZajecia(self, rezerwacja_id: int) -> None:
        try:
            self.rezerwacje_ctrl.procesujAnulowanie(rezerwacja_id)
            print("[UI] Komunikat: Rezerwacja anulowana, miejsce zwolnione dla innych.")
        except ValueError as e:
            self.odrzucenie(str(e))

    def odrzucenie(self, wiadomosc: str) -> None:
        print(f"[UI ODRZUCENIE ANULACJI] {wiadomosc}")

    def przypiszZajecia(self, grupa_id: int, tor_id: int, instruktor_id: int, czas: datetime) -> None:
        try:
            self.harmonogram_ctrl.sprawdzIZapiszHarmonogram({
                'grupa_id': grupa_id, 'tor_id': tor_id, 'instruktor_id': instruktor_id, 'czas': czas
            })
            print("[UI] Komunikat: Zajęcia pomyślnie dodane do harmonogramu.")
        except ValueError as e:
            self.błądKolizji(str(e))

    def błądKolizji(self, wiadomosc: str) -> None:
        print(f"[UI KONFLIKT HARMONOGRAMU] Odrzucono zapis: {wiadomosc}")


class SystemAplikacja:
    def __init__(self, obecnosc_ctrl: ObecnoscController, raport_ctrl: RaportController, powiadomienia_ctrl: PowiadomieniaController):
        self.obecnosc_ctrl = obecnosc_ctrl
        self.raport_ctrl = raport_ctrl
        self.powiadomienia_ctrl = powiadomienia_ctrl

    def oznaczObecnosci(self, zajecia_id: int, lista_obecnych_ids: list) -> None:
        self.obecnosc_ctrl.zapiszFrekwencje(zajecia_id, lista_obecnych_ids)
        print("[UI] Zmiana statusu formularza: Frekwencja zapisana dla Administratora.")

    def generujRaport(self, typ_raportu: str, parametry_dict: dict) -> None:
        plik = self.raport_ctrl.utworzZestawienie(typ_raportu, parametry_dict)
        self.pobierzPlik(plik)

    def pobierzPlik(self, plik: str) -> None:
        print(f"[UI BROWSER] Wywołanie okna pobierania dla pliku: {plik}")

    def wyslijKomunikatMasowy(self, grupa_docelowa: str, tresc: str) -> None:
        self.powiadomienia_ctrl.broadcastMessage(grupa_docelowa, tresc)
        print("[UI] Pasek postępu: Wiadomości zostały rozesłane.")


class SystemCron:
    def __init__(self, powiadomienia_ctrl: PowiadomieniaController):
        self.powiadomienia_ctrl = powiadomienia_ctrl

    def cronJob_sprawdzHarmonogram(self) -> None:
        print("[CRON JOB] Inicjalizacja procesu sprawdzania harmonogramu...")
        self.powiadomienia_ctrl.cronJob_sprawdzHarmonogram()
        print("[CRON JOB] Proces zakończony.")