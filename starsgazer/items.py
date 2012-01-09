# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class StarsgazerItem(Item):
    # define the fields for your item here like:
    # name = Field()
    pass

class ProgramItem(Item):
    code = Field()
    title = Field()
    courses = Field()

class CourseItem(Item):
    code = Field()
    title = Field()
    au = Field()
    passfail = Field()
    prereq = Field()
    mutex = Field()
    unavail = Field()
    desc = Field()
