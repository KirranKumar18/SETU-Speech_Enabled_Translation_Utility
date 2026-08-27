import logging
import urllib.request
import urllib.parse
import json
from typing import Dict, Optional

logger = logging.getLogger("setu.translate")

# Map 2-letter ISO codes to MyMemory language-region pairs for high accuracy
MYMEMORY_LANG_MAP = {
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "en": "en-GB"
}

# Predefined railway announcement dictionary translations for flawless fallback
RAILWAY_DICTIONARY = {
    "hi": {
        "Attention passengers": "यात्री कृपया ध्यान दें",
        "Attention passenger": "यात्री कृपया ध्यान दें",
        "Train number": "गाड़ी संख्या",
        "Train": "गाड़ी",
        "is arriving shortly on platform number": "कुछ ही समय में प्लेटफार्म क्रमांक",
        "is arriving on platform number": "प्लेटफॉर्म संख्या पर आ रही है",
        "is arriving on platform": "प्लेटफॉर्म पर आ रही है",
        "is arriving shortly on platform": "कुछ ही समय में प्लेटफॉर्म पर आ रही है",
        "is arriving": "आ रही है",
        "on platform number": "प्लेटफॉर्म नंबर",
        "on platform": "प्लेटफॉर्म",
        "platform number": "प्लेटफॉर्म नंबर",
        "platform": "प्लेटफॉर्म",
        "delayed by": "देरी से चल रही है",
        "Express": "एक्सप्रेस",
        "Superfast": "सुपरफास्ट",
        "Rajdhani": "राजधानी",
        "Shatabdi": "शताब्दी",
        "Vande Bharat": "वंदे भारत",
        "Mail": "मेल",
        "from": "से",
        "to": "तक"
    },
    "ta": {
        "Attention passengers": "பயணிகள் கவனத்திற்கு",
        "Attention passenger": "பயணிகள் கவனத்திற்கு",
        "Train number": "ரயில் எண்",
        "Train": "ரயில்",
        "is arriving shortly on platform number": "விரைவில் நடைமேடை எண்",
        "is arriving on platform number": "நடைமேடை எண்",
        "is arriving on platform": "நடைமேடை",
        "is arriving shortly on platform": "விரைவில் நடைமேடை",
        "is arriving": "வந்து கொண்டிருக்கிறது",
        "on platform number": "நடைமேடை எண்",
        "on platform": "நடைமேடையில்",
        "platform number": "நடைமேடை எண்",
        "platform": "நடைமேடை",
        "Express": "எக்ஸ்பிரஸ்",
        "Superfast": "சூப்பர்ஃபாஸ்ட்",
        "Rajdhani": "ராஜதானி",
        "Shatabdi": "சதாப்தி",
        "Vande Bharat": "வந்தே பாரத்",
        "Mail": "மெயில்",
        "from": "இருந்து",
        "to": "நோக்கி"
    },
    "te": {
        "Attention passengers": "ప్రయాణికుల దృష్టికి",
        "Attention passenger": "ప్రయాణికుల దృష్టికి",
        "Train number": "రైలు నంబరు",
        "Train": "రైలు",
        "is arriving shortly on platform number": "త్వరలో ప్లాట్‌ఫారమ్ సంఖ్య",
        "is arriving on platform number": "ప్లాట్‌ఫారమ్ సంఖ్యపై వస్తోంది",
        "is arriving on platform": "ప్లాట్‌ఫారమ్‌పై వస్తోంది",
        "is arriving shortly on platform": "త్వరలో ప్లాట్‌ఫారమ్‌పై వస్తోంది",
        "is arriving": "వస్తోంది",
        "on platform number": "ప్లాట్‌ఫారమ్ నంబర్",
        "on platform": "ప్లాట్‌ఫారమ్‌లో",
        "platform number": "ప్లాట్‌ఫారమ్ నంబర్",
        "platform": "ప్లాట్‌ఫారమ్",
        "Express": "ఎక్స్‌ప్రెస్",
        "Superfast": "సూపర్‌ఫాస్ట్",
        "Rajdhani": "రాజధాని",
        "Shatabdi": "శతాబ్ది",
        "Vande Bharat": "వందే భారత్",
        "Mail": "మెయిల్"
    },
    "kn": {
        "Attention passengers": "ಪ್ರಯಾಣಿಕರ ಗಮನಕ್ಕೆ",
        "Attention passenger": "ಪ್ರಯಾಣಿಕರ ಗಮನಕ್ಕೆ",
        "Train number": "ರೈಲು ಸಂಖ್ಯೆ",
        "Train": "ರೈಲು",
        "is arriving shortly on platform number": "ಶೀಘ್ರದಲ್ಲೇ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆ",
        "is arriving on platform number": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆಗೆ ಬರುತ್ತಿದೆ",
        "is arriving on platform": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ಗೆ ಬರುತ್ತಿದೆ",
        "is arriving shortly on platform": "ಶೀಘ್ರದಲ್ಲೇ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ಗೆ ಬರುತ್ತಿದೆ",
        "is arriving": "ಬರುತ್ತಿದೆ",
        "on platform number": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆ",
        "on platform": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ನಲ್ಲಿ",
        "platform number": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆ",
        "platform": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್",
        "Express": "ಎಕ್ಸ್ ಪ್ರೆಸ್",
        "Superfast": "ಸೂಪರ್‌ಫಾಸ್ಟ್",
        "Rajdhani": "ರಾಜಧಾನಿ",
        "Shatabdi": "ಶತಾಬ್ದಿ",
        "Vande Bharat": "ವಂದೇ ಭಾರತ್",
        "Mail": "ಮೇಲ್"
    },
    "mr": {
        "Attention passengers": "यात्र्यांनी कृपया नोंद घ्यावी",
        "Attention passenger": "यात्र्यांनी कृपया नोंद घ्यावी",
        "Train number": "गाडी क्रमांक",
        "Train": "गाडी",
        "is arriving shortly on platform number": "काही वेळात प्लॅटफॉर्म क्रमांक",
        "is arriving on platform number": "प्लॅटफॉर्म क्रमांकावर येत आहे",
        "is arriving on platform": "प्लॅटफॉर्मवर येत आहे",
        "is arriving": "येत आहे",
        "on platform number": "प्लॅटफॉर्म क्रमांक",
        "on platform": "प्लॅटफॉर्मवर",
        "platform number": "प्लॅटफॉर्म क्रमांक",
        "platform": "प्लॅटफॉर्म",
        "Express": "एक्सप्रेस",
        "Superfast": "सुपरफास्ट",
        "Rajdhani": "राजधानी",
        "Shatabdi": "शताब्दी",
        "Vande Bharat": "वंदे भारत",
        "Mail": "मेल"
    },
    "bn": {
        "Attention passengers": "যাত্রী সাধারণের দৃষ্টি আকর্ষণ করা যাচ্ছে",
        "Attention passenger": "যাত্রী সাধারণের দৃষ্টি আকর্ষণ করা যাচ্ছে",
        "Train number": "ট্রেন নম্বর",
        "Train": "ট্রেন",
        "is arriving shortly on platform number": "শীঘ্রই প্ল্যাটফর্ম নম্বর",
        "is arriving on platform number": "নম্বর প্ল্যাটফর্মে আসছে",
        "is arriving on platform": "প্ল্যাটফর্মে আসছে",
        "is arriving": "আসছে",
        "on platform number": "প্ল্যাটফর্ম নম্বর",
        "on platform": "প্ল্যাটফর্মে",
        "platform number": "প্ল্যাটফর্ম নম্বর",
        "platform": "প্ল্যাটফর্ম",
        "Express": "এক্সপ্রেস",
        "Superfast": "সুপারফাস্ট",
        "Rajdhani": "রাজধানী",
        "Shatabdi": "শতাব্দী",
        "Vande Bharat": "বন্দে ভারত",
        "Mail": "মেল"
    },
    "gu": {
        "Attention passengers": "યાત્રીગણ કૃપયા ધ્યાન આપો",
        "Attention passenger": "યાત્રીગણ કૃપયા ધ્યાન આપો",
        "Train number": "ટ્રેન નંબર",
        "Train": "ટ્રેન",
        "is arriving shortly on platform number": "પ્લેટફોર્મ નંબર પર આવી રહી છે",
        "is arriving on platform number": "પ્લેટફોર્મ નંબર પર આવી રહી છે",
        "is arriving on platform": "પ્લેટફોર્મ પર આવી રહી છે",
        "is arriving": "આવી રહી છે",
        "on platform number": "પ્લેટફોર્મ નંબર",
        "on platform": "પ્લેટફોર્મ પર",
        "platform number": "પ્લેટફોર્મ નંબર",
        "platform": "પ્લેટફોર્મ",
        "Express": "એક્સપ્રેસ",
        "Superfast": "સુપરફાસ્ટ",
        "Rajdhani": "રાજધાની",
        "Shatabdi": "શતાબ્દી",
        "Vande Bharat": "વંદે ભારત",
        "Mail": "મેઇલ"
    },
    "ml": {
        "Attention passengers": "യാത്രക്കാരുടെ ശ്രദ്ധയ്ക്ക്",
        "Attention passenger": "യാത്രക്കാരുടെ ശ്രദ്ധയ്ക്ക്",
        "Train number": "ട്രെയിൻ നമ്പർ",
        "Train": "ട്രെയിൻ",
        "is arriving shortly on platform number": "ഉടൻ പ്ലാറ്റ്‌ഫോം നമ്പർ",
        "is arriving on platform number": "പ്ലാറ്റ്‌ഫോം നമ്പറിൽ എത്തും",
        "is arriving on platform": "പ്ലാറ്റ്‌ഫോമിൽ എത്തും",
        "is arriving": "എത്തിച്ചേരുന്നു",
        "on platform number": "പ്ലാറ്റ്‌ഫോം നമ്പർ",
        "on platform": "പ്ലാറ്റ്‌ഫോമിൽ",
        "platform number": "പ്ലാറ്റ്‌ഫോം നമ്പർ",
        "platform": "പ്ലാറ്റ്‌ഫോം",
        "Express": "എക്സ്പ്രസ്",
        "Superfast": "സൂപ്പർഫാസ്റ്റ്",
        "Rajdhani": "രാജധാനി",
        "Shatabdi": "ശതാബ്ദി",
        "Vande Bharat": "വന്ദേ ഭാരത്",
        "Mail": "മെയിൽ"
    },
    "pa": {
        "Attention passengers": "ਯਾਤਰੀ ਕਿਰਪਾ ਕਰਕੇ ਧਿਆਨ ਦੇਣ",
        "Attention passenger": "ਯਾਤਰੀ ਕਿਰਪਾ ਕਰਕੇ ਧਿਆਨ ਦੇਣ",
        "Train number": "ਟਰੇਨ ਨੰਬਰ",
        "Train": "ਟਰੇਨ",
        "is arriving shortly on platform number": "ਜਲਦੀ ਹੀ ਪਲੇਟਫਾਰਮ ਨੰਬਰ",
        "is arriving on platform number": "ਪਲੇਟਫਾਰਮ ਨੰਬਰ 'ਤੇ ਪਹੁੰਚ ਰਹੀ ਹੈ",
        "is arriving on platform": "ਪਲੇਟਫਾਰਮ 'ਤੇ ਪਹੁੰਚ ਰਹੀ ਹੈ",
        "is arriving": "ਪਹੁੰਚ ਰਹੀ ਹੈ",
        "on platform number": "ਪਲੇਟਫਾਰਮ ਨੰਬਰ",
        "on platform": "ਪਲੇਟਫਾਰਮ 'ਤੇ",
        "platform number": "ਪਲੇਟਫਾਰਮ ਨੰਬਰ",
        "platform": "ਪਲੇਟਫਾਰਮ",
        "Express": "ਐਕਸਪ੍ਰੈਸ",
        "Superfast": "ਸੁਪਰਫਾਸਟ",
        "Rajdhani": "ਰਾਜਧਾਨੀ",
        "Shatabdi": "ਸ਼ਤਾਬਦੀ",
        "Vande Bharat": "ਵੰਦੇ ਭਾਰਤ",
        "Mail": "ਮੇਲ"
    }
}

def translate_via_mymemory(text: str, target_lang: str, source_lang: str = "en") -> Optional[str]:
    """Translate text using MyMemory Translation API."""
    try:
        sl = MYMEMORY_LANG_MAP.get(source_lang.lower(), "en-GB")
        tl = MYMEMORY_LANG_MAP.get(target_lang.lower(), target_lang)
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={sl}|{tl}"
        req = urllib.request.Request(url, headers={"User-Agent": "SETU-Translator/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = data.get("responseData", {}).get("translatedText", "").strip()
            if translated and not translated.startswith("MYMEMORY WARNING"):
                # Clean up any HTML entities like &#39;
                import html
                return html.unescape(translated)
    except Exception as e:
        logger.debug(f"MyMemory API failed for {target_lang}: {e}")
    return None

def translate_via_google_translator(text: str, target_lang: str, source_lang: str = "en") -> Optional[str]:
    """Translate text using deep_translator GoogleTranslator."""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        if translated and len(translated.strip()) > 0 and not translated.startswith("Error 500"):
            return translated.strip()
    except Exception as e:
        logger.debug(f"GoogleTranslator failed for {target_lang}: {e}")
    return None

def translate_via_dictionary_fallback(text: str, target_lang: str) -> str:
    """Intelligent fallback for offline/emergency railway phrase translation."""
    dict_map = RAILWAY_DICTIONARY.get(target_lang, {})
    # Sort phrases by descending length so longer phrases get replaced first
    sorted_phrases = sorted(dict_map.keys(), key=len, reverse=True)
    translated_text = text
    for en_phrase in sorted_phrases:
        target_phrase = dict_map[en_phrase]
        # Case-insensitive replacement preserving surrounding text
        import re
        pattern = re.compile(re.escape(en_phrase), re.IGNORECASE)
        translated_text = pattern.sub(target_phrase, translated_text)
    return translated_text

def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """
    Translates text from source language to target Indian regional language.
    Cascades: MyMemory API -> Google Translator -> Dictionary Fallback.
    """
    text = text.strip()
    if not text:
        return ""

    if source_lang.lower() == target_lang.lower():
        return text

    # 1. Primary Engine: MyMemory API
    res = translate_via_mymemory(text, target_lang=target_lang, source_lang=source_lang)
    if res:
        return res

    # 2. Secondary Engine: Google Translator
    res = translate_via_google_translator(text, target_lang=target_lang, source_lang=source_lang)
    if res:
        return res

    # 3. Tertiary Engine: Domain Dictionary Fallback
    logger.info(f"Using Railway Dictionary fallback for language '{target_lang}'")
    return translate_via_dictionary_fallback(text, target_lang)

def translate_to_all_supported_languages(text: str, source_lang: str = "en") -> Dict[str, str]:
    """Translates input transcript into all supported regional languages and logs output."""
    supported_langs = ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa"]
    lang_names = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
        "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati", "ml": "Malayalam", "pa": "Punjabi"
    }

    results = {}

    print("\n" + "="*70)
    print(f"🌐 [SETU MULTILINGUAL TRANSLATION PIPELINE]")
    print(f"   Original Text ({source_lang.upper()}): {text}")
    print("-" * 70)

    for lang in supported_langs:
        try:
            translated = translate_text(text, target_lang=lang, source_lang=source_lang)
            results[lang] = translated
            name = lang_names.get(lang, lang.upper())
            print(f"   [{lang.upper()}] {name:<10}: {translated}")
        except Exception as e:
            logger.error(f"Translation failed for lang '{lang}': {e}")
            results[lang] = text
            print(f"   [{lang.upper()}] FAILED    : {text}")

    print("="*70 + "\n", flush=True)
    return results
