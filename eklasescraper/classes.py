from datetime import datetime
import urllib.parse


def _clean_text(text):
    return " ".join(text.strip().split())


class Expandable:
    def to_dict(self):
        result = {}
        for attr_name, attr_value in vars(self).items():
            if isinstance(attr_value, list):
                result[attr_name] = [
                    item.to_dict()
                    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict"))
                    else item
                    for item in attr_value
                ]
            elif hasattr(attr_value, "to_dict") and callable(
                getattr(attr_value, "to_dict")
            ):
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
    def __init__(self, url=None, title="", href=None):
        if not url:
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            param_to_decode = "destination_uri"
            if param_to_decode in query_params:
                url = query_params[param_to_decode][
                    0
                ]  # Get the first value if there are multiple values
                url = url.encode("utf-8").decode(
                    "unicode-escape"
                )  # Decode the parameter
            else:
                url = href

        self.url = url
        self.title = title


class Day(Expandable):
    def __init__(self):
        self.lessons = []
        self.entries = []
        self.no_data = True

    def set_date(self, date_string, date_format="%d.%m.%y."):
        date = datetime.strptime(date_string, date_format)
        self.date_string = date_string
        self.timestamp = datetime.timestamp(date)


class LessonTime(Expandable):
    def __init__(self, index, start_time, end_time):
        self.index = index
        self.start_time_str = start_time
        self.end_time_str = end_time

        # Seconds to add to the day timestamp
        self.start_timedelta = sum(
            int(x) * 60**i
            for i, x in enumerate(reversed(self.start_time_str.split(":")))
        )
        self.end_timedelta = sum(
            int(x) * 60**i
            for i, x in enumerate(reversed(self.end_time_str.split(":")))
        )

        self.lenght_minutes = self.end_timedelta - self.start_timedelta


class Diary(Expandable):
    def __init__(self):
        self.days = []


class DiaryEntry(Expandable):
    def __init__(self, name, content):
        self.name = _clean_text(name)
        self.content = _clean_text(content)


class LessonHometask(Expandable):
    def __init__(self, text, links=[]):
        self.text = _clean_text(text)
        self.links = links


class LessonSubject(Expandable):
    def __init__(self, text, links=[]):
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
        self.name = _clean_text(name)
        self.subtitle = _clean_text(subtitle)
        self.profile_id = profile_id
        self.organization_id = organization_id
