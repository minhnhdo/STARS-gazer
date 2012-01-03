# encoding=utf-8
import re
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector

from scrapy import log

from starsgazer.items import CourseItem

class ContentSpider(BaseSpider):
    name = 'content'
    allowed_domains = ['wis.ntu.edu.sg']
    start_urls = ['http://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # selecting the last value in academic year
        acadsem = hxs.select('//select[@name="acadsem"]/*[last()]/@value').extract()
        # load the courses of the whole semester
        boption = 'CLoad'
        programs = hxs.select('//select[@name="r_course_yr"]/*/@value').extract()
        for i, p in enumerate(hxs.select('//select[@name="r_course_yr"]/*/@value').extract()):
            print i, p
        #programs = 'CSC;;2;F',
        prognames = hxs.select('//select[@name="r_course_yr"]/*/text()').extract()
        retval = []
        for name, r_course_yr in zip(prognames, programs[:172]):
            if r_course_yr == '':
                continue

            detail = r_course_yr.split(';')
            if detail[0].startswith('ML'):
                callbackname = 'minor'
            elif detail[0].startswith('GE'):
                callbackname = detail[1].lower()
            elif detail[0].startswith('GL'):
                callbackname = 'ger'
            elif detail[0].startswith('CNY'):
                callbackname = 'cny'
            else:
                callbackname = 'program'
            callback = getattr(self, 'parse_' + callbackname, self.parse_program)(detail)
            retval.append(FormRequest.from_response(response,
                                                    formdata=dict(acadsem=acadsem,
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

    def parse_program(self, program):
        def helper(response):
            with open('result.html', 'w') as f:
                f.write(response.body)
            retval = []
            hxs = HtmlXPathSelector(response)
            courses = hxs.select('//table')
            for course in courses:
                courseitem = CourseItem()
                details = course.select('.//tr')
                code_title_au_dept = list(map(unicode.strip, details[0].select('.//font/text()').extract()))
                if code_title_au_dept == []:
                    with open('odd.html', 'a') as f:
                        f.write(repr(program) + '\n')
                        f.write(repr(course.extract()) + '\n')
                    continue
                courseitem['code'] = code_title_au_dept[0]
                courseitem['title'] = code_title_au_dept[1]
                courseitem['au'] = code_title_au_dept[2]
                if courseitem['code'] == 'CSC202':
                    print course.extract()
                courseitem['program'] = program
                courseitem['mutex'] = course.select('.//font[@color="BROWN"]/text()').extract()
                if courseitem['mutex'] == []:
                    courseitem['mutex'] = u''
                else:
                    courseitem['mutex'] = courseitem['mutex'][1]
                courseitem['unavail'] = course.select('.//font[@color="GREEN"]/text()').extract()
                if courseitem['unavail'] == []:
                    courseitem['unavail'] = u''
                else:
                    courseitem['unavail'] = courseitem['unavail'][1]
                courseitem['prereq'] = course.select('.//font[@color="#FF00FF"]/text()').extract()
                if courseitem['prereq'] != []:
                    courseitem['prereq'] = courseitem['prereq'][1:]
                courseitem['desc'] = details[-1].select('.//font/text()').extract()[0].strip('\n')
                retval.append(courseitem)
            return retval

        return helper

    parse_cny = parse_minor = parse_sts = parse_ahss = parse_bm = parse_ls = parse_ger = parse_program
