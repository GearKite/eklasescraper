# E-klase scraper

Can be used to access e-klase.lv programmatically

## Example

    import eklasescraper.eklase

    eklase = eklasescraper.eklase.Scraper()

    eklase.login("peterisi", "parole123")

    # Fetch diary
    diary = eklase.fetch_diary("01.11.2023.")

    # Fetch timetable
    lesson_times_list = eklase.fetch_lesson_times()
