# encoding=utf-8
import re
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector

from scrapy import log

from starsgazer.items import CourseItem, ProgramItem
from starsgazer import utils

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
        #programs = 'CSC;;2;F',
        prognames = hxs.select('//select[@name="r_course_yr"]/*/text()').extract()
        retval = []
        for title, r_course_yr in zip(prognames, programs):#[322:323]):#[:172]):
            if r_course_yr == '':
                continue

            code = r_course_yr.split(';')
            callback = self.parse_program(acadsem, title, code)
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

    def parse_program(self, acadsem, title, code):
        def helper(response):
            hxs = HtmlXPathSelector(response)
            program = ProgramItem()
            courses = []
            toscrape = []
            retval = [program]

            program['title'] = utils.unescape_strip_newline_space(title)
            program['code'] = utils.unescape_strip_newline_space(code)

            self.log('scraping ' + program['title'], level=log.INFO)

            rows = hxs.select('.//tr[descendant::font[@color="#0000FF"]]')
            for r in rows:
                c = utils.unescape_strip_newline_space(r.select('.//font/text()').extract()[0])
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
        length = len(courses)
        if length == 0:
            # no course to process
            return []

        data = hxs.extract().split(courses[0].extract())[1]

        if length == 1:
            course_details = [data]
        else:
            course_details = []
            for course in courses[1:]:
                s = data.split(course.extract())
                course_details.append(s[0])
                data = s[1]
            course_details.append(s[1])

        # sanity check
        assert(length == len(course_details))

        flags = re.UNICODE | re.MULTILINE #| re.DOTALL
        for course, course_detail in zip(courses, course_details):
            code_title_au_dept = course.select('.//font/text()').extract()
            passfail = filter(None, re.findall(u'<font.*color="RED">([^<]*)', course_detail, flags))
            mutex = filter(None, re.findall(u'<font.*color="BROWN">([^<]*)', course_detail, flags))
            unavail = filter(None, re.findall(u'<font.*color="GREEN">([^<]*)', course_detail, flags))
            prereq = filter(None, re.findall(u'<font.*color="#FF00FF">([^<]*)', course_detail, flags))
            desc = re.search(u'<font size="2">([^<]*)', course_detail).groups()[0]
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
            code_title_au = details[0].select('.//font/text()').extract()
            passfail = course.select('.//font[@color="RED"]/text()').extract()
            mutex = course.select('.//font[@color="BROWN"]/text()').extract()
            unavail = course.select('.//font[@color="GREEN"]/text()').extract()
            prereq = course.select('.//font[@color="#FF00FF"]/text()').extract()
            desc = details[-1].select('.//font/text()').extract()[0]
            courseitem = self._fill_in(courselist, code_title_au, passfail, mutex, unavail, prereq, desc)
            if courseitem:
                retval.append(courseitem)
        return retval

    def _fill_in(self, courselist, ctad, passfail, mutex, unavail, prereq, desc):
        # cleansing input
        ctad = utils.unescape_strip_newline_space(ctad)
        passfail = utils.unescape_strip_newline_space(passfail)
        mutex = utils.unescape_strip_newline_space(mutex)
        unavail = utils.unescape_strip_newline_space(unavail)
        prereq = utils.unescape_strip_newline_space(prereq)
        desc = utils.unescape_strip_newline_space(desc)
        courseitem = CourseItem()
        courseitem['code'] = ctad[0]
        # no need to scrape already scraped courses
        if courseitem['code'] not in courselist:
            return None
        courseitem['title'] = ctad[1]
        courseitem['au'] = ctad[2]
        foundau = courseitem['au'].rfind(' AU')
        if foundau != -1:
            courseitem['au'] = courseitem['au'][:foundau]
        if passfail:
            courseitem['passfail'] = True
        if mutex != []:
            courseitem['mutex'] = mutex[1]
        unavail_dict = {}
        for i in range(0, len(unavail), 2):
            unavail_str = ''
            if unavail[i].find('Programme') != -1:
                unavail_str = 'prog_'
            elif unavail[i].find('Race') != -1:
                unavail_str = 'race_'
            elif unavail[i].find('Nation') != -1:
                unavail_str = 'nat_'
            else:
                with open('results/wierds.html', 'a') as f:
                    f.write(str(ctad) + ' ' + str(passfail) + ' ' + str(mutex) + ' ' + str(unavail) + ' ' + str(prereq) + ' ' + str(desc))
                return None

            if unavail[i].find('UE') != -1:
                unavail_str += 'ue'
            elif unavail[i].find('PE') != -1:
                unavail_str += 'pe'
            elif unavail[i].find('Core') != -1:
                unavail_str += 'core'
            else:
                unavail_str += 'all'

            if len(unavail_str) < 5: # can't happen
                raise TypeError('wtf this is wrong!!!!!!!!!!!!')

            unavail_dict[unavail_str] = unavail[i+1]
        if unavail_dict:
            courseitem['unavail'] = unavail_dict

        if prereq != []:
            courseitem['prereq'] = filter((lambda x: x != u'Prerequisite:'), prereq)
        courseitem['desc'] = desc
        return courseitem
