# script.py

class Script:
    START_TXT = (
        "👋 **Hello {first_name}!**\n\n"
        "Welcome to the **Audio Story File Store Bot**.\n"
        "Click episode buttons in the channel to get your audio files."
    )

    FSUB_TXT = (
        "⚠️ **Force Subscribe Notice!**\n\n"
        "फाइल्स एक्सेस करने के लिए आपको हमारे स्पॉन्सर चैनल्स को जॉइन करना अनिवार्य है।\n"
        "नीचे दिए गए चैनल्स जॉइन करें और फिर **Try Again** पर क्लिक करें।"
    )

    BANNED_TXT = (
        "🚫 **You are BANNED from using this bot!**\n\n"
        "📝 **Reason:** `{reason}`\n"
        "💬 Contact support if you think this is a mistake."
    )

    VERIFY_REQ_TXT = (
        "🔒 **Access Verification Required!**\n\n"
        "Please verify access to gain file availability for **{expire_hours} Hours**.\n\n"
        "⏱️ *Note: Complete verification properly without bypass scripts.*"
    )

    VERIFY_SUCCESS_TXT = (
        "🎉 **Verification Successful!**\n\n"
        "Your file access is active for **{hours} Hours**. Sending your files now..."
    )

    TOKEN_EXPIRED_TXT = (
        "❌ **Token Expired or Already Used!**\n\n"
        "यह टोकन पहले ही यूज़ या एक्सपायर किया जा चुका है। कृपया नया लिंक जनरेट करें।"
    )

    AUTO_DEL_WARN_TXT = (
        "⚠️ **Important:**\n\n"
        "All Messages will be deleted after **{del_min} minutes**. "
        "Please save or forward these messages to your personal saved messages to avoid losing them!"
    )

    AUTO_DEL_DONE_TXT = (
        "🗑️ **Your files have been auto-deleted to protect content rights.**\n\n"
        "If you want the files again, click the button below!"
    )

    FUNNY_HACKER_MESSAGES = [
        "🚨 **WHOA BRO! SLOW DOWN!** 🏎️💨\n\nआप इतनी जल्दी तो Flash भी नहीं आ सकता! 🧙‍♂️\nबॉट बाईपास करने की कोशिश? पकड़े गए! 🤖💥\n*(Warning {strike}/3 - 3 स्ट्राइक पर ऑटोमैटिक बैन कर दिया जाएगा!)*",
        "🕵️‍♂️ **Hey Anonymous Hacker!**\n\nscript चला के सोचे थे 2 सेकंड में फाइल मिल जाएगी? 😎\nस्मार्ट आप हो, तो अति-स्मार्ट हम हैं! 🗿\n*(Warning {strike}/3: 3 बार बाईपास करने पर हमेशा के लिए बैन हो जाओगे!)*",
        "🤖 **SYSTEM ALERT: Bypasser Spotted!** 🎯\n\n2 मिनट का रास्ता 5 सेकंड में? उड़ के गए थे क्या? ✈️\nना ना ना! चीटिंग नहीं चलेगी। टोकन Expire कर दिया गया है! 🚫\n*(Strike {strike}/3: सावधान रहें!)*"
    ]

   

    PLEASE_WAIT_TXT = "⚠️ **PLEASE WAIT**\n\nआपकी फाइल्स भेजी जा रही हैं, कृपया प्रतीक्षा करें..."
    CANCELLED_TXT = "❌ **फाइल डिलीवरी यूज़र द्वारा कैंसिल कर दी गई है!**"
    
