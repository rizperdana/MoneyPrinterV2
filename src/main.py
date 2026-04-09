import os
import sys
import schedule
import subprocess

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from art import print_banner
from cache import get_accounts, add_account, remove_account, get_products, add_product
from utils import rem_temp_files, fetch_songs
from config import (
    ROOT_DIR,
    get_verbose,
    get_first_time_running,
    assert_folder_structure,
    get_default_model,
)
from llm_provider import get_active_model, select_model, list_models
from status import error, success, info, warning, question
from constants import (
    OPTIONS,
    YOUTUBE_OPTIONS,
    TWITTER_OPTIONS,
    YOUTUBE_CRON_OPTIONS,
    TWITTER_CRON_OPTIONS,
)
from uuid import uuid4
from termcolor import colored
from classes.Twitter import Twitter
from classes.YouTube import YouTube
from prettytable import PrettyTable
from classes.Outreach import Outreach
from classes.AFM import AffiliateMarketing

try:
    from classes.Tts import TTS

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    TTS = None


def main():
    """Main entry point for the application, providing a menu-driven interface
    to manage YouTube, Twitter bots, Affiliate Marketing, and Outreach tasks.

    This function allows users to:
    1. Start the YouTube Shorts Automater to manage YouTube accounts,
       generate and upload videos, and set up CRON jobs.
    2. Start a Twitter Bot to manage Twitter accounts, post tweets, and
       schedule posts using CRON jobs.
    3. Manage Affiliate Marketing by creating pitches and sharing them via
       Twitter accounts.
    4. Initiate an Outreach process for engagement and promotion tasks.
    5. Exit the application.

    The function continuously prompts users for input, validates it, and
    executes the selected option until the user chooses to quit.

    Args:
        None

    Returns:
        None"""

    # Get user input
    # user_input = int(question("Select an option: "))
    valid_input = False
    while not valid_input:
        try:
            # Show user options
            info("\n============ OPTIONS ============", False)

            for idx, option in enumerate(OPTIONS):
                print(colored(f" {idx + 1}. {option}", "cyan"))

            info("=================================\n", False)
            user_input = input("Select an option: ").strip()
            if user_input == "":
                print("\n" * 100)
                raise ValueError("Empty input is not allowed.")
            user_input = int(user_input)
            valid_input = True
        except ValueError as e:
            print("\n" * 100)
            print(f"Invalid input: {e}")

    # Start the selected option
    if user_input == 1:
        info("Starting YT Shorts Automater...")

        cached_accounts = get_accounts("youtube")

        if len(cached_accounts) == 0:
            warning("No accounts found in cache. Create one now?")
            user_input = question("Yes/No: ")

            if user_input.lower() == "yes":
                generated_uuid = str(uuid4())

                success(f" => Generated ID: {generated_uuid}")
                nickname = question(" => Enter a nickname for this account: ")
                fp_profile = question(" => Enter the path to the Firefox profile: ")
                niche = question(" => Enter the account niche: ")
                language = question(" => Enter the account language: ")

                account_data = {
                    "id": generated_uuid,
                    "nickname": nickname,
                    "firefox_profile": fp_profile,
                    "niche": niche,
                    "language": language,
                    "videos": [],
                }

                add_account("youtube", account_data)

                success("Account configured successfully!")
        else:
            table = PrettyTable()
            table.field_names = ["ID", "UUID", "Nickname", "Niche"]

            for account in cached_accounts:
                table.add_row(
                    [
                        cached_accounts.index(account) + 1,
                        colored(account["id"], "cyan"),
                        colored(account["nickname"], "blue"),
                        colored(account["niche"], "green"),
                    ]
                )

            print(table)
            info("Type 'd' to delete an account.", False)

            user_input = question(
                "Select an account to start (or 'd' to delete): "
            ).strip()

            if user_input.lower() == "d":
                delete_input = question("Enter account number to delete: ").strip()
                account_to_delete = None

                for account in cached_accounts:
                    if str(cached_accounts.index(account) + 1) == delete_input:
                        account_to_delete = account
                        break

                if account_to_delete is None:
                    error("Invalid account selected. Please try again.", "red")
                else:
                    confirm = (
                        question(
                            f"Are you sure you want to delete '{account_to_delete['nickname']}'? (Yes/No): "
                        )
                        .strip()
                        .lower()
                    )

                    if confirm == "yes":
                        remove_account("youtube", account_to_delete["id"])
                        success("Account removed successfully!")
                    else:
                        warning("Account deletion canceled.", False)

                return

            selected_account = None

            for account in cached_accounts:
                if str(cached_accounts.index(account) + 1) == user_input:
                    selected_account = account

            if selected_account is None:
                error("Invalid account selected. Please try again.", "red")
                main()
            else:
                youtube = YouTube(
                    selected_account["id"],
                    selected_account["nickname"],
                    selected_account["firefox_profile"],
                    selected_account["niche"],
                    selected_account["language"],
                )

                while True:
                    rem_temp_files()
                    info("\n============ OPTIONS ============", False)

                    for idx, youtube_option in enumerate(YOUTUBE_OPTIONS):
                        print(colored(f" {idx + 1}. {youtube_option}", "cyan"))

                    info("=================================\n", False)

                    # Get user input
                    user_input = int(question("Select an option: "))

                    if not TTS_AVAILABLE:
                        error("TTS not available - install kittentts")
                        break

                    tts = TTS()

                    if user_input == 1:
                        # Generate Video (Preview) - no upload
                        youtube.generate_video(tts)
                        # Copy to visible output folder
                        import shutil

                        output_dir = os.path.join(ROOT_DIR, "output")
                        os.makedirs(output_dir, exist_ok=True)
                        video_name = os.path.basename(youtube.video_path)
                        output_path = os.path.join(output_dir, video_name)
                        shutil.copy2(youtube.video_path, output_path)
                        success(f"Video saved to: {output_path}")
                        info(
                            "Review the video. Use 'Upload Short' to publish when ready."
                        )
                    elif user_input == 2:
                        # Generate + Upload
                        youtube.generate_video(tts)
                        upload_to_yt = question(
                            "Do you want to upload this video to YouTube? (Yes/No): "
                        )
                        if upload_to_yt.lower() == "yes":
                            upload_success = youtube.upload_video()
                            if upload_success:
                                maybe_crosspost_youtube_short(
                                    video_path=youtube.video_path,
                                    title=youtube.metadata.get("title", ""),
                                    interactive=True,
                                )
                            else:
                                warning(
                                    "YouTube upload failed. Skipping Post Bridge cross-post."
                                )
                    elif user_input == 3:
                        videos = youtube.get_videos()

                        if len(videos) > 0:
                            videos_table = PrettyTable()
                            videos_table.field_names = ["ID", "Date", "Title"]

                            for video in videos:
                                videos_table.add_row(
                                    [
                                        videos.index(video) + 1,
                                        colored(video["date"], "blue"),
                                        colored(video["title"][:60] + "...", "green"),
                                    ]
                                )

                            print(videos_table)
                        else:
                            warning(" No videos found.")
                    elif user_input == 4:
                        info("How often do you want to upload?")

                        info("\n============ OPTIONS ============", False)
                        for idx, cron_option in enumerate(YOUTUBE_CRON_OPTIONS):
                            print(colored(f" {idx + 1}. {cron_option}", "cyan"))

                        info("=================================\n", False)

                        user_input = int(question("Select an Option: "))

                        cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
                        command = [
                            "python",
                            cron_script_path,
                            "youtube",
                            selected_account["id"],
                            get_active_model(),
                        ]

                        def job():
                            subprocess.run(command)

                        if user_input == 1:
                            # Upload Once
                            schedule.every(1).day.do(job)
                            success("Set up CRON Job.")
                        elif user_input == 2:
                            # Upload Twice a day
                            schedule.every().day.at("10:00").do(job)
                            schedule.every().day.at("16:00").do(job)
                            success("Set up CRON Job.")
                        else:
                            break
                    elif user_input == 5:
                        # Upload to All Platforms
                        if not TTS_AVAILABLE:
                            error("TTS not available - install edge-tts")
                            break
                        tts = TTS()
                        youtube.generate_video(tts)
                        # Copy to visible output folder
                        import shutil

                        output_dir = os.path.join(ROOT_DIR, "output")
                        os.makedirs(output_dir, exist_ok=True)
                        video_name = os.path.basename(youtube.video_path)
                        output_path = os.path.join(output_dir, video_name)
                        shutil.copy2(youtube.video_path, output_path)
                        success(f"Video saved to: {output_path}")
                        info("Uploading to all platforms...")
                        results = youtube.upload_to_all_platforms()
                        for platform, (success_flag, result) in results.items():
                            if success_flag:
                                success(f"  {platform}: {result}")
                            else:
                                warning(f"  {platform}: {result}")
                        # Save results to JSON
                        import json
                        from datetime import datetime

                        result_data = {
                            "timestamp": datetime.now().isoformat(),
                            "youtube": {
                                "success": results.get("youtube", (False, ""))[0],
                                "url": results.get("youtube", (False, ""))[1]
                                if results.get("youtube", (False, ""))[0]
                                else None,
                            },
                            "tiktok": {
                                "success": results.get("tiktok", (False, ""))[0],
                                "url": results.get("tiktok", (False, ""))[1]
                                if results.get("tiktok", (False, ""))[0]
                                else None,
                            },
                            "facebook": {
                                "success": results.get("facebook", (False, ""))[0],
                                "url": results.get("facebook", (False, ""))[1]
                                if results.get("facebook", (False, ""))[0]
                                else None,
                            },
                        }
                        result_path = os.path.join(ROOT_DIR, "upload_results.json")
                        with open(result_path, "w") as f:
                            json.dump(result_data, f, indent=2)
                        info(f"Results saved to: {result_path}")
                    elif user_input == 6:
                        # Upload to Facebook only
                        if not hasattr(youtube, "video_path") or not youtube.video_path:
                            error("No video generated yet. Use 'Generate Video' first.")
                            break
                        info("Uploading to Facebook...")
                        fb_success, fb_url = youtube.upload_to_facebook()
                        if fb_success:
                            success(f"Facebook upload successful! URL: {fb_url}")
                        else:
                            warning(f"Facebook upload failed: {fb_url}")
                    elif user_input == 7:
                        # Upload to TikTok only
                        if not hasattr(youtube, "video_path") or not youtube.video_path:
                            error("No video generated yet. Use 'Generate Video' first.")
                            break
                        info("Uploading to TikTok...")
                        tt_success, tt_url = youtube.upload_to_tiktok()
                        if tt_success:
                            success(f"TikTok upload successful! URL: {tt_url}")
                        else:
                            warning(f"TikTok upload failed: {tt_url}")
                    elif user_input == 8:
                        if get_verbose():
                            info(" => Climbing Options Ladder...", False)
                        break
    elif user_input == 2:
        info("Starting Twitter Bot...")

        cached_accounts = get_accounts("twitter")

        if len(cached_accounts) == 0:
            warning("No accounts found in cache. Create one now?")
            user_input = question("Yes/No: ")

            if user_input.lower() == "yes":
                generated_uuid = str(uuid4())

                success(f" => Generated ID: {generated_uuid}")
                nickname = question(" => Enter a nickname for this account: ")
                fp_profile = question(" => Enter the path to the Firefox profile: ")
                topic = question(" => Enter the account topic: ")

                add_account(
                    "twitter",
                    {
                        "id": generated_uuid,
                        "nickname": nickname,
                        "firefox_profile": fp_profile,
                        "topic": topic,
                        "posts": [],
                    },
                )
        else:
            table = PrettyTable()
            table.field_names = ["ID", "UUID", "Nickname", "Account Topic"]

            for account in cached_accounts:
                table.add_row(
                    [
                        cached_accounts.index(account) + 1,
                        colored(account["id"], "cyan"),
                        colored(account["nickname"], "blue"),
                        colored(account["topic"], "green"),
                    ]
                )

            print(table)
            info("Type 'd' to delete an account.", False)

            user_input = question(
                "Select an account to start (or 'd' to delete): "
            ).strip()

            if user_input.lower() == "d":
                delete_input = question("Enter account number to delete: ").strip()
                account_to_delete = None

                for account in cached_accounts:
                    if str(cached_accounts.index(account) + 1) == delete_input:
                        account_to_delete = account
                        break

                if account_to_delete is None:
                    error("Invalid account selected. Please try again.", "red")
                else:
                    confirm = (
                        question(
                            f"Are you sure you want to delete '{account_to_delete['nickname']}'? (Yes/No): "
                        )
                        .strip()
                        .lower()
                    )

                    if confirm == "yes":
                        remove_account("twitter", account_to_delete["id"])
                        success("Account removed successfully!")
                    else:
                        warning("Account deletion canceled.", False)

                return

            selected_account = None

            for account in cached_accounts:
                if str(cached_accounts.index(account) + 1) == user_input:
                    selected_account = account

            if selected_account is None:
                error("Invalid account selected. Please try again.", "red")
                main()
            else:
                twitter = Twitter(
                    selected_account["id"],
                    selected_account["nickname"],
                    selected_account["firefox_profile"],
                    selected_account["topic"],
                )

                while True:
                    info("\n============ OPTIONS ============", False)

                    for idx, twitter_option in enumerate(TWITTER_OPTIONS):
                        print(colored(f" {idx + 1}. {twitter_option}", "cyan"))

                    info("=================================\n", False)

                    # Get user input
                    user_input = int(question("Select an option: "))

                    if user_input == 1:
                        twitter.post()
                    elif user_input == 2:
                        posts = twitter.get_posts()

                        posts_table = PrettyTable()

                        posts_table.field_names = ["ID", "Date", "Content"]

                        for post in posts:
                            posts_table.add_row(
                                [
                                    posts.index(post) + 1,
                                    colored(post["date"], "blue"),
                                    colored(post["content"][:60] + "...", "green"),
                                ]
                            )

                        print(posts_table)
                    elif user_input == 3:
                        info("How often do you want to post?")

                        info("\n============ OPTIONS ============", False)
                        for idx, cron_option in enumerate(TWITTER_CRON_OPTIONS):
                            print(colored(f" {idx + 1}. {cron_option}", "cyan"))

                        info("=================================\n", False)

                        user_input = int(question("Select an Option: "))

                        cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
                        command = [
                            "python",
                            cron_script_path,
                            "twitter",
                            selected_account["id"],
                            get_active_model(),
                        ]

                        def job():
                            subprocess.run(command)

                        if user_input == 1:
                            # Post Once a day
                            schedule.every(1).day.do(job)
                            success("Set up CRON Job.")
                        elif user_input == 2:
                            # Post twice a day
                            schedule.every().day.at("10:00").do(job)
                            schedule.every().day.at("16:00").do(job)
                            success("Set up CRON Job.")
                        elif user_input == 3:
                            # Post thrice a day
                            schedule.every().day.at("08:00").do(job)
                            schedule.every().day.at("12:00").do(job)
                            schedule.every().day.at("18:00").do(job)
                            success("Set up CRON Job.")
                        else:
                            break
                    elif user_input == 4:
                        if get_verbose():
                            info(" => Climbing Options Ladder...", False)
                        break
    elif user_input == 3:
        info("Starting Affiliate Marketing...")

        cached_products = get_products()

        if len(cached_products) == 0:
            warning("No products found in cache. Create one now?")
            user_input = question("Yes/No: ")

            if user_input.lower() == "yes":
                affiliate_link = question(" => Enter the affiliate link: ")
                twitter_uuid = question(" => Enter the Twitter Account UUID: ")

                # Find the account
                account = None
                for acc in get_accounts("twitter"):
                    if acc["id"] == twitter_uuid:
                        account = acc

                add_product(
                    {
                        "id": str(uuid4()),
                        "affiliate_link": affiliate_link,
                        "twitter_uuid": twitter_uuid,
                    }
                )

                afm = AffiliateMarketing(
                    affiliate_link,
                    account["firefox_profile"],
                    account["id"],
                    account["nickname"],
                    account["topic"],
                )

                afm.generate_pitch()
                afm.share_pitch("twitter")
        else:
            table = PrettyTable()
            table.field_names = ["ID", "Affiliate Link", "Twitter Account UUID"]

            for product in cached_products:
                table.add_row(
                    [
                        cached_products.index(product) + 1,
                        colored(product["affiliate_link"], "cyan"),
                        colored(product["twitter_uuid"], "blue"),
                    ]
                )

            print(table)

            user_input = question("Select a product to start: ")

            selected_product = None

            for product in cached_products:
                if str(cached_products.index(product) + 1) == user_input:
                    selected_product = product

            if selected_product is None:
                error("Invalid product selected. Please try again.", "red")
                main()
            else:
                # Find the account
                account = None
                for acc in get_accounts("twitter"):
                    if acc["id"] == selected_product["twitter_uuid"]:
                        account = acc

                afm = AffiliateMarketing(
                    selected_product["affiliate_link"],
                    account["firefox_profile"],
                    account["id"],
                    account["nickname"],
                    account["topic"],
                )

                afm.generate_pitch()
                afm.share_pitch("twitter")

    elif user_input == 5:
        info("Starting Outreach...")

        outreach = Outreach()

        outreach.start()
    elif user_input == 6:
        if get_verbose():
            print(colored(" => Quitting...", "blue"))
        sys.exit(0)
    else:
        error("Invalid option selected. Please try again.", "red")
        main()


if __name__ == "__main__":
    # Print ASCII Banner
    print_banner()

    first_time = get_first_time_running()

    if first_time:
        print(
            colored(
                "Hey! It looks like you're running MoneyPrinter V2 for the first time. Let's get you setup first!",
                "yellow",
            )
        )

    # Setup file tree
    assert_folder_structure()

    # Remove temporary files
    rem_temp_files()

    # Fetch MP3 Files
    fetch_songs()

    # Select LLM model — use cliproxyapi
    configured_model = get_default_model()
    if configured_model:
        select_model(configured_model)
        success(f"Using configured model: {configured_model}")
    else:
        try:
            models = list_models()
        except Exception as e:
            error(f"Could not connect to LLM provider: {e}")
            sys.exit(1)

        if not models:
            error("No models found. Check your LLM provider configuration.")
            sys.exit(1)

        # Prefer free models
        free_models = [m for m in models if ":free" in m or "free" in m.lower()]
        display_models = free_models if free_models else models

        info("\n========== AVAILABLE MODELS =========", False)
        for idx, model_name in enumerate(display_models):
            tag = " [FREE]" if model_name in free_models else ""
            print(colored(f" {idx + 1}. {model_name}{tag}", "cyan"))
        info("==================================\n", False)

        model_choice = None
        while model_choice is None:
            raw = input(colored("Select a model: ", "magenta")).strip()
            try:
                choice_idx = int(raw) - 1
                if 0 <= choice_idx < len(display_models):
                    model_choice = display_models[choice_idx]
                else:
                    warning("Invalid selection. Try again.")
            except ValueError:
                warning("Please enter a number.")

        select_model(model_choice)
        success(f"Using model: {model_choice}")

    while True:
        main()
