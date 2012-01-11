# encoding=utf-8
import re
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector

from scrapy import log

from starsgazer.items import BriefCourseItem, ClassItem
from starsgazer import utils

class IndexSpider(BaseSpider):
    name = 'index'
    allowed_domains = ['wis.ntu.edu.sg']
    start_urls = ['http://wis.ntu.edu.sg/webexe/owa/aus_schedule.main']
    scraped_courses = set()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # selecting the latest date in academic year
        acadsem = hxs.select('//select[@name="acadsem"]/*[1]/@value').extract()[0] # where the difference lies
        acad, semester = acadsem.split(';') # another subtle difference
        # load the courses of the whole semester
        boption = 'CLoad'
        programs = hxs.select('//select[@name="r_course_yr"]/*/@value').extract()
        #programs = 'CSC;;2;F',
        prognames = hxs.select('//select[@name="r_course_yr"]/*/text()').extract()
        retval = []

        for title, r_course_yr in zip(prognames, programs[322:323]):#[:172]):
            if r_course_yr == '':
                continue

            code = r_course_yr.split(';')
            retval.append(FormRequest.from_response(response,
                                                    formdata=dict(acadsem=acadsem,
                                                                  # acad=acad, # another diff
                                                                  # semester=semester, # another diff
                                                                  boption=boption,
                                                                  r_course_yr=r_course_yr,
                                                                  ),
                                                    callback=self.parse_program))
        return retval

    def parse_program(self, response):
        hxs = HtmlXPathSelector(response)
        retval = []

        courseinfo = hxs.select('//table[not(@border)]')
        indexlists = hxs.select('//table[@border]')

        # sanity check
        assert(len(courseinfo) == len(indexlists))

        for course, indexlist in zip(courseinfo, indexlists):
            retval.extend(self.parse_course(course, indexlist))

        return retval

    def parse_course(self, course, indexlist):
        code_title_au = utils.unescape_strip_newline_space(course.select('.//font[@color="#0000FF"]/text()').extract())
        prereq = utils.unescape_strip_newline_space(course.select('.//font[@color="#FF00FF"]/text()').extract())
        indices = utils.unescape_strip_newline_space(indexlist.select('.//tr/td[1]/b[text()]/text()').extract())

        bc = BriefCourseItem()
        bc['code'] = code_title_au[0]
        bc['title'] = code_title_au[1]
        if bc['title'].endswith('#'):
            bc['pe'] = True
            bc['title'] = bc['title'][:-1]
        if bc['title'].endswith('*'):
            bc['ue'] = True
            bc['title'] = bc['title'][:-1]
        bc['au'] = code_title_au[2][:code_title_au[2].rfind(' AU')]
        if prereq:
            bc['prereq'] = filter(lambda x: x and x.startswith('Prerequisite') == False, prereq)
            #print bc['prereq']
        bc['indices'] = indices

        retval = [bc]

        return retval
