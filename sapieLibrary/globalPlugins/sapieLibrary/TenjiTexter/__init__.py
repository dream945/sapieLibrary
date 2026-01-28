import os
import sys
import collections

from . import English_Table
from . import Info_Table
from . import Japanese_Table
from . import nabcc


""" DocumentsViewer """

j01 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j01.items()])
j02 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j02.items()])
j03 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j03.items()])
j04 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j04.items()])
j05 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j05.items()])
j06 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j06.items()])
j07 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j07.items()])
j08 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j08.items()])
j09 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j09.items()])
j10 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j10.items()])
j11 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j11.items()])
j12 = collections.OrderedDict([(v, k) for k, v in Japanese_Table.j12.items()])

i01 = collections.OrderedDict([(v, k) for k, v in Info_Table.i01.items()])
i02 = collections.OrderedDict([(v, k) for k, v in Info_Table.i02.items()])
i03 = collections.OrderedDict([(v, k) for k, v in Info_Table.i03.items()])
i04 = collections.OrderedDict([(v, k) for k, v in Info_Table.i04.items()])
i05 = collections.OrderedDict([(v, k) for k, v in Info_Table.i05.items()])
i06 = collections.OrderedDict([(v, k) for k, v in Info_Table.i06.items()])

e01 = collections.OrderedDict([(v, k) for k, v in English_Table.e01.items()])
e02 = collections.OrderedDict([(v, k) for k, v in English_Table.e02.items()])
e03 = collections.OrderedDict([(v, k) for k, v in English_Table.e03.items()])
e04 = collections.OrderedDict([(v, k) for k, v in English_Table.e04.items()])
e05 = collections.OrderedDict([(v, k) for k, v in English_Table.e05.items()])
e06 = collections.OrderedDict([(v, k) for k, v in English_Table.e06.items()])
e07 = collections.OrderedDict([(v, k) for k, v in English_Table.e07.items()])


"""

print("e01",len(e01),len(English_Table.e01))
print("e02",len(e02),len(English_Table.e02))
print("e03",len(e03),len(English_Table.e03))
print("e04",len(e04),len(English_Table.e04))
print("e05",len(e05),len(English_Table.e05))
print("e06",len(e06),len(English_Table.e06))
print("e07",len(e07),len(English_Table.e07))

print("i01",len(i01),len(Info_Table.i01))
print("i02",len(i02),len(Info_Table.i02))
print("i03",len(i03),len(Info_Table.i03))
print("i04",len(i04),len(Info_Table.i04))
print("i05",len(i05),len(Info_Table.i05))
print("i06",len(i06),len(Info_Table.i06))

print("j01",len(j01),len(Japanese_Table.j01))
print("j02",len(j02),len(Japanese_Table.j02))
print("j03",len(j03),len(Japanese_Table.j03))
print("j04",len(j04),len(Japanese_Table.j04))
print("j05",len(j05),len(Japanese_Table.j05))
print("j06",len(j06),len(Japanese_Table.j06))
print("j07",len(j07),len(Japanese_Table.j07))
print("j08",len(j08),len(Japanese_Table.j08))
print("j09",len(j09),len(Japanese_Table.j09))
print("j10",len(j10),len(Japanese_Table.j10))
print("j11",len(j11),len(Japanese_Table.j11))
print("j12",len(j12),len(Japanese_Table.j12))

"""


class DocumentsViewer():

    """ init """

    def __init__(self):
        self.m_Separator = ["⠀", "⠤", "\r", "\n"]
        self.buff = ""

    """ test """

    def test(self):
        for i in English_Table.e01.keys():
            print(i, English_Table.e01[i])
        for i in English_Table.e02.keys():
            print(i, English_Table.e02[i])
        for i in English_Table.e03.keys():
            print(i, English_Table.e03[i])
        for i in English_Table.e04.keys():
            print(i, English_Table.e04[i])
        for i in English_Table.e05.keys():
            print(i, English_Table.e05[i])
        for i in English_Table.e06.keys():
            print(i, English_Table.e06[i])

    """ view """

    def view(self, FileName):
        ret = ""
        ext = os.path.splitext(FileName)[1].upper()
        if ext == ".BES":
            ret = self.op1(FileName)
        elif ext == ".BET":
            ret = self.op1(FileName)
        elif ext == ".BSE":
            ret = self.op2(FileName)
        # print(ret)
        self.buff = ret

    """ .BES """

    def op1(self, FileName):
        with open(FileName, mode='rb') as fin:
            content = fin.read()
        ret = ""
        i = 0
        for i in range(len(content)):
            if i > 1024:
                break
        tenji = bytearray(content[i:])
        tenji = tenji.replace(b'\x0d\xfe', b'\r\n')
        for i in range(2, len(tenji)):
            if tenji[i] == 0xfd:
                tenji[i-2] = 0x0c
                tenji[i-1] = 0x0c
        for i in range(len(tenji)):
            ch = chr(tenji[i] + 0x2800 - 0xa0)
            if tenji[i] == 0x0d:
                ret = "{}\r".format(ret)
            elif tenji[i] == 0x0a:
                ret = "{}\n".format(ret)
            elif tenji[i] == 0xfd:
                ret = "{}\r\n".format(ret)
            elif tenji[i] == 0xfe:
                ret = "{}\r\n".format(ret)
            elif tenji[i] == 0x0c:
                pass
            elif tenji[i] == 0xff:
                pass  # time.sleep(0.001)
            elif '⠀' <= ch and "⠿" >= ch:
                ret = ret + chr(tenji[i] + 0x2800 - 0xa0)
            # else:
            #    ret = "{}<{}>".format(ret , hex(tenji[i]))
        return ret

    """ .BSE """

    def op2(self, FileName):
        ret = ""
        with open(FileName, mode='rb') as fin:
            content = fin.read()
        i = 0
        for i in range(len(content)):
            if i > 512:  # i>1024:
                break
        tenji = bytearray(content[i:])
        for i in range(len(tenji)):
            if tenji[i] == 0xfd:
                ret = ret + "\r\n"
            elif tenji[i] == 0xfe:
                ret = ret + "\r\n"
            elif tenji[i] == 0x0d:
                pass
            elif tenji[i] == 0x0a:
                ret = ret + "\r\n"
            elif tenji[i] == 0xff:
                pass
            else:
                ret = ret + nabcc.table[chr(tenji[i])]
        return ret

    def braille_code(self):
        ret = ""
        for i in range(ord("⠀"), ord("⠿")+1):
            ret = ret+chr(i)
        return ret

    def braille_code_r(self):
        ret = ""
        for i in range(ord("⠿"), ord("⠀"), -1):
            ret = ret+chr(i)
        return ret

    def winbes_code(self):
        ret = ""
        for i in range(ord(' '), ord('_')+1):
            ret = ret+chr(i)
        return ret

    def winbes_code_r(self):
        ret = ""
        for i in range(ord('_'), ord(' '), -1):
            ret = ret+chr(i)
        return ret

    def katakana_code(self):
        ret = ""
        for i in range(ord('ｱ'), ord('ﾝ')+1):
            ret = ret+chr(i)
        return ret

    def katakana_to_hiragana(self, katakana):
        h1 = 'ぁ'
        h2 = 'ん'
        k1 = 'ァ'
        k2 = 'ン'
        ret = ""
        for i in range(len(katakana)):
            if (katakana[i] < k1) or (katakana[i] > k2):
                ret = ret + katakana[i]
            else:
                ret = ret + chr(ord(katakana[i])+(ord(h1)-ord(k1)))
        return ret

    def hiragana_to_katakana(self, hiragana):
        h1 = 'ぁ'
        h2 = 'ん'
        k1 = 'ァ'
        k2 = 'ン'
        ret = ""
        for i in range(len(hiragana)):
            if (hiragana[i] < h1) or (hiragana[i] > h2):
                ret = ret + hiragana[i]
            else:
                ret = ret + chr(ord(hiragana[i])+(ord(k1)-ord(h1)))
        return ret

    def a_to_A(self, al):
        h1 = 'a'
        h2 = 'z'
        k1 = 'A'
        k2 = 'Z'
        ret = ""
        for i in range(len(al)):
            if (al[i] < h1) or (al[i] > h2):
                ret = ret + al[i]
            else:
                ret = ret + chr(ord(al[i])+(ord(k1)-ord(h1)))
        return ret

    def A_to_a(self, Al):
        h1 = 'A'
        h2 = 'Z'
        k1 = 'a'
        k2 = 'z'
        ret = ""
        for i in range(len(Al)):
            if (Al[i] < h1) or (Al[i] > h2):
                ret = ret + Al[i]
            else:
                ret = ret + chr(ord(Al[i])+(ord(k1)-ord(h1)))
        return ret

    def katakana_conv(self):
        pos = 0
        wbuff = ""
        while pos < len(self.buff):
            ch = self.buff[pos]
            if ch == '⠼':
                ret, pos = self.numeric_conv(pos)
                wbuff = wbuff + ret
            elif ch == '⠰':
                if self.buff[pos+1] == '⠄':
                    wbuff = wbuff + "＜"
                    pos = pos+1
                elif self.buff[pos+1] in self.m_Separator:
                    if self.buff[pos+1] == '⠤':
                        wbuff = wbuff + "『"
                        pos = pos+1
                    else:
                        if self.buff[pos] in j01:
                            wbuff = wbuff + j01[self.buff[pos]]
                ret, pos = self.roma_conv(pos)
                wbuff = wbuff + ret
            elif ch == '⠦':
                ret, pos = self.eng_conv(pos, self.buff[pos-1])    # 外国語引用符処理へ
                wbuff = wbuff + ret
                # ret,pos = self.eng_conv2(pos,self.buff[pos-1])  # 外国語引用符処理へ
            elif ch == '⠤':
                if self.buff[pos+1] == '⠆':
                    wbuff = wbuff + "』"
                    pos = pos + 1
                elif self.buff[pos+1] == '⠂':
                    wbuff = wbuff + "】"
                    pos = pos + 1
                else:
                    wbuff = wbuff + j01[self.buff[pos]]
            elif ch == '⠒':
                if self.buff[pos:pos+1] == '⠂':
                    wbuff = wbuff + "ー・"
                    pos = pos + 1
                else:
                    wbuff = wbuff + j01[self.buff[pos]]
            elif ch == '⠲':
                if self.buff[pos:pos+2] in j09:
                    wbuff = wbuff + j09[self.buff[pos:pos+2]]
                    pos = pos + 1
                else:
                    wbuff = wbuff + "。"
            elif ch == '⠢':
                if self.buff[pos:pos+2] in j08:
                    wbuff = wbuff + j08[self.buff[pos:pos+2]]
                    pos = pos + 1
                else:
                    wbuff = wbuff + "？"
            elif ch == '⠸':
                if self.buff[pos:pos+2] in j07:
                    wbuff = wbuff + j07[self.buff[pos:pos+2]]
                    pos = pos + 1
            elif ch == '⠨':
                if self.buff[pos:pos+2] in j06:
                    wbuff = wbuff + j06[self.buff[pos:pos+2]]
                    pos = pos + 1
            elif ch == '⠘':
                if self.buff[pos:pos+2] in j05:
                    wbuff = wbuff + j05[self.buff[pos:pos+2]]
                    pos = pos + 1
            elif ch == '⠈':
                if self.buff[pos:pos+2] in j04:
                    wbuff = wbuff + j04[self.buff[pos:pos+2]]
                    pos = pos + 1
            elif ch == '⠠':
                if self.buff[pos+1] == '⠦':
                    ret, pos = self.info_conv(pos)
                    wbuff = wbuff + ret
                elif self.buff[pos+1] == '⠆':
                    wbuff = wbuff + "＞"
                    pos = pos + 1
                elif self.buff[pos:pos+2] in j03:
                    wbuff = wbuff + j03[self.buff[pos:pos+2]]
                    pos = pos + 1
            elif ch == '⠐':
                if self.buff[pos:pos+2] in j02:
                    wbuff = wbuff + j02[self.buff[pos:pos+2]]
                    pos = pos + 1
                else:
                    wbuff = wbuff + "ッ"
            elif self.buff[pos] in j01:
                wbuff = wbuff + j01[self.buff[pos]]
            else:
                wbuff = wbuff + self.buff[pos]
            pos = pos + 1
        return wbuff

    def numeric_conv(self, pos):
        wbuff = ""
        pos = pos+1
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            if ch == '⠼':
                wbuff = wbuff + "、"
                break
            if self.buff[pos] == "\r":
                pos = pos + 1
                wbuff = wbuff + "\r\n"
                return wbuff, pos
            if self.buff[pos] not in j10:
                pos = pos - 1
                return wbuff, pos
            else:
                wbuff = wbuff + j10[self.buff[pos]]
            pos = pos + 1
        return wbuff, pos

    def numeric2_conv(self, pos):
        wbuff = ""
        f_hankaku = True
        pos = pos + 1
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            # 数符がきた場合の処理
            if ch == '⠼':
                if f_hankaku:
                    wbuff = wbuff + ","     # カンマを出力
                else:
                    wbuff = wbuff + "、"    # カンマを出力
            else:
                if self.buff[pos] == "\r":
                    pos = pos + 1
                    wbuff = wbuff+"\r\n"
                    return wbuff, pos
                elif self.buff[pos] not in i03:
                    pos = pos - 1
                    return wbuff, pos
                if f_hankaku:
                    if self.buff[pos] in i03:
                        wbuff = wbuff + i03[self.buff[pos]]
                else:
                    if self.buff[pos] in j10:
                        wbuff = wbuff + j10[self.buff[pos]]
            pos = pos + 1
        return wbuff, pos

    def roma_conv(self, pos):
        wbuff = ""
        f_oomoji = 0
        pos = pos + 1
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            if ch == '⠠':
                if self.buff[pos+1] == '⠠':
                    f_oomoji = 1
                elif f_oomoji != 1:
                    f_oomoji = 2
            else:
                if self.buff[pos] not in j11:
                    pos = pos - 1
                    return wbuff, pos
                if f_oomoji == 0:
                    if self.buff[pos] in j12:
                        wbuff = wbuff + j12[self.buff[pos]]
                elif f_oomoji == 1:
                    if self.buff[pos] in j11:
                        wbuff = wbuff + j11[self.buff[pos]]
                elif f_oomoji == 2:
                    if self.buff[pos] in j11:
                        wbuff = wbuff + j11[self.buff[pos]]
                    f_oomoji = 0
            pos = pos + 1
        return wbuff, pos

    def info_conv(self, pos):
        wbuff = ""
        f_oomoji = 0
        pos = pos + 1  # ヘッダーコード分進める。
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            if ch == '⠠':
                if self.buff[pos+1] == '⠴':
                    pos = pos + 1
                    wbuff = wbuff + ")"
                    return wbuff, pos
                elif self.buff[pos+1] == '⠠':
                    f_oomoji = 1    # 大文字連続
                elif f_oomoji != 1:
                    f_oomoji = 2    # 大文字単独フラグ
                elif self.buff[pos+1] == '⠨':
                    f_oomoji = 3    # カナフラグ
            elif ch == '⠼':
                ret, pos = self.numeric2_conv(pos)
                wbuff = wbuff + ret
            else:
                if f_oomoji == 0:
                    x = pos
                    # for x in range(pos,len(self.buff)):
                    while(x < len(self.buff)):
                        if self.buff[x:x+1] == "⠠⠴":
                            pos = x - 1
                            # break
                        elif self.buff[x] == '⠴':
                            wbuff = wbuff + i02[self.buff[x]]
                            x = x + 1
                            pos = x
                            return wbuff, pos
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                            x = x + 1
                        elif self.buff[x:x+2] in i02:
                            wbuff = wbuff + i02[self.buff[x:x+2]]  # '⠂'
                            x = x + 2
                        elif self.buff[x:x+1] in i02:
                            wbuff = wbuff + i02[self.buff[x:x+1]]  # '⠂'
                            x = x + 1
                        elif self.buff[x] in i02:
                            wbuff = wbuff + i02[self.buff[x]]
                        else:
                            pos = x
                            break
                        pos = x

                elif f_oomoji == 1:
                    x = pos
                    # for x in range(pos,len(self.buff)):
                    while(x < len(self.buff)):
                        if self.buff[x:x+1] == "⠠⠴":
                            pos = x - 1
                            break
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                        elif self.buff[x:x+1] in i01:
                            wbuff = wbuff + i01[self.buff[x:x+1]]
                            x = x + 1
                        elif self.buff[x] in i01:
                            wbuff = wbuff + i01[self.buff[x]]
                        else:
                            pos = x
                            break
                        pos = x

                elif f_oomoji == 2:
                    x = pos
                    # for x in range(pos,len(self.buff)):
                    while(x < len(self.buff)):
                        if self.buff[x:x+1] == "⠠⠴":
                            pos = x - 1
                            break
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                        elif self.buff[x:x+1] in i01:
                            wbuff = wbuff + i01[self.buff[x:x+1]]
                            x = x + 1
                        elif self.buff[x] in i01:
                            wbuff = wbuff + i01[self.buff[x]]
                        else:
                            pos = x
                            break
                        pos = x
                        break  # 1回のみ
                    f_oomoji = 0
                elif f_oomoji == 3:
                    f_oomoji = 0
            pos = pos + 1
        return wbuff, pos

    def eng_conv(self, pos, s_c):
        wbuff = ""
        f_oomoji = 0
        xxx = "⠴"
        if s_c in j01:
            ch = j01[s_c]
            if ch == "＿":
                xxx = xxx + s_c
            elif ch == "｜":
                xxx = xxx + s_c
            elif ch == "　":
                xxx = xxx + s_c
        pos = pos + 1
        wbuff = wbuff + "￣"
        if self.buff[pos:pos+1] == "⠠⠠":
            f_oomoji = 1
            pos = pos + 2
        elif self.buff[pos] == "⠠":
            f_oomoji = 2
            pos = pos + 1
        else:
            f_oomoji = 0
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            if ch == '⠴':
                if self.buff[pos:pos+len(xxx)] == xxx:
                    wbuff = wbuff + "￣"
                    return wbuff, pos
                elif self.buff[pos:pos+len(xxx)] == "⠴⠀":
                    wbuff = wbuff + "￣"
                    return wbuff, pos
                elif self.buff[pos:pos+len(xxx)] == "⠴\n":
                    wbuff = wbuff + "￣"
                    return wbuff, pos
                elif self.buff[pos:pos+len(xxx)] == "⠴\r":
                    wbuff = wbuff + "￣"
                    return wbuff, pos
                elif self.buff[pos:pos+len(xxx)] == "⠴⠤":
                    wbuff = wbuff + "￣"
                    return wbuff, pos
            else:
                if f_oomoji == 0:
                    x = pos
                    while(x < len(self.buff)):
                        if self.buff[x:x+len(xxx)] == xxx:
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:pos+len(xxx)] == "⠴⠀":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\n":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\r":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴⠤":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos

                        if self.buff[x:x+1] == "⠠⠠":
                            f_oomoji = 1  # 大文字連続
                            x = x + 1
                            pos = x
                            break
                        elif self.buff[x] == "⠠":
                            f_oomoji = 2     # 大文字単独フラグ
                            pos = x
                            break
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                        elif self.buff[x] in e03:
                            wbuff = wbuff + e03[self.buff[x]]
                        elif self.buff[x] in e02:
                            wbuff = wbuff + e02[self.buff[x]]
                        x = x + 1
                        pos = x
                        # break #1回のみ
                elif f_oomoji == 1:
                    x = pos
                    while(x < len(self.buff)):
                        if self.buff[x:x+len(xxx)] == xxx:
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴⠀":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\n":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\r":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴⠤":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos

                        if self.buff[x:x+1] == "⠠⠠":
                            f_oomoji = 1  # 大文字連続
                            x = x + 1
                            pos = x
                            break
                        elif self.buff[x] == "⠠":
                            f_oomoji = 2     # 大文字単独フラグ
                            pos = x
                            break
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                        elif self.buff[x] in e03:
                            wbuff = wbuff + e03[self.buff[x]]
                        elif self.buff[x] in e01:
                            wbuff = wbuff + e01[self.buff[x]]
                        f_oomoji = 0
                        x = x + 1
                        pos = x
                        # break # 一回のみ。
                elif f_oomoji == 2:
                    x = pos
                    while(x < len(self.buff)):
                        if self.buff[x:x+len(xxx)] == xxx:
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴⠀":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\n":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴\r":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos
                        elif self.buff[x:x+len(xxx)] == "⠴⠤":
                            pos = x
                            wbuff = wbuff + "￣"
                            return wbuff, pos

                        if self.buff[x:x+1] == "⠠⠠":
                            f_oomoji = 1  # 大文字連続
                            x = x + 1
                            pos = x
                            break
                        elif self.buff[x] == "⠠":
                            f_oomoji = 2     # 大文字単独フラグ
                            pos = x
                            break
                        elif self.buff[x] == "⠼":
                            ret, x = self.numeric2_conv(x)
                            wbuff = wbuff + ret
                        elif self.buff[x] in e03:
                            wbuff = wbuff + e03[self.buff[x]]
                        elif self.buff[x] in e01:
                            wbuff = wbuff + e01[self.buff[x]]
                        f_oomoji = 0
                        pos = x
                        break  # 一回のみ。
                else:
                    f_oomoji = 0
                # break
            pos = pos + 1
        return wbuff, pos

    def eng_conv2(self, pos, s_c):
        wbuff = ""
        wbuff = wbuff + "＜ここは英文点字です。>￣"
        xxx = "⠴"
        if s_c in j01:
            ch = j01[s_c]
            if ch == "＿":
                xxx = xxx + s_c
            elif ch == "｜":
                xxx = xxx + s_c
            elif ch == "　":
                xxx = xxx + s_c
        while(pos < len(self.buff)):
            ch = self.buff[pos]
            if ch == '⠴':
                if self.buff[pos:pos+len(xxx)] == xxx:
                    wbuff = wbuff + "￣"
                    return wbuff, pos
                break
            else:
                break
            pos = pos + 1
        return wbuff, pos

    def Cxx(self, cbuff):
        Dc_1 = "ッッ"
        Dc_2 = "……"
        tenji = cbuff.replace(Dc_1, Dc_2)
        Dc_1 = "…ッ"
        tenji = tenji.replace(Dc_1, Dc_2)
        return tenji
        """
        wstring CBraille::Cxx(wstring cbuff)
        {
            size_t  pos=0;
            wstring Dc_1 = L"ッッ";
            wstring Dc_2 = L"……";
            while((pos = cbuff.find(Dc_1.c_str(),pos))!=std::wstring::npos)
            {
                cbuff.replace(pos, Dc_1.length(),Dc_2);
            }
            Dc_1 = L"…ッ";
            pos=0;
            while((pos = cbuff.find(Dc_1.c_str(),pos))!=std::wstring::npos)
            {
                cbuff.replace(pos, Dc_1.length(),Dc_2);
            }
            return cbuff;
        }
        """

    def Cxx2(self, cbuff):
        Dc_1 = "\r\n"
        Dc_2 = "\n"
        tenji = cbuff.replace(Dc_1, Dc_2)
        return tenji
        """
        wstring CBraille::Cxx2(wstring cbuff)
        {
            size_t  pos=0;
            std::wstring Dc_1 = L"\r\n";
            std::wstring Dc_2 = L"\n";
            while((pos = cbuff.find(Dc_1.c_str(),pos))!=std::wstring::npos)
                cbuff.replace(pos, Dc_1.length(),Dc_2);
            return cbuff;
        }
        """

    def Cxx3(self, cbuff):
        Dc_1 = "\n\n"
        Dc_2 = "\n　　　\n"
        tenji = cbuff.replace(Dc_1, Dc_2)
        return tenji
        """
        wstring CBraille::Cxx3(wstring cbuff)
        {
            size_t  pos=0;
            wstring Dc_1 = L"\n\n";
            wstring Dc_2 = L"\n　　　\n";
            while((pos = cbuff.find(Dc_1.c_str(),pos))!=std::wstring::npos)
                cbuff.replace(pos, Dc_1.length(),Dc_2);
            return cbuff;
        }
        """


""" main """


def main():
    p_dv = DocumentsViewer()
    """
    p_dv.view('ReadMe.BES')
    p_dv.view('all_of_me.bse')
    print(p_dv.braille_code())
    print(p_dv.braille_code_r())
    print(p_dv.winbes_code())
    print(p_dv.winbes_code_r())
    print(p_dv.katakana_code())
    print(p_dv.katakana_to_hiragana("アイウa"))
    print(p_dv.hiragana_to_katakana("あいうa"))
    print(p_dv.a_to_A("abcあ"))
    print(p_dv.A_to_a("ABCあ"))
    """
    p_dv.view('ReadMe.BES')
    #p_dv.view(
    #    'C:\\Users\\ukai\\Documents\\サピエ書庫\\Ｐｙｔｈｏｎ入門B3401R03517855\\N0480682-002.BES')
    # p_dv.katakana_conv()
    ret = p_dv.katakana_conv()
    ret = p_dv.Cxx(ret)
    ret = p_dv.Cxx2(ret)
    ret = p_dv.Cxx3(ret)
    print(ret)
    # print(p_dv.buff)
    #p_dv.buff=""
    #for k, v in Japanese_Table.j09.items():
    #    p_dv.buff = p_dv.buff + v
    #print(p_dv.katakana_conv())

    del p_dv


""" main """
if __name__ == '__main__':
    main()
