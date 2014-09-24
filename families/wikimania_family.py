# -*- coding: utf-8 -*-
"""Family module for Wikimedia chapter wikis."""

__version__ = '$Id: 1bb9deace339bae504f5722477b6613cdf77addf $'

from pywikibot import family


class Family(family.Family):

    """Family class for Wikimania wikis."""

    def __init__(self):
        """Constructor."""
        family.Family.__init__(self)
        self.name = 'wikimania'

        self.years = [
            '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015',
        ]

        self.langs = dict([(year, 'wikimania%s.wikimedia.org' % year)
                           for year in self.years])
