# Role Constants
OWNER = "owner"
SUDO = "sudo"
UPLOADER = "uploader"

ROLES = [OWNER, SUDO, UPLOADER]

# Display Names (small caps, futuristic-themed)
ROLE_DISPLAY = {
    OWNER: "⟪ ᴏᴡɴᴇʀ ⟫",
    SUDO: "⊘ sᴜᴅᴏ",
    UPLOADER: "≡ ᴜᴘʟᴏᴀᴅᴇʀ"
}

# Hierarchical Permissions Map
PERMISSIONS = {
    OWNER: [SUDO, UPLOADER],
    SUDO: [UPLOADER],
    # Only superuser can appoint OWNER
}

# Superuser (Only person who can assign OWNERs)
SUPERUSER_ID = 6783092268

# Preview image and caption
PREVIEW_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"
PREVIEW_CAPTION = (
    "⤷ ᴍᴏᴅᴜʟᴀʀ ʀᴏʟᴇ ᴘᴀɴᴇʟ\n"
    "• structured ʜɪᴇʀᴀʀᴄʜʏ ᴇɴꜰᴏʀᴄᴇᴅ\n"
    "• ⟪ ᴏɴᴇ ʀᴏʟᴇ ᴘᴇʀ ᴜꜱᴇʀ ⟫\n"
    "• ꜰᴜᴛᴜʀɪꜱᴛɪᴄ ɪɴᴛᴇʀғᴀᴄᴇ\n"
)
