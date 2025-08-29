import requests
import msvcrt
from bs4 import BeautifulSoup

def get_station_data(url):
    """
    Load fuel price (CZK) and last update date from mbenzin.cz.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract price
        meta_price = soup.find("meta", {"id": "ContentPlaceHolder1_mPriceN95"})
        if meta_price and meta_price.has_attr("content"):
            price_str = meta_price["content"].strip()
            price_czk = float(price_str.replace(",", "."))
        else:
            print(f"Price from {url} was not found.")
            price_czk = None

        # Extract last update date
        date_span = soup.find("span", {"id": "ContentPlaceHolder1_lN95LastUpdate"})
        if date_span:
            last_update = date_span.get_text(strip=True)
        else:
            last_update = "Unknown date"

        return price_czk, last_update
    except Exception as e:
        print(f"Error while fetching data from {url}: {e}")
        return None, None


def get_adjusted_exchange_rate():
    """
    Fetch current EUR → CZK exchange rate from Frankfurter API.
    Apply adjustment coefficient (bank/transaction fee).
    """
    url = "https://api.frankfurter.app/latest"
    params = {
        "from": "EUR",
        "to": "CZK"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if "rates" in data and "CZK" in data["rates"]:
            rate = data["rates"]["CZK"]
            adjusted_rate = rate * 0.9952  # Adjustment factor
            return adjusted_rate
        else:
            print("API response does not contain expected exchange rate data.")
            return None
    except Exception as e:
        print(f"Error while fetching exchange rate: {e}")
        return None


def get_home_price():
    """
    Fetch current local fuel price (EUR) from dalioil.sk.
    """
    url = "https://dalioil.sk/dubnica-nad-vahom/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        figcaption = soup.find("figcaption", class_="elementor-image-carousel-caption")
        if figcaption:
            price_text = figcaption.get_text(strip=True)
            price_text = price_text.replace("€", "").replace(" ", "").replace(",", ".")
            home_price = float(price_text)
            return home_price
        else:
            print("Home price from dalioil.sk was not found.")
            return None
    except Exception as e:
        print(f"Error while fetching home price: {e}")
        return None


def calculate_savings(cr_price_czk, last_update, distance_km, adjusted_rate, home_price, label):
    """
    Calculate potential savings if fueling in Czech Republic vs home station.
    """
    if cr_price_czk is None:
        print(f"Could not fetch price from {label}.")
        return
    
    # Convert CZ price to EUR
    cr_price_eur = cr_price_czk / adjusted_rate

    # Extra distance (round trip)
    extra_distance = distance_km * 2
    # Extra fuel consumption for the trip (6.3 l/100km average consumption)
    extra_liters = extra_distance * 6.3 / 100

    # Savings per liter
    saving_per_liter = home_price - cr_price_eur

    if saving_per_liter <= 0:
        print(f"{label}: No savings, CZ price is not better than home price.")
        return

    # Extra travel cost (spent fuel in EUR)
    extra_cost = home_price * extra_liters

    # Minimum liters needed to offset travel cost
    required_liters = extra_cost / saving_per_liter

    print(f"\n{label}:")
    print(f"Last update: \033[91m{last_update}\033[0m")
    print(f"Price in CZ (converted): {cr_price_eur:.4f} EUR/l")
    print(f"Home price: {home_price:.4f} EUR/l")
    print(f"Savings per liter: {saving_per_liter:.4f} EUR/l")
    print(f"Extra fuel needed for {extra_distance:.1f} km: {extra_liters:.2f} l")
    print(f"Extra travel cost: {extra_cost:.2f} EUR")
    print(f"To break even you need to refuel at least {required_liters:.2f} liters in CZ.")


if __name__ == "__main__":
    # List of CZ stations with distance (one-way, km)
    stations = [
        {
            "label": "Trako Brumov",
            "url": "https://www.mbenzin.cz/Ceny-benzinu-a-nafty/Brumov/Trako-Kloboucka-1397/18019",
            "distance": 25.0
        },
        {
            "label": "EuroOil Valašské Klobouky",
            "url": "https://www.mbenzin.cz/Ceny-benzinu-a-nafty/Valasske-Klobouky/EuroOil- Cyrilometodejska-666/17010",
            "distance": 30.6
        },
        {
            "label": "EuroOil Horní Lideč",
            "url": "https://www.mbenzin.cz/Ceny-benzinu-a-nafty/Horni-Lidec/EuroOil-Horni-Lidec-295-silnice-49/16886",
            "distance": 49.5
        },
        {
            "label": "Silmet Lidečko",
            "url": "https://www.mbenzin.cz/Ceny-benzinu-a-nafty/Lidecko/Silmet-/17956",
            "distance": 38.5
        }
    ]

    # 1. Get exchange rate
    adjusted_rate = get_adjusted_exchange_rate()
    if adjusted_rate is None:
        print("Could not fetch exchange rate.")
        exit(1)

    # 2. Get home price
    home_price = get_home_price()
    if home_price is None:
        print("Could not fetch home price.")
        exit(1)

    # 3. Calculate savings for all CZ stations
    for st in stations:
        cr_price_czk, cr_date = get_station_data(st["url"])
        calculate_savings(cr_price_czk, cr_date, st["distance"], adjusted_rate, home_price, st["label"])

    print("\nProgram is running. Press any key to exit...")
    msvcrt.getch()
