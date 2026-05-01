from __future__ import annotations

# Universal regex patterns for various fields across English, Marathi, Hindi, Gujarati, Tamil, Telugu, Kannada
LABEL_PATTERNS = {
    "customer_name": [
        r"(?:consumer\s*name|customer\s*name|name\s*of\s*consumer|ग्राहकाचे\s*नाव|उपभोक्ता\s*का\s*नाम|ಗ್ರಾಹಕರ\s*ಹೆಸರು|வாடிக்கையாளர்\s*பெயர்)\s*[:\-]?\s*([A-Z][A-Z\s\.]{4,60})",
    ],
    "consumer_number": [
        r"(?:consumer\s*no|consumer\s*number|service\s*no|account\s*no|account\s*number|ग्राहक\s*क्रमांक|ಖಾತೆ\s*ಸಂಖ್ಯೆ|கணக்கு\s*எண்)\s*[:\-]?\s*([0-9]{9,13})",
    ],
    "billing_month": [
        r"(?:bill\s*of\s*supply\s*for\s*the\s*month\s*of|billing\s*month|bill\s*month|महिना|बिल\s*माह|ತಿಂಗಳು|மாதம்)\s*[:\-]?\s*([A-Za-z0-9\-\/ ]{5,20})",
    ],
    "bill_amount": [
        r"(?:bill\s*amount|amount\s*payable|current\s*bill\s*amount|total\s*amount|net\s*payable|देयक\s*रक्कम|कुल\s*राशि|ಒಟ್ಟು\s*ಮೊತ್ತ|மொத்த\s*தொகை)\s*[:\-]?\s*(?:rs\.?|₹|inr)?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "units_consumed": [
        r"(?:units\s*consumed|total\s*units|energy\s*consumed|billed\s*units|consumption|एकूण\s*वापर|कुल\s*खपत|ಬಳಸಿದ\s*ಯೂನಿಟ್|பயன்படுத்தப்பட்ட\s*அலகுகள்)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "connected_load_kw": [
        r"(?:connected\s*load|sanctioned\s*load|मंजूर\s*भार|स्वीकृत\s*भार|ಮಂಜೂರಾದ\s*ಲೋಡ್)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)\s*(?:kw|kva)?",
    ],
    "tariff_category": [
        r"(?:tariff\s*category|tariff|category|दर\s*प्रकार|टैरिफ|ಸುಂಕ|கட்டண)\s*[:\-]?\s*([A-Za-z0-9\-\s\/\|]{3,40})",
    ],
    "meter_number": [
        r"(?:meter\s*no|meter\s*number|मीटर\s*क्रमांक|मीटर\s*संख्या|ಮೀಟರ್\s*ಸಂಖ್ಯೆ|மீட்டர்\s*எண்)\s*[:\-]?\s*([A-Za-z0-9\-]{6,16})",
    ],
    "due_date": [
        r"(?:due\s*date|payment\s*due\s*date|देय\s*दिनांक|नियत\s*तिथि|ಗಡುವು\s*ದಿನಾಂಕ|கெடு\s*தேதி)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
    ],
    "current_reading": [
        r"(?:current\s*reading|present\s*reading|चालू\s*रिडिंग|वर्तमान\s*रीडिंग|ಪ್ರಸ್ತುತ\s*ಓದುವಿಕೆ|தற்போதைய\s*வாசிப்பு)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "previous_reading": [
        r"(?:previous\s*reading|past\s*reading|मागील\s*रिडिंग|पिछली\s*रीडिंग|ಹಿಂದಿನ\s*ಓದುವಿಕೆ|முந்தைய\s*வாசிப்பு)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
}

MONTH_MAP = {
    "jan": "JAN", "janevari": "JAN", "जानेवारी": "JAN", "tf4t": "JAN", "jnatt": "JAN", "जनवरी": "JAN",
    "feb": "FEB", "februari": "FEB", "फेब्रुवारी": "FEB", "फरवरी": "FEB",
    "mar": "MAR", "march": "MAR", "मार्च": "MAR",
    "apr": "APR", "april": "APR", "एप्रिल": "APR", "अप्रैल": "APR",
    "may": "MAY", "मे": "MAY", "मई": "MAY",
    "jun": "JUN", "june": "JUN", "जून": "JUN",
    "jul": "JUL", "july": "JUL", "जुलै": "JUL", "जुलाई": "JUL",
    "aug": "AUG", "august": "AUG", "ऑगस्ट": "AUG", "अगस्त": "AUG",
    "sep": "SEP", "september": "SEP", "सप्टेंबर": "SEP", "सितंबर": "SEP",
    "oct": "OCT", "october": "OCT", "ऑक्टोबर": "OCT", "अक्टूबर": "OCT",
    "nov": "NOV", "november": "NOV", "नोव्हेंबर": "NOV", "नवंबर": "NOV",
    "dec": "DEC", "december": "DEC", "डिसेंबर": "DEC", "दिसंबर": "DEC",
}
