# shivu/sudo/constants.py

# Role Names
OWNER = "owner"
SUDO = "sudo"
UPLOADER = "uploader"

ROLES = [OWNER, SUDO, UPLOADER]

# Role Display (small caps + futuristic)
ROLE_DISPLAY = {
    OWNER: "⟪ ᴏᴡɴᴇʀ ⟫",
    SUDO: "⊘ sᴜᴅᴏ",
    UPLOADER: "≡ ᴜᴘʟᴏᴀᴅᴇʀ"
}

# Permissions Map: who can appoint whom
PERMISSIONS = {
    OWNER: [SUDO, UPLOADER],
    SUDO: [UPLOADER],
    # Only SUPERUSER can appoint OWNER
}

# Static superuser ID (full power)
SUPERUSER_ID = 6783092268

# UI Media (used in /sudo panel view)
PREVIEW_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"
PREVIEW_CAPTION = (
    "⤷ ᴍᴏᴅᴜʟᴀʀ ʀᴏʟᴇ ᴘᴀɴᴇʟ\n"
    "• structured ʜɪᴇʀᴀʀᴄʜʏ ᴇɴꜰᴏʀᴄᴇᴅ\n"
    "• ⟪ ᴏɴᴇ ʀᴏʟᴇ ᴘᴇʀ ᴜꜱᴇʀ ⟫\n"
    "• ꜰᴜᴛᴜʀɪꜱᴛɪᴄ ɪɴᴛᴇʀғᴀᴄᴇ\n"
)
