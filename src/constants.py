"""
This file contains all the constants used in the program.
"""

TWITTER_TEXTAREA_CLASS = "public-DraftStyleDefault-block public-DraftStyleDefault-ltr"
TWITTER_POST_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div[2]/div[1]/div/div/div/div[2]/div[2]/div[2]/div/div/div/div[3]"

OPTIONS = [
    "YouTube Shorts Automation",
    "Twitter Bot",
    "Affiliate Marketing",
    "Outreach",
    "Quit",
]

TWITTER_OPTIONS = ["Post something", "Show all Posts", "Setup CRON Job", "Quit"]


TWITTER_CRON_OPTIONS = ["Once a day", "Twice a day", "Thrice a day", "Quit"]

YOUTUBE_OPTIONS = [
    "Generate Video (Preview)",
    "Upload Short",
    "Show all Shorts",
    "Setup CRON Job",
    "Generate & Upload to All Platforms",
    "Upload to All Platforms (YouTube + Facebook + TikTok)",
    "Upload to Facebook",
    "Upload to TikTok",
    "Quit",
]

YOUTUBE_CRON_OPTIONS = ["Once a day", "Twice a day", "Thrice a day", "Quit"]

# YouTube Section
YOUTUBE_TEXTBOX_ID = "textbox"
YOUTUBE_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_MFK"
YOUTUBE_NOT_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_NOT_MFK"
YOUTUBE_NEXT_BUTTON_ID = "next-button"
YOUTUBE_RADIO_BUTTON_XPATH = '//*[@id="radioLabel"]'
YOUTUBE_DONE_BUTTON_ID = "done-button"

# TikTok Section
TIKTOK_UPLOAD_BUTTON = 'button[data-e2e="upload-button"]'
TIKTOK_TEXTBOX_ID = 'div[class*="DraftEditor"]'
TIKTOK_NEXT_BUTTON = 'button[data-e2e="next-button"]'
TIKTOK_DONE_BUTTON = 'button:contains("Post")'
TIKTOK_TITLE_INPUT = 'input[placeholder*="title"]'
TIKTOK_DESCRIPTION = 'textarea[placeholder*="description"]'
TIKTOK_HASHTAGS = 'input[placeholder*="hashtags"]'

# Amazon Section (AFM)$
AMAZON_PRODUCT_TITLE_ID = "productTitle"
AMAZON_FEATURE_BULLETS_ID = "feature-bullets"
