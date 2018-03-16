# -*- coding: UTF-8 -*-

from os import path as os_path
from pickle import dump, load

this_dir = os_path.dirname(os_path.abspath(__file__))
NAME_WORDS_FILE_NAME = os_path.join(this_dir, "datas", "NameWords.pickle")


class NameWords(object):
    def __init__(self):
        self.common_first_names = []  # 常见姓氏
        self.rare_first_names = []  # 罕见姓氏
        self.first_names = self.common_first_names + self.rare_first_names  # 全部姓氏
        self.popular_words = []  # 名字常用字
        self.common_words = []  # 普通常用字
        self.most_words = self.popular_words + self.common_words  # 全部名字常用字
        citys = ['上海', '广州', '昆明', '山西', '湖北', '青海', '杭州', '澳门', '沈阳', '南昌', '西安', '南宁', '黑龙江', '广西', '四川', '海南', '浙江',
                 '福州', '西宁', '台北', '安徽', '石家庄', '呼和浩特', '天津', '云南', '兰州', '成都', '福建', '郑州', '南京', '深圳', '宁夏', '长春',
                 '广东', '合肥', '长沙', '拉萨', '贵州', '北京', '厦门', '太原', '江苏', '湖南', '银川', '辽宁', '陕西', '西藏', '内蒙古', '新疆', '济南',
                 '武汉', '重庆', '海口', '哈尔滨', '江西', '河北', '贵阳', '山东', '香港', '台湾', '乌鲁木齐', '吉林', '河南', '甘肃']  # 省、省会
        citys.extend(
            ['离岛', '绍兴', '诸暨', '仁怀', '灯塔', '百色', '扶余', '宝鸡', '宜都', '应城', '安顺', '白城', '漳平', '绥化', '云林', '钦州', '随州', '隆昌',
             '同江', '朔州', '文山', '安庆', '平凉', '赤水', '安达', '海宁', '云浮', '宜兴', '泉州', '建瓯', '利川', '定西', '博乐', '洛阳', '富锦', '九龙',
             '常德', '化州', '当阳', '常熟', '庄河', '和龙', '西昌', '揭阳', '开平', '万宁', '嘉义', '恩施', '枣阳', '晋州', '庆阳', '屯昌', '台东', '宜春',
             '巢湖', '栖霞', '运城', '义马', '阜康', '衡阳', '丰城', '吉首', '彭州', '桐乡', '潍坊', '乌海', '果洛', '广汉', '绵阳', '淮安', '临沂', '海西',
             '禹州', '招远', '宜城', '鹤山', '合作', '池州', '曲靖', '周口', '甘孜', '白山', '衢州', '北海', '个旧', '盘锦', '龙海', '来宾', '慈溪', '武威',
             '仪征', '福泉', '樟树', '铜陵', '丰镇', '晋江', '余姚', '简阳', '兴平', '基隆', '东方', '岳阳', '赤壁', '沂州', '珠海', '莱阳', '灵宝', '赣州',
             '琼海', '桦甸', '津市', '虎林', '辽源', '江阴', '上饶', '宿迁', '大同', '韶关', '鹤岗', '黄冈', '保亭', '宣威', '临清', '阿里', '宁安', '古交',
             '滁州', '江山', '莱州', '桃园', '荆州', '泊头', '抚顺', '温岭', '本溪', '兴宁', '安丘', '新界', '锦州', '泰兴', '和田', '吕梁', '邢台', '烟台',
             '漯河', '湖州', '莱芜', '喀什', '澎湖', '阳春', '尚志', '襄樊', '乐平', '四平', '江门', '淮北', '滨州', '毕节', '南投', '吴忠', '宁波', '孟州',
             '蓬莱', '榆树', '六安', '河间', '中山', '亳州', '德宏', '海北', '宜昌', '漳州', '信宜', '甘南', '琼中', '酒泉', '黔南', '郴洲', '包头', '荣成',
             '敦化', '嘉兴', '台南', '大理', '德州', '常宁', '玉溪', '万源', '金门', '神木', '松滋', '海城', '南充', '曲阜', '根河', '定州', '东莞', '兴安',
             '雷州', '德阳', '潜江', '五常', '永康', '汉川', '高要', '永州', '益阳', '海门', '华蓥', '高平', '宁乡', '辽阳', '永济', '河池', '临夏', '丽江',
             '巩义', '林州', '遂宁', '岑溪', '荷泽', '青州', '乳山', '安宁', '台州', '什邡', '黑河', '阳泉', '许昌', '南平', '如皋', '洮南', '广水', '延吉',
             '九江', '扬州', '海东', '玉树', '乐清', '高安', '龙岩', '桐城', '邹城', '黄骅', '广元', '兴义', '新乡', '腾冲', '澄迈', '邯郸', '沁阳', '义乌',
             '辉县', '滕州', '北流', '介休', '贺州', '凌海', '珲春', '福清', '三沙', '钟祥', '白银', '从化', '营口', '临汾', '铜川', '枣庄', '安阳', '西沙',
             '宿州', '花莲', '塔城', '中卫', '增城', '海林', '台中', '安陆', '阆中', '通化', '龙井', '昌都', '扬中', '鞍山', '乐陵', '阜新', '陵水', '聊城',
             '昭通', '泸水', '惠州', '中沙', '安康', '迪庆', '邵武', '长乐', '南康', '鹤壁', '涿州', '怒江', '高雄', '清远', '深州', '凌源', '昆玉', '鹰潭',
             '林芝', '新乐', '宜兰', '集安', '承德', '奎屯', '桂林', '汉中', '自贡', '蛟河', '诸城', '福安', '淮南', '天水', '登封', '密山', '海伦', '资阳',
             '东兴', '东营', '忻州', '新余', '景洪', '武穴', '铜仁', '瑞金', '南安', '镇江', '宁德', '崇左', '芜湖', '儋州', '红河', '武冈', '肇东', '瑞安',
             '衡水', '昆山', '资兴', '凭祥', '金华', '福鼎', '肇庆', '南宫', '舟山', '沅江', '清镇', '平泉', '宜宾', '康定', '吴川', '普洱', '苗栗', '仙桃',
             '开原', '鄂州', '霍州', '十堰', '泰安', '瑞昌', '彰化', '莱西', '长葛', '永安', '都匀', '崇州', '瑞丽', '榆林', '丹阳', '辛集', '廉江', '襄阳',
             '绵竹', '邵阳', '明光', '长治', '卫辉', '济宁', '赤峰', '南通', '汕尾', '穆棱', '商洛', '高邮', '平湖', '新北', '通辽', '咸宁', '无锡', '淄博',
             '枝江', '宁国', '北屯', '石首', '白沙', '眉山', '濮阳', '大安', '海阳', '原平', '英德', '黄南', '伊宁', '河源', '兰溪', '朝阳', '乐山', '建德',
             '高州', '禹城', '三明', '凉山', '项城', '荥阳', '舞钢', '嵊州', '延边', '玉林', '凯里', '临沧', '芒市', '即墨', '青岛', '台山', '磐石', '临安',
             '晋城', '金昌', '乐东', '邓州', '新密', '松原', '昌吉', '汾阳', '大庆', '潞城', '梧州', '哈密', '延安', '邳州', '临川', '陇南', '霸州', '罗定',
             '洪湖', '阜阳', '北镇', '保山', '阿坝', '桂平', '太仓', '鸡西', '广安', '湘乡', '灵武', '醴陵', '启东', '盘州', '定安', '合山', '雅安', '大连',
             '沧州', '图们', '沙河', '东台', '渭南', '娄底', '乐昌', '张掖', '黄山', '菏泽', '信阳', '保定', '新民', '兴化', '湘西', '唐山', '新郑', '廊坊',
             '北票', '武安', '新沂', '达州', '遵化', '肥城', '麻城', '寿光', '双辽', '东宁', '南雄', '玉环', '郴州', '舒兰', '柳州', '德兴', '北安', '吉安',
             '韩城', '恩平', '固原', '伊犁', '新竹', '黄石', '蚌埠', '乌苏', '四会', '涟源', '那曲', '德惠', '丹东', '兴城', '东港', '宣城', '贵港', '孝感',
             '新泰', '巴中', '南阳', '屏东', '泰州', '贵溪', '敦煌', '抚远', '徐州', '天长', '江油', '铁岭', '石狮', '威海', '三河', '双河', '楚雄', '萍乡',
             '汕头', '湛江', '临海', '孝义', '南沙', '天门', '佛山', '界首', '抚州', '湘潭', '浏阳', '偃师', '洪江', '迁安', '开远', '高密', '靖江', '晋中',
             '铁力', '邛崃', '商丘', '任丘', '文昌', '内江', '日照', '东阳', '莆田', '安国', '昌邑', '普宁', '句容', '靖西', '丽水', '咸阳', '凤城', '临江',
             '庐山', '河津', '伊春', '盐城', '泸州', '胶州', '龙泉', '济源', '荆门', '龙口', '弥勒', '汝州', '温州', '汨罗', '苏州', '焦作', '潮州', '侯马',
             '耒阳', '临高', '梅州', '昌江', '陆丰', '开封', '溧阳', '阳江', '大冶', '山南', '盖州', '韶山', '讷河', '玉门', '平度', '毫州', '华阴', '怀化',
             '茂名', '蒙自', '三亚', '常州', '遵义', '九台', '连州', '临湘', '株洲', '永城', '五指山', '武夷山', '库尔勒', '葫芦岛', '张家口', '阿拉善',
             '兴安盟', '石河子', '景德镇', '张家港', '黔东南', '都江堰', '峨眉山', '阿图什', '攀枝花', '日喀则', '老河口', '平顶山', '秦皇岛', '青铜峡', '瓦房店',
             '阿拉尔', '牡丹江', '黔西南', '共青城', '驻马店', '绥芬河', '嘉峪关', '阿勒泰', '大石桥', '神龙架', '牙克石', '马尔康', '铁门关', '格尔木', '扎兰屯',
             '马鞍山', '张家界', '六盘水', '调兵山', '公主岭', '德令哈', '阿克苏', '高碑店', '五家渠', '三门峡', '防城港', '吐鲁番', '双鸭山', '冷水江', '石嘴山',
             '齐哈尔', '丹江口', '满洲里', '阿尔山', '梅河口', '七台河', '连云港', '井冈山', '佳木斯', '霍尔果斯', '海南藏族', '大兴安岭', '呼伦贝尔', '博尔塔拉',
             '香格里拉', '二连浩特', '巴彦淖尔', '霍林郭勒', '乌兰察布', '齐齐哈尔', '阿拉山口', '额尔古纳', '乌兰浩特', '锡林浩特', '可克达拉', '五大连池',
             '锡林郭勒', '西双版纳', '克拉玛依', '巴音郭楞', '鄂尔多斯', '图木舒克', '延边朝鲜族', '锡林郭勒盟', '克孜勒苏柯尔克孜']
        )  # 中小城市
        self.citys = citys  # 全部省和城市
        self.rare_words = []  # 罕见字


def get_name_words():
    with open(NAME_WORDS_FILE_NAME, "rb") as f:
        return load(f)


def update_name_words():
    from collections import defaultdict
    from itertools import islice, chain
    from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_SHIXIN_DB, \
        MONGO_COMPANY_DETAIL_COLLECTIONS, MONGO_COMPANY_DETAIL3_COLLECTIONS, \
        MONGO_SHIXIN_DETAIL_COLLECTIONS, MONGO_ZHIXING_DETAIL_COLLECTIONS, \
        MONGO_P2P_DEADBEAT_COLLECTIONS
    from data_storage.mongo_db import MongoDB

    name_words = get_name_words()
    hanzi_start_ord = ord("\u4E00")
    hanzi_end_ord = ord("\u9FA5")

    first_names = name_words.first_names
    rare_words = set(i for i in name_words.rare_words if hanzi_start_ord <= ord(i) <= hanzi_end_ord)

    long_first_names = [w for w in first_names if len(w) > 1]
    single_first_names = [w for w in first_names if len(w) == 1]

    first_name_stat = defaultdict(int)
    word_stat = defaultdict(int)
    parse_count = 0

    def name_parse(name):
        if not name or len(name) > 6:
            return

        nonlocal parse_count

        parse_count += 1
        first_name = name[0]
        index = 1
        for i in long_first_names:
            if name.startswith(i):
                first_name = i
                index = 2
                break
        else:
            for i in single_first_names:
                if name.startswith(i):
                    first_name = i
                    index = 1
                    break

        if index == 2 or hanzi_start_ord <= ord(first_name) <= hanzi_end_ord:
            first_name_stat[first_name] += 1

        for w in islice(name, index, None):
            if hanzi_start_ord <= ord(w) <= hanzi_end_ord:
                word_stat[w] += 1

    def company_detail(mongo_instance):
        for i in mongo_instance.getAll(fields={"legal_person": 1,
                                               "member_info": 1,
                                               "shareholder_info": 1,
                                               "_id": 0}):
            name_set = set()
            name_set.add(i.get("legal_person"))
            name_set.update(j[0] for j in i.get("member_info", []))
            name_set.update(j[0] for j in i.get("shareholder_info", []))
            for j in name_set:
                name_parse(j)
            del name_set

    def shixin(mongo_instance):
        for item in mongo_instance.getAll(fields={"name": 1, "_id": 0}):
            try:
                name_parse(item["name"])
            except Exception:
                continue

    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL_COLLECTIONS) as mongo_instance:
        company_detail(mongo_instance)
    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL3_COLLECTIONS) as mongo_instance:
        company_detail(mongo_instance)

    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_DETAIL_COLLECTIONS) as mongo_instance:
        shixin(mongo_instance)
    with MongoDB(MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS) as mongo_instance:
        shixin(mongo_instance)
    with MongoDB(MONGO_SHIXIN_DB, MONGO_P2P_DEADBEAT_COLLECTIONS) as mongo_instance:
        shixin(mongo_instance)

    for k in ['钅', "亻", "扌", "犭"]:
        try:
            del first_name_stat[k]
        except Exception:
            pass
        try:
            del word_stat[k]
        except Exception:
            pass
        try:
            rare_words.remove(k)
        except Exception:
            pass

    # print(sorted(first_name_stat.items(), key=itemgetter(1), reverse=True))
    # print(sorted(word_stat.items(), key=itemgetter(1), reverse=True))

    # 处理姓氏
    new_common_first_names = []
    new_rare_first_names = []
    threshold = int(parse_count * 1E-4)
    for i in first_name_stat:
        if first_name_stat[i] > threshold:
            new_common_first_names.append(i)
        else:
            new_rare_first_names.append(i)
    new_rare_first_names.extend(i for i in first_names if i not in first_name_stat and len(i) > 1)

    def _print_words(words_list, stat_dict):
        ret_list = sorted(words_list, key=lambda a: stat_dict[a], reverse=True)
        for word in ret_list:
            print(word, stat_dict[word], sep=":", end=", ")
        print()
        print("".center(100, "-"))
        return ret_list

    new_common_first_names = _print_words(new_common_first_names, first_name_stat)
    new_rare_first_names = _print_words(new_rare_first_names, first_name_stat)

    # 处理名字
    all_first_names = new_common_first_names + new_rare_first_names
    # for i in all_first_names:  # 删除已经存在于姓氏中的字
    #     try:
    #         del word_stat[i]
    #     except Exception:
    #         pass

    new_popular_words = []
    new_common_words = []
    threshold1 = int(parse_count * 1E-4)
    threshold2 = int(parse_count * 4E-6)
    for i in word_stat:
        count = word_stat[i]
        if count > threshold1:
            new_popular_words.append(i)
        elif count > threshold2:
            new_common_words.append(i)
        else:
            rare_words.add(i)

    new_most_words = new_popular_words + new_common_words
    rare_words -= set(chain(all_first_names, new_most_words))
    # rare_words &= word_stat.keys()

    new_popular_words = _print_words(new_popular_words, word_stat)
    new_common_words = _print_words(new_common_words, word_stat)
    new_rare_words = _print_words(rare_words, word_stat)

    name_words.common_first_names = new_common_first_names
    name_words.rare_first_names = new_rare_first_names
    name_words.first_names = all_first_names
    name_words.popular_words = new_popular_words
    name_words.common_words = new_common_words
    name_words.most_words = new_most_words
    name_words.rare_words = new_rare_words

    with open(NAME_WORDS_FILE_NAME, "wb") as f:
        dump(name_words, f)


if __name__ == '__main__':
    update_name_words()
