import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime, time
import json

class Scraper:
    def __init__(self, headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"}, cookies = None) -> None:
        self._session = requests.Session()
        self._session.headers.update(headers)
        self._success_status_codes = [200, 302]
        self._urls = {
            "base": "https://my.e-klase.lv",
            "login": "https://my.e-klase.lv/?v=15",
            "switcher": "https://my.e-klase.lv/SessionContext/SwitchStudentWithFamilyStudentAutoAdd",
            "home": "https://my.e-klase.lv/Family/Home?login=1",
            "diary": "https://my.e-klase.lv/Family/Diary",
            "times": "https://my.e-klase.lv/Family/LessonTimes",
            "profile_selector": "https://my.e-klase.lv/Family/UserLoginProfile"
            
        }
    
    def login(self, username:str, password:str, profile_id:str=None, organization_id:str=None, profileIndex:int=1):
        """Sets the cookies for access. Use the username and password of your account.
        
If you have multiple profiles under one account you will need to specify either {profile_id and organization_id} or {profileIndex}.
        """
        data = {
            "UserName": username,
            "Password": password,
            "fake_pass": ""
        }
        resp = self._session.post(url=self._urls["login"], data=data)
        if resp.status_code not in self._success_status_codes:
            raise Exception(f"Login 1 failed with status code {resp.status_code}!\n{resp.text}\n{resp}")
        respS = BeautifulSoup(resp.text, "lxml")
        if not profile_id or not organization_id:
            try: # Check if there is no need to manually enter an id
                self._organization_id = respS.select_one("#frmTest > input:nth-child(1)")["value"]
                self._profile_id = respS.select_one("#frmTest > input:nth-child(2)")["value"]
            except Exception as e:
                profiles = {}
                index = 0
                for button in respS.select("button[name=pf_id]"):
                    profiles[index] = {
                        "name": button.parent.parent.text.strip(),
                        "profile_id": str(button["data-pf_id"]),
                        "organization_id": str(button["data-tenantid"])
                    }
                    index += 1
                if profileIndex is not None:
                    self._profile_id = profiles[profileIndex]["profile_id"]
                    self._organization_id = profiles[profileIndex]["organization_id"]
                else:
                    print(json.dumps(profiles, indent=4))
                    print(f"Multiple profiles are available. Pass in pfId and organization_id.")
                    raise e
            
            
        data2 = {
            "TenantId": self._organization_id,
            "pf_id": self._profile_id
        }
        resp2 = self._session.post(url=self._urls["switcher"], data=data2)
        if resp2.status_code not in self._success_status_codes:
            raise Exception(f"Login 2 failed with status code {resp2.status_code}!\n{resp2.text}\n{resp2}")
        
        self._getStudentSelectorId()
        
    def _getStudentSelectorId(self):
        resp3 = self._session.get(url=self._urls["home"])
        if resp3.status_code not in self._success_status_codes:
            raise Exception(f"Login 3 failed with status code {resp3.status_code}!\n{resp3.text}\n{resp3}")
        resp3S = BeautifulSoup(resp3.text, "lxml")
        script = resp3S.select_one(".student-selector > script:nth-child(2)")
        self._studentSelectorData = list(str(script).split("student_selector_data = ")[1].split(";")[0])
        self._student_selector_id = str(script).split("student_selector_value = ")[1].split(";")[0]

        
    def fetch_diary(self, date):
        r = self._session.get(url=self._urls["diary"], params={"Date": date})
        html = r.text
        
        S = BeautifulSoup(html, 'lxml')
        
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
            for lesson in day_lessons.select("tr:not(.info)"): # Get only lesson list, not other diary entries
                hometask_html = lesson.select_one(".hometask")
                subject_html = lesson.select_one(".subject")
                
                day.lessons.append(Lesson(
                    index = lesson.select_one(".number").text.strip(),
                    lesson = lesson.select_one(".title").contents[0],
                    room = lesson.select_one(".room").text.strip(),
                    hometask = LessonHometask(
                        text = hometask_html.text.strip(),
                        links = [Link(href = link['href'], title = link.text) for link in hometask_html.find_all('a')]
                    ),
                    subject = LessonSubject(
                        text = subject_html.text.strip(),
                        links = [Link(href = link['href'], title = link.text) for link in hometask_html.find_all('a')]
                    ),
                    score = lesson.select_one(".score").text.strip(),
                    
                ))
                
            for entry in day_lessons.select(".info"): # Get diary entries
                day.entries.append(DiaryEntry(
                    name = entry.select_one(".first-column").text.strip(),
                    content = entry.select_one(".info-content").text.strip(),
                ))
                
            diary.days.append(day)
            
        return diary
    
    def fetch_lesson_times(self):
        """Fetches the lesson timetable

        Returns:
            ExpandableList: List of LessonTime objects
        """
        r = self._session.get(url=self._urls["times"])
        html = r.text
        
        S = BeautifulSoup(html, 'lxml')
        
        lesson_indexes = S.select("div.timetible-item div span")
        lesson_times = S.select("div.timetible-item div.time")
        
        output = ExpandableList()
        
        for index_name, time in zip(lesson_indexes, lesson_times):
            times = _clean_text(time.text).split(" - ")
            
            output.append(LessonTime(
                index = _clean_text(index_name.text).split()[0],
                start_time = times[0],
                end_time = times[1],
            ))
            
        return output
            
    
def _clean_text(text):
    return " ".join(text.strip().split())

class Expandable:
    def to_dict(self):
        result = {}
        for attr_name, attr_value in vars(self).items():
            if isinstance(attr_value, list):
                result[attr_name] = [item.to_dict() if hasattr(item, 'to_dict') and callable(getattr(item, 'to_dict')) else item for item in attr_value]
            elif hasattr(attr_value, 'to_dict') and callable(getattr(attr_value, 'to_dict')):
                result[attr_name] = attr_value.to_dict()
            else:
                result[attr_name] = attr_value
        return result

class ExpandableList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def to_dict(self):
        return [item.to_dict() for item in self if isinstance(item, Expandable)]

class Link(Expandable):
    def __init__(self, url = None, title = "", href = None):
        if not url:
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            param_to_decode = "destination_uri"
            if param_to_decode in query_params:
                url = query_params[param_to_decode][0]  # Get the first value if there are multiple values
                url = url.encode('utf-8').decode('unicode-escape')  # Decode the parameter
            else:
                url = href
                
        self.url = url
        self.title = title

class Diary(Expandable):
    def __init__(self):
        self.days = []

class Day(Expandable):
    def __init__(self):
        self.lessons = []
        self.entries = []
        self.no_data = True
        
    def set_date(self, date_string, date_format = "%d.%m.%y."):
        date = datetime.strptime(date_string, date_format)
        self.date_string = date_string
        self.timestamp = datetime.timestamp(date)
        
class LessonTime(Expandable):
    def __init__(self, index, start_time, end_time):
        self.index = index
        self.start_time_str = start_time
        self.end_time_str = end_time
        
        # Seconds to add to the day timestamp
        self.start_timedelta = sum(int(x) * 60 ** i for i, x in enumerate(reversed(self.start_time_str.split(":"))))
        self.end_timedelta = sum(int(x) * 60 ** i for i, x in enumerate(reversed(self.end_time_str.split(":"))))
        
        self.lenght_minutes = self.end_timedelta - self.start_timedelta
    
class DiaryEntry(Expandable):
    def __init__(self, name, content):
        self.name = _clean_text(name)
        self.content = _clean_text(content)
        
class LessonHometask(Expandable):
    def __init__(self, text, links = []):
        self.text = _clean_text(text)
        self.links = links

class LessonSubject(Expandable):
    def __init__(self, text, links = []):
        self.text = _clean_text(text)
        self.links = links
    
class Lesson(Expandable):
    def __init__(self, index, lesson, room, hometask, subject, score=None):
        self.index = _clean_text(index)
        self.lesson = _clean_text(lesson)
        self.room = _clean_text(room)
        self.hometask = hometask
        self.subject = subject
        self.score = _clean_text(score)
        
class StudentProfile(Expandable):
    def __init__(self, name, subtitle, profile_id, organization_id):
        self.name = name
        self.subtitle = subtitle
        self.profile_id = profile_id
        self.organization_id = organization_id