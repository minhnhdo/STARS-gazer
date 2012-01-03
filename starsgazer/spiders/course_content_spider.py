# encoding=utf-8
import re
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector

from scrapy import log

from starsgazer.items import CourseItem, ProgramItem

class ContentSpider(BaseSpider):
    name = 'content'
    allowed_domains = ['wis.ntu.edu.sg']
    start_urls = ['http://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main']
    scraped_courses = set()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # selecting the latest date in academic year
        acadsem = hxs.select('//select[@name="acadsem"]/*[last()]/@value').extract()[0]
        acad, semester = acadsem.split('_')
        # load the courses of the whole semester
        boption = 'CLoad'
        programs = hxs.select('//select[@name="r_course_yr"]/*/@value').extract()
        #for i, p in enumerate(hxs.select('//select[@name="r_course_yr"]/*/@value').extract()):
        #    print i, p
        #programs = 'CSC;;2;F',
        prognames = hxs.select('//select[@name="r_course_yr"]/*/text()').extract()
        retval = []
        for title, r_course_yr in zip(prognames, programs):#[322:323]):#[:172]):
            if r_course_yr == '':
                continue

            code = r_course_yr.split(';')
            callback = self.parse_program(response, acadsem, title, code)
            retval.append(FormRequest.from_response(response,
                                                    formdata=dict(acadsem=acadsem,
                                                                  acad=acad,
                                                                  semester=semester,
                                                                  boption=boption,
                                                                  r_course_yr=r_course_yr,
                                                                  ),
                                                    callback=callback))
        return retval
        # for individual course
        # 'boption': 'Search',
        # 'r_subj_code':'CSC201',
        # for whole year
        # 'boption': 'CLoad',
        # 'acadsem': '2011_2',
        # 'r_course_yr': 'CSC;;2;F',

    def parse_program(self, mainpage, acadsem, title, code):
        def helper(response):
            hxs = HtmlXPathSelector(response)
            program = ProgramItem()
            courses = []
            toscrape = []
            retval = [program]

            program['title'] = title
            program['code'] = code

            rows = hxs.select('.//tr[descendant::font[@color="#0000FF"]]')
            for r in rows:
                c = r.select('.//font/text()').extract()[0].strip()
                courses.append(c)
                if c not in self.scraped_courses:
                    self.scraped_courses.add(c)
                    toscrape.append(c)

            program['courses'] = courses

            if code[0].startswith('GL') or code[0].startswith('GE') or code[0].startswith('ML') or code[0].startswith('CN'):
                courseitems = self.parse_course_list(response, toscrape)
            else:
                courseitems = self.parse_program_courses(response, toscrape)

            retval.extend(courseitems)

            return retval

        return helper

    def parse_course_list(self, response, courselist):
        retval = []
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('.//tr[descendant::font[@color="#0000FF"]]')
        data = hxs.extract().split(courses[0].extract())[1]
        course_details = []
        for course in courses[1:]:
            s = data.split(course.extract())
            course_details.append(s[0])
            data = s[1]
        course_details.append(s[1])
        flags = re.UNICODE | re.MULTILINE #| re.DOTALL
        for course, course_detail in zip(courses, course_details):
            code_title_au_dept = list(map(unicode.strip, course.select('.//font/text()').extract()))
            passfail = filter(None, re.findall(u'<font.*color="RED">([^<]*)', course_detail, flags))
            mutex = filter(None, re.findall(u'<font.*color="BROWN">([^<]*)', course_detail, flags))
            unavail = filter(None, re.findall(u'<font.*color="GREEN">([^<]*)', course_detail, flags))
            prereq = filter(None, re.findall(u'<font.*color="#FF00FF">([^<]*)', course_detail, flags))
            desc = re.search('<font size="2">([^<]*)', course_detail).groups()[0].strip('\n')
            courseitem = self._fill_in(courselist, code_title_au_dept, passfail, mutex, unavail, prereq, desc)
            if courseitem:
                retval.append(courseitem)
        return retval

    def parse_program_courses(self, response, courselist):
        retval = []
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('//table')
        for course in courses:
            details = course.select('.//tr')
            code_title_au = list(map(unicode.strip, details[0].select('.//font/text()').extract()))
            passfail = course.select('.//font[@color="RED"]/text()').extract()
            mutex = course.select('.//font[@color="BROWN"]/text()').extract()
            unavail = course.select('.//font[@color="GREEN"]/text()').extract()
            prereq = course.select('.//font[@color="#FF00FF"]/text()').extract()
            desc = details[-1].select('.//font/text()').extract()[0].strip('\n')
            courseitem = self._fill_in(courselist, code_title_au, passfail, mutex, unavail, prereq, desc)
            if courseitem:
                retval.append(courseitem)
        return retval

    def _fill_in(self, courselist, ctad, passfail, mutex, unavail, prereq, desc):
        courseitem = CourseItem()
        courseitem['code'] = ctad[0]
        # no need to scrape already scraped courses
        if courseitem['code'] not in courselist:
            return None
        courseitem['title'] = ctad[1]
        courseitem['au'] = ctad[2]
        foundau = ctad[2].rfind(' AU')
        if foundau != -1:
            courseitem['au'] = courseitem['au'][:foundau]
        if passfail:
            courseitem['passfail'] = True
        if mutex == []:
            courseitem['mutex'] = u''
        else:
            courseitem['mutex'] = mutex[1]
        for i in range(0, len(unavail), 2):
            if unavail[i].find('UE') != -1:
                courseitem['ue_unavail'] = unavail[i+1]
            elif unavail[i].find('PE') != -1:
                courseitem['pe_unavail'] = unavail[i+1]
            elif unavail[i].find('Core') != -1:
                courseitem['core_unavail'] = unavail[i+1]
            else:
                courseitem['unavail'] = unavail[i+1]
        if prereq != []:
            courseitem['prereq'] = filter((lambda x: x != u'Prerequisite:'), prereq)
        courseitem['desc'] = desc
        return courseitem
