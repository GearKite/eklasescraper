import requests
from bs4 import BeautifulSoup
from datetime import datetime
from .classes import (
    ExpandableList,
    Link,
    Day,
    LessonTime,
    Diary,
    DiaryEntry,
    Lesson,
    LessonHometask,
    LessonSubject,
    StudentProfile,
)


class Scraper:
    """e-klase.lv scraper"""

    def __init__(self, session: requests.Session = None) -> None:
        """Initialize the scraper

        Args:
            session (requests.Session, optional): Requests session with your parameters. Creates new session if not specified.
        """
        if not session:
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"
                }
            )

        self._session = session

        self._success_status_codes = [200, 302]
        self._urls = {
            "base": "https://my.e-klase.lv",
            "login": "https://my.e-klase.lv/?v=15",
            "switcher": "https://my.e-klase.lv/SessionContext/SwitchStudentWithFamilyStudentAutoAdd",
            "home": "https://my.e-klase.lv/Family/Home?login=1",
            "diary": "https://my.e-klase.lv/Family/Diary",
            "times": "https://my.e-klase.lv/Family/LessonTimes",
            "profile_selector": "https://my.e-klase.lv/Family/UserLoginProfile",
        }

    def login(
        self,
        username: str,
        password: str,
        profile_id: str = None,
        organization_id: str = None,
        profile_index: int = 0,
    ):
        """Logs in to your account and selects a profile

        If you have multiple profiles under one account you will want to specify profile_id and organization_id or the index of the profile.
        """

        data = {"UserName": username, "Password": password, "fake_pass": ""}
        resp = self._session.post(url=self._urls["login"], data=data)
        if resp.status_code not in self._success_status_codes:
            raise Exception(
                f"Login 1 failed with status code {resp.status_code}!\n{resp.text}\n{resp}"
            )

        if profile_id is None and organization_id is None:
            # Use profile_index for selecting the profile
            self._profiles = self.fetch_profiles()

            self._profile_id = self._profiles[profile_index].profile_id
            self._organization_id = self._profiles[profile_index].organization_id
        else:
            self._profile_id = profile_id
            self._organization_id = organization_id

        # Select profile with profile_id and organization_id

        data2 = {"TenantId": self._organization_id, "pf_id": self._profile_id}
        resp2 = self._session.post(url=self._urls["switcher"], data=data2)
        if resp2.status_code not in self._success_status_codes:
            raise Exception(
                f"Login 2 failed with status code {resp2.status_code}!\n{resp2.text}\n{resp2}"
            )

    def fetch_profiles(self):
        """Fetches the available profiles

        Returns:
            profiles (ExpandableList): List of available profiles (StudentProfile)
        """
        r = self._session.get(url=self._urls["profile_selector"])
        html = r.text

        S = BeautifulSoup(html, "lxml")

        select_panels = S.select("div.modal-options-item.student-item")

        profiles = ExpandableList()

        for panel in select_panels:
            button = panel.select_one("button.btn-switch-student")

            profiles.append(
                StudentProfile(
                    name=panel.select_one("div.modal-options-title > span").text,
                    subtitle=panel.select_one("div.modal-options-choice > small").text,
                    profile_id=button["data-pf_id"],
                    organization_id=button["data-tenantid"],
                )
            )

        return profiles

    def fetch_diary(self, week_date: str | datetime) -> Diary:
        """Fetches the diary for a given week

        Args:
            week_date (str | datetime): Date of any day in the week. Must be in the e-klase.lv format "%d.%m.%Y." or datetime.datetime object.

        Returns:
            Diary: Returns a Diary object
        """
        # Handle datetime.datetime and string formats
        if isinstance(week_date, datetime):
            date_str = week_date.strftime("%d.%m.%Y.")
        else:
            date_str = week_date

        r = self._session.get(url=self._urls["diary"], params={"Date": date_str})
        html = r.text

        S = BeautifulSoup(html, "lxml")

        days_table = S.select_one(".student-journal-lessons-table-holder")
        days = days_table.select("h2")
        day_lesson_tables = days_table.select("table tbody")

        diary = Diary()

        # Repeat for each day
        for day_lessons, date in zip(day_lesson_tables, days):
            day = Day()

            no_data = bool(day_lessons.select("tr > td.no-data"))

            day.no_data = no_data

            if no_data:
                diary.days.append(day)
                continue

            day.set_date(date.text.split()[0])

            # Repeat for each lesson that day
            for lesson in day_lessons.select(
                "tr:not(.info)"
            ):  # Get only lesson list, not other diary entries
                hometask_html = lesson.select_one(".hometask")
                subject_html = lesson.select_one(".subject")

                day.lessons.append(
                    Lesson(
                        index=lesson.select_one(".number").text.strip(),
                        lesson=lesson.select_one(".title").contents[0],
                        room=lesson.select_one(".room").text.strip(),
                        hometask=LessonHometask(
                            text=hometask_html.text.strip(),
                            links=[
                                Link(href=link["href"], title=link.text)
                                for link in hometask_html.find_all("a")
                            ],
                        ),
                        subject=LessonSubject(
                            text=subject_html.text.strip(),
                            links=[
                                Link(href=link["href"], title=link.text)
                                for link in hometask_html.find_all("a")
                            ],
                        ),
                        score=lesson.select_one(".score").text.strip(),
                    )
                )

            for entry in day_lessons.select(".info"):  # Get diary entries
                day.entries.append(
                    DiaryEntry(
                        name=entry.select_one(".first-column").text.strip(),
                        content=entry.select_one(".info-content").text.strip(),
                    )
                )

            diary.days.append(day)

        return diary

    def fetch_lesson_times(self):
        """Fetches the lesson timetable

        Returns:
            ExpandableList: List of LessonTime objects
        """
        r = self._session.get(url=self._urls["times"])
        html = r.text

        S = BeautifulSoup(html, "lxml")

        lesson_indexes = S.select("div.timetible-item div span")
        lesson_times = S.select("div.timetible-item div.time")

        output = ExpandableList()

        for index_name, time in zip(lesson_indexes, lesson_times):
            times = time.text.split(" - ")

            output.append(
                LessonTime(
                    index=index_name.text.split()[0],
                    start_time=times[0],
                    end_time=times[1],
                )
            )

        return output
