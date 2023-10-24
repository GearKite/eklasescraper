import eklase
import json
import dotenv
from os import getenv

dotenv.load_dotenv()

eklase = eklase.Scraper()

eklase.login(getenv("USERNAME"), getenv("PASSWORD"), getenv("PROFILE_ID"), getenv("ORGANIZATION_ID"), getenv("PROFILE_INDEX"))

# Fetch diary for the date's week
diary = eklase.fetch_diary("22.10.2023.")
    
# Fetch timetable
lesson_times = eklase.fetch_lesson_times()


# Save both to json files

with open("diary.json", "w+") as f:
    json.dump(diary.to_dict(), f, indent=4)

with open("times.json", "w+") as f:
    json.dump(lesson_times.to_dict(), f, indent=4)