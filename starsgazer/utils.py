from HTMLParser import HTMLParser

htmlparser = HTMLParser()

def unescape_strip_newline_space(a):
    if isinstance(a, str) or isinstance(a, unicode):
        return htmlparser.unescape(a).strip('\n').strip()
    else:
        return [htmlparser.unescape(i).strip('\n').strip() for i in a]
