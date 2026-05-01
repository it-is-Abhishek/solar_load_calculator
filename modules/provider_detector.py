import re

class ProviderDetector:
    PROVIDERS = {
        "MSEDCL": [r"mahavitaran", r"msedcl", r"maharashtra\s*state\s*electricity", r"mahadiscom"],
        "TATA_POWER": [r"tata\s*power", r"tata\s*electricity"],
        "ADANI": [r"adani\s*electricity", r"adani\s*power"],
        "BESCOM": [r"bescom", r"bangalore\s*electricity"],
        "BSES": [r"bses\s*rajdhani", r"bses\s*yamuna", r"bses"],
        "TORRENT_POWER": [r"torrent\s*power"]
    }

    @classmethod
    def detect(cls, raw_text: str) -> str:
        """
        Detect the electricity provider from the full raw OCR text.
        Returns the provider ID (e.g., 'MSEDCL') or 'UNKNOWN'.
        """
        text_lower = raw_text.lower()
        best_match = "UNKNOWN"
        highest_score = 0
        
        for provider, keywords in cls.PROVIDERS.items():
            score = 0
            for kw in keywords:
                matches = re.findall(kw, text_lower)
                score += len(matches)
            
            if score > highest_score:
                highest_score = score
                best_match = provider
                
        return best_match
