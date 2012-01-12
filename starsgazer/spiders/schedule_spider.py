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
        acadsem = hxs.select('//select[@name="acadsem"]/option[1]/@value').extract()[0] # where the difference lies
        acad, semester = acadsem.split(';') # another subtle difference
        # load the courses of the whole semester
        boption = 'CLoad'
        programs = hxs.select('//select[@name="r_course_yr"]/option').re(re.compile('<.*value="([\w;\d]*)".*>([^<]*)', re.UNICODE))
        #programs = 'CSC;;2;F',
        progcodes = programs[:len(programs):2]
        prognames = programs[1:len(programs):2]
        retval = []

        # sanity checks
        assert(len(prognames) == len(progcodes))
        assert(len(prognames) == len(programs) / 2)

        with open('results/abi', 'w') as f:
            for i, v in enumerate(progcodes):
                f.write(str(i) + ' ' + str(v) + ' ' + str(prognames[i][:-1]) + '\n')

        count = 0

        for title, r_course_yr in zip(prognames, progcodes):#[322:323]):#[:172]):
            if r_course_yr == '':
                continue

            count += 1
            code = r_course_yr.split(';')
            retval.append(FormRequest.from_response(response,
                                                    formdata=dict(acadsem=acadsem,
                                                                  # acad=acad, # another diff
                                                                  # semester=semester, # another diff
                                                                  boption=boption,
                                                                  r_course_yr=r_course_yr,
                                                                  ),
                                                    callback=self.parse_program))
        print 'Number of programs:', count

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
        if bc['code'] in self.scraped_courses:
            return []
        else:
            with open('results/scrapedi', 'a') as f:
                f.write(bc['code'] + '\n')
            self.scraped_courses.add(bc['code'])
        bc['title'] = code_title_au[1]
        if bc['title'].endswith('#'):
            bc['pe'] = True
            bc['title'] = bc['title'][:-1]
        if bc['title'].endswith('*'):
            bc['ue'] = True
            bc['title'] = bc['title'][:-1]
        bc['au'] = code_title_au[2][:code_title_au[2].rfind(' AU')]
        if prereq:
            bc['prereq'] = filter(lambda x: x and not x.startswith('Prerequisite'), prereq)
        bc['indices'] = indices

        retval = [bc]

        retval.extend(self.parse_indexlist(bc['title'], indexlist))

        return retval

    def parse_indexlist(self, title, indexlist):
        retval = []
        fields = ('code', 'type', 'group', 'day', 'time', 'venue', 'remark')

        for row in indexlist.select('.//tr'):
            cells = utils.unescape_strip_newline_space(row.select('.//td/b/text()').extract())
            length = len(cells)

            if length == 0:
                continue
            elif length == 7: # full
                retval.append(ClassItem(dict(zip(fields, cells))))
                code = cells[0]
            elif length == 6 and cells[0].isdigit(): # missing remarks
                retval.append(ClassItem(dict(zip(fields[:-1], cells))))
                code = cells[0]
                with open('results/sus', 'a') as f:
                    f.write(str(zip(fields[:-1], cells)) + '\n')
            elif length == 6: # missing code
                ci = ClassItem(dict(zip(fields[1:], cells)))
                ci['code'] = code
                retval.append(ci)
                with open('results/sus', 'a') as f:
                    f.write(str(zip(fields[1:], cells)) + '\n')
            elif length == 5: # missing code and remarks
                ci = ClassItem(dict(zip(fields[1:-1], cells)))
                ci['code'] = code
                retval.append(ci)
                with open('results/sus', 'a') as f:
                    f.write(str(zip(fields[1:-1], cells)) + '\n')
            else: # weirds
                with open('results/weirds', 'a') as f:
                    f.write(title + '\n' + str(cells) + '\n\n')

        return retval
