# Scrapy settings for starsgazer project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'starsgazer'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['starsgazer.spiders']
NEWSPIDER_MODULE = 'starsgazer.spiders'
DEFAULT_ITEM_CLASS = 'starsgazer.items.StarsgazerItem'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

