# -*- coding: utf-8 -*-

from itertools import product, chain

from crawler_bqjr.spider_class import NameSearchSpider, RecordSearchedSpider


class TwoWordsNameSearchSpider(NameSearchSpider, RecordSearchedSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        long_first_names = [w for w in self.first_names if len(w) > 1]
        common_single_first_names = [w for w in self.common_first_names if len(w) == 1]
        rare_single_first_names = [w for w in self.rare_first_names if len(w) == 1]
        first_names = common_single_first_names + rare_single_first_names

        self.search_iter = chain(long_first_names,
                                 (a + b for a, b in product(first_names, self.popular_words)),
                                 (a + b for a, b in product(first_names, self.common_words)),
                                 (a + b for a, b in product(first_names, self.rare_words)),
                                 # self.citys
                                 )
        self.all_citys_str = ",".join(self.citys)

    def get_next_search_word(self):
        search_iter = self.search_iter
        all_citys_str = self.all_citys_str
        is_search_name_exists = self.is_search_name_exists
        record_search_name = self.record_search_name
        while True:
            try:
                search_word = next(search_iter)
                if not is_search_name_exists(search_word) and search_word not in all_citys_str:
                    record_search_name(search_word)
                    self.logger.info("search word: " + search_word)
                    return search_word
            except StopIteration:
                return None
