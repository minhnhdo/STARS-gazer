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
        # selecting the last value in academic year
        acadsem = hxs.select('//select[@name="acadsem"]/*[last()]/@value').extract()[0]
        acad, semester = acadsem.split('_')
        # load the courses of the whole semester
        boption = 'CLoad'
        programs = hxs.select('//select[@name="r_course_yr"]/*/@value').extract()
        for i, p in enumerate(hxs.select('//select[@name="r_course_yr"]/*/@value').extract()):
            print i, p
        #programs = 'CSC;;2;F',
        prognames = hxs.select('//select[@name="r_course_yr"]/*/text()').extract()
        retval = []
        for title, r_course_yr in zip(prognames, programs[:172]):
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
        for course in courses:
            courseitem = CourseItem()
            code_title_au_dept = list(map(unicode.strip, course.select('.//font/text()').extract()))
            courseitem['code'] = code_title_au_dept[0]
            if courseitem['code'] not in courselist:
                continue
            courseitem['title'] = code_title_au_dept[1]
            courseitem['au'] = code_title_au_dept[2]
        return retval

    def parse_program_courses(self, response, courselist):
        retval = []
        hxs = HtmlXPathSelector(response)
        courses = hxs.select('//table')
        for course in courses:
            courseitem = CourseItem()
            details = course.select('.//tr')
            code_title_au = list(map(unicode.strip, details[0].select('.//font/text()').extract()))
            if code_title_au == []:
                with open('results/odd.html', 'a') as f:
                    f.write(repr(course.extract()) + '\n')
                continue
            courseitem['code'] = code_title_au[0]
            # no need to scrape already scraped courses
            if courseitem['code'] not in courselist:
                continue
            courseitem['title'] = code_title_au[1]
            courseitem['au'] = code_title_au[2][:code_title_au[2].rfind(' AU')]
            if course.select('.//font[@color="RED"]/text()').extract() != []:
                courseitem['passfail'] = True
            courseitem['mutex'] = course.select('.//font[@color="BROWN"]/text()').extract()
            if courseitem['mutex'] == []:
                courseitem['mutex'] = u''
            else:
                courseitem['mutex'] = courseitem['mutex'][1]
            unavail = course.select('.//font[@color="GREEN"]/text()').extract()
            for i in range(0, len(unavail), 2):
                if unavail[i].find('UE') != -1:
                    courseitem['ue_unavail'] = unavail[i+1]
                elif unavail[i].find('PE') != -1:
                    courseitem['pe_unavail'] = unavail[i+1]
                elif unavail[i].find('Core') != -1:
                    courseitem['core_unavail'] = unavail[i+1]
                else:
                    courseitem['unavail'] = unavail[i+1]
            courseitem['prereq'] = course.select('.//font[@color="#FF00FF"]/text()').extract()
            if courseitem['prereq'] != []:
                courseitem['prereq'] = courseitem['prereq'][1:]
            courseitem['desc'] = details[-1].select('.//font/text()').extract()[0].strip('\n')
            retval.append(courseitem)
        return retval
