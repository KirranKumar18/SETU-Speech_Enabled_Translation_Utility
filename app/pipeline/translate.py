import logging
from typing import Dict, Optional

logger = logging.getLogger("setu.translate")

# Predefined railway announcement dictionary translations for flawless accuracy in common phrasing
RAILWAY_DICTIONARY = {
    "hi": {
        "Attention passengers": "यात्री कृपया ध्यान दें",
        "Train number": "गाड़ी संख्या",
        "is arriving shortly on platform number": "कुछ ही समय में प्लेटफार्म क्रमांक",
        "is arriving on platform number": "प्लेटफॉर्म संख्या पर आ रही है",
        "on platform number": "प्लेटफॉर्म नंबर",
        "delayed by": "देरी से चल रही है",
        "Express": "एक्सप्रेस"
    },
    "ta": {
        "Attention passengers": "பயணிகள் கவனத்திற்கு",
        "Train number": "ரயில் எண்",
        "is arriving shortly on platform number": "விரைவில் நடைமேடை எண்",
        "on platform number": "நடைமேடை எண்",
        "Express": "எக்ஸ்பிரஸ்"
    },
    "te": {
        "Attention passengers": "ప్రయాణికుల దృష్టికి",
        "Train number": "రైలు నంబరు",
        "is arriving shortly on platform number": "త్వరలో ప్లాట్‌ఫారమ్ సంఖ్య",
        "on platform number": "ప్లాట్‌ఫారమ్ నంబర్",
        "Express": "ఎక్స్‌ప్రెస్"
    },
    "kn": {
        "Attention passengers": "ಪ್ರಯಾಣಿಕರ ಗಮನಕ್ಕೆ",
        "Train number": "ರೈಲು ಸಂಖ್ಯೆ",
        "is arriving shortly on platform number": "ಶೀಘ್ರದಲ್ಲೇ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆ",
        "on platform number": "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಸಂಖ್ಯೆ",
        "Express": "ಎಕ್ಸ್ ಪ್ರೆಸ್"
    },
    "mr": {
        "Attention passengers": "यात्र्यांनी कृपया नोंद घ्यावी",
        "Train number": "गाडी क्रमांक",
        "is arriving shortly on platform number": "काही वेळात प्लॅटफॉर्म क्रमांक",
        "on platform number": "प्लॅटफॉर्म क्रमांक",
        "Express": "एक्सप्रेस"
    },
    "bn": {
        "Attention passengers": "যাত্রী সাধারণের দৃষ্টি আকর্ষণ করা যাচ্ছে",
        "Train number": "ট্রেন নম্বর",
        "is arriving shortly on platform number": "শীঘ্রই প্ল্যাটফর্ম নম্বর",
        "on platform number": "প্ল্যাটফর্ম নম্বর",
        "Express": "এক্সপ্রেস"
    },
    "gu": {
        "Attention passengers": "યાત્રીગણ કૃપયા ધ્યાન આપો",
        "Train number": "ટ્રેન નંબર",
        "is arriving shortly on platform number": "પ્લેટફોર્મ નંબર",
        "on platform number": "પ્લેટફોર્મ નંબર",
        "Express": "એક્સપ્રેસ"
    },
    "ml": {
        "Attention passengers": "യാത്രക്കാരുടെ ശ്രദ്ധയ്ക്ക്",
        "Train number": "ട്രെയിൻ നമ്പർ",
        "is arriving shortly on platform number": "ഉടൻ പ്ലാറ്റ്‌ഫോം നമ്പർ",
        "on platform number": "പ്ലാറ്റ്‌ഫോം നമ്പർ",
        "Express": "എക്സ്പ്രസ്"
    },
    "pa": {
        "Attention passengers": "ਯਾਤਰੀ ਕਿਰਪਾ ਕਰਕੇ ਧਿਆਨ ਦੇਣ",
        "Train number": "ਟਰੇਨ ਨੰਬਰ",
        "is arriving shortly on platform number": "ਜਲਦੀ ਹੀ ਪਲੇਟਫਾਰਮ ਨੰਬਰ",
        "on platform number": "ਪਲੇਟਫਾਰਮ ਨੰਬਰ",
        "Express": "ਐਕਸਪ੍ਰੈਸ"
    }
}

# Hugging Face IndicTrans2 Pipeline Cache
_indictrans_model = None
_indictrans_tokenizer = None

def load_indictrans2():
    """Attempt loading AI4Bharat IndicTrans2 model if transformers/torch installed."""
    global _indictrans_model, _indictrans_tokenizer
    if _indictrans_model is None:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            model_name = "ai4bharat/indictrans2-en-indic-1B"
            logger.info(f"Attempting to load IndicTrans2 model '{model_name}'...")
            _indictrans_tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            _indictrans_model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)
            logger.info("IndicTrans2 model loaded successfully.")
        except Exception as e:
            logger.info(f"IndicTrans2 local model load skipped ({e}). Falling back to multi-engine translation pipeline.")
            _indictrans_model = "fallback"
    return _indictrans_model, _indictrans_tokenizer

def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """
    Translates text from source language to target Indian regional language.
    Uses IndicTrans2 if present, followed by deep_translator / GoogleTranslate API fallback.
    """
    text = text.strip()
    if not text:
        return ""

    if source_lang.lower() == target_lang.lower():
        return text

    # Try deep-translator GoogleTranslator engine first for fast, reliable demo performance
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        if translated and len(translated.strip()) > 0:
            return translated.strip()
    except Exception as e:
        logger.warning(f"GoogleTranslator fallback error for {target_lang}: {e}")

    # Try IndicTrans2 model if available
    model, tokenizer = load_indictrans2()
    if model != "fallback" and model is not None and tokenizer is not None:
        try:
            # Format inputs for IndicTrans2
            inputs = tokenizer(text, return_tensors="pt", padding=True)
            generated_tokens = model.generate(**inputs, max_length=256)
            translated = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            if translated:
                return translated.strip()
        except Exception as e:
            logger.error(f"IndicTrans2 generation failed: {e}")

    # Fallback to dictionary pattern replacement for offline/resilient hackathon demo
    dict_map = RAILWAY_DICTIONARY.get(target_lang, {})
    translated_text = text
    for en_phrase, target_phrase in dict_map.items():
        translated_text = translated_text.replace(en_phrase, target_phrase)

    return translated_text

def translate_to_all_supported_languages(text: str, source_lang: str = "en") -> Dict[str, str]:
    """Translates input transcript into all supported regional languages."""
    supported_langs = ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa"]
    results = {}
    for lang in supported_langs:
        try:
            results[lang] = translate_text(text, target_lang=lang, source_lang=source_lang)
        except Exception as e:
            logger.error(f"Translation failed for lang '{lang}': {e}")
            results[lang] = text
    return results
