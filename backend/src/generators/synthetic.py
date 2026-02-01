"""Synthetic data generator using Faker for type-appropriate substitutes."""

import hashlib
import ipaddress
import random
import re
import uuid
from collections.abc import Callable

from faker import Faker

# Try to import names_dataset for culturally-aware name generation
try:
    from names_dataset import NameDataset
    _names_dataset = NameDataset()
    NAMES_DATASET_AVAILABLE = True
except ImportError:
    _names_dataset = None
    NAMES_DATASET_AVAILABLE = False

# Try to import geonamescache for real city data with coordinates
try:
    from geonamescache import GeonamesCache
    _geonames_cache = GeonamesCache()
    _geonames_cities = list(_geonames_cache.get_cities().values())
    GEONAMES_AVAILABLE = True
except ImportError:
    _geonames_cache = None
    _geonames_cities = []
    GEONAMES_AVAILABLE = False


# Mapping from locale codes to country alpha-2 codes for names-dataset
LOCALE_TO_COUNTRY = {
    "ar_SA": "SA",  # Saudi Arabia
    "ar_EG": "EG",  # Egypt
    "ar_AE": "AE",  # UAE
    "zh_CN": "CN",  # China
    "zh_TW": "TW",  # Taiwan
    "ja_JP": "JP",  # Japan
    "ko_KR": "KR",  # South Korea
    "ru_RU": "RU",  # Russia
    "hi_IN": "IN",  # India
    "en_IN": "IN",  # India (English)
    "de_DE": "DE",  # Germany
    "de_AT": "AT",  # Austria
    "fr_FR": "FR",  # France
    "fr_CA": "CA",  # Canada
    "es_ES": "ES",  # Spain
    "es_MX": "MX",  # Mexico
    "pt_BR": "BR",  # Brazil
    "pt_PT": "PT",  # Portugal
    "it_IT": "IT",  # Italy
    "nl_NL": "NL",  # Netherlands
    "pl_PL": "PL",  # Poland
    "tr_TR": "TR",  # Turkey
    "en_US": "US",  # United States
    "en_GB": "GB",  # United Kingdom
    "en_AU": "AU",  # Australia
}

# Countries that primarily use non-Latin scripts
NON_LATIN_COUNTRIES = {"SA", "EG", "AE", "CN", "TW", "JP", "KR", "RU", "IN"}


def _is_latin_script(text: str) -> bool:
    """Check if the text is primarily in Latin script."""
    if not text:
        return True

    latin_count = 0
    non_space_count = 0

    for char in text:
        if char.isspace() or char in "-'.":
            continue
        non_space_count += 1
        if char.isascii() and char.isalpha():
            latin_count += 1
        elif '\u00C0' <= char <= '\u024F':  # Latin Extended
            latin_count += 1

    if non_space_count == 0:
        return True

    return (latin_count / non_space_count) > 0.8


def _detect_name_country(name: str) -> str | None:
    """Detect the most likely country of origin for a name using names-dataset.

    Returns ISO alpha-2 country code or None.
    """
    if not NAMES_DATASET_AVAILABLE or not name:
        return None

    # Split name into parts and search each
    parts = name.strip().split()
    country_scores: dict[str, float] = {}

    for part in parts:
        if len(part) < 2:
            continue

        result = _names_dataset.search(part)

        # Check first name data
        if "first_name" in result and result["first_name"]:
            countries = result["first_name"].get("country", {})
            for country, score in countries.items():
                # Get alpha-2 code
                try:
                    import pycountry
                    c = pycountry.countries.get(name=country)
                    if c:
                        code = c.alpha_2
                        country_scores[code] = country_scores.get(code, 0) + score
                except Exception:
                    pass

        # Check last name data
        if "last_name" in result and result["last_name"]:
            countries = result["last_name"].get("country", {})
            for country, score in countries.items():
                try:
                    import pycountry
                    c = pycountry.countries.get(name=country)
                    if c:
                        code = c.alpha_2
                        country_scores[code] = country_scores.get(code, 0) + score
                except Exception:
                    pass

    if not country_scores:
        return None

    # Return country with highest score
    return max(country_scores, key=country_scores.get)


def _get_names_for_country(country_code: str, n: int = 50) -> dict:
    """Get top names for a country from names-dataset.

    Returns dict with 'first_male', 'first_female', 'last' lists.
    """
    if not NAMES_DATASET_AVAILABLE:
        return {}

    result = {"first_male": [], "first_female": [], "last": []}

    try:
        # Get first names
        first_names = _names_dataset.get_top_names(n=n, country_alpha2=country_code)
        if country_code in first_names:
            result["first_male"] = first_names[country_code].get("M", [])
            result["first_female"] = first_names[country_code].get("F", [])

        # Get last names
        last_names = _names_dataset.get_top_names(
            n=n, country_alpha2=country_code, use_first_names=False
        )
        if country_code in last_names:
            result["last"] = last_names[country_code]

    except Exception:
        pass

    return result


def _filter_latin_names(names: list[str]) -> list[str]:
    """Filter a list of names to only include Latin-script names."""
    return [name for name in names if _is_latin_script(name)]


# RFC 1918 Private IP ranges (strict definition)
RFC1918_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

# Additional special ranges we treat as "internal"
INTERNAL_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
]


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is RFC 1918 private or internal.

    Only considers RFC 1918 private ranges (10.x, 172.16-31.x, 192.168.x)
    plus loopback and link-local. Does NOT include documentation ranges
    like TEST-NET which Python's ipaddress.is_private includes.
    """
    try:
        ip = ipaddress.ip_address(ip_str)

        # Check RFC 1918 private ranges
        for network in RFC1918_PRIVATE_RANGES:
            if ip in network:
                return True

        # Check internal ranges (loopback, link-local)
        for network in INTERNAL_RANGES:
            if ip in network:
                return True

        return False
    except ValueError:
        return False


def is_network_address(ip_str: str) -> tuple[bool, int | None]:
    """Check if the string is a network definition (not a host IP).

    A network address has all host bits set to 0 and represents a range.
    Example: 192.168.1.0/24 is a network (256 addresses), 192.168.1.50/24 is a host.

    Returns:
        Tuple of (is_network, prefix_length or None)
    """
    if "/" not in ip_str:
        return False, None

    try:
        parts = ip_str.split("/")
        prefix_len = int(parts[1])

        # Parse as network - this will fail if it's a host IP with CIDR
        ipaddress.ip_network(ip_str, strict=True)
        # If we get here, it's a valid network address
        return True, prefix_len
    except ValueError:
        # strict=True fails for host IPs like 192.168.1.50/24
        return False, None


def parse_ip_with_cidr(ip_str: str) -> tuple[str, str | None]:
    """Parse an IP address, separating the IP from any CIDR suffix.

    Returns:
        Tuple of (ip_address, cidr_suffix or None)
        Example: "192.168.1.50/24" -> ("192.168.1.50", "/24")
    """
    if "/" in ip_str:
        parts = ip_str.split("/", 1)
        return parts[0], "/" + parts[1]
    return ip_str, None


def generate_private_ipv4() -> str:
    """Generate a random private IPv4 address."""
    # Choose from common private ranges
    range_choice = random.choice([
        ("10", 0, 255, 0, 255, 1, 254),
        ("172", 16, 31, 0, 255, 1, 254),
        ("192.168", None, None, 0, 255, 1, 254),
    ])

    if range_choice[0] == "10":
        return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    elif range_choice[0] == "172":
        return f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    else:
        return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"


def generate_public_ipv4() -> str:
    """Generate a random public IPv4 address."""
    while True:
        # Generate random IP
        ip_str = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        try:
            ip = ipaddress.ip_address(ip_str)
            # Ensure it's not private, loopback, link-local, multicast, or reserved
            if not (ip.is_private or ip.is_loopback or ip.is_link_local or
                    ip.is_multicast or ip.is_reserved):
                return ip_str
        except ValueError:
            continue


def generate_private_network(prefix_len: int) -> str:
    """Generate a random private network address with the given prefix length."""
    # Generate random octets based on prefix length
    if prefix_len <= 8:
        # For /8 or larger, use 10.x.x.x range with random first octet variation
        # Since 10.0.0.0/8 is the only /8 private range, vary within constraints
        first = 10
        second = random.randint(0, 255)
        third = random.randint(0, 255)
        fourth = 0
    elif prefix_len <= 12:
        # Use 172.16-31.x.x range
        first = 172
        second = random.randint(16, 31)
        third = random.randint(0, 255)
        fourth = 0
    elif prefix_len <= 16:
        # Use 192.168.x.x or 10.x.x.x
        if random.choice([True, False]):
            first, second = 192, 168
        else:
            first = 10
            second = random.randint(0, 255)
        third = random.randint(0, 255)
        fourth = 0
    else:
        # For /17 and smaller, use 192.168.x.x or 10.x.x.x
        choice = random.choice(["192.168", "10", "172"])
        if choice == "192.168":
            first, second = 192, 168
            third = random.randint(0, 255)
        elif choice == "10":
            first = 10
            second = random.randint(0, 255)
            third = random.randint(0, 255)
        else:
            first = 172
            second = random.randint(16, 31)
            third = random.randint(0, 255)
        fourth = 0

    # Create the IP and normalize to network address
    try:
        ip_str = f"{first}.{second}.{third}.{fourth}/{prefix_len}"
        network = ipaddress.ip_network(ip_str, strict=False)
        return str(network)
    except ValueError:
        # Fallback
        return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.0/{prefix_len}"


def generate_public_network(prefix_len: int) -> str:
    """Generate a random public network address with the given prefix length."""
    max_attempts = 200
    for _ in range(max_attempts):
        # Generate a random IP first, then we'll convert to network
        first = random.randint(1, 223)
        second = random.randint(0, 255)
        third = random.randint(0, 255)
        fourth = random.randint(0, 255)

        try:
            # Check if this IP is public
            test_ip = ipaddress.ip_address(f"{first}.{second}.{third}.{fourth}")
            if test_ip.is_private or test_ip.is_reserved or test_ip.is_loopback or test_ip.is_multicast:
                continue

            # Now create a network with this prefix
            ip_str = f"{first}.{second}.{third}.{fourth}/{prefix_len}"
            network = ipaddress.ip_network(ip_str, strict=False)

            # Double-check the network address is also public
            network_ip = network.network_address
            if network_ip.is_private or network_ip.is_reserved or network_ip.is_loopback:
                continue

            return str(network)
        except ValueError:
            continue

    # Fallback - generate something that looks public
    # Using ranges that are clearly not private
    first = random.choice([45, 52, 54, 63, 74, 89, 104, 142, 157, 185, 199, 216])
    second = random.randint(0, 255)
    third = random.randint(0, 255)
    try:
        ip_str = f"{first}.{second}.{third}.0/{prefix_len}"
        network = ipaddress.ip_network(ip_str, strict=False)
        return str(network)
    except ValueError:
        return f"45.{random.randint(0, 255)}.{random.randint(0, 255)}.0/{prefix_len}"


# Supported Faker locales with their typical phone formats
SUPPORTED_LOCALES = {
    "en_US": "English (United States)",
    "en_GB": "English (United Kingdom)",
    "en_AU": "English (Australia)",
    "en_CA": "English (Canada)",
    "en_IN": "English (India)",
    "de_DE": "German (Germany)",
    "de_AT": "German (Austria)",
    "de_CH": "German (Switzerland)",
    "fr_FR": "French (France)",
    "fr_CA": "French (Canada)",
    "fr_BE": "French (Belgium)",
    "es_ES": "Spanish (Spain)",
    "es_MX": "Spanish (Mexico)",
    "it_IT": "Italian (Italy)",
    "pt_BR": "Portuguese (Brazil)",
    "pt_PT": "Portuguese (Portugal)",
    "nl_NL": "Dutch (Netherlands)",
    "nl_BE": "Dutch (Belgium)",
    "pl_PL": "Polish (Poland)",
    "ru_RU": "Russian (Russia)",
    "ja_JP": "Japanese (Japan)",
    "zh_CN": "Chinese (China)",
    "zh_TW": "Chinese (Taiwan)",
    "ko_KR": "Korean (South Korea)",
    "ar_SA": "Arabic (Saudi Arabia)",
    "hi_IN": "Hindi (India)",
    "sv_SE": "Swedish (Sweden)",
    "da_DK": "Danish (Denmark)",
    "no_NO": "Norwegian (Norway)",
    "fi_FI": "Finnish (Finland)",
}


class SyntheticGenerator:
    """Generate type-appropriate synthetic data for PII substitution.

    Uses Faker to create realistic-looking substitute values that match
    the format of the original PII type.
    """

    def __init__(self, seed: str | None = None, locale: str = "en_US"):
        """Initialize the generator.

        Args:
            seed: Optional seed for reproducible generation
            locale: Locale for Faker (default: en_US)
        """
        self._locale = locale
        self._faker = Faker(locale)
        self._seed = seed
        if seed:
            Faker.seed(seed)

        # Cache of Faker instances for different locales (for name origin matching)
        self._locale_fakers: dict[str, Faker] = {locale: self._faker}

        # Map entity types to generator functions
        self._generators: dict[str, Callable[[str | None], str]] = {
            "PERSON": self._generate_person,
            "EMAIL_ADDRESS": self._generate_email,
            "PHONE_NUMBER": self._generate_phone,
            "CREDIT_CARD": self._generate_credit_card,
            "US_SSN": self._generate_ssn,
            "US_BANK_NUMBER": self._generate_bank_number,
            "US_DRIVER_LICENSE": self._generate_driver_license,
            "US_ITIN": self._generate_itin,
            "US_PASSPORT": self._generate_passport,
            "IP_ADDRESS": self._generate_ip,
            "LOCATION": self._generate_location,
            "STREET_ADDRESS": self._generate_street_address,
            "DATE_TIME": self._generate_datetime,
            "NRP": self._generate_nrp,
            "MEDICAL_LICENSE": self._generate_medical_license,
            "URL": self._generate_url,
            "IBAN_CODE": self._generate_iban,
            "CRYPTO": self._generate_crypto,
            "GUID": self._generate_guid,
        }

    @property
    def locale(self) -> str:
        """Get the current locale."""
        return self._locale

    def set_locale(self, locale: str) -> None:
        """Change the locale for generation.

        Args:
            locale: New locale code (e.g., "en_US", "de_DE")
        """
        if locale != self._locale:
            self._locale = locale
            self._faker = Faker(locale)

    @staticmethod
    def get_supported_locales() -> dict[str, str]:
        """Get dictionary of supported locales with descriptions."""
        return SUPPORTED_LOCALES.copy()

    def _get_faker_for_locale(self, locale: str) -> Faker:
        """Get or create a Faker instance for a specific locale."""
        if locale not in self._locale_fakers:
            try:
                self._locale_fakers[locale] = Faker(locale)
                if self._seed:
                    self._locale_fakers[locale].seed_instance(hash(self._seed + locale) % (2**32))
            except Exception:
                # If locale not supported, fall back to default
                return self._faker
        return self._locale_fakers[locale]

    def generate(
        self, entity_type: str, original_value: str | None = None, original_hash: str | None = None
    ) -> str:
        """Generate a substitute value for the given entity type.

        Args:
            entity_type: The Presidio entity type
            original_value: The original PII value (used for smart substitution)
            original_hash: Optional hash to seed generation for consistency

        Returns:
            A synthetic substitute value
        """
        # Seed with hash for deterministic generation if provided
        if original_hash:
            seed_value = int(hashlib.md5(original_hash.encode()).hexdigest()[:8], 16)
            self._faker.seed_instance(seed_value)

        generator = self._generators.get(entity_type, self._generate_default)
        return generator(original_value)

    def _generate_person(self, original: str | None = None) -> str:
        """Generate a realistic person name, preserving cultural origin and script.

        Uses names-dataset library to detect origin and generate culturally-appropriate names.
        Always outputs Latin-script names when input is Latin-script.
        """
        if original and NAMES_DATASET_AVAILABLE:
            # Detect country of origin using names-dataset
            country = _detect_name_country(original)

            if country:
                # Get names from that country
                names = _get_names_for_country(country, n=100)

                # Check if original is Latin script - if so, filter to Latin names only
                if _is_latin_script(original):
                    first_male = _filter_latin_names(names.get("first_male", []))
                    first_female = _filter_latin_names(names.get("first_female", []))
                    last_names = _filter_latin_names(names.get("last", []))
                else:
                    first_male = names.get("first_male", [])
                    first_female = names.get("first_female", [])
                    last_names = names.get("last", [])

                # Generate name if we have data
                if (first_male or first_female) and last_names:
                    # Pick first name (random gender)
                    if random.choice([True, False]) and first_male:
                        first = random.choice(first_male)
                    elif first_female:
                        first = random.choice(first_female)
                    elif first_male:
                        first = random.choice(first_male)
                    else:
                        first = self._faker.first_name()

                    last = random.choice(last_names) if last_names else self._faker.last_name()
                    return f"{first} {last}"

        # Fall back to the configured locale
        return self._faker.name()

    def _generate_email(self, original: str | None = None) -> str:
        """Generate a realistic email address."""
        return self._faker.email()

    def _generate_phone(self, original: str | None = None) -> str:
        """Generate a phone number in locale-appropriate format."""
        return self._faker.phone_number()

    def _generate_credit_card(self, original: str | None = None) -> str:
        """Generate a credit card number."""
        return self._faker.credit_card_number(card_type="visa")

    def _generate_ssn(self, original: str | None = None) -> str:
        """Generate a US Social Security Number."""
        return self._faker.ssn()

    def _generate_bank_number(self, original: str | None = None) -> str:
        """Generate a bank account number."""
        return self._faker.bban()

    def _generate_driver_license(self, original: str | None = None) -> str:
        """Generate a driver's license number."""
        # Format varies by state, using a generic format
        return f"{self._faker.random_uppercase_letter()}{self._faker.random_number(digits=12)}"

    def _generate_itin(self, original: str | None = None) -> str:
        """Generate a US Individual Taxpayer ID Number."""
        # ITIN format: 9XX-XX-XXXX where first digit is 9
        middle = random.randint(70, 99)  # Valid middle digits for ITIN
        last = random.randint(1000, 9999)
        return f"9{random.randint(0,9)}{random.randint(0,9)}-{middle}-{last}"

    def _generate_passport(self, original: str | None = None) -> str:
        """Generate a passport number."""
        return self._faker.passport_number()

    def _generate_ip(self, original: str | None = None) -> str:
        """Generate an IP address, preserving private/public classification.

        - Private IPs are replaced with private IPs
        - Public IPs are replaced with public IPs
        - Network addresses (e.g., 192.168.1.0/24) are replaced with same-type networks
        - Host IPs with CIDR (e.g., 192.168.1.50/24) are replaced, preserving the CIDR suffix
        """
        if original is None:
            # No original value, generate a random public IP
            return generate_public_ipv4()

        # Check if it's a network address (e.g., 192.168.1.0/24)
        is_network, prefix_len = is_network_address(original)
        if is_network and prefix_len is not None:
            # Extract the network address to check if private/public
            ip_part = original.split("/")[0]
            if is_private_ip(ip_part):
                return generate_private_network(prefix_len)
            else:
                return generate_public_network(prefix_len)

        # Parse IP and CIDR suffix separately
        ip_part, cidr_suffix = parse_ip_with_cidr(original)

        # Extract just the IP part (in case there's extra formatting)
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', ip_part)
        if not ip_match:
            # Not a valid IPv4, return a public IP
            return generate_public_ipv4()

        ip_str = ip_match.group(1)

        # Check if private or public and generate matching type
        if is_private_ip(ip_str):
            new_ip = generate_private_ipv4()
        else:
            new_ip = generate_public_ipv4()

        # Preserve CIDR suffix if present
        if cidr_suffix:
            return new_ip + cidr_suffix
        return new_ip

    def _generate_location(self, original: str | None = None) -> str:
        """Generate a real location/city name using geonamescache.

        Falls back to Faker if geonamescache is not available.
        """
        if GEONAMES_AVAILABLE and _geonames_cities:
            city = random.choice(_geonames_cities)
            return city.get("name", self._faker.city())
        return self._faker.city()

    def generate_location_with_coordinates(self) -> dict:
        """Generate a real location with coordinates.

        Returns dict with keys: name, latitude, longitude, country_code
        Useful for replacing structured location data like Azure SigninLogs LocationDetails.
        """
        if GEONAMES_AVAILABLE and _geonames_cities:
            city = random.choice(_geonames_cities)
            return {
                "name": city.get("name", "Unknown"),
                "latitude": city.get("latitude", 0.0),
                "longitude": city.get("longitude", 0.0),
                "country_code": city.get("countrycode", "US"),
            }
        # Fallback to Faker-generated data with random coordinates
        return {
            "name": self._faker.city(),
            "latitude": float(self._faker.latitude()),
            "longitude": float(self._faker.longitude()),
            "country_code": self._faker.country_code(),
        }

    def _generate_guid(self, original: str | None = None) -> str:
        """Generate a GUID/UUID."""
        return str(uuid.uuid4())

    def _generate_street_address(self, original: str | None = None) -> str:
        """Generate a street address."""
        return self._faker.street_address()

    def _generate_datetime(self, original: str | None = None) -> str:
        """Generate a date string."""
        return self._faker.date()

    def _generate_nrp(self, original: str | None = None) -> str:
        """Generate a nationality/religious/political group reference."""
        # Return a generic placeholder since this is sensitive
        options = ["Group A", "Organization B", "Community C", "Association D"]
        return random.choice(options)

    def _generate_medical_license(self, original: str | None = None) -> str:
        """Generate a medical license number."""
        return f"ML{self._faker.random_number(digits=8)}"

    def _generate_url(self, original: str | None = None) -> str:
        """Generate a URL."""
        return self._faker.url()

    def _generate_iban(self, original: str | None = None) -> str:
        """Generate an IBAN."""
        return self._faker.iban()

    def _generate_crypto(self, original: str | None = None) -> str:
        """Generate a cryptocurrency address-like string."""
        # Generate a Bitcoin-like address
        prefix = random.choice(["1", "3", "bc1"])
        chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        address = "".join(random.choices(chars, k=32))
        return f"{prefix}{address}"

    def _generate_default(self, original: str | None = None) -> str:
        """Generate a default placeholder for unknown entity types."""
        return f"<REDACTED_{self._faker.random_number(digits=6)}>"


# Singleton instance
_generator_instance: SyntheticGenerator | None = None


def get_generator(seed: str | None = None, locale: str = "en_US") -> SyntheticGenerator:
    """Get or create a SyntheticGenerator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SyntheticGenerator(seed=seed, locale=locale)
    return _generator_instance


def reset_generator() -> None:
    """Reset the singleton generator instance (useful for locale changes)."""
    global _generator_instance
    _generator_instance = None
